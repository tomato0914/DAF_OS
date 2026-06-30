from crewai import Agent, LLM
from services.notion_service import load_handbook


def create_atlas(llm: LLM, notion_api_key: str | None = None, page_id: str | None = None) -> Agent:
    handbook, source = load_handbook(
        notion_page_id=page_id,
        fallback_path="memory/atlas.md",
        notion_api_key=notion_api_key,
    )
    print(f"[Atlas] 社員手帳ソース: {source}")

    return Agent(
        role="CTO",
        goal=(
            "提案された改善案の技術リスク・実装難易度・保守性を評価する。"
            "シンプルで長期的に維持しやすい実装を推奨する。"
        ),
        backstory=(
            f"あなたはAtlas、DAFのCTOです。以下があなたの社員手帳です。\n\n{handbook}\n\n"
            "改善案ごとに実装難易度（高・中・低）と技術リスクを具体的に示してください。"
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
