import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OUTPUTS = Path("outputs")


def check_env() -> str | None:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        print("[エラー] OPENROUTER_API_KEY が設定されていません。")
        print(".env ファイルに以下を追加してください：")
        print("  OPENROUTER_API_KEY=sk-or-...")
        return None
    return key


def save(filename: str, content: str) -> Path:
    path = OUTPUTS / filename
    path.write_text(content, encoding="utf-8")
    print(f"  ✓ {path}")
    return path


def clean_outputs() -> None:
    """実行前に前回の生成物を削除する。フォルダ自体は残す。"""
    print("[Clean]")

    # フォルダ内のファイルをすべて削除（フォルダは残す）
    dirs_to_clear = [
        OUTPUTS / "issues",
        OUTPUTS / "claude_tasks",
    ]
    for d in dirs_to_clear:
        if d.exists():
            files = [f for f in d.iterdir() if f.is_file()]
            for f in files:
                f.unlink()
            if files:
                print(f"  ✓ {d} を初期化（{len(files)}件削除）")
            else:
                print(f"  - {d} は空でした")
        else:
            d.mkdir(parents=True)
            print(f"  ✓ {d} を作成")

    # トップレベルの再生成ファイルを削除
    files_to_delete = [
        OUTPUTS / "appstore_description.md",
        OUTPUTS / "social_posts.md",
        OUTPUTS / "launch_checklist.md",
        OUTPUTS / "report.md",
        OUTPUTS / "meeting_log.md",
        OUTPUTS / "github_issue_results.md",
        OUTPUTS / "dashboard.md",
        OUTPUTS / "implementation_queue.md",
        OUTPUTS / "memory_update_suggestions.md",
        OUTPUTS / "pr_draft.md",
        OUTPUTS / "autonomous_flow.md",
        OUTPUTS / "ceo_brief.md",
    ]
    deleted = [f for f in files_to_delete if f.exists() and (f.unlink() or True)]
    if deleted:
        print(f"  ✓ outputs/ の成果物を初期化（{len(deleted)}件削除）")


