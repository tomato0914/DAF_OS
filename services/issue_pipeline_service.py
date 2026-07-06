"""
DAF OS Quest87 — Issue Auto Pipeline サービス

CEO Decision Center（Quest81）はCEOのapprove/hold/rejectを記録するだけで、
「承認された提案が実際に実装待ちのIssueになる」ところまでは繋がっていなかった。
このサービスは、CEOがapproveしたAutonomous Issue・Self Improvement提案・
Memory Update Suggestionsを、実装待ち（pending_implementation）のIssueとして
outputs/issue_pipeline/generated_issues.md に自動生成する。

「提案 → 承認 → Issue化」の自動化がこのQuestの目的であり、GitHub Issue化
そのもの（gh CLI・GitHub API連携）は行わない。次のQuest88で
「Issue → Claude Code実装」へ繋げる前提の、実装待ちIssue一覧を作る段階まで。

対象：CEO Decision History（services/decision_center_service.get_decision_history()）
のうち、以下をすべて満たすもの
- decision == "approved"
- source_type in {"autonomous_issue", "self_improvement", "memory_update"}

重複生成防止：同じTitleのIssueは再生成しない（v1はTitle完全一致で十分と判断）。
既存の outputs/issue_pipeline/generated_issues.md を読み直し、既にある
Titleと重複するものはスキップし、新規分のみ追記する。

必要な関数：
- generate_issue_pipeline():         CEO Decision Historyのapprove済み提案から
                                      実装待ちIssueを生成し、
                                      outputs/issue_pipeline/generated_issues.md に
                                      保存して（既存分＋新規分の）Issue一覧を返す
- generate_issue_pipeline_summary(): AI会議へ注入する短いMarkdown要約を返す
- load_generated_issues():           現在の実装待ちIssue一覧を構造化データで返す
                                      （Quest88 execution_planner_service.py から呼ばれる）

CLI:
  python services/issue_pipeline_service.py

各情報源の読み込みは個別にtry/exceptで守られており、1つが欠けても他の
Issue生成・DAF OS全体には影響しない。approve済みの対象が0件でも正常終了する。
"""

import re
import sys
from datetime import datetime
from pathlib import Path

# `python services/issue_pipeline_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/self_improvement_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_MEMORY_DIR = _BASE_DIR / "memory"
_OUTPUTS_DIR = _BASE_DIR / "outputs"
_PIPELINE_DIR_NAME = "issue_pipeline"
_GENERATED_ISSUES_FILENAME = "generated_issues.md"

_ELIGIBLE_SOURCE_TYPES = frozenset({"autonomous_issue", "self_improvement", "memory_update"})

_DESCRIPTION_TEXT = "CEOにより承認されたため、正式Issueとして登録候補に追加。"
_DEFAULT_ACCEPTANCE_CRITERIA = ["原因分析完了", "改善案整理", "次Issueへ分解"]

_SEVERITY_TO_PRIORITY = {"critical": "High", "warning": "Medium"}

_NO_ISSUES_TEXT = "現在、承認された提案はありません。"
_NO_DATA_SUMMARY = "## Issue Pipeline Summary\n\n現在、生成されたIssueはありません。"


def _pipeline_dir(outputs_dir: Path) -> Path:
    return outputs_dir / _PIPELINE_DIR_NAME


def _safe_decision_history(outputs_dir: Path) -> list[dict]:
    try:
        from services.decision_center_service import get_decision_history
        return get_decision_history(outputs_dir=outputs_dir)
    except Exception as e:
        print(f"[警告] CEO Decision Historyの取得に失敗しました：{e}")
        return []


def _safe_autonomous_issue_lookup(title: str, outputs_dir: Path) -> tuple[str, list[str]]:
    """
    autonomous_issue提案から、Priority（severity由来）とAcceptance Criteriaを
    引き当てる。見つからない・失敗した場合はデフォルト値を返す。
    """
    try:
        from services.autonomous_issue_service import load_autonomous_issues
        for issue in load_autonomous_issues(outputs_dir=outputs_dir):
            if issue.get("title") == title:
                priority = _SEVERITY_TO_PRIORITY.get(issue.get("severity"), "Medium")
                return priority, issue.get("acceptance_criteria") or list(_DEFAULT_ACCEPTANCE_CRITERIA)
        return "Medium", list(_DEFAULT_ACCEPTANCE_CRITERIA)
    except Exception as e:
        print(f"[警告] Autonomous Issueの引き当てに失敗しました：{e}")
        return "Medium", list(_DEFAULT_ACCEPTANCE_CRITERIA)


