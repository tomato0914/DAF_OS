from crewai import Agent, LLM
from services.notion_service import load_handbook


def create_cosmos(llm: LLM, notion_api_key: str | None = None, page_id: str | None = None) -> Agent:
    handbook, source = load_handbook(
        notion_page_id=page_id,
        fallback_path="memory/cosmos.md",
        notion_api_key=notion_api_key,
    )
    print(f"[Cosmos] 社員手帳ソース: {source}")

    return Agent(
        role="CIO",
        goal=(
            "もふログのデータ活用・計測・セキュリティの観点から改善案を評価し、"
            "意思決定に必要な情報基盤を整える提言を行う。"
        ),
        backstory=(
            f"あなたはCosmos、DAFのCIOです。以下があなたの社員手帳です。\n\n{handbook}\n\n"
            "改善案について、必要なKPI・データ取得設計・プライバシーリスクを評価し、"
            "情報に基づいた経営判断ができる環境を整えるための提言をしてください。"
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
