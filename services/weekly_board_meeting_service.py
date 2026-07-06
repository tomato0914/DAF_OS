"""
DAF OS Quest82 — Weekly Board Meeting サービス

Strategic Goals → Initiatives → KPI Alerts → Autonomous Issues → CEO Inbox →
CEO Decisionまでの戦略レイヤーが完成した（Quest76〜81）。しかしCEOは毎日
これらを個別に確認する必要があった。このサービスはそれらを週次で1つに
まとめ、「今週何が起きたか／最大のリスクは何か／来週何に集中すべきか」を
CEOが5分で把握できる経営会議資料（outputs/weekly_board_meeting.md）として
自動生成する。

参照対象：Strategic Goals・Initiatives・KPI Alerts・Autonomous Issues・
CEO Decisions・Meeting Quality・Reflection Report・CEO Inbox

出力内容：
1. Executive Summary
2. Goal Review
3. Initiative Review
4. KPI Review
5. CEO Decisions This Week
6. Biggest Risks
7. Recommended Priorities Next Week
8. Board Recommendation

v1方針（あえてシンプルにする）：
- LLMは使わず、各情報源のサマリー関数・構造化データを組み合わせて
  決定的にレポートを組み立てる（autonomous_issue_serviceと同じ理由で、
  外部API依存を避けてDAF OS全体を止めないことを優先した）。
- Autonomous Issueや承認待ちIssueの「増加」は、v1では週次スナップショットを
  持たないため「現時点の件数」で代替している（履歴比較はv2以降の課題）。
- Issueの実行やGitHub連携はここでは行わない（あくまで週次レビュー資料）。

必要な関数：
- generate_weekly_board_meeting():         各情報源を集約し、
                                            outputs/weekly_board_meeting.md に
                                            保存してファイルパスを返す
- generate_weekly_board_meeting_summary(): outputs/weekly_board_meeting.md を
                                            AI会議へ注入する短いMarkdown要約
                                            として返す

CLI:
  python services/weekly_board_meeting_service.py

ファイル未存在・各情報源の読み込み失敗・パース失敗のいずれでも例外を投げず、
DAF OS全体を止めない。
"""

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# `python services/weekly_board_meeting_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/ceo_inbox_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_MEMORY_DIR = _BASE_DIR / "memory"
_OUTPUTS_DIR = _BASE_DIR / "outputs"

_NO_MEETING_SUMMARY = "## Weekly Board Meeting Summary\n\n現在、Weekly Board Meetingはまだ生成されていません。"


