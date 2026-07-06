"""
DAF OS Quest81 — CEO Decision Center サービス

CEO Inbox（Quest80）はAI会社からの提案を1箇所に集約するところまでだった。
このサービスは、CEOがそれぞれの提案に対して approve / hold / reject の
判断を記録できる「決裁ログ」を提供する。

v1のスコープ（あえてシンプルにする）：
- Markdownベースの決裁ログを残すことが目的。GitHub Issue化・Memoryへの自動反映・
  実際の承認センター（outputs/approvals/）との自動連携は行わない。
- LLMは使わない、読み書きのみの決定的な処理。
- 「AI会社が提案 → CEOが判断 → 判断履歴を保存」までを完成させる。

対象アイテム（source_type）：
- autonomous_issue:  Quest79で生成された改善Issue案
- pending_approval:  既存の承認待ちIssue（outputs/approvals/pending/）
- memory_update:      Memory Update Suggestions
- kpi_alert:          重大なKPIアラートそのものへの判断
- self_improvement:   Quest85で生成されたSelf Improvement Suggestions
- other:              将来拡張用

判断（decision）の意味：
- approve: 次のアクションへ進める（例：正式Issue化・Memoryへ反映）
- hold:    保留（情報不足・タイミング待ち）
- reject:  今回は採用しない

ディレクトリ構造:
  outputs/decisions/approved/  承認した判断の記録
  outputs/decisions/on_hold/   保留した判断の記録
  outputs/decisions/rejected/  却下した判断の記録

必要な関数：
- record_decision():                1件の判断をMarkdownファイルとして記録する
- get_decision_history():           記録済みの判断履歴を一覧として返す
- generate_decision_log_summary():  AI会議・CEO Inboxへ注入する短いMarkdown要約を返す
- generate_ceo_decision_summary():  generate_decision_log_summary()の薄いラッパー
                                     （Memory Context注入用の正式名。Quest81追加修正）

CLI:
  python services/decision_center_service.py record <source_type> <item_id> <decision> [理由]
  python services/decision_center_service.py list

ファイル未存在・ディレクトリ未存在・パース失敗のいずれでも例外を投げず、
DAF OS全体を止めない。
"""

import re
import sys
from datetime import datetime
from pathlib import Path

# `python services/decision_center_service.py ...` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/approval_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"
_DECISIONS_DIR_NAME = "decisions"

_SOURCE_TYPES = frozenset({
    "autonomous_issue",
    "pending_approval",
    "memory_update",
    "kpi_alert",
    "self_improvement",
    "other",
})

# decision（CEOの入力語）→ 保存先フォルダ名。approved/on_hold/rejectedの
# 3フォルダに対応させる。
_DECISION_DIRS = {
    "approve": "approved",
    "approved": "approved",
    "hold": "on_hold",
    "on_hold": "on_hold",
    "reject": "rejected",
    "rejected": "rejected",
}

_NO_DECISIONS_SUMMARY = "## Decision Log Summary\n\n現在、記録されたCEOの判断はありません。"


def _decisions_dir(outputs_dir: Path) -> Path:
    return outputs_dir / _DECISIONS_DIR_NAME


def _sanitize(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z一-龥ぁ-んァ-ン_-]+", "_", value.strip())
    return value.strip("_")[:60] or "item"


