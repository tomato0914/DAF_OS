"""
DAF OS Quest80 — CEO Inbox サービス

KPI Alert（Quest78）・Autonomous Issue Suggestions（Quest79）・Memory Update
Suggestions（memory_review_service）・承認待ち（outputs/approvals/pending/）が
それぞれ別ファイルに散らばっており、CEOが毎回探しに行く必要があった。
このサービスはそれらを1つの outputs/ceo_inbox.md に集約し、
「まずCEO Inboxを見ればよい」状態にする。

必要な関数：
- generate_ceo_inbox():        4つの情報源を読み込み、outputs/ceo_inbox.md を
                                危険度が高い順（KPI Alert → Autonomous Issue →
                                Pending Approvals → Memory Update Suggestions）に
                                まとめて保存し、生成したファイルパスを返す
- generate_ceo_inbox_summary(): outputs/ceo_inbox.md をAI会議へ注入する
                                短いMarkdown要約として返す
                                （services/memory_service.py から呼ばれ、
                                Memory Contextの最上部に注入される）

CLI:
  python services/ceo_inbox_service.py

v1方針：
- Markdown集約のみ。LLMは使わない（読み込み専用の決定的な処理）。
- GitHub Issue作成・承認処理はここでは行わない（CEOが別途判断する）。
- 4つの情報源のいずれかが存在しない・空・読み込み失敗でも、該当セクションに
  「〜はありません」の旨を書き込むだけで、DAF OS全体を止めない。
"""

import re
import sys
from datetime import datetime
from pathlib import Path

# `python services/ceo_inbox_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/kpi_alert_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"

_NO_KPI_ALERT_TEXT = "現在、重大なKPI悪化は検出されていません。"
_NO_AUTONOMOUS_ISSUE_TEXT = "現在、提案中のAutonomous Issueはありません。"
_NO_PENDING_APPROVAL_TEXT = "現在、承認待ちはありません。"
_NO_MEMORY_UPDATE_TEXT = "現在、Memory Update Suggestionsはありません。"
_EMPTY_INBOX_SUMMARY = "## CEO Inbox Summary\n\n現在、CEO Inboxは空です。"


def _read_text(path: Path) -> str:
    """ファイルを読み込む。存在しない・読み込み失敗の場合は空文字を返す。"""
    try:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _strip_first_heading(text: str) -> str:
    """先頭行が見出し（#〜）の場合、それを取り除いて本文だけを返す。"""
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("#"):
        lines = lines[1:]
    return "\n".join(lines).strip()


def _kpi_alert_section(outputs_dir: Path) -> str:
    """outputs/kpi_alerts.md からPriority 1セクションの本文を組み立てる。"""
    try:
        content = _read_text(outputs_dir / "kpi_alerts.md")
        if not content:
            return _NO_KPI_ALERT_TEXT
        body = _strip_first_heading(content)
        if "CRITICAL" not in body and "WARNING" not in body:
            return _NO_KPI_ALERT_TEXT
        return body
    except Exception as e:
        print(f"[警告] KPI Alert Summaryの読み込みに失敗しました：{e}")
        return _NO_KPI_ALERT_TEXT


def _autonomous_issue_section(outputs_dir: Path) -> str:
    """outputs/autonomous_issues.md からPriority 2セクションの本文を組み立てる。"""
    try:
        content = _read_text(outputs_dir / "autonomous_issues.md")
        if not content:
            return _NO_AUTONOMOUS_ISSUE_TEXT
        body = _strip_first_heading(content)
        if "Source KPI:" not in body:
            return _NO_AUTONOMOUS_ISSUE_TEXT
        return body
    except Exception as e:
        print(f"[警告] Autonomous Issue Suggestionsの読み込みに失敗しました：{e}")
        return _NO_AUTONOMOUS_ISSUE_TEXT