def _strip_first_heading(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("#"):
        lines = lines[1:]
    return "\n".join(lines).strip()


# ──────────────────────────────────────────
# 情報源ごとの読み込み（それぞれ個別にtry/exceptで守る）
# ──────────────────────────────────────────

def _safe_goal_review(memory_dir: Path) -> tuple[str, dict]:
    """Strategic Goalsを読み込み、Goal Review本文と生データを返す。"""
    try:
        from services.strategic_goal_service import load_strategic_goals, generate_strategic_goal_summary
        goals = load_strategic_goals(memory_dir=memory_dir)
        body = _strip_first_heading(generate_strategic_goal_summary(memory_dir=memory_dir))
        return body or "現在、明確な経営目標は登録されていません。", goals
    except Exception as e:
        print(f"[警告] Goal Reviewの生成に失敗しました：{e}")
        return "現在、明確な経営目標は登録されていません。", {}


def _safe_initiative_review(memory_dir: Path) -> tuple[str, list[dict]]:
    """Initiativesを読み込み、Initiative Review本文と生データを返す。"""
    try:
        from services.initiative_service import load_initiatives, generate_initiative_summary
        initiatives = load_initiatives(memory_dir=memory_dir)
        body = _strip_first_heading(generate_initiative_summary(memory_dir=memory_dir))
        return body or "現在、登録されている施策はありません。", initiatives
    except Exception as e:
        print(f"[警告] Initiative Reviewの生成に失敗しました：{e}")
        return "現在、登録されている施策はありません。", []


def _safe_kpi_alerts(kpi_dir: Path | None, memory_dir: Path) -> list[dict]:
    """アクティブなKPI Alertを取得する。失敗時は空リスト。"""
    try:
        from services.kpi_alert_service import get_active_kpi_alerts
        return get_active_kpi_alerts(kpi_dir=kpi_dir, memory_dir=memory_dir)
    except Exception as e:
        print(f"[警告] KPI Alertsの取得に失敗しました：{e}")
        return []


def _safe_autonomous_issues(outputs_dir: Path) -> list[dict]:
    """現在のAutonomous Issue Suggestions一覧を取得する。失敗時は空リスト。"""
    try:
        from services.autonomous_issue_service import load_autonomous_issues
        return load_autonomous_issues(outputs_dir=outputs_dir)
    except Exception as e:
        print(f"[警告] Autonomous Issue Suggestionsの取得に失敗しました：{e}")
        return []


def _safe_decisions_this_week(outputs_dir: Path) -> list[dict]:
    """直近7日以内に記録されたCEO Decisionを新しい順で返す。失敗時は空リスト。"""
    try:
        from services.decision_center_service import get_decision_history
        records = get_decision_history(outputs_dir=outputs_dir)
        cutoff = datetime.now() - timedelta(days=7)

        this_week = []
        for r in records:
            decided_at = r.get("decided_at")
            if not decided_at:
                continue
            try:
                dt = datetime.strptime(decided_at, "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            if dt >= cutoff:
                this_week.append(r)
        return this_week
    except Exception as e:
        print(f"[警告] CEO Decisionsの取得に失敗しました：{e}")
        return []


def _safe_meeting_quality_summary(outputs_dir: Path, memory_dir: Path) -> str:
    try:
        from services.meeting_quality_service import generate_meeting_quality_summary
        return _strip_first_heading(generate_meeting_quality_summary(outputs_dir=outputs_dir, memory_dir=memory_dir))
    except Exception as e:
        print(f"[警告] Meeting Quality Summaryの取得に失敗しました：{e}")
        return "現時点では十分な会議品質データがありません。"


def _safe_reflection_summary(outputs_dir: Path) -> dict | None:
    try:
        from services.reflection_service import get_reflection_summary
        return get_reflection_summary(outputs_dir)
    except Exception as e:
        print(f"[警告] Reflection Reportの取得に失敗しました：{e}")
        return None


def _safe_pending_approval_count(outputs_dir: Path) -> int:
    try:
        pending_dir = outputs_dir / "approvals" / "pending"
        if not pending_dir.exists():
            return 0
        return len(list(pending_dir.glob("*.md")))
    except Exception:
        return 0


def _safe_ceo_inbox_generated_at(outputs_dir: Path) -> str | None:
    try:
        path = outputs_dir / "ceo_inbox.md"
        if not path.exists():
            return None
        m = re.search(r"^Generated At:\s*(.+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
        return m.group(1).strip() if m else None
    except Exception:
        return None


# ──────────────────────────────────────────
# セクション組み立て
# ──────────────────────────────────────────

def _format_kpi_alert_line(alert: dict) -> str:
    sign = "+" if alert["change_pct"] >= 0 else ""
    line = f"- {alert['metric']}: {alert['before']} → {alert['after']} ({sign}{alert['change_pct']:.0f}%)"
    extra = []
    if alert.get("related_goal"):
        extra.append(f"Goal: {alert['related_goal']}")
    if alert.get("related_initiative"):
        extra.append(f"Initiative: {alert['related_initiative']}")
    if extra:
        line += f"（{' / '.join(extra)}）"
    return line


def _build_executive_summary(
    critical_alerts: list[dict],
    warning_alerts: list[dict],
    autonomous_issues: list[dict],
    decisions_this_week: list[dict],
    meeting_quality_body: str,
) -> str:
    approved = len([d for d in decisions_this_week if d.get("decision") == "approved"])
    on_hold = len([d for d in decisions_this_week if d.get("decision") == "on_hold"])
    rejected = len([d for d in decisions_this_week if d.get("decision") == "rejected"])

    score_match = re.search(r"(\d+)\s*/\s*100", meeting_quality_body)
    score_text = f"{score_match.group(1)} / 100" if score_match else "未計測"

    lines = [
        f"- Critical KPI Alert: {len(critical_alerts)}件",
        f"- Warning KPI Alert: {len(warning_alerts)}件",
        f"- Autonomous Issue提案（現時点）: {len(autonomous_issues)}件",
        f"- 今週のCEO判断: {len(decisions_this_week)}件（承認{approved} / 保留{on_hold} / 却下{rejected}）",
        f"- 直近の会議品質スコア: {score_text}",
    ]
    return "\n".join(lines)


def _build_biggest_risks(
    critical_alerts: list[dict],
    warning_alerts: list[dict],
    not_started_initiatives: list[dict],
    autonomous_issues: list[dict],
    pending_approval_count: int,
) -> str:
    lines = []

    if critical_alerts:
        lines.append("### Critical KPI Alert")
        lines.extend(_format_kpi_alert_line(a) for a in critical_alerts)
        lines.append("")

    if warning_alerts:
        lines.append("### Warning KPI Alert")
        lines.extend(_format_kpi_alert_line(a) for a in warning_alerts)
        lines.append("")

    if not_started_initiatives:
        lines.append("### 未着手Initiative")
        lines.extend(f"- {i['name']}（関連Issueが未登録）" for i in not_started_initiatives)
        lines.append("")

    if autonomous_issues:
        lines.append("### Autonomous Issue Suggestions")
        lines.append(f"- 現在{len(autonomous_issues)}件のAutonomous Issue提案が承認待ちです")
        lines.append("")

    if pending_approval_count > 0:
        lines.append("### Pending Approvals")
        lines.append(f"- 現在{pending_approval_count}件の承認待ちIssueがあります")
        lines.append("")

    if not lines:
        return "現在、大きなリスクは検出されていません。"

    return "\n".join(lines).rstrip()


def _build_recommended_priorities(
    critical_alerts: list[dict],
    initiatives: list[dict],
    annual_goals: list[str],
    approved_this_week: list[dict],
) -> str:
    lines = []

    for alert in critical_alerts:
        lines.append(f"{alert['metric']}の改善を最優先する（Critical KPI）")

    annual_goal_initiatives = [
        i for i in initiatives
        if i.get("goal") and i["goal"] in annual_goals
    ]
    for i in annual_goal_initiatives:
        lines.append(f"{i['name']}（Annual Goal「{i['goal']}」に直結）を推進する")

    for d in approved_this_week:
        title = d.get("title") or d.get("item_id")
        lines.append(f"今週CEOが承認した「{title}」を進める")

    initiative_names = {i["name"] for i in initiatives}
    if "User Acquisition" in initiative_names:
        lines.append("User Acquisition施策を継続する")
    if "Onboarding Improvement" in initiative_names:
        lines.append("Onboarding Improvement施策を継続する")

    if not lines:
        return "現在、特筆すべき推奨優先事項はありません。"

    return "\n".join(f"- {line}" for line in lines)


def _build_board_recommendation(critical_alerts: list[dict], warning_alerts: list[dict]) -> str:
    if critical_alerts:
        return (
            "リスクが高い状態です。Critical KPI Alertへの対応を最優先し、"
            "関連するInitiative・Autonomous Issueを速やかに確認してください。"
        )
    if warning_alerts:
        return "軽微な悪化の兆候があります。来週中に原因を確認し、必要であれば対応してください。"
    return "現在、大きなリスクは検出されていません。既存の優先事項を継続してください。"


def generate_weekly_board_meeting(
    kpi_dir: Path | None = None,
    memory_dir: Path | None = None,
    outputs_dir: Path | None = None,
) -> Path:
    """
    Strategic Goals・Initiatives・KPI Alerts・Autonomous Issues・CEO Decisions・
    Meeting Quality・Reflection Report・CEO Inboxを集約し、
    outputs/weekly_board_meeting.md に週次経営会議資料として保存する。

    各情報源の読み込みは個別にtry/exceptで守られており、1つの情報源が
    無い・壊れていても他のセクション・DAF OS全体には影響しない。
    """
    base_memory_dir = memory_dir or _MEMORY_DIR
    base_outputs_dir = outputs_dir or _OUTPUTS_DIR

    try:
        base_outputs_dir.mkdir(parents=True, exist_ok=True)

        goal_review_body, goals = _safe_goal_review(base_memory_dir)
        initiative_review_body, initiatives = _safe_initiative_review(base_memory_dir)

        alerts = _safe_kpi_alerts(kpi_dir, base_memory_dir)
        critical_alerts = [a for a in alerts if a.get("level") == "CRITICAL"]
        warning_alerts = [a for a in alerts if a.get("level") == "WARNING"]

        autonomous_issues = _safe_autonomous_issues(base_outputs_dir)
        decisions_this_week = _safe_decisions_this_week(base_outputs_dir)
        meeting_quality_body = _safe_meeting_quality_summary(base_outputs_dir, base_memory_dir)
        pending_approval_count = _safe_pending_approval_count(base_outputs_dir)

        not_started_initiatives = [i for i in initiatives if not i.get("related_issues")]
        annual_goals = goals.get("annual_goals", []) if isinstance(goals, dict) else []
        approved_this_week = [d for d in decisions_this_week if d.get("decision") == "approved"]

        # KPI Review本文
        if not alerts:
            kpi_review_body = "現在、重大なKPI悪化は検出されていません。"
        else:
            kpi_lines = []
            if critical_alerts:
                kpi_lines.append("### CRITICAL")
                kpi_lines.extend(_format_kpi_alert_line(a) for a in critical_alerts)
                kpi_lines.append("")
            if warning_alerts:
                kpi_lines.append("### WARNING")
                kpi_lines.extend(_format_kpi_alert_line(a) for a in warning_alerts)
            kpi_review_body = "\n".join(kpi_lines).rstrip()

        # CEO Decisions This Week本文
        if not decisions_this_week:
            decisions_body = "今週記録されたCEOの判断はありません。"
        else:
            decisions_body = "\n".join(
                f"- [{d.get('decision', '').upper()}] {d.get('title') or d.get('item_id')}"
                f"（{d.get('source_type', 'other')} / {d.get('decided_at', '不明')}）"
                for d in decisions_this_week
            )

        reflection = _safe_reflection_summary(base_outputs_dir)
        if reflection and (reflection.get("success") or reflection.get("needs_review") or reflection.get("next_meeting")):
            reflection_lines = []
            if reflection.get("success"):
                reflection_lines.append("成功した判断: " + " / ".join(reflection["success"]))
            if reflection.get("needs_review"):
                reflection_lines.append("改善が必要な判断: " + " / ".join(reflection["needs_review"]))
            if reflection.get("next_meeting"):
                reflection_lines.append("次回会議への反映: " + " / ".join(reflection["next_meeting"]))
            reflection_note = "\n".join(reflection_lines)
        else:
            reflection_note = "現在、参照できるReflection Reportはありません。"

        biggest_risks_body = _build_biggest_risks(
            critical_alerts, warning_alerts, not_started_initiatives,
            autonomous_issues, pending_approval_count,
        )
        recommended_priorities_body = _build_recommended_priorities(
            critical_alerts, initiatives, annual_goals, approved_this_week,
        )
        board_recommendation_body = _build_board_recommendation(critical_alerts, warning_alerts)
        executive_summary_body = _build_executive_summary(
            critical_alerts, warning_alerts, autonomous_issues,
            decisions_this_week, meeting_quality_body,
        )

        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        period_end = datetime.now().strftime("%Y-%m-%d")
        period_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        lines = [
            "# Weekly Board Meeting",
            "",
            f"Generated At: {generated_at}",
            f"Period: {period_start} 〜 {period_end}",
            "",
            "## 1. Executive Summary",
            "",
            executive_summary_body,
            "",
            "## 2. Goal Review",
            "",
            goal_review_body,
            "",
            "## 3. Initiative Review",
            "",
            initiative_review_body,
            "",
            "## 4. KPI Review",
            "",
            kpi_review_body,
            "",
            "## 5. CEO Decisions This Week",
            "",
            decisions_body,
            "",
            "## 6. Biggest Risks",
            "",
            biggest_risks_body,
            "",
            "## 7. Recommended Priorities Next Week",
            "",
            recommended_priorities_body,
            "",
            "## 8. Board Recommendation",
            "",
            board_recommendation_body,
            "",
            "---",
            "",
            "## Reflection Note",
            "",
            reflection_note,
        ]

        path = base_outputs_dir / "weekly_board_meeting.md"
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return path
    except Exception as e:
        print(f"[警告] Weekly Board Meetingの生成に失敗しました：{e}")
        try:
            base_outputs_dir.mkdir(parents=True, exist_ok=True)
            path = base_outputs_dir / "weekly_board_meeting.md"
            path.write_text("# Weekly Board Meeting\n\n生成に失敗しました。\n", encoding="utf-8")
            return path
        except Exception:
            return base_outputs_dir / "weekly_board_meeting.md"


def generate_weekly_board_meeting_summary(outputs_dir: Path | None = None) -> str:
    """
    outputs/weekly_board_meeting.md を読み込み、AI会議へ注入する短いMarkdown要約に
    整形する（services/memory_service.py の load_company_memory() から呼ばれる）。
    ファイル未存在・空・読み込み失敗のいずれの場合も
    「現在、Weekly Board Meetingはまだ生成されていません。」を返す。例外を投げない。
    """
    try:
        base = outputs_dir or _OUTPUTS_DIR
        path = base / "weekly_board_meeting.md"
        if not path.exists():
            return _NO_MEETING_SUMMARY

        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return _NO_MEETING_SUMMARY

        body = _strip_first_heading(content).strip()
        if not body:
            return _NO_MEETING_SUMMARY

        return f"## Weekly Board Meeting Summary\n\n{body}"
    except Exception as e:
        print(f"[警告] Weekly Board Meeting Summaryの生成に失敗しました：{e}")
        return _NO_MEETING_SUMMARY


if __name__ == "__main__":
    # Quest82: Dashboard/main.pyの週次バッチを待たずに手動で再生成したい場合のCLI導線。
    #   python services/weekly_board_meeting_service.py
    path = generate_weekly_board_meeting()
    print(f"[Weekly Board Meeting] {path} を生成しました。")
