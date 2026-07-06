"""
DAF OS Quest88 — Execution Planner サービス

Issue Auto Pipeline（Quest87）は「CEOがapproveした提案 → 実装待ちIssue」までを
自動化した。しかし「そのIssueを実際にどう作るか（制作工程）」はまだ計画されて
いなかった。このサービスは実装待ちIssueをAsset Type（成果物の種類）ごとに分類し、
Deliverables（成果物一覧）とTasks（実行可能な制作タスク）に分解した
Execution Planを outputs/execution_plans/ に生成する。

最終目標「Project → Digital Asset Completed」に向けた、
「AIが制作計画を立てられること」までがこのQuestのゴール。
実際の成果物生成（Asset Generation）はまだ行わない（Quest89で接続する）。

Asset Type（v1固定・7種類）：
- line_sticker  : LINEスタンプ
- youtube_short : YouTube Shorts動画
- blog          : ブログ記事
- ebook         : 電子書籍
- ios_app       : iOSアプリ
- saas          : SaaS / Webサービス
- generic       : 上記のいずれにも該当しない場合のフォールバック

Asset Type判定：Issueのタイトル・説明文に含まれるキーワードで簡易判定する
（例：「LINE」「スタンプ」→ line_sticker、「YouTube」「動画」「Shorts」→
youtube_short 等）。v1では判定材料をIssueのタイトル・説明文に絞っている
（Goal・Initiativeの文言まで含めた判定はv2以降の課題。他のQuestで採用している
「まずはシンプルに」という方針に合わせた）。

実行タスクType（v1固定・9種類）：
planning / text_generation / image_generation / audio_generation /
video_generation / code_generation / python_processing / file_generation / review

必要な関数：
- generate_execution_plans():         Issue Pipelineの実装待ちIssueを
                                       Asset Typeごとに分類し、
                                       outputs/execution_plans/<asset_type>_project.md
                                       に保存して、現在有効なExecution Plan
                                       一覧を返す
- generate_execution_plan_summary(): AI会議へ注入する短いMarkdown要約を返す
- list_execution_plans():            現在有効なExecution Plan一覧を読み込み
                                      専用で返す（Quest90
                                      asset_generator_service.py から呼ばれる）

CLI:
  python services/execution_planner_service.py

重複生成防止：同じProject（Issueタイトル）のExecution Planは再生成しない
（v1はTitle完全一致で十分と判断。Issue Auto Pipelineと同じ方針）。

各情報源の読み込みは個別にtry/exceptで守られており、1つが欠けても他の
Execution Plan生成・DAF OS全体には影響しない。対象Issueが0件でも正常終了する。
"""

import re
import sys
from datetime import datetime
from pathlib import Path

# `python services/execution_planner_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/issue_pipeline_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"
_PLANS_DIR_NAME = "execution_plans"

_ELIGIBLE_STATUS = "pending_implementation"

# Asset Type判定キーワード（順番に評価し、最初に一致したものを採用する）。
_ASSET_TYPE_KEYWORDS: dict[str, list[str]] = {
    "line_sticker": ["LINE", "line", "スタンプ"],
    "youtube_short": ["YouTube", "youtube", "Shorts", "shorts", "動画"],
    "blog": ["ブログ", "blog", "記事"],
    "ebook": ["電子書籍", "ebook", "Ebook", "EBOOK"],
    "ios_app": ["iOS", "ios", "App", "app", "アプリ"],
    "saas": ["SaaS", "saas", "Webサービス"],
}
_DEFAULT_ASSET_TYPE = "generic"

_NO_DATA_SUMMARY = "## Execution Plan Summary\n\n現在、有効なExecution Planはありません。"
_NO_PLANS_TEXT = "現在、有効なExecution Planはありません。"