def _frontmatter_field(text: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _pending_approval_section(outputs_dir: Path) -> str:
    """outputs/approvals/pending/ 配下の .md からPriority 3セクションの本文を組み立てる。"""
    try:
        pending_dir = outputs_dir / "approvals" / "pending"
        if not pending_dir.exists():
            return _NO_PENDING_APPROVAL_TEXT

        files = sorted(pending_dir.glob("*.md"))
        if not files:
            return _NO_PENDING_APPROVAL_TEXT

        lines = []
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            title = _frontmatter_field(text, "title") or path.stem
            priority = _frontmatter_field(text, "advisor_priority")
            risk = _frontmatter_field(text, "advisor_risk")
            details = []
            if priority:
                details.append(f"優先度: {priority}")
            if risk:
                details.append(f"リスク: {risk}")
            suffix = f"（{' / '.join(details)}）" if details else ""
            lines.append(f"- {title}{suffix}")

        return "\n".join(lines) if lines else _NO_PENDING_APPROVAL_TEXT
    except Exception as e:
        print(f"[警告] Pending Approvalsの読み込みに失敗しました：{e}")
        return _NO_PENDING_APPROVAL_TEXT


def _memory_update_section(outputs_dir: Path) -> str:
    """outputs/memory_update_suggestions.md からPriority 4セクションの本文を組み立てる。"""
    try:
        content = _read_text(outputs_dir / "memory_update_suggestions.md")
        if not content:
            return _NO_MEMORY_UPDATE_TEXT
        body = _strip_first_heading(content)
        return body or _NO_MEMORY_UPDATE_TEXT
    except Exception as e:
        print(f"[警告] Memory Update Suggestionsの読み込みに失敗しました：{e}")
        return _NO_MEMORY_UPDATE_TEXT


def generate_ceo_inbox(outputs_dir: Path | None = None) -> Path:
    """
    KPI Alert Summary・Autonomous Issue Suggestions・Pending Approvals・
    Memory Update Suggestionsを、危険度が高い順（Priority 1〜4）に
    outputs/ceo_inbox.md へまとめる。

    いずれかの読み込みに失敗しても、そのセクションだけ「〜はありません」に
    フォールバックし、DAF OS全体を止めない。ファイルは必ず生成する。
    """
    base = outputs_dir or _OUTPUTS_DIR

    try:
        base.mkdir(parents=True, exist_ok=True)

        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines = [
            "# CEO Inbox",
            "",
            f"Generated At: {generated_at}",
            "",
            "## Priority 1: Critical / Warning KPI Alerts",
            "",
            _kpi_alert_section(base),
            "",
            "## Priority 2: Autonomous Issue Suggestions",
            "",
            _autonomous_issue_section(base),
            "",
            "## Priority 3: Pending Approvals",
            "",
            _pending_approval_section(base),
            "",
            "## Priority 4: Memory Update Suggestions",
            "",
            _memory_update_section(base),
            "",
            "---",
            "",
            "## CEO Recommended Actions",
            "",
            "1. Critical KPI Alertがある場合は最優先で確認する",
            "2. Autonomous Issue Suggestionsを確認し、必要なら正式Issue化する",
            "3. Pending Approvalsを承認・却下する",
            "4. Memory Update Suggestionsを確認する",
        ]

        path = base / "ceo_inbox.md"
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return path
    except Exception as e:
        print(f"[警告] CEO Inboxの生成に失敗しました：{e}")
        try:
            base.mkdir(parents=True, exist_ok=True)
            path = base / "ceo_inbox.md"
            path.write_text("# CEO Inbox\n\n生成に失敗しました。\n", encoding="utf-8")
            return path
        except Exception:
            return base / "ceo_inbox.md"


def generate_ceo_inbox_summary(outputs_dir: Path | None = None) -> str:
    """
    outputs/ceo_inbox.md を読み込み、AI会議へ注入する短いMarkdown要約に整形する
    （services/memory_service.py の load_company_memory() から、Memory Contextの
    最上部に注入するために呼ばれる）。
    ファイル未存在・空・読み込み失敗のいずれの場合も「現在、CEO Inboxは空です。」
    を返す。例外を投げない。
    """
    try:
        base = outputs_dir or _OUTPUTS_DIR
        content = _read_text(base / "ceo_inbox.md")
        if not content:
            return _EMPTY_INBOX_SUMMARY

        body = _strip_first_heading(content).strip()
        if not body:
            return _EMPTY_INBOX_SUMMARY

        return f"## CEO Inbox Summary\n\n{body}"
    except Exception as e:
        print(f"[警告] CEO Inbox Summaryの生成に失敗しました：{e}")
        return _EMPTY_INBOX_SUMMARY


if __name__ == "__main__":
    # Quest80: Dashboard/main.pyの日次バッチを待たずに手動で再生成したい場合のCLI導線。
    #   python services/ceo_inbox_service.py
    path = generate_ceo_inbox()
    print(f"[CEO Inbox] {path} を生成しました。")
