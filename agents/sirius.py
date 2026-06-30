from crewai import Agent, LLM
from services.notion_service import load_handbook


def create_sirius(llm: LLM, notion_api_key: str | None = None, page_id: str | None = None) -> Agent:
    handbook, source = load_handbook(
        notion_page_id=page_id,
        fallback_path="memory/sirius.md",
        notion_api_key=notion_api_key,
    )
    print(f"[Sirius] 社員手帳ソース: {source}")

    return Agent(
        role="CPO",
        goal=(
            "ユーザー視点でプロダクトの改善案を評価し、"
            "本当に価値ある体験を届ける機能を特定する。"
        ),
        backstory=(
            f"あなたはSirius、DAFのCPOです。以下があなたの社員手帳です。\n\n{handbook}\n\n"
            "初めて犬を飼ったユーザーのペインポイントと喜びを深く理解し、"
            "プロダクトとして自然で気持ちいい体験になるか評価してください。"
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
