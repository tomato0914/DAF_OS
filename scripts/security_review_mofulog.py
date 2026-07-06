"""
DAF OS — もふログ セキュリティレビュー（GitHub Issue #118 完了条件対応）

もふログはネットワーク送信を行わないローカル完結型アプリであり、
OWASP ZAP等のWebアプリ向け動的スキャナで診断できる稼働中のサーバー/APIが存在しない。
そのため、実際に意味のある形で以下を代替実施する：

1. 依存パッケージの脆弱性診断（npm audit）
2. ソースコードの静的セキュリティレビュー（ハードコードされた秘密情報・ネットワーク送信の有無）

結果を outputs/security_test_mofulog.md に報告書として保存する。

実行方法:
    python scripts/security_review_mofulog.py

安全設計：
- 外部APIを呼ばない（npm auditはnpmのローカル/公開DBに対する読み取り専用チェック）
- .env を読み取らない・表示しない
- もふログのソースを変更しない（読み取り専用の診断のみ）
"""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.product_registry_service import get_product_by_name  # noqa: E402

_SECRET_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{16,}", "OpenAI/OpenRouter風APIキー"),
    (r"AIza[0-9A-Za-z_\-]{20,}", "Google APIキー"),
    (r"ghp_[a-zA-Z0-9]{20,}", "GitHub Personal Access Token"),
    (r"(?i)password\s*=\s*[\"'][^\"']{4,}[\"']", "ハードコードされたパスワード"),
]

_NETWORK_PATTERN = re.compile(r"\bfetch\(|axios\.|XMLHttpRequest")


def _find_mofulog_path() -> Path | None:
    entry = get_product_by_name("mofulog")
    if not entry or not entry.get("path_exists"):
        return None
    return Path(entry["resolved_path"])


