"""
DAF OS Quest79 — Autonomous Issue Generation サービス

KPI Alert System（Quest78）はKPIの悪化を検知するだけで、
「では何をすればいいか」まではAI社員が提案していなかった。
このサービスはアクティブなKPI Alert（services/kpi_alert_service.get_active_kpi_alerts()）
から改善Issue案を自動生成し、outputs/autonomous_issues.md にCEO承認待ちの
Markdownとして出力する。

v1方針（あえてシンプルにする）：
- LLMは使わず、KPIの性質（獲得/継続/品質/安定性のどれに関わるか）ごとの
  テンプレートで文章を組み立てる決定的な処理にする。
  外部API呼び出しに依存しないため、ネットワーク障害やAPIコストの影響を受けず、
  DAF OS全体を止めるリスクが無い。
- KPI Alertが1件も無い場合はIssueを生成しない（空リストを返す。ファイルには
  「提案するIssueはありません」の旨のみ書き込む）。
- 生成物は即GitHub Issue化せず、必ず `Status: pending_ceo_approval` を付けた
  Markdown案として出力するだけにとどめる（実際のGitHub Issue化・承認センターへの
  投入は別のタイミングでCEOが判断する）。

必要な関数：
- generate_autonomous_issues():        KPI Alertから改善Issue案を生成し、
                                        outputs/autonomous_issues.md に保存して
                                        （既存分＋新規分の）Issue案リストを返す
- generate_autonomous_issue_summary(): outputs/autonomous_issues.md をAI会議へ
                                        注入する短いMarkdown要約として返す
                                        （services/memory_service.py から呼ばれる）
- load_autonomous_issues():            outputs/autonomous_issues.md を読み込み専用で
                                        パースして返す（Quest82 weekly_board_meeting_
                                        service.py から呼ばれる。書き込みは行わない）

CLI:
  python services/autonomous_issue_service.py

重複生成防止（追加修正）：
generate_autonomous_issues() は実行のたびに outputs/autonomous_issues.md を
上書きするが、既存ファイルに同じ (Source KPI, Severity) の組み合わせを持つ
Issue案が既にある場合は再生成しない（既存の案をそのまま残す）。v1のため
日付判定は行わない（同じKPI・Severityが一度でも存在すればスキップ）。

ファイル未存在・KPI Alert 0件・パース失敗のいずれでも例外を投げず、安全に動作する。
"""

import re
import sys
from pathlib import Path

# `python services/autonomous_issue_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/kpi_alert_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"

_NO_ALERT_CONTENT = (
    "# Autonomous Issue Suggestions\n\n"
    "現在、KPI Alertが無いため、提案するIssueはありません。\n"
)

_NO_SUGGESTIONS_SUMMARY = "## Autonomous Issue Summary\n\n現在、Autonomous Issue Suggestionsはありません。"

# KPIごとの日本語ラベルと、悪化方向（低下が悪いか／上昇が悪いか）。
# kpi_alert_service._NEGATIVE_IS_BAD / _POSITIVE_IS_BAD と対応させている。
_METRIC_LABELS: dict[str, str] = {
    "Downloads": "ダウンロード数",
    "New Users": "新規ユーザー数",
    "DAU": "DAU（日次アクティブユーザー数）",
    "Retention": "継続率",
    "D1 Retention": "Day1継続率",
    "Record Completion Rate": "初回記録完了率",
    "App Store Review Success": "App Storeレビュー評価",
    "User Trust": "ユーザー信頼度",
    "Crash Free Rate": "クラッシュフリー率",
    "Review Rating": "レビュー評価",
    "Crash Rate": "クラッシュ率",
    "Error Rate": "エラー率",
    "Churn Rate": "解約率（チャーン率）",
}

_INCREASE_IS_BAD_METRICS = frozenset({"Crash Rate", "Error Rate", "Churn Rate"})