def record_decision(
    source_type: str,
    item_id: str,
    title: str,
    decision: str,
    reason: str | None = None,
    outputs_dir: Path | None = None,
) -> Path | None:
    """
    1件の提案に対するCEOの判断（approve / hold / reject）をMarkdownファイルとして
    outputs/decisions/{approved,on_hold,rejected}/ に記録する。

    引数:
        source_type: "autonomous_issue" | "pending_approval" | "memory_update" |
                      "kpi_alert" | "other"
        item_id:     判断対象を識別する文字列（例：approval_id、KPI名など）
        title:       判断対象のタイトル・内容
        decision:    "approve" | "hold" | "reject"（"approved"/"on_hold"/"rejected"も可）
        reason:      判断理由（任意）

    戻り値: 保存したファイルのPath。source_type・decisionが不正、または
    書き込みに失敗した場合はNoneを返す（例外を投げず、DAF OS全体を止めない）。
    """
    try:
        if source_type not in _SOURCE_TYPES:
            print(f"[警告] 不正なsource_typeです：{source_type}")
            return None

        decision_key = (decision or "").strip().lower()
        folder = _DECISION_DIRS.get(decision_key)
        if not folder:
            print(f"[警告] 不正なdecisionです：{decision}")
            return None

        base = outputs_dir or _OUTPUTS_DIR
        target_dir = _decisions_dir(base) / folder
        target_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        stem = f"{now.strftime('%Y-%m-%d_%H%M%S')}_{source_type}_{_sanitize(item_id)}"
        path = target_dir / f"{stem}.md"
        suffix = 2
        while path.exists():
            path = target_dir / f"{stem}_{suffix}.md"
            suffix += 1

        decided_at = now.strftime("%Y-%m-%d %H:%M")
        lines = [
            "---",
            f"source_type: {source_type}",
            f"item_id: {item_id}",
            f"title: {title}",
            f"decision: {folder}",
            f"reason: {reason or '（理由なし）'}",
            f"decided_at: {decided_at}",
            "---",
            "",
            f"# CEO Decision: {title}",
            "",
            f"- Source Type: {source_type}",
            f"- Item ID: {item_id}",
            f"- Decision: {folder}",
            f"- Reason: {reason or '（理由なし）'}",
            f"- Decided At: {decided_at}",
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
    except Exception as e:
        print(f"[警告] CEO Decisionの記録に失敗しました：{e}")
        return None


def _parse_decision_file(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
        fm_match = re.search(r"^---\n([\s\S]*?)\n---", text)
        if not fm_match:
            return None
        fm = fm_match.group(1)

        def _field(key: str) -> str | None:
            m = re.search(rf"^{re.escape(key)}:\s*(.+)$", fm, re.MULTILINE)
            return m.group(1).strip() if m else None

        return {
            "source_type": _field("source_type"),
            "item_id": _field("item_id"),
            "title": _field("title"),
            "decision": _field("decision"),
            "reason": _field("reason"),
            "decided_at": _field("decided_at"),
            "path": str(path),
        }
    except Exception:
        return None


def get_decision_history(
    outputs_dir: Path | None = None,
    source_type: str | None = None,
) -> list[dict]:
    """
    outputs/decisions/{approved,on_hold,rejected}/ 配下の全記録を読み込み、
    decided_atの新しい順に一覧として返す。source_typeを指定するとその種類のみに絞る。
    ディレクトリ未存在・ファイル無し・パース失敗のいずれでも例外を投げず、空リストを返す。
    """
    try:
        base = outputs_dir or _OUTPUTS_DIR
        decisions_dir = _decisions_dir(base)
        if not decisions_dir.exists():
            return []

        records = []
        for folder in ("approved", "on_hold", "rejected"):
            folder_path = decisions_dir / folder
            if not folder_path.exists():
                continue
            for file_path in folder_path.glob("*.md"):
                record = _parse_decision_file(file_path)
                if record:
                    records.append(record)

        if source_type:
            records = [r for r in records if r.get("source_type") == source_type]

        records.sort(key=lambda r: r.get("decided_at") or "", reverse=True)
        return records
    except Exception as e:
        print(f"[警告] Decision Historyの読み込みに失敗しました：{e}")
        return []


def generate_decision_log_summary(outputs_dir: Path | None = None, limit: int = 10) -> str:
    """
    get_decision_history() の結果をAI会議・CEO Inboxへ注入する短いMarkdown要約に整形する。
    直近limit件のみ表示する。記録が1件も無い場合は
    「現在、記録されたCEOの判断はありません。」を返す。例外を投げない。
    """
    try:
        records = get_decision_history(outputs_dir=outputs_dir)
        if not records:
            return _NO_DECISIONS_SUMMARY

        lines = ["## Decision Log Summary", ""]
        for r in records[:limit]:
            decision_label = (r.get("decision") or "").upper()
            title = r.get("title") or r.get("item_id") or "（無題）"
            decided_at = r.get("decided_at") or "不明"
            source_type = r.get("source_type") or "other"
            lines.append(f"- [{decision_label}] {title}（{source_type} / {decided_at}）")

        return "\n".join(lines).rstrip()
    except Exception as e:
        print(f"[警告] Decision Log Summaryの生成に失敗しました：{e}")
        return _NO_DECISIONS_SUMMARY


def generate_ceo_decision_summary(outputs_dir: Path | None = None, limit: int = 10) -> str:
    """
    generate_decision_log_summary() の薄いラッパー。Memory Context注入用の
    正式名として追加した（Quest81追加修正）。generate_decision_log_summary()自体は
    そのまま残し、既存の呼び出し箇所（CLIなど）に影響を与えない。
    Memory Context側の見出しは「## CEO Decision Summary」に統一するため、
    generate_decision_log_summary()側の見出し（## Decision Log Summary）だけ
    差し替える。
    """
    try:
        body = generate_decision_log_summary(outputs_dir=outputs_dir, limit=limit)
        return body.replace("## Decision Log Summary", "## CEO Decision Summary", 1)
    except Exception:
        return "## CEO Decision Summary\n\n現在、記録されたCEOの判断はありません。"


def _cli_record(args: list[str]) -> None:
    if len(args) < 3:
        print("使い方: python services/decision_center_service.py record <source_type> <item_id> <decision> [理由]")
        return
    source_type, item_id, decision = args[0], args[1], args[2]
    reason = " ".join(args[3:]) if len(args) > 3 else None
    path = record_decision(source_type, item_id, item_id, decision, reason=reason)
    if path:
        print(f"[Decision Center] 記録しました：{path}")
    else:
        print("[Decision Center] 記録に失敗しました（source_type/decisionを確認してください）。")


if __name__ == "__main__":
    # Quest81: CLI導線。
    #   python services/decision_center_service.py record <source_type> <item_id> <decision> [理由]
    #   python services/decision_center_service.py list
    argv = sys.argv[1:]
    if argv and argv[0] == "record":
        _cli_record(argv[1:])
    else:
        print(generate_decision_log_summary())
