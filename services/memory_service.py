"""
DAF OS v1.3 — 会社メモリ読み込みサービス
memory/ フォルダのファイルを読み込み、
AI社員のタスク description に注入するためのテキストを返す。

Quest53（Company Context Awareness）でproduct_status.md / completed_issues.md を追加し、
「何が終わっていて、何が未完了か」もAI社員が参照できるようにした。

Quest56（Product Executive Summary）でexecutive_summary.mdを先頭に追加。
他のmemoryと内容が矛盾する場合は経営サマリーを最優先の事実として扱う
（crews/launch_crew.py と crews/meeting_crew.py の _reasoning_note 側で指示している）。

Quest57（CEO Decision History）でceo_decision_history.mdを追加。
ceo_preferences.md（好み・意思決定スタイル）とは役割を分け、
こちらは実際にCEOが下した承認・却下の履歴と傾向を記録する。

Quest58（KPI Memory）で、executive_summary.md読み込み時にKPI Summary
（services/kpi_memory_service.generate_kpi_summary()）を注入するようにした。
KPIデータが無い場合は何も注入されず、従来通りの挙動になる（既存の仕組みを壊さない）。

Quest59（Reflection Loop）で、outputs/reflection_report.md（既に生成済みの場合のみ）
をReflection Summaryとして続けて注入するようにした。
load_company_memory()自体はレポートを生成しない（読み込むだけの読み取り専用処理のまま）。
レポートの生成は services/reflection_service.generate_reflection_report() を
別途呼び出して行う。

Quest73（Failed Decision Memory）で、Reflection Summaryの後に
Failed Decision Summary（services/failed_decision_service.generate_failed_decision_summary()）
を続けて注入するようにした。過去に失敗した意思決定をAI社員が会議中に
参照できるようにするため。失敗データが無くても「現時点で記録された
失敗判断はありません。」という文言が注入されるだけで、既存の仕組みは壊さない。

Quest74（Decision Confidence History）で、Failed Decision Summaryの後に
Confidence History Summary（services/confidence_history_service.generate_confidence_history_summary()）
を続けて注入するようにした。DAF OS自身のConfidence予測精度をAI社員が
参照できるようにするため。履歴が無くても「現時点では十分な履歴がありません。」
という文言が注入されるだけで、既存の仕組みは壊さない。

Quest75（Meeting Quality Score）で、Confidence History Summaryの後に
Meeting Quality Summary（services/meeting_quality_service.generate_meeting_quality_summary()）
を続けて注入するようにした。会議の自己評価（スコア・強み・改善点）をAI社員が
次回会議で参照できるようにするため。既存の仕組みは壊さない。

Quest76（Strategic Goal Memory）で、Executive Summaryの直後（KPI Summaryより前）に
Strategic Goal Summary（services/strategic_goal_service.generate_strategic_goal_summary()）
を注入するようにした。会社の目標（North Star Metric・年次/四半期/今月目標・
現在の優先事項）をAI経営会議が常に参照できるようにするため。既存の仕組みは壊さない。

Quest77（Initiative Tracking）で、Strategic Goal Summaryの直後（KPI Summaryより前）に
Initiative Summary（services/initiative_service.generate_initiative_summary()）を
注入するようにした。Goal（目標）とIssue（実行）の間にある「今どの施策が進んでいるか」を
AI経営会議が参照できるようにするため。既存の仕組みは壊さない。

Quest78（KPI Alert System）で、KPI Summaryの直後（Reflection Summaryより前）に
KPI Alert Summary（services/kpi_alert_service.get_kpi_alert_summary()）を注入する
ようにした。直近2件のKPIスナップショットを比較して悪化を検知し、Strategic Goal・
Initiativeと紐付けてAI経営会議が早めに気づけるようにするため。既存の仕組みは壊さない。

Quest79（Autonomous Issue Generation）で、KPI Alert Summaryの直後（Reflection Summary
より前）にAutonomous Issue Summary（services/autonomous_issue_service.
generate_autonomous_issue_summary()）を注入するようにした。outputs/autonomous_issues.md
（KPI Alertから自動生成されたCEO承認待ちのIssue案）をAI経営会議が参照できるように
するため。既存の仕組みは壊さない。

Quest80（CEO Inbox）で、Memory Contextの最上部（Executive Summaryより前）に
CEO Inbox Summary（services/ceo_inbox_service.generate_ceo_inbox_summary()）を
注入するようにした。KPI Alert・Autonomous Issue・Pending Approval・Memory Update
Suggestionsを1つに集約したCEO Inboxを、AI経営会議も真っ先に参照できるようにするため。
既存の仕組みは壊さない。

Quest81（CEO Decision Center）で、CEO Inbox Summaryの直後（Executive Summaryより前）に
CEO Decision Summary（services/decision_center_service.generate_ceo_decision_summary()、
generate_decision_log_summary()の薄いラッパー）を注入するようにした。CEOがapprove/hold/
rejectで記録した判断履歴をAI経営会議も参照できるようにするため。既存の仕組みは壊さない。

Quest82（Weekly Board Meeting）で、CEO Decision Summaryの直後（Executive Summaryより前）に
Weekly Board Meeting Summary（services/weekly_board_meeting_service.
generate_weekly_board_meeting_summary()）を注入するようにした。Strategic Goals・
Initiatives・KPI Alerts・Autonomous Issues・CEO Decisions・Meeting Quality・
Reflection Report・CEO Inboxを週次で集約した経営会議資料をAI経営会議も
参照できるようにするため。既存の仕組みは壊さない。

Quest83（Scenario Planning）で、Weekly Board Meeting Summaryの直後
（Executive Summaryより前）にScenario Planning Summary（services/
scenario_planning_service.generate_scenario_planning_summary()）を注入する
ようにした。DAU急減・App Store審査落ち・初回ユーザー不足・Crash Rate急増など
「まだ起きていないが起こり得るリスク」への事前準備事項を、AI経営会議も
参照できるようにするため。既存の仕組みは壊さない。

Quest84（Capital Allocation Engine）で、Scenario Planning Summaryの直後
（Executive Summaryより前）にCapital Allocation Summary（services/
capital_allocation_service.generate_capital_allocation_summary()）を注入する
ようにした。KPI Alert・Initiative・Weekly Board Meeting・Scenario Planningを
ルールベースで集約した「今週どこに時間・エネルギーを使うべきか」の推奨配分を
AI経営会議も参照できるようにするため。既存の仕組みは壊さない。

Quest85（Self Improvement Loop）で、Capital Allocation Summaryの直後
（Executive Summaryより前）にSelf Improvement Summary（services/
self_improvement_service.generate_self_improvement_summary()）を注入する
ようにした。KPI Alert・Autonomous Issue・Pending Approval・Meeting Qualityを
ルールベースで分析し、DAF OS自身が次に作るべきQuest（改善テーマ）を
提案する自己改善ループを、AI経営会議も参照できるようにするため。
既存の仕組みは壊さない。

Quest87（Issue Auto Pipeline）で、Self Improvement Summaryの直後
（Executive Summaryより前）にIssue Pipeline Summary（services/
issue_pipeline_service.generate_issue_pipeline_summary()）を注入するように
した。CEOがapproveしたAutonomous Issue・Self Improvement提案・Memory Update
Suggestionsが実装待ちIssueとしてどれだけ溜まっているかを、AI経営会議も
参照できるようにするため。既存の仕組みは壊さない。

Quest88（Execution Planner）で、Issue Pipeline Summaryの直後
（Executive Summaryより前）にExecution Plan Summary（services/
execution_planner_service.generate_execution_plan_summary()）を注入する
ようにした。実装待ちIssueをAsset Type（成果物の種類）ごとに分類し、
Deliverables・Tasksに分解した制作計画（Execution Plan）を、AI経営会議も
参照できるようにするため。既存の仕組みは壊さない。

Quest89（Asset Type Registry）で、Execution Plan Summaryの直後
（Executive Summaryより前）にAsset Registry Summary（services/
asset_registry_service.generate_asset_registry_summary()）を注入するように
した。memory/asset_registry/*.jsonに定義したAsset Typeごとの知識
（成果物・制作手順・レビュー項目・公開時に必要なもの）を、AI経営会議も
参照できるようにするため。Registry自体は静的定義（読み込み専用）のため、
main.pyでの生成処理は不要（Memory Contextへの注入のみ）。既存の仕組みは壊さない。

Quest90（Asset Generator v1）で、Asset Registry Summaryの直後
（Executive Summaryより前）にAsset Generator Summary（services/
asset_generator_service.generate_asset_generator_summary()）を注入する
ようにした。Execution Planを起点に実際に生成されたデジタル資産
（v1はline_stickerのみ）の状態（pending_review等）を、AI経営会議も
参照できるようにするため。既存の仕組みは壊さない。

Quest91（Artifact Review Center）で、Asset Generator Summaryの直後
（Executive Summaryより前）にArtifact Review Summary（services/
artifact_review_service.generate_artifact_review_summary()）を注入する
ようにした。生成済みデジタル資産のレビュー状態（Pending Review・Approved・
Published件数）を、AI経営会議も参照できるようにするため。レビュー自体は
main.pyの自動実行フローには含めない（CEOが明示的に呼んだ時のみ実行される）。
既存の仕組みは壊さない。

Quest92（Notification Center）で、Artifact Review Summaryの直後
（Executive Summaryより前）にNotification Summary（services/
notification_service.generate_notification_summary()）を注入するようにした。
DAF OS内の重要イベント（Asset Generated・Review Requested・Review
Decision・Critical KPI Alert・Pending Implementation）を集約した通知ログ
（outputs/notifications.md）を、AI経営会議も参照できるようにするため。
既存の仕組みは壊さない。

Quest93（Project Management Service）で、Memory Contextの最上部
（CEO Inbox Summaryより前）にProject Summary（services/project_service.
get_project_summary()）を注入するようにした。projects/配下に登録された
プロジェクト（Active/Completed）を、AI経営会議が真っ先に参照できるように
するため。既存の仕組みは壊さない。

Memory Context全体の注入順序：
Project Summary → CEO Inbox Summary → CEO Decision Summary →
Weekly Board Meeting Summary → Scenario Planning Summary →
Capital Allocation Summary → Self Improvement Summary → Issue Pipeline Summary →
Execution Plan Summary → Asset Registry Summary → Asset Generator Summary →
Artifact Review Summary → Notification Summary → Executive Summary →
Strategic Goal Summary → Initiative Summary → KPI Summary → KPI Alert Summary →
Autonomous Issue Summary → Reflection Summary →
Failed Decision Summary → Confidence History Summary → Meeting Quality Summary
"""

