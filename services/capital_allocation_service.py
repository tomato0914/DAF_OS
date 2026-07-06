"""
DAF OS Quest84 — Capital Allocation Engine サービス

Strategic Goals → Initiatives → KPI Alerts → Autonomous Issues → CEO Decision →
Weekly Board Meeting → Scenario Planningまでの仕組みは、状況の把握・記録・
リスクの事前準備までをカバーした。しかしCEOの時間は有限であり、「今週どこに
時間・エネルギーを使うべきか」までは提案していなかった。このサービスは
それらの情報源をルールベースで集約し、施策（Initiative）単位の推奨配分比率
（合計100%）を提案する。

意思決定を代替するものではなく、CEOの限られた時間を最も価値の高い場所へ
向けるための経営支援機能である。

配分対象（v1固定）：
- App Store公開準備
- User Acquisition
- Onboarding Improvement
- その他（上記3つに紐付かないシグナルの受け皿）

v1配分ルール（加点方式、対象はKPI Alert/Autonomous Issueのrelated_initiative、
Initiativeの紐付くGoal、Weekly Board Meetingの推奨優先事項本文、Scenario
Planningの高リスクシナリオから特定する）：
1. Critical KPI Alert:              +30
2. Warning KPI Alert:                +15
3. Annual Goal直結Initiative:         +20
4. Autonomous Issue存在:              +10
5. Weekly Board MeetingでPriority指定: +10
6. Scenario PlanningでHigh Risk:      +15
シグナルが1つも無い場合は、3つの実施策（App Store公開準備・User Acquisition・
Onboarding Improvement）に均等な基礎スコアを与え、その他は0のままにする
（データ0件でも実行でき、かつ「その他」に100%割り振られる無意味な結果を避けるため）。

必要な関数：
- generate_capital_allocation():         各情報源を集約し、
                                          outputs/capital_allocation.md に保存して
                                          ファイルパスを返す
- generate_capital_allocation_summary(): AI会議へ注入する短いMarkdown要約を返す

CLI:
  python services/capital_allocation_service.py

各情報源の読み込みは個別にtry/exceptで守られており、1つの情報源が無い・
壊れていても他のセクション・DAF OS全体には影響しない。
"""

import re
import sys
from datetime import datetime
from pathlib import Path

# `python services/capital_allocation_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/scenario_planning_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_MEMORY_DIR = _BASE_DIR / "memory"
_OUTPUTS_DIR = _BASE_DIR / "outputs"

_TARGETS = ["App Store公開準備", "User Acquisition", "Onboarding Improvement", "その他"]
_OTHER = "その他"
_BASE_SCORE_WHEN_NO_SIGNAL = 1

_NO_DATA_SUMMARY = "## Capital Allocation Summary\n\n現在、Capital Allocationはまだ生成されていません。"


def _safe_kpi_alerts(memory_dir: Path) -> list[dict]:
    try:
        from services.kpi_alert_service import get_active_kpi_alerts
        return get_active_kpi_alerts(memory_dir=memory_dir)
    except Exception as e:
        print(f"[警告] KPI Alertsの取得に失敗しました：{e}")
        return []


def _safe_initiatives(memory_dir: Path) -> list[dict]:
    try:
        from services.initiative_service import load_initiatives
        return load_initiatives(memory_dir=memory_dir)
    except Exception as e:
        print(f"[警告] Initiativesの取得に失敗しました：{e}")
        return []


def _safe_annual_goals(memory_dir: Path) -> list[str]:
    try:
        from services.strategic_goal_service import load_strategic_goals
        goals = load_strategic_goals(memory_dir=memory_dir)
        return goals.get("annual_goals", [])
    except Exception as e:
        print(f"[警告] Strategic Goalsの取得に失敗しました：{e}")
        return []


def _safe_autonomous_issues(outputs_dir: Path) -> list[dict]:
    try:
        from services.autonomous_issue_service import load_autonomous_issues
        return load_autonomous_issues(outputs_dir=outputs_dir)
    except Exception as e:
        print(f"[警告] Autonomous Issue Suggestionsの取得に失敗しました：{e}")
        return []


def _safe_weekly_priorities_text(outputs_dir: Path) -> str:
    """Weekly Board Meetingの「Recommended Priorities Next Week」本文だけを取り出す。"""
    try:
        path = outputs_dir / "weekly_board_meeting.md"
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8")
        m = re.search(
            r"## 7\. Recommended Priorities Next Week\s*\n([\s\S]*?)(?=\n## |\Z)",
            text,
        )
        return m.group(1).strip() if m else ""
    except Exception as e:
        print(f"[警告] Weekly Board Meetingの取得に失敗しました：{e}")
        return ""


