"""
DAF OS Quest85 — Self Improvement Loop サービス

Strategic Goals → ... → Capital Allocation（Quest76〜84）までは、会社の
状況把握・記録・リスク準備・資源配分の提案をカバーした。しかしそれらは
すべて「プロダクト（mofulog）をどう成長させるか」の話であり、
「DAF OS自身のどこが弱く、次に何を改善すべきか」は提案していなかった。
このサービスは、DAF OS自身の運用データ（KPI Alert・Autonomous Issue・
CEO Inbox・CEO Decisions・Weekly Board Meeting・Scenario Planning・
Capital Allocation・Meeting Quality）をルールベースで分析し、
次に作るべきQuest（改善テーマ）を提案する、自己改善ループの最初の一歩。

v1 改善ルール（該当すれば提案を追加。複数該当する場合はすべて提案する）：
1. Critical KPI Alertが3件以上         → Notification Center      （Priority: High）
2. Pending Approvalsが5件以上          → Decision Dashboard        （Priority: Medium）
3. Autonomous Issueが10件以上          → Issue Prioritization Engine（Priority: Medium）
4. Meeting Qualityが70点未満           → Meeting Improvement Engine（Priority: High）
5. Capital Allocationが毎週大きく変化  → Resource Planning Engine  （Priority: Low）
6. 該当なし                            → 「現在、大きな改善テーマはありません。」

Rule 1は本来「Critical KPI Alertが3回以上"続いた"」（時系列での継続）を意図
しているが、v1では継続検知のための履歴（アラート発生履歴）をまだ持たないため、
「現時点でアクティブなCritical KPI Alertが3件以上」で代替している
（時系列比較はv2以降の課題。他のQuestで採用している「現時点の件数で代替する」
v1簡略化と同じ方針）。
Rule 5も同様に、Capital Allocationの週次履歴をまだ持たないため、v1では常に
非該当として扱う（履歴の永続化はv2以降の課題。虚偽の代替指標を作るより、
「まだ判定できない」ことを明示する方が誠実だと判断した）。

必要な関数：
- generate_self_improvement_suggestions(): 上記ルールを分析し、
                                            outputs/self_improvement_suggestions.md
                                            に保存してファイルパスを返す
- generate_self_improvement_summary():     AI会議へ注入する短いMarkdown要約を返す
- get_current_suggestions():                現在の提案を構造化データで返す
                                            （Quest87 issue_pipeline_service.py
                                            から呼ばれる）

CLI:
  python services/self_improvement_service.py

各情報源の読み込みは個別にtry/exceptで守られており、1つが欠けても他の
ルール判定・DAF OS全体には影響しない。提案が0件でも正常終了する。
"""

import sys
from datetime import datetime
from pathlib import Path

# `python services/self_improvement_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/capital_allocation_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_MEMORY_DIR = _BASE_DIR / "memory"
_OUTPUTS_DIR = _BASE_DIR / "outputs"

_NO_SUGGESTIONS_TEXT = "現在、大きな改善テーマはありません。"
_NO_DATA_SUMMARY = "## Self Improvement Summary\n\n現在、Self Improvement Suggestionsはまだ生成されていません。"

_PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def _safe_critical_kpi_alert_count(kpi_dir: Path | None, memory_dir: Path) -> int:
    try:
        from services.kpi_alert_service import get_active_kpi_alerts
        alerts = get_active_kpi_alerts(kpi_dir=kpi_dir, memory_dir=memory_dir)
        return len([a for a in alerts if a.get("level") == "CRITICAL"])
    except Exception as e:
        print(f"[警告] KPI Alertsの取得に失敗しました：{e}")
        return 0


def _safe_pending_approval_count(outputs_dir: Path) -> int:
    try:
        pending_dir = outputs_dir / "approvals" / "pending"
        if not pending_dir.exists():
            return 0
        return len(list(pending_dir.glob("*.md")))
    except Exception as e:
        print(f"[警告] Pending Approvalsの取得に失敗しました：{e}")
        return 0