from pathlib import Path


_MEMORY_FILES = [
    ("executive_summary.md",     "【経営サマリー】"),
    ("company_memory.md",        "【会社の価値観】"),
    ("ceo_preferences.md",       "【CEOの意思決定スタイル】"),
    ("lessons_learned.md",       "【過去の学び・教訓】"),
    ("product_status.md",        "【プロダクトの現状】"),
    ("completed_issues.md",      "【完了済みIssue一覧】"),
    ("ceo_decision_history.md",  "【CEOの過去の意思決定】"),
]

_MEMORY_DIR = Path(__file__).parent.parent / "memory"


def _safe_project_summary(memory_dir: Path) -> str:
    """
    Project Summaryを生成する。project_serviceが無い・エラーになる場合でも
    load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    get_project_summary()自体は登録0件でも例外を投げず「現在、登録されている
    Projectはありません。」を返す設計のため、ここではimport・呼び出し自体の
    失敗のみを守る。
    """
    try:
        from services.project_service import get_project_summary
        projects_dir = memory_dir.parent / "projects"
        return get_project_summary(projects_dir=projects_dir)
    except Exception:
        return ""


def _safe_ceo_inbox_summary(memory_dir: Path) -> str:
    """
    CEO Inbox Summaryを生成する。ceo_inbox_serviceが無い・エラーになる場合でも
    load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    """
    try:
        from services.ceo_inbox_service import generate_ceo_inbox_summary
        outputs_dir = memory_dir.parent / "outputs"
        return generate_ceo_inbox_summary(outputs_dir=outputs_dir)
    except Exception:
        return ""