def _safe_high_risk_scenarios() -> list[dict]:
    try:
        from services.scenario_planning_service import get_high_risk_scenarios
        return get_high_risk_scenarios()
    except Exception as e:
        print(f"[警告] Scenario Planningの取得に失敗しました：{e}")
        return []


def _resolve_target(name: str | None) -> str:
    """Initiative名を配分対象（_TARGETS）に正規化する。該当が無ければその他。"""
    if name and name in _TARGETS:
        return name
    return _OTHER


def _match_scenario_target(scenario: dict, initiatives: list[dict]) -> str:
    """
    Scenarioのタイトルから配分対象を推定する。
    1. 配分対象（Initiative名）の英数字部分（例："App Store公開準備"→"App Store"）が
       タイトルに含まれるか（"App Store審査に落ちた場合"のように、Initiative名の
       全体ではなく先頭の英字部分だけがタイトルと重なるケースに対応するため）
    2. いずれかのInitiativeのSuccess KPIがタイトルに含まれるか
    のいずれかで一致すればそのInitiative、無ければその他。
    """
    title = scenario.get("title", "")

    for target in _TARGETS:
        if target == _OTHER:
            continue
        prefix_match = re.match(r"^[A-Za-z0-9 ]+", target)
        keyword = prefix_match.group(0).strip() if prefix_match else target
        if keyword and keyword in title:
            return target

    for initiative in initiatives:
        name = initiative.get("name")
        if name not in _TARGETS:
            continue
        for kpi in initiative.get("success_kpi", []):
            if kpi and kpi in title:
                return name

    return _OTHER


def _compute_allocation(memory_dir: Path, outputs_dir: Path) -> dict:
    """
    v1配分ルールを適用し、{target: {"score": float, "reasons": list[str]}} を返す。
    情報源の取得はすべて個別にtry/exceptで守られているため、この関数自体は
    例外を投げない前提（呼び出し側でもさらに守る）。
    """
    scores = {t: 0 for t in _TARGETS}
    reasons: dict[str, list[str]] = {t: [] for t in _TARGETS}

    def _add(target: str, points: int, reason: str) -> None:
        target = _resolve_target(target)
        scores[target] += points
        reasons[target].append(reason)

    kpi_alerts = _safe_kpi_alerts(memory_dir)
    for alert in kpi_alerts:
        target = alert.get("related_initiative")
        if alert.get("level") == "CRITICAL":
            _add(target, 30, f"Critical KPI Alert: {alert.get('metric')}")
        elif alert.get("level") == "WARNING":
            _add(target, 15, f"Warning KPI Alert: {alert.get('metric')}")

    initiatives = _safe_initiatives(memory_dir)
    annual_goals = _safe_annual_goals(memory_dir)
    for initiative in initiatives:
        if initiative.get("goal") and initiative["goal"] in annual_goals:
            _add(initiative.get("name"), 20, "Annual Goal直結")

    autonomous_issues = _safe_autonomous_issues(outputs_dir)
    for issue in autonomous_issues:
        _add(issue.get("related_initiative"), 10, f"Autonomous Issue: {issue.get('title')}")

    weekly_priorities_text = _safe_weekly_priorities_text(outputs_dir)
    if weekly_priorities_text:
        for target in _TARGETS:
            if target != _OTHER and target in weekly_priorities_text:
                _add(target, 10, "Weekly Board MeetingでPriority指定")

    high_risk_scenarios = _safe_high_risk_scenarios()
    for scenario in high_risk_scenarios:
        target = _match_scenario_target(scenario, initiatives)
        _add(target, 15, f"High Risk Scenario: {scenario.get('short_title', scenario.get('title'))}")

    # シグナルが1つも無い場合、実施策（その他を除く）に均等な基礎スコアを与える。
    if sum(scores.values()) == 0:
        for target in _TARGETS:
            if target != _OTHER:
                scores[target] = _BASE_SCORE_WHEN_NO_SIGNAL
                reasons[target].append("特筆すべきシグナルなし（均等配分）")

    return {t: {"score": scores[t], "reasons": reasons[t]} for t in _TARGETS}


def _normalize_to_percent(allocation: dict) -> dict[str, int]:
    """スコアを合計100%になるよう正規化する（丸め誤差は最大配分先で吸収する）。"""
    total = sum(v["score"] for v in allocation.values())
    if total <= 0:
        # 万一すべて0の場合でも100%になるよう、その他に全振りする。
        return {t: (100 if t == _OTHER else 0) for t in allocation}

    raw = {t: (v["score"] / total) * 100 for t, v in allocation.items()}
    rounded = {t: round(p) for t, p in raw.items()}

    diff = 100 - sum(rounded.values())
    if diff != 0:
        top_target = max(raw, key=lambda t: raw[t])
        rounded[top_target] += diff

    return rounded