def _safe_autonomous_issue_count(outputs_dir: Path) -> int:
    try:
        from services.autonomous_issue_service import load_autonomous_issues
        return len(load_autonomous_issues(outputs_dir=outputs_dir))
    except Exception as e:
        print(f"[警告] Autonomous Issue Suggestionsの取得に失敗しました：{e}")
        return 0


def _safe_meeting_quality_score(outputs_dir: Path, memory_dir: Path) -> int | None:
    try:
        from services.meeting_quality_service import evaluate_meeting_quality
        result = evaluate_meeting_quality(outputs_dir=outputs_dir, memory_dir=memory_dir)
        return result.get("score")
    except Exception as e:
        print(f"[警告] Meeting Qualityの取得に失敗しました：{e}")
        return None


def _capital_allocation_changed_significantly(outputs_dir: Path) -> bool:
    """
    Rule 5: Capital Allocationが毎週大きく変化しているかどうか。
    v1では週次履歴を持たないため、常にFalse（非該当）を返す
    （実装のドキュメント参照）。
    """
    return False


def _detect_suggestions(kpi_dir: Path | None, memory_dir: Path, outputs_dir: Path) -> list[dict]:
    """v1改善ルールを適用し、該当する提案のリストを返す。"""
    suggestions = []

    critical_count = _safe_critical_kpi_alert_count(kpi_dir, memory_dir)
    if critical_count >= 3:
        suggestions.append({
            "title": "Notification Center",
            "reason": f"Critical KPI Alertが複数回発生している（現在{critical_count}件アクティブ）。",
            "expected_impact": "CEOへの通知速度向上。",
            "priority": "High",
        })

    pending_count = _safe_pending_approval_count(outputs_dir)
    if pending_count >= 5:
        suggestions.append({
            "title": "Decision Dashboard",
            "reason": f"承認待ちが増加している（現在{pending_count}件）。",
            "expected_impact": "意思決定速度向上。",
            "priority": "Medium",
        })

    autonomous_issue_count = _safe_autonomous_issue_count(outputs_dir)
    if autonomous_issue_count >= 10:
        suggestions.append({
            "title": "Issue Prioritization Engine",
            "reason": f"Autonomous Issue提案が増加している（現在{autonomous_issue_count}件）。",
            "expected_impact": "Issueの整理・優先順位付けの効率化。",
            "priority": "Medium",
        })

    meeting_quality_score = _safe_meeting_quality_score(outputs_dir, memory_dir)
    if meeting_quality_score is not None and meeting_quality_score < 70:
        suggestions.append({
            "title": "Meeting Improvement Engine",
            "reason": f"会議品質スコアが基準を下回っている（現在{meeting_quality_score} / 100）。",
            "expected_impact": "AI経営会議の品質向上。",
            "priority": "High",
        })

    if _capital_allocation_changed_significantly(outputs_dir):
        suggestions.append({
            "title": "Resource Planning Engine",
            "reason": "Capital Allocationが週次で大きく変化している。",
            "expected_impact": "資源配分の安定化。",
            "priority": "Low",
        })

    suggestions.sort(key=lambda s: _PRIORITY_ORDER.get(s["priority"], 99))
    return suggestions


def get_current_suggestions(
    kpi_dir: Path | None = None,
    memory_dir: Path | None = None,
    outputs_dir: Path | None = None,
) -> list[dict]:
    """
    現在のシグナルからSelf Improvement Suggestionsを再計算し、構造化データの
    まま返す公開関数（Quest87 issue_pipeline_service.py が、CEOが承認した
    Self Improvement提案のPriorityを引き当てるために使う）。_detect_suggestions()
    の薄いラッパー。失敗時は空リストを返す。
    """
    try:
        base_memory_dir = memory_dir or _MEMORY_DIR
        base_outputs_dir = outputs_dir or _OUTPUTS_DIR
        return _detect_suggestions(kpi_dir, base_memory_dir, base_outputs_dir)
    except Exception as e:
        print(f"[警告] Self Improvement Suggestionsの取得に失敗しました：{e}")
        return []