def _safe_self_improvement_priority(
    title: str,
    kpi_dir: Path | None,
    memory_dir: Path,
    outputs_dir: Path,
) -> str:
    """Self Improvement提案から、現在のPriorityを引き当てる。見つからなければMedium。"""
    try:
        from services.self_improvement_service import get_current_suggestions
        for s in get_current_suggestions(kpi_dir=kpi_dir, memory_dir=memory_dir, outputs_dir=outputs_dir):
            if s.get("title") == title:
                return s.get("priority", "Medium")
        return "Medium"
    except Exception as e:
        print(f"[警告] Self Improvement提案の引き当てに失敗しました：{e}")
        return "Medium"


def _field(block: str, label: str) -> str | None:
    m = re.search(rf"^{re.escape(label)}:\s*\n(.+)$", block, re.MULTILINE)
    return m.group(1).strip() if m else None


def _bullets_after(block: str, label: str) -> list[str]:
    m = re.search(rf"^{re.escape(label)}:\s*\n((?:- .+\n?)+)", block, re.MULTILINE)
    if not m:
        return []
    return [line.strip()[2:].strip() for line in m.group(1).splitlines() if line.strip().startswith("- ")]


def _parse_existing_generated_issues(content: str) -> list[dict]:
    """
    既存の generated_issues.md を再度構造化データに戻す。重複生成防止
    （Titleの既存チェック）とIssue一覧の再レンダリングに使う。パース失敗の
    場合も例外を投げず、空リストを返す。
    """
    try:
        text = re.sub(r"^# Generated Issues\s*\n+", "", content.strip())
        blocks = re.split(r"\n-{3,}\n", text)

        issues = []
        for block in blocks:
            block = block.strip()
            if not block.startswith("## Issue"):
                continue

            title = _field(block, "Title")
            if not title:
                continue

            issues.append({
                "title": title,
                "source": _field(block, "Source") or "other",
                "priority": _field(block, "Priority") or "Medium",
                "status": _field(block, "Status") or "pending_implementation",
                "description": _field(block, "Description") or _DESCRIPTION_TEXT,
                "acceptance_criteria": _bullets_after(block, "Acceptance Criteria"),
            })
        return issues
    except Exception:
        return []