def _build_ceo_recommendation(percentages: dict[str, int]) -> str:
    non_other = {t: p for t, p in percentages.items() if t != _OTHER}
    if not non_other or max(non_other.values()) == 0:
        return "現在、特筆すべき集中対象はありません。既存の優先事項を継続してください。"
    top_target = max(non_other, key=lambda t: non_other[t])
    return f"今週は{top_target}へ最も多くの時間を配分してください。"


def generate_capital_allocation(
    memory_dir: Path | None = None,
    outputs_dir: Path | None = None,
) -> Path:
    """
    Strategic Goals・Initiatives・KPI Alerts・Autonomous Issues・Weekly Board
    Meeting・Scenario Planningを集約し、施策単位の推奨配分比率（合計100%）を
    outputs/capital_allocation.md に保存する。情報源の読み込みはすべて個別に
    try/exceptで守られているため、1つが欠けても他セクション・DAF OS全体には
    影響しない。
    """
    base_memory_dir = memory_dir or _MEMORY_DIR
    base_outputs_dir = outputs_dir or _OUTPUTS_DIR

    try:
        base_outputs_dir.mkdir(parents=True, exist_ok=True)

        allocation = _compute_allocation(base_memory_dir, base_outputs_dir)
        percentages = _normalize_to_percent(allocation)

        ordered_targets = sorted(_TARGETS, key=lambda t: percentages[t], reverse=True)

        lines = [
            "# Capital Allocation Engine",
            "",
            "Generated At:",
            datetime.now().strftime("%Y-%m-%d"),
            "",
            "---",
            "",
            "## Recommended Allocation",
            "",
        ]

        sections = []
        for target in ordered_targets:
            pct = percentages[target]
            reasons = allocation[target]["reasons"]
            section_lines = [f"### {target}", f"{pct}%", ""]
            if reasons:
                section_lines.append("Reason:")
                section_lines.extend(f"- {r}" for r in reasons)
            else:
                section_lines.append("Reason:")
                section_lines.append("- 現時点で該当するシグナルはありません")
            sections.append("\n".join(section_lines))

        lines.append("\n\n---\n\n".join(sections))
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## CEO Recommendation")
        lines.append("")
        lines.append(_build_ceo_recommendation(percentages))

        path = base_outputs_dir / "capital_allocation.md"
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return path
    except Exception as e:
        print(f"[警告] Capital Allocationの生成に失敗しました：{e}")
        try:
            base_outputs_dir.mkdir(parents=True, exist_ok=True)
            path = base_outputs_dir / "capital_allocation.md"
            path.write_text("# Capital Allocation Engine\n\n生成に失敗しました。\n", encoding="utf-8")
            return path
        except Exception:
            return base_outputs_dir / "capital_allocation.md"


def generate_capital_allocation_summary(
    memory_dir: Path | None = None,
    outputs_dir: Path | None = None,
) -> str:
    """
    現在のシグナルからCapital Allocationを再計算し、AI会議へ注入する短い
    Markdown要約を返す。ファイルの生成有無に依存しない（常に最新のシグナルから
    直接計算する）。情報源の取得はすべて個別にtry/exceptで守られているため、
    例外を投げない。
    """
    base_memory_dir = memory_dir or _MEMORY_DIR
    base_outputs_dir = outputs_dir or _OUTPUTS_DIR

    try:
        allocation = _compute_allocation(base_memory_dir, base_outputs_dir)
        percentages = _normalize_to_percent(allocation)
        ordered_targets = sorted(_TARGETS, key=lambda t: percentages[t], reverse=True)

        lines = ["## Capital Allocation Summary", "", "### Recommended Allocation"]
        for target in ordered_targets:
            if percentages[target] <= 0:
                continue
            lines.append(f"- {target}：{percentages[target]}%")
        lines.append("")
        lines.append("### CEO Recommendation")
        lines.append(_build_ceo_recommendation(percentages))

        return "\n".join(lines).rstrip()
    except Exception as e:
        print(f"[警告] Capital Allocation Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


if __name__ == "__main__":
    # Quest84: Dashboard/main.pyの日次バッチを待たずに手動で再生成したい場合のCLI導線。
    #   python services/capital_allocation_service.py
    path = generate_capital_allocation()
    print(f"[Capital Allocation] {path} を生成しました。")
    print()
    print(generate_capital_allocation_summary())