def _safe_ceo_decision_summary(memory_dir: Path) -> str:
    """
    CEO Decision Summaryを生成する。decision_center_serviceが無い・エラーになる
    場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    generate_ceo_decision_summary()自体が「判断履歴0件」でも例外を投げず
    「現在、記録されたCEOの判断はありません。」を返す設計のため、ここでは
    import・呼び出し自体の失敗のみを守る。
    """
    try:
        from services.decision_center_service import generate_ceo_decision_summary
        outputs_dir = memory_dir.parent / "outputs"
        return generate_ceo_decision_summary(outputs_dir=outputs_dir)
    except Exception:
        return ""


def _safe_weekly_board_meeting_summary(memory_dir: Path) -> str:
    """
    Weekly Board Meeting Summaryを生成する。weekly_board_meeting_serviceが無い・
    エラーになる場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    generate_weekly_board_meeting_summary()自体は未生成でも例外を投げず
    「まだ生成されていません」を返す設計のため、ここではimport・呼び出し自体の
    失敗のみを守る。
    """
    try:
        from services.weekly_board_meeting_service import generate_weekly_board_meeting_summary
        outputs_dir = memory_dir.parent / "outputs"
        return generate_weekly_board_meeting_summary(outputs_dir=outputs_dir)
    except Exception:
        return ""


