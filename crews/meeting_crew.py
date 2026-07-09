"""
DAF OS Quest55 — Dedicated Meeting Crew

run_launch_crew() は「もふログ公開準備会議」専用（App Store説明文・SNS投稿・
チェックリスト・Issue生成という固定テンプレート）に縛られているため、
CEOからの自由な相談に直接答えるための専用Crewをここに新設する。

Dashboardの「💬 DAFに相談」からのみ呼ばれる。main.py / ./run_daf.sh からは呼ばれない。
"""

from datetime import datetime
from crewai import Crew, Task, LLM
from agents.orion import create_orion
from agents.atlas import create_atlas
from agents.sirius import create_sirius
from agents.nova import create_nova
from agents.cosmos import create_cosmos


def build_llm(api_key: str, max_tokens: int = 3000) -> LLM:
    """
    max_tokens を明示指定する（launch_crew.pyと同じ理由）。
    残クレジットが少ない状態でも動くよう3000に抑えている。
    """
    return LLM(
        model="openrouter/openai/gpt-4o-mini",
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=max_tokens,
    )


def run_meeting_crew(
    ceo_input: str,
    openrouter_api_key: str,
    notion_api_key: str | None = None,
    orion_page_id: str | None = None,
    atlas_page_id: str | None = None,
    sirius_page_id: str | None = None,
    nova_page_id: str | None = None,
    cosmos_page_id: str | None = None,
    company_memory: str = "",
) -> dict[str, str]:
    from services.ai_runtime_guard import require_ai_enabled
    if not require_ai_enabled("Meeting Crew / AI経営会議"):
        message = (
            "AI Runtime GuardによりAI呼び出しが無効化されているため、"
            "AI経営会議は実行されませんでした（DAF_RUNTIME_MODE=production かつ "
            "DAF_AI_ENABLED=true の場合のみ実行できます）。"
        )
        meeting_log = (
            f"# DAFに相談 会議ログ\n\n"
            f"> 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"> CEOからの相談: {ceo_input}\n\n"
            "---\n\n"
            f"⚠️ {message}\n"
        )
        return {
            "sirius": message, "nova": message, "cosmos": message,
            "atlas": message, "orion": message, "meeting_log": meeting_log,
        }

    llm = build_llm(openrouter_api_key)
    llm_long = build_llm(openrouter_api_key, max_tokens=3000)

    # 会社メモリ（company_memory.md / ceo_preferences.md / lessons_learned.md /
    # product_status.md / completed_issues.md）を全タスクの冒頭に付加する
    _mem = f"{company_memory}\n\n" if company_memory else ""

    # Quest54と同じ推論の指針。相談専用Crewでも完了済みIssueの再提案防止・
    # プロダクト現状の考慮・CEOの質問への直接回答を徹底する
    # Quest56で【経営サマリー】優先の一文を追加。Quest57でCEOの過去の意思決定を参考にする一文を追加。
    # 注意：この _reasoning_note は crews/launch_crew.py にも同一の文言で重複定義されている
    # （MVPのため共通化はまだ行っていない。変更する場合は両ファイルを同時に更新すること）。
    _reasoning_note = (
        "\n\n【推論の指針】\n"
        "- 会社メモリの【経営サマリー】を最優先の事実として扱い、他の記述と矛盾する場合は経営サマリーを優先すること\n"
        "- 会社メモリの【完了済みIssue一覧】に記載されている項目は解決済みとして扱い、同じ内容を再提案しないこと\n"
        "- 会社メモリの【プロダクトの現状】を踏まえた上で、今何が必要かを判断すること\n"
        "- 会社メモリの【CEOの過去の意思決定】を参考にし、CEOが過去に承認・却下した傾向と一貫性のある提案をすること\n"
        "- CEOからの依頼・質問には一般論で答えず、まずその依頼・質問に直接答えること\n"
        "- 上記のメモリ内容と矛盾しない、現在の状況に基づいた具体的な提案をすること\n\n"
    )

    # Quest51と同じ、根拠memoryを明記させる指示（相談専用Crewでは全タスクに付与する）
    _memory_note = (
        "\n\n回答の最後に必ず `### 参照したmemory` という見出しを付け、"
        "company_memory.md / ceo_preferences.md / lessons_learned.md / "
        "product_status.md / completed_issues.md / 自分の社員手帳（例：atlas.md）のうち、"
        "どれを根拠にしたかを箇条書きで明記してください。"
    )

    orion = create_orion(llm_long, notion_api_key=notion_api_key, page_id=orion_page_id)
    atlas = create_atlas(llm, notion_api_key=notion_api_key, page_id=atlas_page_id)
    sirius = create_sirius(llm, notion_api_key=notion_api_key, page_id=sirius_page_id)
    nova = create_nova(llm, notion_api_key=notion_api_key, page_id=nova_page_id)
    cosmos = create_cosmos(llm, notion_api_key=notion_api_key, page_id=cosmos_page_id)

    task_sirius = Task(
        description=(
            f"{_mem}{_reasoning_note}"
            f"CEOからの相談：{ceo_input}\n\n"
            "CPOとして、ユーザー体験・初心者目線（初めて犬を飼った人）から、"
            "この相談に対する優先順位・考慮すべきポイントを提案してください。"
            f"{_memory_note}"
        ),
        expected_output="ユーザー体験・初心者目線からの提案。CEOの相談に直接答え、優先順位を示す。",
        agent=sirius,
    )

    task_nova = Task(
        description=(
            f"{_mem}{_reasoning_note}"
            f"CEOからの相談：{ceo_input}\n\n"
            "CMOとして、マーケティング・最初の100人獲得・発信戦略の観点から、"
            "この相談に対する提案をしてください。"
            f"{_memory_note}"
        ),
        expected_output="マーケティング・初期ユーザー獲得・発信戦略の観点からの提案。CEOの相談に直接答える。",
        agent=nova,
    )

    task_cosmos = Task(
        description=(
            f"{_mem}{_reasoning_note}"
            f"CEOからの相談：{ceo_input}\n\n"
            "CIOとして、AI活用・自動化・データ・KPI・情報管理の観点から、"
            "この相談に対する提案をしてください。"
            f"{_memory_note}"
        ),
        expected_output="AI活用・自動化・データ・KPI・情報管理の観点からの提案。CEOの相談に直接答える。",
        agent=cosmos,
    )

    task_atlas = Task(
        description=(
            f"{_mem}{_reasoning_note}"
            f"CEOからの相談：{ceo_input}\n\n"
            "CTOとして、技術リスク・実装難易度・シンプルな設計の観点から、"
            "この相談に対する提案をしてください。"
            f"{_memory_note}"
        ),
        expected_output="技術リスク・実装難易度・シンプルな設計の観点からの提案。CEOの相談に直接答える。",
        agent=atlas,
    )

    task_orion = Task(
        description=(
            f"{_mem}{_reasoning_note}"
            f"CEOからの相談：{ceo_input}\n\n"
            "Sirius・Nova・Cosmos・Atlasの意見を統合し、"
            "COOとしてCEOが次に取るべき意思決定を1〜3個に絞って提案してください。\n\n"
            "以下の形式で出力してください：\n\n"
            "## Orion（COO）の統合判断\n"
            "## CEOが次に取るべき意思決定（1〜3個）\n"
            f"{_memory_note}"
        ),
        expected_output="4人の意見を統合し、CEOが次に取るべき意思決定を1〜3個に絞った提案。",
        agent=orion,
        context=[task_sirius, task_nova, task_cosmos, task_atlas],
    )

    crew = Crew(
        agents=[sirius, nova, cosmos, atlas, orion],
        tasks=[task_sirius, task_nova, task_cosmos, task_atlas, task_orion],
        verbose=True,
    )

    crew.kickoff()

    # Quest69: 会議提案（CEOからの相談内容）に対するDecision Confidence Scoreを
    # 会議ログ末尾に追加する。confidence_serviceが無い・エラーになる場合でも
    # 会議ログ生成自体は止めない（未分類時と同じ「30% / 十分な過去データがありません」を返す）。
    # 注意：この _safe_confidence_block は crews/launch_crew.py にも同一の実装で
    # 重複定義されている（MVPのため共通化はまだ行っていない。変更する場合は両ファイルを同時に更新すること）。
    def _safe_confidence_block(text: str) -> str:
        try:
            from services.confidence_service import calculate_confidence
            result = calculate_confidence(text)
        except Exception as e:
            print(f"[警告] Confidence Scoreの計算に失敗しました：{e}")
            result = {"confidence": 30, "reason": "十分な過去データがありません"}
        confidence = result.get("confidence", 30)
        reason = result.get("reason", "十分な過去データがありません")
        return f"## Confidence\nConfidence：{confidence}%\n理由：{reason}\n"

    meeting_log = (
        f"# DAFに相談 会議ログ\n\n"
        f"> 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"> CEOからの相談: {ceo_input}\n\n"
        "---\n\n"
        f"## Sirius（CPO）\n\n{task_sirius.output.raw}\n\n"
        "---\n\n"
        f"## Nova（CMO）\n\n{task_nova.output.raw}\n\n"
        "---\n\n"
        f"## Cosmos（CIO）\n\n{task_cosmos.output.raw}\n\n"
        "---\n\n"
        f"## Atlas（CTO）\n\n{task_atlas.output.raw}\n\n"
        "---\n\n"
        f"## Orion（COO）\n\n{task_orion.output.raw}\n\n"
        "---\n\n"
        f"{_safe_confidence_block(ceo_input)}"
    )

    return {
        "sirius": str(task_sirius.output.raw),
        "nova": str(task_nova.output.raw),
        "cosmos": str(task_cosmos.output.raw),
        "atlas": str(task_atlas.output.raw),
        "orion": str(task_orion.output.raw),
        "meeting_log": meeting_log,
    }