def main():
    openrouter_key = check_env()
    if not openrouter_key:
        sys.exit(1)

    notion_key = os.getenv("NOTION_API_KEY") or None
    if notion_key:
        print("[Notion] API キー検出 → Notionから社員手帳を読み込みます")
    else:
        print("[Notion] API キー未設定 → ローカル memory/*.md を使用します")

    os.chdir(Path(__file__).parent)
    OUTPUTS.mkdir(exist_ok=True)
    clean_outputs()

    from crews.launch_crew import run_launch_crew
    from services.issue_parser import parse_and_save_issues
    from services.claude_task_generator import generate_claude_tasks
    from services.github_issue_service import register_issues, save_results
    from services.dashboard_generator import save_dashboard
    from services.notion_log_service import try_save_log
    from services.notification_service import notify
    from services.implementation_service import generate_implementation_queue
    from services.memory_service import load_company_memory, print_memory_status
    from services.memory_review_service import try_generate_memory_suggestions
    from services.approval_service import run_approval_generation
    from services.pr_preparation_service import generate_pr_draft
    from services.autonomous_flow_service import run_autonomous_flow_generation
    from services.product_registry_service import load_products, print_product_status
    from services.ceo_brief_service import try_generate_ceo_brief

    # 会社メモリ読み込み（起動時に自動実行）
    company_memory = load_company_memory()
    print_memory_status(company_memory)

    # マルチプロダクト読み込み（起動時に自動実行）
    products = load_products()
    print_product_status(products)

    ceo_input = "もふログの公開準備を進めてください。"

    print("=" * 60)
    print("DAF OS v1.3 起動 — 公開準備会議 + Issue生成 + Claude Task + GitHub登録 + ダッシュボード")
    print("CEO入力：", ceo_input)
    print("=" * 60)

    try:
        results = run_launch_crew(
            ceo_input=ceo_input,
            openrouter_api_key=openrouter_key,
            notion_api_key=notion_key,
            orion_page_id=os.getenv("ORION_PAGE_ID") or None,
            atlas_page_id=os.getenv("ATLAS_PAGE_ID") or None,
            sirius_page_id=os.getenv("SIRIUS_PAGE_ID") or None,
            nova_page_id=os.getenv("NOVA_PAGE_ID") or None,
            cosmos_page_id=os.getenv("COSMOS_PAGE_ID") or None,
            company_memory=company_memory,
        )
    except Exception as e:
        print(f"\n[エラー] 実行中に問題が発生しました：{e}")
        print("APIキーや通信環境を確認してください。")
        sys.exit(1)

    print("\n生成された成果物：")
    save("appstore_description.md", results["appstore_description"])
    save("social_posts.md", results["social_posts"])
    save("launch_checklist.md", results["launch_checklist"])
    save("report.md", results["report"])
    save("meeting_log.md", results["meeting_log"])

    # Issue を個別ファイルに分割して保存
    issues_dir = OUTPUTS / "issues"
    issue_files = parse_and_save_issues(results["issues_raw"], issues_dir)

    if issue_files:
        print(f"\n生成されたIssue（{len(issue_files)}件）：")
        for path in issue_files:
            print(f"  ✓ {path}")
    else:
        print("\n[警告] Issueファイルの分割に失敗しました。")
        fallback = OUTPUTS / "issues" / "issues_raw.md"
        fallback.write_text(results["issues_raw"], encoding="utf-8")
        print(f"  → 生データを保存しました：{fallback}")

    # Issue から Claude Code 用実装指示書を生成
    claude_tasks_dir = OUTPUTS / "claude_tasks"
    if issue_files:
        task_files = generate_claude_tasks(issues_dir, claude_tasks_dir)
        if task_files:
            print(f"\n生成されたClaude Task指示書（{len(task_files)}件）：")
            for path in task_files:
                print(f"  ✓ {path}")
        else:
            print("\n[警告] Claude Task指示書の生成に失敗しました。")
    else:
        print("\n[スキップ] Issueがないため Claude Task 生成をスキップします。")

    # GitHub Issues 登録
    github_token = os.getenv("GITHUB_TOKEN") or None
    github_owner = os.getenv("GITHUB_REPO_OWNER") or None
    github_repo  = os.getenv("GITHUB_REPO_NAME") or None

    if not github_token:
        print("\n[GitHub] GITHUB_TOKEN 未設定 → GitHub Issue登録をスキップします")
        print("  登録するには .env に GITHUB_TOKEN / GITHUB_REPO_OWNER / GITHUB_REPO_NAME を追加してください")
    elif not github_owner or not github_repo:
        print("\n[GitHub] GITHUB_REPO_OWNER または GITHUB_REPO_NAME が未設定 → スキップします")
    elif not issue_files:
        print("\n[GitHub] 登録するIssueがありません → スキップします")
    else:
        print(f"\n[GitHub] {github_owner}/{github_repo} にIssueを登録します...")
        try:
            gh_results = register_issues(
                issues_dir=issues_dir,
                token=github_token,
                owner=github_owner,
                repo=github_repo,
            )
            result_path = OUTPUTS / "github_issue_results.md"
            save_results(gh_results, github_owner, github_repo, result_path)
            print(f"  ✓ {result_path}")
        except RuntimeError as e:
            print(f"\n[エラー] GitHub登録に失敗しました：{e}")
            print("  トークンの権限（repo スコープ）とリポジトリ名を確認してください")

    # 実装キュー生成（GitHub Issues → Claude Code プロンプト）
    print("\n実装キューを生成中...")
    generate_implementation_queue(
        outputs=OUTPUTS,
        token=github_token,
        owner=github_owner,
        repo=github_repo,
    )

    # PR作成準備（コード変更差分から下書きを生成。commit/push/PR作成はしない）
    print("\nPR作成準備を確認中...")
    generate_pr_draft(OUTPUTS)

    # ダッシュボード生成（最後に実行して全情報を集約）
    print("\nダッシュボードを生成中...")
    dashboard_path = save_dashboard(
        outputs=OUTPUTS,
        github_token=github_token,
        github_owner=github_owner,
        github_repo=github_repo,
    )
    print(f"  ✓ {dashboard_path}")

    # メモリ見直し提案（dashboard.md 生成後に実行）
    print("\nメモリ見直し提案を生成中...")
    try_generate_memory_suggestions(
        outputs=OUTPUTS,
        memory_dir=Path(__file__).parent / "memory",
        openrouter_api_key=openrouter_key,
    )

    # 承認センター（dashboard & memory_review 生成後に実行）
    run_approval_generation(OUTPUTS)

    # 半自律実装フロー（承認済みの実装アイテムのみを対象に生成）
    print("\n半自律実装フローを確認中...")
    run_autonomous_flow_generation(OUTPUTS)

    # CEOデイリーブリーフ（承認・実装キュー・プロダクト状況が出揃った後に生成）
    try_generate_ceo_brief(OUTPUTS)

    # Decision Outcome自動更新（Quest72-2）
    # Reflection Reportが「更新後の最新状態」を元に再生成されるよう、
    # 必ずReflection Report再生成の直前に実行する。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nDecision Outcomeを自動更新中...")
    try:
        from services.outcome_update_service import update_pending_outcomes
        outcome_result = update_pending_outcomes(memory_dir=Path(__file__).parent / "memory")
        checked = len(outcome_result.get("checked", []))
        updated = len(outcome_result.get("updated", []))
        skipped = len(outcome_result.get("skipped", []))
        print(f"[Outcome Update] 検査: {checked}件 / 更新: {updated}件 / 保留: {skipped}件")
        if outcome_result.get("updated"):
            print("  更新されたIssue:", ", ".join(f"#{i}" for i in outcome_result["updated"]))
    except Exception as e:
        print(f"[Outcome Update] 警告: Decision Outcome自動更新に失敗しました: {e}")

    # Failed Decision Memory更新（Quest73）
    # Decision Outcome自動更新でFAILEDになった意思決定を、同じ実行内で
    # memory/failed_decisions.md に反映する。Reflection Reportや次回会議で
    # 参照しやすくするため、Reflection Report再生成の直前に実行する。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nFailed Decision Memoryを更新中...")
    try:
        from services.failed_decision_service import update_failed_decision_memory
        failed_result = update_failed_decision_memory(memory_dir=Path(__file__).parent / "memory")
        added = len(failed_result.get("added", []))
        skipped_existing = len(failed_result.get("skipped_existing", []))
        total_failed = failed_result.get("total_failed", 0)
        print(f"[Failed Decision Memory] 追加: {added}件 / 既存: {skipped_existing}件 / 総失敗数: {total_failed}件")
        if failed_result.get("added"):
            print("  新規登録:", ", ".join(f"#{i}" for i in failed_result["added"]))
    except Exception as e:
        print(f"[Failed Decision Memory] 警告: 更新に失敗しました: {e}")

    # Decision Confidence History更新（Quest74）
    # decision_outcomes.mdのSUCCESS/FAILEDと、承認待ち時点のConfidence予測を
    # 突き合わせ、DAF OS自身の予測精度を記録する。Reflection Reportが
    # 更新後の最新状態を元に再生成されるよう、必ずその直前に実行する。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nConfidence Historyを更新中...")
    try:
        from services.confidence_history_service import update_confidence_history
        confidence_history_result = update_confidence_history(memory_dir=Path(__file__).parent / "memory")
        ch_added = len(confidence_history_result.get("added", []))
        ch_skipped = len(confidence_history_result.get("skipped_existing", []))
        ch_total = confidence_history_result.get("total", 0)
        print(f"[Confidence History] 追加: {ch_added}件 / 既存: {ch_skipped}件 / 総件数: {ch_total}件")
        if confidence_history_result.get("added"):
            print("  新規登録:", ", ".join(f"#{i}" for i in confidence_history_result["added"]))
    except Exception as e:
        print(f"[Confidence History] 警告: 更新に失敗しました: {e}")

    # Reflection Report（Quest60）
    # 会議ログ（meeting_log.md）・CEO Decision History・KPI Memory・承認結果が
    # 出揃った最後のタイミングで振り返りレポートを再生成する。
    # Decision Outcome自動更新・Failed Decision Memory更新・Confidence History更新
    # （直前のステップ）の後に実行することで、更新後の最新状態を反映したレポートになる。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nReflection Reportを更新中...")
    try:
        from services.reflection_service import generate_reflection_report
        reflection_path = generate_reflection_report(
            outputs_dir=OUTPUTS,
            memory_dir=Path(__file__).parent / "memory",
        )
        print(f"  ✓ {reflection_path}")
    except Exception as e:
        print(f"  [警告] Reflection Reportの生成に失敗しました（処理は続行します）：{e}")

    # Meeting Quality更新（Quest75）
    # 今回の会議がKPI・Reflection・Failed Decision・Confidence Historyを
    # どれだけ活用できたか、提案の質（件数・重複の少なさ）はどうだったかを
    # 自己評価し、memory/meeting_quality_history.md に記録する。
    # Reflection Report再生成の後に実行することで、最新のReflection結果を
    # 踏まえた評価になる。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nMeeting Qualityを更新中...")
    try:
        from services.meeting_quality_service import update_meeting_quality_history
        quality_result = update_meeting_quality_history(
            outputs_dir=OUTPUTS,
            memory_dir=Path(__file__).parent / "memory",
        )
        if "error" in quality_result:
            print(f"[Meeting Quality] 警告: 更新に失敗しました: {quality_result['error']}")
        else:
            action_label = "新規登録" if quality_result["action"] == "added" else "更新"
            print(
                f"[Meeting Quality] {action_label}（{quality_result['date']}）: "
                f"Score {quality_result['score']} / 100（Rating {quality_result['rating']} / 10）"
            )
    except Exception as e:
        print(f"[Meeting Quality] 警告: 更新に失敗しました: {e}")

    # KPI Alert Report生成（Quest78）
    # 直近2件のKPIスナップショットを比較し、悪化しているKPIをStrategic Goal・
    # Initiativeと紐付けてoutputs/kpi_alerts.mdに記録する。Meeting Quality更新の後、
    # 一連のmemory更新が出揃った最後のタイミングで実行する。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nKPI Alert Reportを生成中...")
    try:
        from services.kpi_alert_service import generate_kpi_alert_report
        kpi_alert_path = generate_kpi_alert_report()
        print(f"  ✓ {kpi_alert_path}")
    except Exception as e:
        print(f"  [警告] KPI Alert Reportの生成に失敗しました（処理は続行します）：{e}")

    # Autonomous Issue Suggestions生成（Quest79）
    # KPI Alert Reportが出揃った直後に実行し、悪化しているKPIから改善Issue案を
    # 自動生成する。生成物はCEO承認待ちのMarkdown案であり、GitHub Issue化や
    # 承認センターへの投入は行わない（CEOが別途判断する）。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nAutonomous Issue Suggestionsを生成中...")
    try:
        from services.autonomous_issue_service import generate_autonomous_issues
        autonomous_issues = generate_autonomous_issues()
        print(f"  ✓ outputs/autonomous_issues.md（{len(autonomous_issues)}件）")
    except Exception as e:
        print(f"  [警告] Autonomous Issue Suggestionsの生成に失敗しました（処理は続行します）：{e}")

    # CEO Inbox生成（Quest80）
    # KPI Alert・Autonomous Issue Suggestions・Pending Approvals・Memory Update
    # Suggestionsが出揃った最後のタイミングで、危険度の高い順に1つのMarkdownへ
    # 集約する。CEOが毎回複数ファイルを探さなくても良いようにするため。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nCEO Inboxを生成中...")
    try:
        from services.ceo_inbox_service import generate_ceo_inbox
        ceo_inbox_path = generate_ceo_inbox()
        print(f"  ✓ {ceo_inbox_path}")
    except Exception as e:
        print(f"  [警告] CEO Inboxの生成に失敗しました（処理は続行します）：{e}")

    # Weekly Board Meeting生成（Quest82）
    # Strategic Goals・Initiatives・KPI Alert・Autonomous Issue・CEO Decision・
    # Meeting Quality・Reflection Report・CEO Inboxが出揃った最後のタイミングで、
    # 週次の経営会議資料として1つのMarkdownへ集約する。CEOが毎日細かい数字を
    # 追わなくても「今週何が起きたか・最大のリスク・来週の優先事項」を
    # 把握できるようにするため。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nWeekly Board Meetingを生成中...")
    try:
        from services.weekly_board_meeting_service import generate_weekly_board_meeting
        weekly_board_meeting_path = generate_weekly_board_meeting()
        print(f"  ✓ {weekly_board_meeting_path}")
    except Exception as e:
        print(f"  [警告] Weekly Board Meetingの生成に失敗しました（処理は続行します）：{e}")

    # Scenario Planning生成（Quest83）
    # DAU急減・App Store審査落ち・初回ユーザー不足・Crash Rate急増など
    # 「まだ起きていないが起こり得るリスク」を先回りしてシミュレーションする。
    # シナリオ定義は固定でKPI実測値に依存しないため、他の生成物の順序に
    # 影響されず単独で実行できる。Weekly Board Meeting生成の直後・Notion議事録
    # 保存の前に実行する。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nScenario Planningを生成中...")
    try:
        from services.scenario_planning_service import generate_scenario_planning
        scenario_planning_path = generate_scenario_planning()
        print(f"  ✓ {scenario_planning_path}")
    except Exception as e:
        print(f"  [警告] Scenario Planningの生成に失敗しました（処理は続行します）：{e}")

    # Capital Allocation Engine生成（Quest84）
    # KPI Alert・Initiative・Weekly Board Meeting・Scenario Planningが出揃った
    # 最後のタイミングで、「今週どこに時間・エネルギーを使うべきか」の推奨配分を
    # ルールベースで算出する。Scenario Planning生成の直後・Notion議事録保存の前に
    # 実行する（Weekly Board MeetingとScenario Planningのファイルを読み込むため）。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nCapital Allocationを生成中...")
    try:
        from services.capital_allocation_service import generate_capital_allocation
        capital_allocation_path = generate_capital_allocation()
        print(f"  ✓ {capital_allocation_path}")
    except Exception as e:
        print(f"  [警告] Capital Allocationの生成に失敗しました（処理は続行します）：{e}")

    # Self Improvement生成（Quest85）
    # KPI Alert・Autonomous Issue・Pending Approval・Meeting Qualityが出揃った
    # 最後のタイミングで、DAF OS自身の弱点・次に作るべきQuestをルールベースで
    # 提案する。Capital Allocation生成の直後・Notion議事録保存の前に実行する。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nSelf Improvementを生成中...")
    try:
        from services.self_improvement_service import generate_self_improvement_suggestions
        self_improvement_path = generate_self_improvement_suggestions()
        print(f"  ✓ {self_improvement_path}")
    except Exception as e:
        print(f"  [警告] Self Improvementの生成に失敗しました（処理は続行します）：{e}")

    # Issue Auto Pipeline生成（Quest87）
    # CEO Decision History（Quest81）でCEOがapproveしたAutonomous Issue・
    # Self Improvement提案・Memory Update Suggestionsを、実装待ちIssueとして
    # outputs/issue_pipeline/generated_issues.md に自動生成する。Self Improvement
    # 生成の直後・Notion議事録保存の前に実行する。GitHub Issue化は行わない
    # （次のQuest88でClaude Code実装へ繋げる前提の準備段階）。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nIssue Pipelineを生成中...")
    try:
        from services.issue_pipeline_service import generate_issue_pipeline
        issue_pipeline_path = generate_issue_pipeline()
        print(f"  ✓ {issue_pipeline_path}")
    except Exception as e:
        print(f"  [警告] Issue Pipelineの生成に失敗しました（処理は続行します）：{e}")

    # Execution Planner生成（Quest88）
    # Issue Pipeline（Quest87）の実装待ちIssueをAsset Type（成果物の種類）ごとに
    # 分類し、Deliverables・Tasksに分解したExecution Planを生成する。まだ
    # 成果物生成（Asset Generation）は行わない（次のQuest89で接続する）。
    # Issue Pipeline生成の直後・Notion議事録保存の前に実行する。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nExecution Plannerを生成中...")
    try:
        from services.execution_planner_service import generate_execution_plans
        execution_plans = generate_execution_plans()
        print(f"  ✓ outputs/execution_plans/（現在有効なPlan: {len(execution_plans)}件）")
    except Exception as e:
        print(f"  [警告] Execution Plannerの生成に失敗しました（処理は続行します）：{e}")

    # Asset Generator生成（Quest90・v1はline_stickerのみ対応）
    # Execution Planner（Quest88）で生成されたline_sticker向けのExecution Planを
    # 起点に、LINEスタンプ素材一式（仮画像・phrases・prompts・metadata・
    # stickers.zip）を生成する。Execution Planner生成の直後・Notion議事録保存の
    # 前に実行する。既に生成済み（pending_review/approved）の場合は再生成しない。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nAsset Generatorを生成中...")
    try:
        from services.asset_generator_service import generate_assets
        asset_result = generate_assets()
        print(f"  ✓ {asset_result}")
    except Exception as e:
        print(f"  [警告] Asset Generatorの生成に失敗しました（処理は続行します）：{e}")

    # Notification Center生成（Quest92）
    # レビュー待ちAsset・Critical KPI Alert・実装待ちIssueなど、CEOが見逃す
    # べきでない重要イベントを outputs/notifications.md に集約する。
    # Asset Generator生成の直後・Notion議事録保存の前に実行する。
    # ここでの失敗はDaily Brief/AI会議全体を止めないよう、警告ログのみ出して続行する。
    print("\nNotification Centerを更新中...")
    try:
        from services.notification_service import generate_notifications
        added_notifications = generate_notifications()
        print(f"  ✓ 新規通知: {len(added_notifications)}件")
    except Exception as e:
        print(f"  [警告] Notification Centerの更新に失敗しました（処理は続行します）：{e}")

    # Notion 議事録保存（dashboard.md 生成後に実行）
    notion_log_db = os.getenv("NOTION_LOG_DATABASE_ID") or None
    try_save_log(OUTPUTS, notion_key, notion_log_db)

    # Mac 通知（最後に実行）
    notify(OUTPUTS, issue_count=len(issue_files) if issue_files else 0)

    print("\n" + "=" * 60)
    print("完了。outputs/ フォルダに全成果物を保存しました。")
    print("=" * 60)
    print(f"\n📋 ダッシュボード: {dashboard_path}")


if __name__ == "__main__":
    main()