# KPIのカテゴリ（獲得 / 継続・オンボーディング / 品質・信頼 / 安定性）ごとに
# 「懸念文」「Proposed Action」を切り替える。
_ACQUISITION_METRICS = frozenset({"Downloads", "New Users", "DAU"})
_RETENTION_METRICS = frozenset({"Retention", "D1 Retention", "Record Completion Rate"})
_QUALITY_METRICS = frozenset({"App Store Review Success", "User Trust", "Review Rating"})
_STABILITY_METRICS = frozenset({"Crash Free Rate", "Crash Rate", "Error Rate"})
_CHURN_METRICS = frozenset({"Churn Rate"})

_CATEGORY_TEMPLATES: dict[str, dict] = {
    "acquisition": {
        "concern": "ユーザー獲得に問題がある可能性があります。",
        "actions": [
            "流入経路（SNS・広告・口コミ）の効果を確認する",
            "獲得チャネルごとのコンバージョン率を確認する",
            "競合・市場環境の変化がないか確認する",
        ],
    },
    "retention": {
        "concern": "初回体験に問題がある可能性があります。",
        "actions": [
            "初回記録画面の離脱ポイントを確認する",
            "記録ボタンの位置・文言・導線を見直す",
            "初回ユーザーの操作ログまたはフィードバックを確認する",
        ],
    },
    "quality": {
        "concern": "プロダクトの評価・信頼に問題がある可能性があります。",
        "actions": [
            "直近のレビュー・問い合わせ内容を確認する",
            "評価が下がった時期の変更・リリース内容を確認する",
            "ユーザーサポート対応に改善余地が無いか確認する",
        ],
    },
    "stability": {
        "concern": "アプリの安定性に問題がある可能性があります。",
        "actions": [
            "直近のクラッシュ・エラーログを確認する",
            "直近のリリース・変更内容とクラッシュ増加の時期を突き合わせる",
            "影響範囲（端末・OSバージョン・機能）を特定する",
        ],
    },
    "churn": {
        "concern": "ユーザーの定着に問題がある可能性があります。",
        "actions": [
            "解約・離脱直前のユーザー行動を確認する",
            "解約理由のフィードバックを収集する",
            "継続利用を促す施策（通知・機能改善）を検討する",
        ],
    },
}


def _category_for(metric: str) -> str:
    if metric in _ACQUISITION_METRICS:
        return "acquisition"
    if metric in _RETENTION_METRICS:
        return "retention"
    if metric in _QUALITY_METRICS:
        return "quality"
    if metric in _CHURN_METRICS:
        return "churn"
    return "stability"


def _build_issue(alert: dict) -> dict:
    """1件のKPI Alertから改善Issue案（構造化データ）を組み立てる。"""
    metric = alert["metric"]
    label = _METRIC_LABELS.get(metric, metric)
    level = alert.get("level", "WARNING")
    threshold = "20%以上" if level == "CRITICAL" else "10%以上"
    direction = "上昇" if metric in _INCREASE_IS_BAD_METRICS else "低下"

    category = _category_for(metric)
    template = _CATEGORY_TEMPLATES[category]

    title = f"{label}の{direction}原因を分析する"
    why = f"{label}が{threshold}{direction}しており、{template['concern']}"

    return {
        "title": title,
        "status": "pending_ceo_approval",
        "source_kpi": metric,
        "severity": level.lower(),
        "related_goal": alert.get("related_goal"),
        "related_initiative": alert.get("related_initiative"),
        "why": why,
        "proposed_action": list(template["actions"]),
        "acceptance_criteria": [
            f"{label}{direction}の原因候補が整理されている",
            "改善案が1つ以上提示されている",
            "実装が必要な場合は次Issueに分解されている",
        ],
    }