def load_generated_issues(outputs_dir: Path | None = None) -> list[dict]:
    """
    現在の outputs/issue_pipeline/generated_issues.md を読み込み専用でパースして
    返す（generate_issue_pipeline()と違い、CEO Decision History取得や
    ファイル書き込みは行わない）。Quest88（Execution Planner）など、他サービスから
    実装待ちIssue一覧だけを参照したい場合に使う。ファイル未存在・パース失敗時は
    空リストを返す。
    """
    try:
        base = outputs_dir or _OUTPUTS_DIR
        path = _pipeline_dir(base) / _GENERATED_ISSUES_FILENAME
        if not path.exists():
            return []
        return _parse_existing_generated_issues(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _render_issue(issue: dict) -> str:
    lines = [
        "## Issue",
        "",
        "Title:",
        issue["title"],
        "",
        "Source:",
        issue["source"],
        "",
        "Priority:",
        issue["priority"],
        "",
        "Status:",
        issue["status"],
        "",
        "Description:",
        issue["description"],
    ]
    if issue.get("acceptance_criteria"):
        lines.append("")
        lines.append("Acceptance Criteria:")
        lines.extend(f"- {c}" for c in issue["acceptance_criteria"])
    return "\n".join(lines)


def generate_issue_pipeline(
    kpi_dir: Path | None = None,
    memory_dir: Path | None = None,
    outputs_dir: Path | None = None,
) -> Path:
    """
    CEO Decision Historyのうち decision=="approved" かつ
    source_type in {autonomous_issue, self_improvement, memory_update} の
    提案から実装待ちIssueを生成し、outputs/issue_pipeline/generated_issues.md に
    保存する。同じTitleのIssueは再生成しない（重複生成防止）。

    戻り値は保存先のPath。approve済みの対象・既存Issueがどちらも0件の場合も
    正常にファイルを生成する。各情報源の読み込みは個別にtry/exceptで守られて
    おり、DAF OS全体を止めない。
    """
    base_memory_dir = memory_dir or _MEMORY_DIR
    base_outputs_dir = outputs_dir or _OUTPUTS_DIR

    try:
        pipeline_dir = _pipeline_dir(base_outputs_dir)
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        path = pipeline_dir / _GENERATED_ISSUES_FILENAME

        existing_content = ""
        if path.exists():
            try:
                existing_content = path.read_text(encoding="utf-8")
            except Exception:
                existing_content = ""

        existing_issues = _parse_existing_generated_issues(existing_content) if existing_content else []
        existing_titles = {i["title"] for i in existing_issues}

        decisions = _safe_decision_history(base_outputs_dir)
        approved = [
            d for d in decisions
            if d.get("decision") == "approved" and d.get("source_type") in _ELIGIBLE_SOURCE_TYPES
        ]

        new_issues = []
        for d in approved:
            title = d.get("title") or d.get("item_id")
            if not title or title in existing_titles:
                continue

            source = d.get("source_type")
            if source == "autonomous_issue":
                priority, acceptance_criteria = _safe_autonomous_issue_lookup(title, base_outputs_dir)
            elif source == "self_improvement":
                priority = _safe_self_improvement_priority(title, kpi_dir, base_memory_dir, base_outputs_dir)
                acceptance_criteria = []
            else:  # memory_update
                priority = "Medium"
                acceptance_criteria = []

            new_issues.append({
                "title": title,
                "source": source,
                "priority": priority,
                "status": "pending_implementation",
                "description": _DESCRIPTION_TEXT,
                "acceptance_criteria": acceptance_criteria,
            })
            existing_titles.add(title)

        all_issues = existing_issues + new_issues

        lines = [
            "# Generated Issues",
            "",
            "Generated At:",
            datetime.now().strftime("%Y-%m-%d"),
            "",
            "---",
            "",
        ]
        if not all_issues:
            lines.append(_NO_ISSUES_TEXT)
        else:
            lines.append("\n\n---\n\n".join(_render_issue(i) for i in all_issues))

        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return path
    except Exception as e:
        print(f"[警告] Issue Pipelineの生成に失敗しました：{e}")
        try:
            pipeline_dir = _pipeline_dir(base_outputs_dir)
            pipeline_dir.mkdir(parents=True, exist_ok=True)
            path = pipeline_dir / _GENERATED_ISSUES_FILENAME
            path.write_text("# Generated Issues\n\n生成に失敗しました。\n", encoding="utf-8")
            return path
        except Exception:
            return _pipeline_dir(base_outputs_dir) / _GENERATED_ISSUES_FILENAME


def generate_issue_pipeline_summary(outputs_dir: Path | None = None) -> str:
    """
    outputs/issue_pipeline/generated_issues.md を読み込み、AI会議へ注入する
    短いMarkdown要約に整形する（services/memory_service.py の
    load_company_memory() から呼ばれる）。ファイル未存在・空・パース失敗の
    いずれの場合も「現在、生成されたIssueはありません。」を返す。例外を投げない。
    """
    try:
        base = outputs_dir or _OUTPUTS_DIR
        path = _pipeline_dir(base) / _GENERATED_ISSUES_FILENAME
        if not path.exists():
            return _NO_DATA_SUMMARY

        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return _NO_DATA_SUMMARY

        issues = _parse_existing_generated_issues(content)
        if not issues:
            return _NO_DATA_SUMMARY

        pending = [i for i in issues if i.get("status") == "pending_implementation"]

        lines = ["## Issue Pipeline Summary", "", "### Pending Implementation", ""]
        if pending:
            lines.extend(f"- {i['title']}" for i in pending)
        else:
            lines.append(f"- {_NO_ISSUES_TEXT}")
        lines.append("")
        lines.append("### Total")
        lines.append(f"{len(issues)} Issues")

        return "\n".join(lines).rstrip()
    except Exception as e:
        print(f"[警告] Issue Pipeline Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


if __name__ == "__main__":
    # Quest87: Dashboard/main.pyの日次バッチを待たずに手動で再生成したい場合のCLI導線。
    #   python services/issue_pipeline_service.py
    path = generate_issue_pipeline()
    print(f"[Issue Pipeline] {path} を生成しました。")
    print()
    print(generate_issue_pipeline_summary())