def _safe_scenario_planning_summary(memory_dir: Path) -> str:
    """
    Scenario Planning Summaryを生成する。scenario_planning_serviceが無い・
    エラーになる場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    generate_scenario_planning_summary()自体は固定シナリオ定義から組み立てるため
    常に非空文字列を返す設計だが、ここではimport・呼び出し自体の失敗のみを守る。
    """
    try:
        from services.scenario_planning_service import generate_scenario_planning_summary
        outputs_dir = memory_dir.parent / "outputs"
        return generate_scenario_planning_summary(outputs_dir=outputs_dir)
    except Exception:
        return ""


def _safe_capital_allocation_summary(memory_dir: Path) -> str:
    """
    Capital Allocation Summaryを生成する。capital_allocation_serviceが無い・
    エラーになる場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    generate_capital_allocation_summary()自体は現在のシグナルから都度再計算し、
    シグナルが無くても均等配分にフォールバックする設計のため、ここでは
    import・呼び出し自体の失敗のみを守る。
    """
    try:
        from services.capital_allocation_service import generate_capital_allocation_summary
        outputs_dir = memory_dir.parent / "outputs"
        return generate_capital_allocation_summary(memory_dir=memory_dir, outputs_dir=outputs_dir)
    except Exception:
        return ""


def _safe_self_improvement_summary(memory_dir: Path) -> str:
    """
    Self Improvement Summaryを生成する。self_improvement_serviceが無い・
    エラーになる場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    generate_self_improvement_summary()自体は現在のシグナルから都度再計算し、
    該当ルールが無くても「大きな改善テーマはありません」を返す設計のため、
    ここではimport・呼び出し自体の失敗のみを守る。
    """
    try:
        from services.self_improvement_service import generate_self_improvement_summary
        outputs_dir = memory_dir.parent / "outputs"
        return generate_self_improvement_summary(memory_dir=memory_dir, outputs_dir=outputs_dir)
    except Exception:
        return ""


def _safe_issue_pipeline_summary(memory_dir: Path) -> str:
    """
    Issue Pipeline Summaryを生成する。issue_pipeline_serviceが無い・エラーに
    なる場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    generate_issue_pipeline_summary()自体は未生成・0件でも例外を投げず
    「現在、生成されたIssueはありません。」を返す設計のため、ここでは
    import・呼び出し自体の失敗のみを守る。
    """
    try:
        from services.issue_pipeline_service import generate_issue_pipeline_summary
        outputs_dir = memory_dir.parent / "outputs"
        return generate_issue_pipeline_summary(outputs_dir=outputs_dir)
    except Exception:
        return ""