def _fallback_deliverables_and_tasks(asset_type: str) -> tuple[list[str], list[dict]]:
    """
    Asset Typeごとの固定テンプレート（Deliverables・Tasks）を返す
    （Quest89のAsset Registryが存在しない・読み込めない場合のフォールバック）。
    """
    if asset_type == "line_sticker":
        deliverables = [f"stamp_{i:02d}.png" for i in range(1, 41)] + [
            "main.png", "tab.png", "metadata.md", "stickers.zip",
        ]
        tasks = [
            {"title": "Character Design", "type": "planning"},
            {"title": "Generate 40 Phrases", "type": "text_generation"},
            {"title": "Generate 40 Sticker Images", "type": "image_generation"},
            {"title": "Resize Images", "type": "python_processing"},
            {"title": "Package Assets", "type": "file_generation"},
        ]
    elif asset_type == "youtube_short":
        deliverables = ["script.md", "narration.wav", "thumbnail.png", "video.mp4", "description.md"]
        tasks = [
            {"title": "Write Script", "type": "planning"},
            {"title": "Generate Narration", "type": "audio_generation"},
            {"title": "Generate Thumbnail", "type": "image_generation"},
            {"title": "Generate Video", "type": "video_generation"},
            {"title": "Write Description", "type": "text_generation"},
        ]
    elif asset_type == "blog":
        deliverables = ["outline.md", "draft.md", "final_article.md", "featured_image.png", "meta_description.md"]
        tasks = [
            {"title": "Create Outline", "type": "planning"},
            {"title": "Write Draft", "type": "text_generation"},
            {"title": "Generate Featured Image", "type": "image_generation"},
            {"title": "Write Meta Description", "type": "text_generation"},
            {"title": "Review Article", "type": "review"},
        ]
    elif asset_type == "ebook":
        deliverables = ["outline.md", "chapters/", "manuscript.md", "cover.png", "ebook.epub"]
        tasks = [
            {"title": "Create Outline", "type": "planning"},
            {"title": "Write Chapters", "type": "text_generation"},
            {"title": "Generate Cover", "type": "image_generation"},
            {"title": "Compile Ebook", "type": "file_generation"},
            {"title": "Review Manuscript", "type": "review"},
        ]
    elif asset_type == "ios_app":
        deliverables = ["PRD.md", "wireframes.md", "source_code/", "app_icon.png", "screenshots/", "app_store_description.md"]
        tasks = [
            {"title": "Write PRD", "type": "planning"},
            {"title": "Create Wireframes", "type": "planning"},
            {"title": "Generate Source Code", "type": "code_generation"},
            {"title": "Generate App Icon", "type": "image_generation"},
            {"title": "Generate Screenshots", "type": "image_generation"},
            {"title": "Write App Store Description", "type": "text_generation"},
            {"title": "Review Build", "type": "review"},
        ]
    elif asset_type == "saas":
        deliverables = ["PRD.md", "architecture.md", "source_code/", "landing_page.md", "pricing.md"]
        tasks = [
            {"title": "Write PRD", "type": "planning"},
            {"title": "Design Architecture", "type": "planning"},
            {"title": "Generate Source Code", "type": "code_generation"},
            {"title": "Write Landing Page", "type": "text_generation"},
            {"title": "Write Pricing Page", "type": "text_generation"},
            {"title": "Review Build", "type": "review"},
        ]
    else:  # generic
        deliverables = ["plan.md", "draft.md", "final_output.md"]
        tasks = [
            {"title": "Create Plan", "type": "planning"},
            {"title": "Create Draft", "type": "text_generation"},
            {"title": "Review Output", "type": "review"},
        ]

    for t in tasks:
        t["status"] = "pending"
    return deliverables, tasks


def _asset_deliverables_and_tasks(asset_type: str) -> tuple[list[str], list[dict]]:
    """
    Asset TypeごとのDeliverables・Tasksを返す。Quest89（Asset Type Registry）の
    memory/asset_registry/<asset_type>.json が存在すればそちらを優先し、
    無い・読み込みに失敗した場合はQuest88時点の既存ロジック
    （_fallback_deliverables_and_tasks()）にフォールバックする
    （既存ロジックは変更しない）。

    RegistryのTasksはタスク名の文字列一覧のみでType（planning/
    text_generation等）を持たないため、既存ロジックのType割り当てと
    件数が一致する場合のみタイトルを差し替える（順序はどちらも同じ
    Asset Typeを想定して揃えてある）。件数が一致しない場合はTaskの
    差し替えを行わず、既存ロジックのタイトル・Typeをそのまま使う
    （不整合なペアリングを避けるため）。
    """
    deliverables, tasks = _fallback_deliverables_and_tasks(asset_type)

    try:
        from services.asset_registry_service import get_asset_template
        template = get_asset_template(asset_type)

        registry_deliverables = template.get("deliverables") or []
        if registry_deliverables:
            deliverables = list(registry_deliverables)

        registry_task_titles = template.get("tasks") or []
        if registry_task_titles and len(registry_task_titles) == len(tasks):
            for task, title in zip(tasks, registry_task_titles):
                task["title"] = title
    except Exception as e:
        print(f"[警告] Asset Registryの参照に失敗しました（{asset_type}）。既存ロジックを使用します：{e}")

    return deliverables, tasks


