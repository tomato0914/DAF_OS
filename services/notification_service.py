"""
DAF OS v1.2 — Mac 通知サービス
osascript を使って通知センターに結果を表示する。
失敗してもエラー停止しない。
"""

import re
import subprocess
from pathlib import Path


def _extract_actions(dashboard_text: str) -> list[str]:
    m = re.search(r"## 3\. 次にCEOがやること\s*\n([\s\S]*?)(?=\n## |\Z)", dashboard_text)
    if not m:
        return []
    actions = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if re.match(r"\d+\.", line):
            clean = re.sub(r"^\d+\.\s*\*?\*?", "", line).replace("**", "").strip()
            # Issue番号だけ残してタイトルを短縮
            clean = re.sub(r"（担当:.+）", "", clean).strip()
            actions.append(clean)
    return actions[:2]


def _extract_ceo_brief_actions(outputs: Path, limit: int = 3) -> list[str]:
    """
    CEOデイリーブリーフ（v2.4）の「📋 今日やること」を通知用に抽出する。
    ceo_brief.md が無い・壊れている場合は空リストを返し、呼び出し側で従来のフォールバックへ委ねる。
    """
    try:
        path = outputs / "ceo_brief.md"
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8")
        m = re.search(r"## 📋 今日やること（3つまで）\s*\n([\s\S]*?)(?=\n## |\Z)", text)
        if not m:
            return []
        actions = []
        for line in m.group(1).splitlines():
            line = line.strip()
            if re.match(r"\d+\.", line):
                clean = re.sub(r"^\d+\.\s*", "", line).replace("`", "").strip()
                actions.append(clean)
        return actions[:limit]
    except Exception:
        return []


def _osa_escape(text: str) -> str:
    """AppleScript 文字列内でのエスケープ（ダブルクォート・バックスラッシュ）。"""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def notify(
    outputs: Path,
    issue_count: int = 0,
) -> bool:
    """
    Mac 通知センターに DAF OS の実行結果を表示する。
    戻り値: 通知成功なら True。
    """
    dashboard_path = outputs / "dashboard.md"

    # 今日やることTOP3（CEOデイリーブリーフ優先。無ければ従来のダッシュボード抽出にフォールバック）
    actions: list[str] = _extract_ceo_brief_actions(outputs)
    if not actions and dashboard_path.exists():
        actions = _extract_actions(dashboard_path.read_text(encoding="utf-8"))

    # 通知本文を組み立て
    lines = [f"Issue {issue_count}件を生成しました。"]
    if actions:
        lines.append("今日やることTOP3:" if len(actions) > 1 else "今日やること:")
        for a in actions:
            lines.append(f"• {a}")
    lines.append(f"📋 {dashboard_path}")

    title   = "DAF OS 実行完了"
    message = "\n".join(lines)

    script = (
        f'display notification "{_osa_escape(message)}" '
        f'with title "{_osa_escape(title)}" '
        f'sound name "Glass"'
    )

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print("[通知] Mac通知を送信しました")
            return True
        else:
            print(f"[通知] osascript エラー: {result.stderr.strip()}")
            return False
    except FileNotFoundError:
        print("[通知] osascript が見つかりません（Mac以外の環境）→ スキップ")
        return False
    except subprocess.TimeoutExpired:
        print("[通知] osascript タイムアウト → スキップ")
        return False
    except Exception as e:
        print(f"[通知] 通知送信に失敗しました: {e} → スキップ")
        return False