def _safe_execution_plan_summary(memory_dir: Path) -> str:
    """
    Execution Plan Summaryを生成する。execution_planner_serviceが無い・
    エラーになる場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    generate_execution_plan_summary()自体は未生成・0件でも例外を投げず
    「現在、有効なExecution Planはありません。」を返す設計のため、ここでは
    import・呼び出し自体の失敗のみを守る。
    """
    try:
        from services.execution_planner_service import generate_execution_plan_summary
        outputs_dir = memory_dir.parent / "outputs"
        return generate_execution_plan_summary(outputs_dir=outputs_dir)
    except Exception:
        return ""


def _safe_asset_registry_summary(memory_dir: Path) -> str:
    """
    Asset Registry Summaryを生成する。asset_registry_serviceが無い・エラーに
    なる場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    generate_asset_registry_summary()自体は登録0件でも例外を投げず
    「現在、登録されているAsset Typeはありません。」を返す設計のため、
    ここではimport・呼び出し自体の失敗のみを守る。
    """
    try:
        from services.asset_registry_service import generate_asset_registry_summary
        return generate_asset_registry_summary(memory_dir=memory_dir)
    except Exception:
        return ""


def _safe_asset_generator_summary(memory_dir: Path) -> str:
    """
    Asset Generator Summaryを生成する。asset_generator_serviceが無い・
    エラーになる場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    generate_asset_generator_summary()自体は未生成でも例外を投げず
    「現在、生成されたAssetはありません。」を返す設計のため、ここでは
    import・呼び出し自体の失敗のみを守る。
    """
    try:
        from services.asset_generator_service import generate_asset_generator_summary
        outputs_dir = memory_dir.parent / "outputs"
        return generate_asset_generator_summary(outputs_dir=outputs_dir)
    except Exception:
        return ""


def _safe_artifact_review_summary(memory_dir: Path) -> str:
    """
    Artifact Review Summaryを生成する。artifact_review_serviceが無い・
    エラーになる場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    generate_artifact_review_summary()自体は生成済みAssetが無くても例外を投げず
    「現在、レビュー対象のAssetはありません。」を返す設計のため、ここでは
    import・呼び出し自体の失敗のみを守る。
    """
    try:
        from services.artifact_review_service import generate_artifact_review_summary
        outputs_dir = memory_dir.parent / "outputs"
        return generate_artifact_review_summary(outputs_dir=outputs_dir)
    except Exception:
        return ""


def _safe_notification_summary(memory_dir: Path) -> str:
    """
    Notification Summaryを生成する。notification_serviceが無い・エラーに
    なる場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    generate_notification_summary()自体は通知が無くても例外を投げず
    「現在、通知はありません。」を返す設計のため、ここではimport・呼び出し
    自体の失敗のみを守る。
    """
    try:
        from services.notification_service import generate_notification_summary
        outputs_dir = memory_dir.parent / "outputs"
        return generate_notification_summary(outputs_dir=outputs_dir)
    except Exception:
        return ""


def _safe_strategic_goal_summary(memory_dir: Path) -> str:
    """
    Strategic Goal Summaryを生成する。strategic_goal_serviceが無い・エラーになる
    場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    """
    try:
        from services.strategic_goal_service import generate_strategic_goal_summary
        return generate_strategic_goal_summary(memory_dir=memory_dir)
    except Exception:
        return ""


def _safe_initiative_summary(memory_dir: Path) -> str:
    """
    Initiative Summaryを生成する。initiative_serviceが無い・エラーになる
    場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    """
    try:
        from services.initiative_service import generate_initiative_summary
        return generate_initiative_summary(memory_dir=memory_dir)
    except Exception:
        return ""


def _safe_kpi_summary() -> str:
    """
    KPI Summaryを生成する。kpi_memory_serviceが無い・エラーになる場合でも
    load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    """
    try:
        from services.kpi_memory_service import generate_kpi_summary
        return generate_kpi_summary()
    except Exception:
        return ""


