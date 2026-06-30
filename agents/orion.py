from crewai import Agent, LLM
from services.notion_service import load_handbook


def create_orion(llm: LLM, notion_api_key: str | None = None, page_id: str | None = None) -> Agent:
    handbook, source = load_handbook(
        notion_page_id=page_id,
        fallback_path="memory/orion.md",
        notion_api_key=notion_api_key,
    )
    print(f"[Orion] 社員手帳ソース: {source}")

    return Agent(
        role="COO",
        goal=(
            "プロダクトの改善案を経営視点で評価し、最重要課題を特定する。"
            "最終的にCEOへの提案書としてまとめる。"
        ),
        backstory=(
            f"あなたはOrion、DAFのCOOです。以下があなたの社員手帳です。\n\n{handbook}\n\n"
            "Atlasの技術レビューを受けて、現実的かつ仕組み化できる改善案を優先順位付けし、"
            "CEOが意思決定できる形でまとめてください。"
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