def generate_self_improvement_suggestions(
    kpi_dir: Path | None = None,
    memory_dir: Path | None = None,
    outputs_dir: Path | None = None,
) -> Path:
    """
    DAF OS自身の運用データ（KPI Alert・Autonomous Issue・CEO Inbox・
    CEO Decisions・Weekly Board Meeting・Scenario Planning・Capital
    Allocation・Meeting Quality）をルールベースで分析し、次に作るべきQuest
    （改善テーマ）を outputs/self_improvement_suggestions.md に保存する。
    提案が0件でも正常にファイルを生成する（「現在、大きな改善テーマはありません。」）。
    各情報源の読み込みは個別にtry/exceptで守られており、DAF OS全体を止めない。
    """
    base_memory_dir = memory_dir or _MEMORY_DIR
    base_outputs_dir = outputs_dir or _OUTPUTS_DIR

    try:
        base_outputs_dir.mkdir(parents=True, exist_ok=True)

        suggestions = _detect_suggestions(kpi_dir, base_memory_dir, base_outputs_dir)

        lines = [
            "# Self Improvement Suggestions",
            "",
            "Generated At:",
            datetime.now().strftime("%Y-%m-%d"),
            "",
            "---",
            "",
            "## Suggested Quest",
            "",
        ]

        if not suggestions:
            lines.append(_NO_SUGGESTIONS_TEXT)
        else:
            sections = []
            for s in suggestions:
                sections.append(
                    "\n".join([
                        f"### {s['title']}",
                        "",
                        "Reason:",
                        s["reason"],
                        "",
                        "Expected Impact:",
                        s["expected_impact"],
                        "",
                        "Priority:",
                        s["priority"],
                    ])
                )
            lines.append("\n\n---\n\n".join(sections))

        path = base_outputs_dir / "self_improvement_suggestions.md"
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return path
    except Exception as e:
        print(f"[警告] Self Improvement Suggestionsの生成に失敗しました：{e}")
        try:
            base_outputs_dir.mkdir(parents=True, exist_ok=True)
            path = base_outputs_dir / "self_improvement_suggestions.md"
            path.write_text("# Self Improvement Suggestions\n\n生成に失敗しました。\n", encoding="utf-8")
            return path
        except Exception:
            return base_outputs_dir / "self_improvement_suggestions.md"


def generate_self_improvement_summary(
    kpi_dir: Path | None = None,
    memory_dir: Path | None = None,
    outputs_dir: Path | None = None,
) -> str:
    """
    現在のシグナルからSelf Improvement Suggestionsを再計算し、AI会議へ注入する
    短いMarkdown要約を返す。ファイルの生成有無に依存しない（常に最新のシグナル
    から直接計算する）。情報源の取得はすべて個別にtry/exceptで守られているため、
    例外を投げない。
    """
    base_memory_dir = memory_dir or _MEMORY_DIR
    base_outputs_dir = outputs_dir or _OUTPUTS_DIR

    try:
        suggestions = _detect_suggestions(kpi_dir, base_memory_dir, base_outputs_dir)

        lines = ["## Self Improvement Summary", ""]

        lines.append("### Suggested Quests")
        if suggestions:
            lines.extend(f"- {s['title']}" for s in suggestions)
        else:
            lines.append(f"- {_NO_SUGGESTIONS_TEXT}")
        lines.append("")

        lines.append("### Recommendation")
        if suggestions:
            top = suggestions[0]
            lines.append(f"{top['title']}の優先度が高い。")
        else:
            lines.append(_NO_SUGGESTIONS_TEXT)

        return "\n".join(lines).rstrip()
    except Exception as e:
        print(f"[警告] Self Improvement Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


if __name__ == "__main__":
    # Quest85: Dashboard/main.pyの日次バッチを待たずに手動で再生成したい場合のCLI導線。
    #   python services/self_improvement_service.py
    path = generate_self_improvement_suggestions()
    print(f"[Self Improvement] {path} を生成しました。")
    print()
    print(generate_self_improvement_summary())
