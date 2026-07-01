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
        OUTPUTS / "github_issue_results.md",
        OUTPUTS / "dashboard.md",
        OUTPUTS / "implementation_queue.md",
        OUTPUTS / "memory_update_suggestions.md",
        OUTPUTS / "pr_draft.md",
        OUTPUTS / "autonomous_flow.md",
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

    # 会社メモリ読み込み（起動時に自動実行）
    company_memory = load_company_memory()
    print_memory_status(company_memory)

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