def _classify_asset_type(text: str) -> str:
    """Issueのタイトル・説明文からAsset Typeを簡易判定する。"""
    haystack = (text or "").casefold()
    for asset_type, keywords in _ASSET_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw.casefold() in haystack:
                return asset_type
    return _DEFAULT_ASSET_TYPE


def _safe_pending_issues(outputs_dir: Path) -> list[dict]:
    try:
        from services.issue_pipeline_service import load_generated_issues
        issues = load_generated_issues(outputs_dir=outputs_dir)
        return [i for i in issues if i.get("status") == _ELIGIBLE_STATUS]
    except Exception as e:
        print(f"[警告] Issue Pipelineの取得に失敗しました：{e}")
        return []


def _render_plan(project: str, asset_type: str, generated_at: str, deliverables: list[str], tasks: list[dict]) -> str:
    lines = [
        "# Execution Plan",
        "",
        "Project:",
        project,
        "",
        "Asset Type:",
        asset_type,
        "",
        "Generated At:",
        generated_at,
        "",
        "---",
        "",
        "## Deliverables",
        "",
    ]
    lines.extend(f"- {d}" for d in deliverables)
    lines.append("")
    lines.append("## Tasks")
    lines.append("")

    task_blocks = []
    for i, t in enumerate(tasks, start=1):
        task_blocks.append(
            "\n".join([
                f"### Task {i}",
                t["title"],
                "",
                "Type:",
                t["type"],
                "",
                "Status:",
                t["status"],
            ])
        )
    lines.append("\n\n---\n\n".join(task_blocks))
    return "\n".join(lines)


def _existing_project_titles(content: str) -> set[str]:
    return set(re.findall(r"^Project:\s*\n(.+)$", content, re.MULTILINE))


def _plans_dir(outputs_dir: Path) -> Path:
    return outputs_dir / _PLANS_DIR_NAME


