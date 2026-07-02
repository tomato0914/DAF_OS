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


def run_launch_crew(
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
    llm = build_llm(openrouter_api_key)

    # 会社メモリがある場合、全タスクの冒頭に付加するプレフィックスを作る
    _mem = f"{company_memory}\n\n" if company_memory else ""

    orion = create_orion(llm, notion_api_key=notion_api_key, page_id=orion_page_id)
    atlas = create_atlas(llm, notion_api_key=notion_api_key, page_id=atlas_page_id)
    sirius = create_sirius(llm, notion_api_key=notion_api_key, page_id=sirius_page_id)
    nova = create_nova(llm, notion_api_key=notion_api_key, page_id=nova_page_id)
    cosmos = create_cosmos(llm, notion_api_key=notion_api_key, page_id=cosmos_page_id)

    task_sirius = Task(
        description=(
            f"{_mem}"
            f"CEOからの依頼：{ceo_input}\n\n"
            "CPOとして、もふログのApp Store掲載用説明文を作成してください。\n"
            "ターゲットは初めて犬を飼った人です。\n\n"
            "以下の形式で出力してください：\n\n"
            "# もふログ - App Store説明文\n\n"
            "## アプリ名\n"
            "## キャッチコピー（30文字以内）\n"
            "## 短い説明（80文字以内）\n"
            "## 詳細説明（400文字程度）\n"
            "## 主な機能リスト\n"
            "## キーワード（検索用、10個）\n"
        ),
        expected_output="App Store掲載に使えるMarkdown形式の説明文一式。",
        agent=sirius,
    )

    task_nova = Task(
        description=(
            f"{_mem}"
            f"CEOからの依頼：{ceo_input}\n\n"
            "CMOとして、もふログのSNS投稿文を5本作成してください。\n"
            "ターゲットは初めて犬を飼った人です。\n\n"
            "以下の形式で出力してください：\n\n"
            "# もふログ - SNS投稿案\n\n"
            "## 投稿1（リリース告知）\n"
            "## 投稿2（機能紹介）\n"
            "## 投稿3（ユーザーストーリー）\n"
            "## 投稿4（共感訴求）\n"
            "## 投稿5（ダウンロード促進）\n\n"
            "各投稿には本文とハッシュタグを含めてください。"
        ),
        expected_output="SNS投稿5本のMarkdown。各投稿に本文とハッシュタグを含む。",
        agent=nova,
    )

    task_cosmos = Task(
        description=(
            f"{_mem}"
            f"CEOからの依頼：{ceo_input}\n\n"
            "CIOとして、アプリ公開前の確認チェックリストを作成してください。\n\n"
            "以下の形式で出力してください：\n\n"
            "# もふログ - 公開前チェックリスト\n\n"
            "## セキュリティ・プライバシー\n"
            "## データ管理\n"
            "## KPI・計測\n"
            "## 法的確認\n"
            "## インフラ・障害対応\n\n"
            "各項目は「- [ ] タスク内容」形式のチェックボックスで記述してください。"
        ),
        expected_output="公開前チェックリストのMarkdown。全項目がチェックボックス形式。",
        agent=cosmos,
    )

    task_atlas = Task(
        description=(
            f"{_mem}"
            f"CEOからの依頼：{ceo_input}\n\n"
            "CTOとして、もふログ公開前の技術リスク確認レポートを作成してください。\n\n"
            "以下の形式で出力してください（report.md の一部として使用します）：\n\n"
            "## Atlas（CTO）の技術リスク確認\n\n"
            "### 現時点の技術的懸念事項\n"
            "### 公開前に必ず対応すべき事項\n"
            "### 許容できるリスクと理由\n"
            "### 推奨する技術スタック・ツール\n"
        ),
        expected_output="技術リスク確認レポートのMarkdown。懸念・必須対応・許容リスク・推奨スタックを含む。",
        agent=atlas,
    )

    task_orion = Task(
        description=(
            f"{_mem}"
            f"CEOからの依頼：{ceo_input}\n\n"
            "Sirius・Nova・Cosmos・Atlasの成果物を踏まえて、"
            "COOとして最終提案書をまとめてください。\n\n"
            "以下の形式で出力してください：\n\n"
            "# もふログ公開準備 最終提案書\n\n"
            "## Orion（COO）の総合判断\n"
            "## Atlas（CTO）の技術リスク確認\n"
            "## Sirius（CPO）のプロダクト判断\n"
            "## Nova（CMO）のマーケティング方針\n"
            "## Cosmos（CIO）の情報管理方針\n"
            "## 公開に向けたアクションプラン\n"
            "### フェーズ1（公開前 1週間）\n"
            "### フェーズ2（公開当日）\n"
            "### フェーズ3（公開後 1週間）\n"
            "## CEOへの最終提言\n"
        ),
        expected_output="6セクション＋3フェーズのアクションプランを含むMarkdown形式の最終提案書。",
        agent=orion,
        context=[task_sirius, task_nova, task_cosmos, task_atlas],
    )

    task_issues = Task(
        description=(
            f"{_mem}"
            f"CEOからの依頼：{ceo_input}\n\n"
            "会議の全成果物（App Store説明文・SNS投稿・チェックリスト・技術リスク・最終提案）を踏まえて、"
            "COOとして実装タスク（Issue）を3〜5個生成してください。\n\n"
            "必ず以下の形式で、Issueを「---」で区切って出力してください。"
            "各Issueは必ずこのテンプレートに従い、空欄を作らずに全項目を埋めてください：\n\n"
            "# Issue #001\n\n"
            "## タイトル\n"
            "（具体的なタイトル）\n\n"
            "## 背景\n"
            "（会議での議論から導かれた背景）\n\n"
            "## 要件\n"
            "（箇条書きで具体的な要件）\n\n"
            "## 優先度\n"
            "高 / 中 / 低\n\n"
            "## 想定担当\n"
            "Atlas / Sirius / Nova / Cosmos のいずれか\n\n"
            "## 完了条件\n"
            "（チェックボックス形式）\n\n"
            "## 関連成果物\n"
            "（report.md / appstore_description.md / social_posts.md / launch_checklist.md のいずれか）\n\n"
            "## 対象プロダクト\n"
            "（このIssueが対象とするプロダクト名。もふログアプリ本体に関する内容なら mofulog、"
            "DAF OS自体の運用・ツールに関する内容なら DAF_OS。不明な場合は DAF_OS）\n\n"
            "---\n\n"
            "# Issue #002\n\n"
            "...\n\n"
            "Issue番号は001から連番で振ってください。"
        ),
        expected_output=(
            "3〜5個のIssueをMarkdown形式で出力。各Issueは「---」で区切られ、"
            "全項目（タイトル・背景・要件・優先度・想定担当・完了条件・関連成果物・対象プロダクト）が埋められている。"
        ),
        agent=orion,
        context=[task_sirius, task_nova, task_cosmos, task_atlas, task_orion],
    )

    crew = Crew(
        agents=[sirius, nova, cosmos, atlas, orion],
        tasks=[task_sirius, task_nova, task_cosmos, task_atlas, task_orion, task_issues],
        verbose=True,
    )

    crew.kickoff()

    return {
        "appstore_description": str(task_sirius.output.raw),
        "social_posts": str(task_nova.output.raw),
        "launch_checklist": str(task_cosmos.output.raw),
        "report": str(task_orion.output.raw),
        "issues_raw": str(task_issues.output.raw),
    }
