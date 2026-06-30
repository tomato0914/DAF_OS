from crewai import Crew, Task, LLM
from agents.orion import create_orion
from agents.atlas import create_atlas
from agents.sirius import create_sirius
from agents.nova import create_nova
from agents.cosmos import create_cosmos


def build_llm(api_key: str) -> LLM:
    return LLM(
        model="openrouter/openai/gpt-4o-mini",
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def run_mofulog_crew(
    ceo_input: str,
    openrouter_api_key: str,
    notion_api_key: str | None = None,
    orion_page_id: str | None = None,
    atlas_page_id: str | None = None,
    sirius_page_id: str | None = None,
    nova_page_id: str | None = None,
    cosmos_page_id: str | None = None,
) -> str:
    llm = build_llm(openrouter_api_key)

    orion = create_orion(llm, notion_api_key=notion_api_key, page_id=orion_page_id)
    atlas = create_atlas(llm, notion_api_key=notion_api_key, page_id=atlas_page_id)
    sirius = create_sirius(llm, notion_api_key=notion_api_key, page_id=sirius_page_id)
    nova = create_nova(llm, notion_api_key=notion_api_key, page_id=nova_page_id)
    cosmos = create_cosmos(llm, notion_api_key=notion_api_key, page_id=cosmos_page_id)

    task_atlas = Task(
        description=(
            f"CEOからの依頼：\n{ceo_input}\n\n"
            "CTOとして技術レビューを行ってください。\n"
            "各改善アイデアの実装難易度（高・中・低）、技術リスク、保守性を示してください。"
        ),
        expected_output="改善案ごとの技術評価。各項目に実装難易度・技術リスク・コメントを含む。",
        agent=atlas,
    )

    task_sirius = Task(
        description=(
            f"CEOからの依頼：\n{ceo_input}\n\n"
            "CPOとしてプロダクト視点でレビューしてください。\n"
            "初めて犬を飼ったユーザーのペインポイントを起点に、"
            "どの改善が最も価値ある体験をもたらすか評価してください。"
        ),
        expected_output="ユーザー価値ベースの改善案評価。体験品質・優先度・UXコメントを含む。",
        agent=sirius,
    )

    task_nova = Task(
        description=(
            f"CEOからの依頼：\n{ceo_input}\n\n"
            "CMOとしてマーケティング戦略を提案してください。\n"
            "初めて犬を飼った人に届くメッセージ、集客チャネル、口コミを生む仕掛けを考えてください。"
        ),
        expected_output="マーケティング戦略の提案。ターゲット感情・チャネル・コンテンツ施策を含む。",
        agent=nova,
    )

    task_cosmos = Task(
        description=(
            f"CEOからの依頼：\n{ceo_input}\n\n"
            "CIOとしてデータ・情報管理の観点から評価してください。\n"
            "必要なKPI設計、データ取得の可否、プライバシーリスクを示してください。"
        ),
        expected_output="データ・情報基盤の評価。KPI案・計測設計・プライバシーリスクを含む。",
        agent=cosmos,
    )

    task_orion = Task(
        description=(
            f"CEOからの依頼：\n{ceo_input}\n\n"
            "Atlas（CTO）・Sirius（CPO）・Nova（CMO）・Cosmos（CIO）の意見を統合し、"
            "COOとして以下の形式で最終提案書をまとめてください。\n\n"
            "# もふログ公開準備会議\n\n"
            "## Orion（COO）\n"
            "## Atlas（CTO）\n"
            "## Sirius（CPO）\n"
            "## Nova（CMO）\n"
            "## Cosmos（CIO）\n"
            "## 最終提案\n"
        ),
        expected_output=(
            "上記6セクションを含むMarkdown形式の会議録。"
            "各メンバーの主要意見を簡潔にまとめ、最終提案にCEO向けのアクションプランを含む。"
        ),
        agent=orion,
        context=[task_atlas, task_sirius, task_nova, task_cosmos],
    )

    crew = Crew(
        agents=[atlas, sirius, nova, cosmos, orion],
        tasks=[task_atlas, task_sirius, task_nova, task_cosmos, task_orion],
        verbose=True,
    )

    result = crew.kickoff()
    return str(result)
