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

    from crews.launch_crew import run_launch_crew
    from services.issue_parser import parse_and_save_issues

    ceo_input = "もふログの公開準備を進めてください。"

    print("=" * 60)
    print("DAF OS v0.5a 起動 — 公開準備会議 + Issue生成")
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

    print("\n" + "=" * 60)
    print("完了。outputs/ フォルダに全成果物を保存しました。")
    print("=" * 60)


if __name__ == "__main__":
    main()