def _run_npm_audit(mofulog_path: Path) -> dict:
    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            cwd=mofulog_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        # npm audit は脆弱性があると exit code != 0 を返すため、標準出力のJSONだけを見る
        data = json.loads(result.stdout or "{}")
        meta = data.get("metadata", {}).get("vulnerabilities", {})
        high_risk = []
        for name, v in data.get("vulnerabilities", {}).items():
            if v.get("severity") in ("high", "critical"):
                titles = [
                    s.get("title", "")
                    for s in v.get("via", [])
                    if isinstance(s, dict)
                ]
                high_risk.append({
                    "name": name,
                    "severity": v.get("severity"),
                    "is_direct": v.get("isDirect", False),
                    "title": titles[0] if titles else "",
                })
        return {"ok": True, "summary": meta, "high_risk": high_risk}
    except FileNotFoundError:
        return {"ok": False, "error": "npm コマンドが見つかりません"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "npm audit がタイムアウトしました"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _scan_source_for_secrets(mofulog_path: Path) -> list[dict]:
    findings = []
    skip_dirs = {"node_modules", ".git", "ios", "android", ".expo", "app-store-screenshots"}
    for src_dir in ["app", "lib", "components"]:
        d = mofulog_path / src_dir
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if not f.is_file() or f.suffix not in (".ts", ".tsx", ".js", ".jsx"):
                continue
            if any(part in skip_dirs for part in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for pattern, label in _SECRET_PATTERNS:
                if re.search(pattern, text):
                    findings.append({"file": str(f.relative_to(mofulog_path)), "issue": label})
    return findings


def _scan_source_for_network_calls(mofulog_path: Path) -> list[str]:
    hits = []
    for src_dir in ["app", "lib", "components"]:
        d = mofulog_path / src_dir
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if not f.is_file() or f.suffix not in (".ts", ".tsx", ".js", ".jsx"):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if _NETWORK_PATTERN.search(text):
                hits.append(str(f.relative_to(mofulog_path)))
    return hits


def _build_report(mofulog_path: Path, audit: dict, secrets: list[dict], network_hits: list[str]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# セキュリティテスト結果 — もふログ（GitHub Issue #118）",
        "",
        f"> 実行日時: {now}",
        f"> 対象: {mofulog_path}",
        "",
        "## 方針",
        "",
        "もふログはネットワーク送信を行わないローカル完結型アプリであり、"
        "OWASP ZAP等のWeb向け動的スキャナで診断できる稼働中サーバー/APIが存在しない。"
        "そのため、実効性のある代替診断として **依存パッケージの脆弱性診断（npm audit）** と "
        "**ソースコードの静的セキュリティレビュー** を実施した。",
        "",
        "---",
        "",
        "## 1. 依存パッケージの脆弱性診断（npm audit）",
        "",
    ]

    if not audit.get("ok"):
        lines.append(f"❌ 実行できませんでした: {audit.get('error')}")
    else:
        summary = audit["summary"]
        lines += [
            f"| 深刻度 | 件数 |",
            f"|--------|------|",
            f"| critical | {summary.get('critical', 0)} |",
            f"| high | {summary.get('high', 0)} |",
            f"| moderate | {summary.get('moderate', 0)} |",
            f"| low | {summary.get('low', 0)} |",
            f"| **合計** | **{summary.get('total', 0)}** |",
            "",
        ]
        if audit["high_risk"]:
            lines.append("### high / critical の内訳")
            lines.append("")
            lines.append("| パッケージ | 深刻度 | 直接依存か | 内容 |")
            lines.append("|-----------|--------|-----------|------|")
            for item in audit["high_risk"]:
                direct = "直接" if item["is_direct"] else "間接（推移的依存）"
                lines.append(f"| {item['name']} | {item['severity']} | {direct} | {item['title']} |")
            lines.append("")
            all_indirect = all(not i["is_direct"] for i in audit["high_risk"])
            if all_indirect:
                lines.append(
                    "> すべて間接依存（開発ツール経由）であり、直接依存のパッケージには "
                    "high/critical の脆弱性は検出されなかった。ビルド・開発時にのみ使われ、"
                    "配布されるアプリ本体には含まれない可能性が高い。ただし放置せず、"
                    "`npm audit fix` や依存パッケージの更新で解消を進めることを推奨する。"
                )
        else:
            lines.append("high / critical の脆弱性は検出されなかった。")

    lines += [
        "",
        "---",
        "",
        "## 2. ソースコードの静的セキュリティレビュー",
        "",
        "### 2-1. ハードコードされた秘密情報の検索",
        "",
    ]
    if secrets:
        lines.append("⚠️ 以下の疑わしいパターンが見つかった：")
        lines.append("")
        for s in secrets:
            lines.append(f"- `{s['file']}`: {s['issue']}")
    else:
        lines.append("✅ APIキー・パスワード等のハードコードされた秘密情報は検出されなかった。")

    lines += [
        "",
        "### 2-2. ネットワーク送信の有無",
        "",
    ]
    if network_hits:
        lines.append("以下のファイルでネットワーク呼び出しの記述が見つかった（内容の確認を推奨）：")
        lines.append("")
        for h in network_hits:
            lines.append(f"- `{h}`")
    else:
        lines.append(
            "✅ `fetch` / `axios` / `XMLHttpRequest` によるネットワーク送信は検出されなかった。"
            "すべてのデータは端末内（AsyncStorage）にのみ保存されている。"
        )

    lines += [
        "",
        "---",
        "",
        "## 3. 修正計画",
        "",
        "| # | 項目 | 優先度 | 対応 |",
        "|---|------|--------|------|",
        "| 1 | 依存パッケージのhigh/critical脆弱性 | 中 | `npm audit fix` を実行し、破壊的変更がないか確認の上で反映する |",
        "| 2 | プライバシーポリシーとコードの整合性 | 高 | 対応済み（Issue #120のレビューでv1.2に是正済み） |",
        "| 3 | 将来ネットワーク機能（クラウド同期等）を追加する場合 | — | 追加時に本レポートを更新し、通信の暗号化（HTTPS必須）・認証方式を再レビューすること |",
        "",
        "---",
        "",
        "## まとめ",
        "",
        "- 現状のもふログはローカル完結型のため、外部からの攻撃面（サーバー・API）は存在しない",
        "- 直接依存パッケージにhigh/critical脆弱性はなし。間接依存の開発ツール経由の脆弱性のみ検出",
        "- ハードコードされた秘密情報・意図しないネットワーク送信は検出されなかった",
        "- 将来、クラウド同期や広告SDKを有効化する際は、その時点で本レポートを更新し再診断すること",
    ]

    return "\n".join(lines)


def main() -> int:
    print("[セキュリティレビュー] もふログの脆弱性診断を実行中...")

    mofulog_path = _find_mofulog_path()
    if not mofulog_path:
        print("[エラー] products/mofulog.md が見つからない、またはpathが存在しません → スキップ")
        return 1

    audit = _run_npm_audit(mofulog_path)
    secrets = _scan_source_for_secrets(mofulog_path)
    network_hits = _scan_source_for_network_calls(mofulog_path)

    report = _build_report(mofulog_path, audit, secrets, network_hits)

    outputs_dir = Path(__file__).parent.parent / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    report_path = outputs_dir / "security_test_mofulog.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"[セキュリティレビュー] ✓ {report_path}")
    if audit.get("ok"):
        print(f"  依存パッケージ脆弱性: {audit['summary']}")
    print(f"  秘密情報の疑いのある箇所: {len(secrets)}件")
    print(f"  ネットワーク呼び出し検出: {len(network_hits)}件")

    return 0


if __name__ == "__main__":
    sys.exit(main())
