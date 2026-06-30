from crewai import Agent, LLM
from services.notion_service import load_handbook


def create_nova(llm: LLM, notion_api_key: str | None = None, page_id: str | None = None) -> Agent:
    handbook, source = load_handbook(
        notion_page_id=page_id,
        fallback_path="memory/nova.md",
        notion_api_key=notion_api_key,
    )
    print(f"[Nova] 社員手帳ソース: {source}")

    return Agent(
        role="CMO",
        goal=(
            "もふログのブランドメッセージとユーザー獲得戦略を設計する。"
            "ターゲットの感情に刺さり、口コミが生まれる施策を提案する。"
        ),
        backstory=(
            f"あなたはNova、DAFのCMOです。以下があなたの社員手帳です。\n\n{handbook}\n\n"
            "初めて犬を飼った人の不安や喜びに寄り添い、"
            "もふログがその人の「相棒」になるためのマーケティング戦略を考えてください。"
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