def _safe_kpi_alert_summary(memory_dir: Path) -> str:
    """
    KPI Alert Summaryを生成する。kpi_alert_serviceが無い・エラーになる場合でも
    load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    """
    try:
        from services.kpi_alert_service import get_kpi_alert_summary
        return get_kpi_alert_summary(memory_dir=memory_dir)
    except Exception:
        return ""


def _safe_autonomous_issue_summary(memory_dir: Path) -> str:
    """
    Autonomous Issue Summaryを生成する。autonomous_issue_serviceが無い・
    エラーになる場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    """
    try:
        from services.autonomous_issue_service import generate_autonomous_issue_summary
        outputs_dir = memory_dir.parent / "outputs"
        return generate_autonomous_issue_summary(outputs_dir=outputs_dir)
    except Exception:
        return ""


def _safe_reflection_summary(memory_dir: Path) -> str:
    """
    outputs/reflection_report.md が既に生成されている場合のみ、その内容を返す。
    ここでは新規生成しない（読み込み専用）。ファイルが無い・読み込みエラーの場合は
    空文字を返し、load_company_memory()全体を壊さない。
    """
    try:
        outputs_dir = memory_dir.parent / "outputs"
        path = outputs_dir / "reflection_report.md"
        if not path.exists():
            return ""
        content = path.read_text(encoding="utf-8").strip()
        return f"## Reflection Summary\n\n{content}" if content else ""
    except Exception:
        return ""


def _safe_failed_decision_summary(memory_dir: Path) -> str:
    """
    Failed Decision Summaryを生成する。failed_decision_serviceが無い・エラーになる
    場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    """
    try:
        from services.failed_decision_service import generate_failed_decision_summary
        return generate_failed_decision_summary(memory_dir=memory_dir)
    except Exception:
        return ""


def _safe_confidence_history_summary(memory_dir: Path) -> str:
    """
    Confidence History Summaryを生成する。confidence_history_serviceが無い・
    エラーになる場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    """
    try:
        from services.confidence_history_service import generate_confidence_history_summary
        return generate_confidence_history_summary(memory_dir=memory_dir)
    except Exception:
        return ""


def _safe_meeting_quality_summary(memory_dir: Path) -> str:
    """
    Meeting Quality Summaryを生成する。meeting_quality_serviceが無い・エラーになる
    場合でも load_company_memory()全体を壊さないよう、失敗時は空文字を返す。
    """
    try:
        from services.meeting_quality_service import generate_meeting_quality_summary
        return generate_meeting_quality_summary(memory_dir=memory_dir)
    except Exception:
        return ""