def _load_all_plans(plans_dir: Path) -> list[dict]:
    """
    outputs/execution_plans/ 配下の全ファイルから (Project, Asset Type,
    Generated At) の組を抽出する。generate_execution_plans()の戻り値、
    generate_execution_plan_summary()の集計の両方に使う。
    """
    if not plans_dir.exists():
        return []

    pattern = re.compile(
        r"Project:\s*\n(.+?)\s*\n\s*\nAsset Type:\s*\n(.+?)\s*\n\s*\nGenerated At:\s*\n(.+?)\s*\n",
        re.MULTILINE,
    )
    plans = []
    for path in sorted(plans_dir.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in pattern.finditer(text):
            plans.append({
                "project": m.group(1).strip(),
                "asset_type": m.group(2).strip(),
                "generated_at": m.group(3).strip(),
                "file": str(path),
            })
    return plans


def list_execution_plans(asset_type: str | None = None, outputs_dir: Path | None = None) -> list[dict]:
    """
    outputs/execution_plans/ 配下の現在有効なExecution Plan一覧を、読み込み専用で
    返す（Quest90 asset_generator_service.py など、他サービスから参照する
    ための公開関数）。asset_typeを指定すると、その種類のみに絞る。
    ディレクトリ未存在・読み込み失敗時は空リストを返す。例外を投げない。
    """
    try:
        base = outputs_dir or _OUTPUTS_DIR
        plans = _load_all_plans(_plans_dir(base))
        if asset_type:
            plans = [p for p in plans if p.get("asset_type") == asset_type]
        return plans
    except Exception as e:
        print(f"[警告] Execution Plansの取得に失敗しました：{e}")
        return []


def generate_execution_plans(
    memory_dir: Path | None = None,
    outputs_dir: Path | None = None,
) -> list[dict]:
    """
    Issue Pipeline（services/issue_pipeline_service.load_generated_issues()）の
    実装待ち（Status: pending_implementation）Issueを対象に、Asset Typeごとに
    分類してExecution Planを outputs/execution_plans/<asset_type>_project.md に
    生成する。同じProject（Issueタイトル）は再生成しない（重複生成防止）。

    対象Issueが0件の場合も outputs/execution_plans/ ディレクトリは作成し、
    正常に空リストを返す（例外を投げない）。

    戻り値: [{"project": str, "asset_type": str, "generated_at": str,
              "file": str}, ...]（既存分＋新規分をすべて含む、現在有効な
    Execution Planの一覧）
    """
    base_outputs_dir = outputs_dir or _OUTPUTS_DIR
    plans_dir = _plans_dir(base_outputs_dir)

    try:
        plans_dir.mkdir(parents=True, exist_ok=True)

        pending_issues = _safe_pending_issues(base_outputs_dir)

        grouped: dict[str, list[dict]] = {}
        for issue in pending_issues:
            title = issue.get("title") or issue.get("item_id") or "Untitled"
            searchable = f"{title} {issue.get('description') or ''}"
            asset_type = _classify_asset_type(searchable)
            grouped.setdefault(asset_type, []).append(issue)

        generated_at = datetime.now().strftime("%Y-%m-%d")

        for asset_type, group_issues in grouped.items():
            path = plans_dir / f"{asset_type}_project.md"
            existing_content = ""
            if path.exists():
                try:
                    existing_content = path.read_text(encoding="utf-8")
                except Exception:
                    existing_content = ""

            existing_titles = _existing_project_titles(existing_content)

            new_blocks = []
            for issue in group_issues:
                title = issue.get("title") or issue.get("item_id") or "Untitled"
                if title in existing_titles:
                    continue
                deliverables, tasks = _asset_deliverables_and_tasks(asset_type)
                new_blocks.append(_render_plan(title, asset_type, generated_at, deliverables, tasks))
                existing_titles.add(title)

            if not new_blocks:
                continue

            if existing_content.strip():
                content = existing_content.rstrip() + "\n\n---\n\n" + "\n\n---\n\n".join(new_blocks) + "\n"
            else:
                content = "\n\n---\n\n".join(new_blocks) + "\n"
            path.write_text(content, encoding="utf-8")

        return _load_all_plans(plans_dir)
    except Exception as e:
        print(f"[警告] Execution Planの生成に失敗しました：{e}")
        try:
            plans_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return []


def generate_execution_plan_summary(outputs_dir: Path | None = None) -> str:
    """
    outputs/execution_plans/ 配下の現在有効なExecution Planを集計し、
    AI会議へ注入する短いMarkdown要約に整形する（services/memory_service.py の
    load_company_memory() から呼ばれる）。Execution Planが1件も無い場合は
    「現在、有効なExecution Planはありません。」を返す。例外を投げない。
    """
    try:
        base = outputs_dir or _OUTPUTS_DIR
        plans = _load_all_plans(_plans_dir(base))
        if not plans:
            return _NO_DATA_SUMMARY

        active_plan_names = sorted({Path(p["file"]).stem for p in plans})
        asset_types = sorted({p["asset_type"] for p in plans})

        lines = ["## Execution Plan Summary", "", "### Active Plans"]
        lines.extend(f"- {name}" for name in active_plan_names)
        lines.append("")
        lines.append("### Asset Types")
        lines.extend(f"- {t}" for t in asset_types)
        lines.append("")
        lines.append("### Recommendation")
        if asset_types:
            lines.append(f"まず{asset_types[0]}を完成させて、Asset Generator実装を検証してください。")
        else:
            lines.append(_NO_PLANS_TEXT)

        return "\n".join(lines).rstrip()
    except Exception as e:
        print(f"[警告] Execution Plan Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


if __name__ == "__main__":
    # Quest88: Dashboard/main.pyの日次バッチを待たずに手動で再生成したい場合のCLI導線。
    #   python services/execution_planner_service.py
    plans = generate_execution_plans()
    print(f"[Execution Planner] outputs/execution_plans/ を更新しました（現在有効なPlan: {len(plans)}件）。")
    for p in plans:
        print(f"  - [{p['asset_type']}] {p['project']}")
    print()
    print(generate_execution_plan_summary())