def _render_issue(index: int, issue: dict) -> str:
    lines = [
        f"## {index}. {issue['title']}",
        "",
        "Status: pending_ceo_approval",
        f"Source KPI: {issue['source_kpi']}",
        f"Severity: {issue['severity']}",
        f"Related Goal: {issue['related_goal'] or '未設定'}",
        f"Related Initiative: {issue['related_initiative'] or '未設定'}",
        "",
        "### Why",
        issue["why"],
        "",
        "### Proposed Action",
    ]
    lines.extend(f"- {a}" for a in issue["proposed_action"])
    lines.append("")
    lines.append("### Acceptance Criteria")
    lines.extend(f"- {c}" for c in issue["acceptance_criteria"])
    return "\n".join(lines)


def _field(block: str, label: str) -> str | None:
    m = re.search(rf"^{re.escape(label)}:\s*(.+)$", block, re.MULTILINE)
    if not m:
        return None
    value = m.group(1).strip()
    return value or None


def _section_text(block: str, heading: str) -> str:
    m = re.search(rf"^### {re.escape(heading)}\s*\n(.*?)(?=\n### |\Z)", block, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _bullets(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
    return items


def _parse_existing_issues(content: str) -> list[dict]:
    """
    既存の outputs/autonomous_issues.md を再度構造化データに戻す。
    重複生成防止（(Source KPI, Severity) の既存チェック）と、Issue案の
    再レンダリングに使う。パース失敗の場合も例外を投げず、空リストを返す。
    """
    try:
        text = re.sub(r"^# Autonomous Issue Suggestions\s*\n+", "", content.strip())
        blocks = re.split(r"\n-{3,}\n", text)

        issues = []
        for block in blocks:
            block = block.strip()
            if not block.startswith("## "):
                continue
            m = re.match(r"^## \d+\.\s*(.+)", block)
            if not m:
                continue

            source_kpi = _field(block, "Source KPI")
            severity = _field(block, "Severity")
            if not source_kpi or not severity:
                continue

            related_goal = _field(block, "Related Goal")
            related_initiative = _field(block, "Related Initiative")

            issues.append({
                "title": m.group(1).strip(),
                "status": "pending_ceo_approval",
                "source_kpi": source_kpi,
                "severity": severity.strip().lower(),
                "related_goal": None if related_goal == "未設定" else related_goal,
                "related_initiative": None if related_initiative == "未設定" else related_initiative,
                "why": _section_text(block, "Why"),
                "proposed_action": _bullets(_section_text(block, "Proposed Action")),
                "acceptance_criteria": _bullets(_section_text(block, "Acceptance Criteria")),
            })
        return issues
    except Exception:
        return []


def load_autonomous_issues(outputs_dir: Path | None = None) -> list[dict]:
    """
    現在の outputs/autonomous_issues.md を読み込み専用でパースして返す
    （generate_autonomous_issues()と違い、KPI Alert取得やファイル書き込みは行わない）。
    Quest82（Weekly Board Meeting）など、他サービスから現在のIssue案一覧だけを
    参照したい場合に使う。ファイル未存在・パース失敗時は空リストを返す。
    """
    try:
        base = outputs_dir or _OUTPUTS_DIR
        path = base / "autonomous_issues.md"
        if not path.exists():
            return []
        return _parse_existing_issues(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def generate_autonomous_issues(
    kpi_dir: Path | None = None,
    memory_dir: Path | None = None,
    outputs_dir: Path | None = None,
) -> list[dict]:
    """
    アクティブなKPI Alert（services/kpi_alert_service.get_active_kpi_alerts()）から
    改善Issue案を生成し、outputs/autonomous_issues.md にCEO承認待ちのMarkdownとして
    保存する。

    重複生成防止：既存の outputs/autonomous_issues.md に同じ (Source KPI, Severity)
    のIssue案が既にある場合、そのアラートについては再生成しない（既存の案をそのまま
    残す）。新しく検知されたアラート分のみ追記する。v1のため日付判定は行わない。

    KPI Alertが1件も無く、既存のIssue案も無い場合はファイルに
    「提案するIssueはありません」の旨のみ書き込み、空リストを返す。

    戻り値: [{
        "title": str,
        "status": "pending_ceo_approval",
        "source_kpi": str,
        "severity": "warning" | "critical",
        "related_goal": str | None,
        "related_initiative": str | None,
        "why": str,
        "proposed_action": list[str],
        "acceptance_criteria": list[str],
    }, ...]
    （既存分＋新規分を合わせた「現在有効なIssue案」の一覧）

    ファイル未存在・KPI Alert取得失敗・書き込み失敗のいずれでも例外を投げず、
    DAF OS全体を止めない（失敗時は空リストを返す）。
    """
    base_outputs_dir = outputs_dir or _OUTPUTS_DIR

    try:
        from services.kpi_alert_service import get_active_kpi_alerts
        alerts = get_active_kpi_alerts(kpi_dir=kpi_dir, memory_dir=memory_dir)
    except Exception as e:
        print(f"[警告] KPI Alertsの取得に失敗しました：{e}")
        alerts = []

    try:
        base_outputs_dir.mkdir(parents=True, exist_ok=True)
        path = base_outputs_dir / "autonomous_issues.md"

        existing_content = ""
        if path.exists():
            try:
                existing_content = path.read_text(encoding="utf-8")
            except Exception:
                existing_content = ""

        existing_issues = _parse_existing_issues(existing_content) if existing_content else []
        existing_keys = {(i["source_kpi"], i["severity"]) for i in existing_issues}

        new_alerts = [
            a for a in alerts
            if (a["metric"], a.get("level", "WARNING").lower()) not in existing_keys
        ]
        new_issues = [_build_issue(alert) for alert in new_alerts]

        all_issues = existing_issues + new_issues

        if not all_issues:
            path.write_text(_NO_ALERT_CONTENT, encoding="utf-8")
            return []

        sections = [_render_issue(i, issue) for i, issue in enumerate(all_issues, start=1)]
        content = "# Autonomous Issue Suggestions\n\n" + "\n\n---\n\n".join(sections) + "\n"
        path.write_text(content, encoding="utf-8")

        return all_issues
    except Exception as e:
        print(f"[警告] Autonomous Issue Suggestionsの生成に失敗しました：{e}")
        try:
            base_outputs_dir.mkdir(parents=True, exist_ok=True)
            (base_outputs_dir / "autonomous_issues.md").write_text(_NO_ALERT_CONTENT, encoding="utf-8")
        except Exception:
            pass
        return []


def generate_autonomous_issue_summary(outputs_dir: Path | None = None) -> str:
    """
    outputs/autonomous_issues.md を読み込み、AI会議へ注入する短いMarkdown要約に
    整形する（services/memory_service.py の load_company_memory() から呼ばれる）。
    ファイル未存在・空・パース失敗のいずれの場合も
    「現在、Autonomous Issue Suggestionsはありません。」を返す。例外を投げない。
    """
    try:
        base = outputs_dir or _OUTPUTS_DIR
        path = base / "autonomous_issues.md"
        if not path.exists():
            return _NO_SUGGESTIONS_SUMMARY

        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return _NO_SUGGESTIONS_SUMMARY

        body = re.sub(r"^# Autonomous Issue Suggestions\s*\n+", "", content).strip()
        if not body:
            return _NO_SUGGESTIONS_SUMMARY

        return f"## Autonomous Issue Summary\n\n{body}"
    except Exception as e:
        print(f"[警告] Autonomous Issue Summaryの生成に失敗しました：{e}")
        return _NO_SUGGESTIONS_SUMMARY


if __name__ == "__main__":
    # Quest79: Dashboard/main.pyの日次バッチを待たずに手動で再生成したい場合のCLI導線。
    #   python services/autonomous_issue_service.py
    issues = generate_autonomous_issues()
    print(f"[Autonomous Issue] outputs/autonomous_issues.md を生成しました（{len(issues)}件）。")
    for issue in issues:
        print(f"  - [{issue['severity']}] {issue['title']}")