def load_company_memory(memory_dir: Path | None = None) -> str:
    """
    memory/ の各ファイル（_MEMORY_FILES）を読み込み、AI社員に渡す1つのコンテキスト文字列を返す。
    ファイルが存在しない場合はそのセクションをスキップする。
    executive_summary.md読み込み時は、Quest76のStrategic Goal Summary・Quest77のInitiative Summary・
    Quest58のKPI Summary・Quest78のKPI Alert Summary・Quest79のAutonomous Issue Summary・
    Quest59のReflection Summary・Quest73のFailed Decision Summary・
    Quest74のConfidence History Summary・Quest75のMeeting Quality Summaryを続けて注入する。
    さらにQuest80のCEO Inbox Summary・Quest81のCEO Decision Summary・
    Quest82のWeekly Board Meeting Summary・Quest83のScenario Planning Summary・
    Quest84のCapital Allocation Summary・Quest85のSelf Improvement Summary・
    Quest87のIssue Pipeline Summary・Quest88のExecution Plan Summary・
    Quest89のAsset Registry Summary・Quest90のAsset Generator Summary・
    Quest91のArtifact Review Summary・Quest92のNotification Summary・
    Quest93のProject Summaryを、全セクションの最上部（Project Summary →
    CEO Inbox Summary → CEO Decision Summary → Weekly Board Meeting Summary →
    Scenario Planning Summary → Capital Allocation Summary →
    Self Improvement Summary → Issue Pipeline Summary → Execution Plan Summary →
    Asset Registry Summary → Asset Generator Summary → Artifact Review Summary →
    Notification Summary → Executive Summary...の順）に注入する。
    """
    base = memory_dir or _MEMORY_DIR
    sections: list[str] = []

    project_summary = _safe_project_summary(base)
    if project_summary:
        sections.append(project_summary)

    ceo_inbox_summary = _safe_ceo_inbox_summary(base)
    if ceo_inbox_summary:
        sections.append(ceo_inbox_summary)

    ceo_decision_summary = _safe_ceo_decision_summary(base)
    if ceo_decision_summary:
        sections.append(ceo_decision_summary)

    weekly_board_meeting_summary = _safe_weekly_board_meeting_summary(base)
    if weekly_board_meeting_summary:
        sections.append(weekly_board_meeting_summary)

    scenario_planning_summary = _safe_scenario_planning_summary(base)
    if scenario_planning_summary:
        sections.append(scenario_planning_summary)

    capital_allocation_summary = _safe_capital_allocation_summary(base)
    if capital_allocation_summary:
        sections.append(capital_allocation_summary)

    self_improvement_summary = _safe_self_improvement_summary(base)
    if self_improvement_summary:
        sections.append(self_improvement_summary)

    issue_pipeline_summary = _safe_issue_pipeline_summary(base)
    if issue_pipeline_summary:
        sections.append(issue_pipeline_summary)

    execution_plan_summary = _safe_execution_plan_summary(base)
    if execution_plan_summary:
        sections.append(execution_plan_summary)

    asset_registry_summary = _safe_asset_registry_summary(base)
    if asset_registry_summary:
        sections.append(asset_registry_summary)

    asset_generator_summary = _safe_asset_generator_summary(base)
    if asset_generator_summary:
        sections.append(asset_generator_summary)

    artifact_review_summary = _safe_artifact_review_summary(base)
    if artifact_review_summary:
        sections.append(artifact_review_summary)

    notification_summary = _safe_notification_summary(base)
    if notification_summary:
        sections.append(notification_summary)

    for filename, label in _MEMORY_FILES:
        path = base / filename
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8").strip()
        if filename == "executive_summary.md":
            strategic_goal_summary = _safe_strategic_goal_summary(base)
            if strategic_goal_summary:
                content = f"{content}\n\n{strategic_goal_summary}"
            initiative_summary = _safe_initiative_summary(base)
            if initiative_summary:
                content = f"{content}\n\n{initiative_summary}"
            kpi_summary = _safe_kpi_summary()
            if kpi_summary:
                content = f"{content}\n\n{kpi_summary}"
            kpi_alert_summary = _safe_kpi_alert_summary(base)
            if kpi_alert_summary:
                content = f"{content}\n\n{kpi_alert_summary}"
            autonomous_issue_summary = _safe_autonomous_issue_summary(base)
            if autonomous_issue_summary:
                content = f"{content}\n\n{autonomous_issue_summary}"
            reflection_summary = _safe_reflection_summary(base)
            if reflection_summary:
                content = f"{content}\n\n{reflection_summary}"
            failed_decision_summary = _safe_failed_decision_summary(base)
            if failed_decision_summary:
                content = f"{content}\n\n{failed_decision_summary}"
            confidence_history_summary = _safe_confidence_history_summary(base)
            if confidence_history_summary:
                content = f"{content}\n\n{confidence_history_summary}"
            meeting_quality_summary = _safe_meeting_quality_summary(base)
            if meeting_quality_summary:
                content = f"{content}\n\n{meeting_quality_summary}"
        if content:
            sections.append(f"{label}\n\n{content}")

    if not sections:
        return ""

    header = (
        "=== DAF 会社メモリ ===\n"
        "以下は会社の価値観・CEOの好み・過去の学びです。"
        "すべての提案・判断においてこれらを考慮してください。\n\n"
    )
    return header + "\n\n---\n\n".join(sections) + "\n\n=== 会社メモリ ここまで ==="


def print_memory_status(memory: str) -> None:
    """読み込み状況を標準出力に表示する。"""
    if memory:
        lines = memory.count("\n")
        print(f"[Memory] 会社メモリを読み込みました（{lines}行）")
    else:
        print("[Memory] 会社メモリなし（memory/*.md が見つかりません）")
