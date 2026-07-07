"""
DAF OS Quest93 — Project Management Service

Strategic Goals（Quest76）〜Notification Center（Quest92）までは、既に
プロダクト（mofulog）が存在する前提の「経営支援・制作支援レイヤー」だった。
しかしDAF OS自体には「新しいプロジェクトを立ち上げる入口」が存在せず、
これまでは手動でフォルダを作る必要があった。このサービスはCEOが
Dashboardから「New Project」を作るだけでDAF OSが動き始める、という
起点を提供する。

ディレクトリ構造:
  projects/<id>_<slug>/
    project.md      プロジェクトのメタ情報（ID/Name/Asset Type/Status/Vision/Success Metrics）
    goals.md        このプロジェクト固有のGoal（AI役員会議・自動起動で更新）
    initiatives.md  このプロジェクト固有のInitiative（AI役員会議で更新）
    assets/         Asset Generator（Quest90）が生成する成果物の置き場（v1では空）
    outputs/        プロジェクト単位の生成物置き場（meeting_log.md・issues.md・
                    execution_plan.mdなど、自動起動が生成するものを含む）

Project Status: draft / active / completed / archived
（create_project()で作成した直後はactiveから開始する）

必要な関数：
- create_project(name, asset_type, vision, success_metrics=None):
    新規プロジェクトを作成し、自動採番・project.md/goals.md/initiatives.md/
    assets//outputs/ を生成する。可能であれば「自動起動」
    （AI役員会議 → Goal生成 → Issue生成 → Execution Plan生成）をベストエフォートで
    実行する（Asset Generatorまでは実行しない。重い処理を避けるため）。
- list_projects(): 登録済みプロジェクトの一覧を返す
- archive_project(project_id): Statusをarchivedに変更する
- get_project_summary(): AI会議へ注入する短いMarkdown要約を返す

自動起動について（v1の割り切り）：
「AI役員会議」はOPENROUTER_API_KEYが設定されている場合のみ試行し、無ければ
スキップする（コスト・ネットワーク依存を避けるため）。「Goal生成」「Issue生成」は
LLMを使わず、create_project()に渡されたvision/success_metricsから決定的に
プロジェクト固有のgoals.md・outputs/issues.mdを組み立てる（v1では会社全体の
Strategic Goals・Issue Pipelineとは連携しない。プロジェクト単体の下書きを
作るところまで）。「Execution Plan生成」はAsset Type Registry（Quest89）の
テンプレートを再利用し、outputs/execution_plan.mdへ書き出す。

CLI:
  python services/project_service.py list
  python services/project_service.py create <name> <asset_type> <vision>

読み込み・書き込みはこのサービス内で完結し、失敗してもDAF OS全体を止めない
（各ステップは個別にtry/exceptで守られている）。
"""

import re
import sys
from datetime import datetime
from pathlib import Path

# `python services/project_service.py ...` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/artifact_review_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_PROJECTS_DIR = _BASE_DIR / "projects"

_STATUSES = ("draft", "active", "completed", "archived")
_DEFAULT_STATUS = "active"

_NO_DATA_SUMMARY = "## Project Summary\n\n現在、登録されているProjectはありません。"


def _projects_dir(projects_dir: Path | None = None) -> Path:
    return projects_dir or _PROJECTS_DIR


def _next_project_id(base: Path) -> str:
    """既存のprojects/配下のIDから次の連番（3桁ゼロ埋め）を返す。"""
    max_id = 0
    if base.exists():
        for entry in base.iterdir():
            if not entry.is_dir():
                continue
            m = re.match(r"^(\d+)_", entry.name)
            if m:
                max_id = max(max_id, int(m.group(1)))
    return f"{max_id + 1:03d}"


def _slugify(name: str, project_id: str) -> str:
    """
    プロジェクト名から英数字トークンを抽出してslugを作る。
    日本語のみなど英数字が抽出できない場合は project_<id> にフォールバックする。
    """
    tokens = re.findall(r"[A-Za-z0-9]+", name or "")
    if tokens:
        slug = "_".join(t.lower() for t in tokens)
        return slug[:40] or f"project_{project_id}"
    return f"project_{project_id}"


def _field(text: str, label: str) -> str | None:
    m = re.search(rf"^{re.escape(label)}:\s*\n(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _project_dir_for_id(project_id: str, base: Path) -> Path | None:
    if not base.exists():
        return None
    for entry in sorted(base.iterdir()):
        if entry.is_dir() and entry.name.startswith(f"{project_id}_"):
            return entry
    return None


def _render_project_md(
    project_id: str,
    name: str,
    asset_type: str,
    status: str,
    created_at: str,
    vision: str,
    success_metrics: list[str],
) -> str:
    lines = [
        "# Project",
        "",
        "ID:",
        project_id,
        "",
        "Name:",
        name,
        "",
        "Asset Type:",
        asset_type,
        "",
        "Status:",
        status,
        "",
        "Created At:",
        created_at,
        "",
        "---",
        "",
        "## Vision",
        "",
        vision,
        "",
        "## Success Metrics",
        "",
    ]
    metrics = success_metrics or ["（未設定）"]
    lines.extend(f"- {m}" for m in metrics)
    return "\n".join(lines) + "\n"


def _auto_launch(project: dict, auto_launch_meeting: bool = False) -> dict:
    """
    Project作成直後にベストエフォートで実行する自動起動フロー。
    AI役員会議 → Goal生成 → Issue生成 → Execution Plan生成の順に試み、
    Asset Generatorまでは実行しない（試験運用では重い処理を避けるため）。
    各ステップは個別にtry/exceptで守られており、1つが失敗しても他の
    ステップ・プロジェクト作成自体には影響しない。

    AI役員会議（crews.meeting_crew.run_meeting_crew()）は実際にOpenRouter API
    へ課金付きのリクエストを送り、数十秒〜数分かかることがある。テスト中に
    Dashboardの「Create」ボタンがこの呼び出しの完了までブロックされる
    ことを確認したため、CEOの明示的な判断により auto_launch_meeting=False を
    既定値とした（.envにOPENROUTER_API_KEYが設定されていても自動実行しない）。
    Goal生成・Issue生成・Execution Plan生成はLLMを使わない決定的な処理のため、
    常に実行する。
    """
    project_path = Path(project["path"])
    result = {
        "meeting": "skipped", "goals": "skipped", "issues": "skipped",
        "execution_plan": "skipped", "creative_brief": "skipped",
    }

    # 1. AI役員会議：既定では自動実行しない（コスト・レイテンシへの配慮。CEOの判断）。
    #    auto_launch_meeting=Trueを明示的に指定した場合のみ、
    #    OPENROUTER_API_KEYがあれば試行する。
    if not auto_launch_meeting:
        result["meeting"] = "skipped_by_default"
    else:
        try:
            import os
            api_key = os.getenv("OPENROUTER_API_KEY")
            if api_key:
                from crews.meeting_crew import run_meeting_crew
                ceo_input = f"新しいプロジェクト「{project['name']}」を開始しました。\nVision: {project['vision']}"
                meeting_results = run_meeting_crew(ceo_input=ceo_input, openrouter_api_key=api_key)
                meeting_log = meeting_results.get("meeting_log", "") if isinstance(meeting_results, dict) else ""
                (project_path / "outputs" / "meeting_log.md").write_text(meeting_log, encoding="utf-8")
                result["meeting"] = "generated"
            else:
                result["meeting"] = "skipped_no_api_key"
        except Exception as e:
            print(f"[警告] 自動起動：AI役員会議の実行に失敗しました：{e}")
            result["meeting"] = "error"

    # 2. Goal生成（決定的：vision/success_metricsをこのプロジェクトのgoals.mdへ反映）
    try:
        lines = ["# Goals", "", "## North Star", "", project["vision"], "", "## Success Metrics", ""]
        metrics = project.get("success_metrics") or ["（未設定）"]
        lines.extend(f"- {m}" for m in metrics)
        (project_path / "goals.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        result["goals"] = "generated"
    except Exception as e:
        print(f"[警告] 自動起動：Goal生成に失敗しました：{e}")
        result["goals"] = "error"

    # 3. Issue生成（決定的：Visionから初期Issue案をこのプロジェクトのoutputs/issues.mdへ）
    try:
        content = (
            "# Initial Issues\n\n"
            f"1. {project['vision']}を実現するための最初のステップを検討する\n"
            f"2. {project['asset_type']}の制作に必要な素材・工程を洗い出す\n"
        )
        (project_path / "outputs" / "issues.md").write_text(content, encoding="utf-8")
        result["issues"] = "generated"
    except Exception as e:
        print(f"[警告] 自動起動：Issue生成に失敗しました：{e}")
        result["issues"] = "error"

    # 4. Execution Plan生成（Asset Type Registry・Quest89のテンプレートを再利用）
    try:
        from services.asset_registry_service import get_asset_template
        template = get_asset_template(project["asset_type"])
        plan_lines = [
            "# Execution Plan",
            "",
            "Project:",
            project["name"],
            "",
            "Asset Type:",
            project["asset_type"],
            "",
            "Generated At:",
            datetime.now().strftime("%Y-%m-%d"),
            "",
            "---",
            "",
            "## Deliverables",
            "",
        ]
        plan_lines.extend(f"- {d}" for d in template.get("deliverables", []))
        plan_lines.extend(["", "## Tasks", ""])
        for i, task_title in enumerate(template.get("tasks", []), start=1):
            plan_lines.extend([f"### Task {i}", task_title, "", "Status:", "pending", ""])
        (project_path / "outputs" / "execution_plan.md").write_text(
            "\n".join(plan_lines).rstrip() + "\n", encoding="utf-8"
        )
        result["execution_plan"] = "generated"
    except Exception as e:
        print(f"[警告] 自動起動：Execution Plan生成に失敗しました：{e}")
        result["execution_plan"] = "error"

    # 5. Creative Brief生成（Quest99：Vega/Creative DirectorがCharacter Bible・
    #    Style Guideを土台にProject単位のCreative Brief（設計方針）を作る。
    #    LLM不使用・決定的な処理で、画像生成APIは呼ばない）
    try:
        from services.creative_brief_service import generate_creative_brief
        brief_result = generate_creative_brief(
            project["id"], project["name"],
            vision=project["vision"], asset_type=project["asset_type"],
        )
        result["creative_brief"] = "generated" if brief_result.get("ok") else "error"
    except Exception as e:
        print(f"[警告] 自動起動：Creative Brief生成に失敗しました：{e}")
        result["creative_brief"] = "error"

    return result


def create_project(
    name: str,
    asset_type: str,
    vision: str,
    success_metrics: list[str] | None = None,
    projects_dir: Path | None = None,
    auto_launch: bool = True,
    auto_launch_meeting: bool = False,
) -> dict:
    """
    新規プロジェクトを作成する。projects/<id>_<slug>/ 配下に project.md /
    goals.md / initiatives.md / assets/ / outputs/ を生成し、Statusは
    "active" から始まる。

    auto_launch=True（既定）の場合、可能であれば「Goal生成 → Issue生成 →
    Execution Plan生成」をベストエフォートで実行する（Asset Generatorまでは
    実行しない）。失敗してもプロジェクト作成自体は成功として扱う。

    AI役員会議（crews.meeting_crew.run_meeting_crew()）は実際にOpenRouter API
    へ課金付きのリクエストを送り数十秒〜数分かかることがあるため、
    auto_launch_meeting=False（既定）では実行しない。CEOが明示的に
    auto_launch_meeting=Trueを指定した場合のみ試行する
    （その場合もOPENROUTER_API_KEY未設定ならスキップする）。

    戻り値: {"ok": bool, "id": str, "name": str, "asset_type": str,
             "status": str, "path": str, "vision": str,
             "success_metrics": list[str], "auto_launch": dict | None,
             "error": str | None}
    """
    base = _projects_dir(projects_dir)

    try:
        base.mkdir(parents=True, exist_ok=True)

        project_id = _next_project_id(base)
        slug = _slugify(name, project_id)
        project_path = base / f"{project_id}_{slug}"
        project_path.mkdir(parents=True, exist_ok=False)
        (project_path / "assets").mkdir(parents=True, exist_ok=True)
        (project_path / "outputs").mkdir(parents=True, exist_ok=True)

        created_at = datetime.now().strftime("%Y-%m-%d")
        metrics = list(success_metrics) if success_metrics else []

        project_md = _render_project_md(
            project_id, name, asset_type, _DEFAULT_STATUS, created_at, vision, metrics,
        )
        (project_path / "project.md").write_text(project_md, encoding="utf-8")
        (project_path / "goals.md").write_text("# Goals\n\n（AI役員会議で更新）\n", encoding="utf-8")
        (project_path / "initiatives.md").write_text("# Initiatives\n\n（AI役員会議で更新）\n", encoding="utf-8")

        project = {
            "id": project_id,
            "name": name,
            "asset_type": asset_type,
            "status": _DEFAULT_STATUS,
            "path": str(project_path),
            "vision": vision,
            "success_metrics": metrics,
        }

        auto_launch_result = None
        if auto_launch:
            try:
                auto_launch_result = _auto_launch(project, auto_launch_meeting=auto_launch_meeting)
            except Exception as e:
                print(f"[警告] 自動起動に失敗しました：{e}")
                auto_launch_result = {"error": str(e)}

        project["ok"] = True
        project["error"] = None
        project["auto_launch"] = auto_launch_result
        return project
    except Exception as e:
        print(f"[警告] Projectの作成に失敗しました（{name}）：{e}")
        return {"ok": False, "name": name, "asset_type": asset_type, "error": str(e)}


def list_projects(projects_dir: Path | None = None) -> list[dict]:
    """
    projects/ 配下の登録済みプロジェクト一覧を返す。
    戻り値: [{"id": str, "name": str, "asset_type": str, "status": str,
              "created_at": str | None, "path": str}, ...]（id昇順）
    ディレクトリ未存在・読み込み失敗時は空リストを返す。例外を投げない。
    """
    try:
        base = _projects_dir(projects_dir)
        if not base.exists():
            return []

        projects = []
        for entry in sorted(base.iterdir()):
            if not entry.is_dir():
                continue
            project_md = entry / "project.md"
            if not project_md.exists():
                continue
            try:
                text = project_md.read_text(encoding="utf-8")
            except Exception:
                continue
            projects.append({
                "id": _field(text, "ID") or entry.name.split("_")[0],
                "name": _field(text, "Name") or entry.name,
                "asset_type": _field(text, "Asset Type") or "generic",
                "status": _field(text, "Status") or "draft",
                "created_at": _field(text, "Created At"),
                "path": str(entry),
            })

        projects.sort(key=lambda p: p["id"])
        return projects
    except Exception as e:
        print(f"[警告] Project一覧の取得に失敗しました：{e}")
        return []


def archive_project(project_id: str, projects_dir: Path | None = None) -> dict:
    """
    指定Projectのproject.mdのStatusをarchivedへ変更する。
    戻り値: {"ok": bool, "id": str, "status": str | None, "error": str | None}
    Project未存在・書き込み失敗のいずれでも例外を投げない。
    """
    try:
        base = _projects_dir(projects_dir)
        project_path = _project_dir_for_id(project_id, base)
        if not project_path:
            return {"ok": False, "id": project_id, "error": "Projectが見つかりません"}

        project_md = project_path / "project.md"
        if not project_md.exists():
            return {"ok": False, "id": project_id, "error": "project.mdが見つかりません"}

        text = project_md.read_text(encoding="utf-8")
        new_text = re.sub(r"^Status:\s*\n.+$", "Status:\narchived", text, count=1, flags=re.MULTILINE)
        project_md.write_text(new_text, encoding="utf-8")

        return {"ok": True, "id": project_id, "status": "archived", "error": None}
    except Exception as e:
        print(f"[警告] Projectのアーカイブに失敗しました（{project_id}）：{e}")
        return {"ok": False, "id": project_id, "error": str(e)}


def generate_project_assets(
    project_id: str,
    projects_dir: Path | None = None,
    outputs_dir: Path | None = None,
) -> dict:
    """
    Quest94：Project Management ServiceとAsset Generatorを接続する。
    指定Projectを起点に「Execution Plan登録 → Asset生成 → Notification更新」
    まで進める。v1では asset_type が line_sticker のProjectのみ対応する
    （Asset Generator自体がline_sticker専用のため。他のAsset Typeは
    "unsupported_asset_type" を返し、何もしない）。

    Execution Plan・Asset生成とも既存のグローバルなoutputs/（Execution
    Planner・Asset Generatorが元々参照している場所）を経由する。プロジェクト
    固有のoutputs/execution_plan.md（create_project()の自動起動で生成される
    下書き）は変更しない。

    戻り値: {"ok": bool, "id": str, "asset_type": str | None,
             "status": "generated" | "skipped_existing" | "no_plan" |
                       "unsupported_asset_type" | "not_found" | "error",
             "execution_plan": dict | None, "asset_generation": dict | None,
             "notifications_added": list[dict], "error": str | None}

    各ステップは個別にtry/exceptで守られており、1つが失敗しても他の
    ステップ・DAF OS全体には影響しない。例外を投げない。
    """
    base = _projects_dir(projects_dir)

    try:
        projects = list_projects(projects_dir=base)
        project = next((p for p in projects if p["id"] == project_id), None)
        if not project:
            return {"ok": False, "id": project_id, "asset_type": None, "status": "not_found", "error": "Projectが見つかりません"}

        asset_type = project.get("asset_type")
        if asset_type != "line_sticker":
            return {
                "ok": False, "id": project_id, "asset_type": asset_type,
                "status": "unsupported_asset_type",
                "error": "v1ではline_stickerのみAsset生成に対応しています",
            }

        execution_plan_result = None
        try:
            from services.execution_planner_service import register_project_execution_plan
            execution_plan_result = register_project_execution_plan(
                project["name"], asset_type, outputs_dir=outputs_dir,
            )
        except Exception as e:
            print(f"[警告] Execution Planの登録に失敗しました（{project_id}）：{e}")
            execution_plan_result = {"ok": False, "error": str(e)}

        asset_generation_result = None
        try:
            from services.asset_generator_service import generate_assets
            # Quest97：project_nameを指定し、このProjectだけを対象に生成する
            # （指定しないと登録済みの全line_sticker Planがバッチ生成されてしまう）。
            asset_generation_result = generate_assets(outputs_dir=outputs_dir, project_name=project["name"])
        except Exception as e:
            print(f"[警告] Asset生成に失敗しました（{project_id}）：{e}")
            asset_generation_result = {"status": "error", "error": str(e)}

        notifications_added = []
        try:
            from services.notification_service import generate_notifications
            notifications_added = generate_notifications(outputs_dir=outputs_dir)
        except Exception as e:
            print(f"[警告] Notification更新に失敗しました（{project_id}）：{e}")

        overall_status = (asset_generation_result or {}).get("status", "error")

        return {
            "ok": overall_status in ("generated", "skipped_existing"),
            "id": project_id,
            "asset_type": asset_type,
            "status": overall_status,
            "execution_plan": execution_plan_result,
            "asset_generation": asset_generation_result,
            "notifications_added": notifications_added,
            "error": None,
        }
    except Exception as e:
        print(f"[警告] Project起点のAsset生成に失敗しました（{project_id}）：{e}")
        return {"ok": False, "id": project_id, "asset_type": None, "status": "error", "error": str(e)}


def get_project_summary(projects_dir: Path | None = None) -> str:
    """
    登録済みプロジェクトをAI会議へ注入する短いMarkdown要約に整形する。
    プロジェクトが1件も無い場合は「現在、登録されているProjectはありません。」
    を返す。例外を投げない。
    """
    try:
        projects = list_projects(projects_dir=projects_dir)
        if not projects:
            return _NO_DATA_SUMMARY

        active = [p["name"] for p in projects if p["status"] == "active"]
        completed = [p["name"] for p in projects if p["status"] == "completed"]

        lines = ["## Project Summary", "", "### Active Projects", ""]
        lines.extend(f"- {name}" for name in active) if active else lines.append("- なし")
        lines.append("")
        lines.append("### Completed Projects")
        lines.append("")
        lines.extend(f"- {name}" for name in completed) if completed else lines.append("- なし")
        lines.append("")
        lines.append("### Recommendation")
        if len(active) == 0:
            lines.append("新しいプロジェクトを作成してください。")
        elif len(active) == 1:
            lines.append("まず1つのプロジェクトへ集中してください。")
        else:
            lines.append(f"{len(active)}件のプロジェクトが進行中です。優先順位を明確にしてください。")

        return "\n".join(lines).rstrip()
    except Exception as e:
        print(f"[警告] Project Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


def _cli_create(args: list[str]) -> None:
    if len(args) < 3:
        print("使い方: python services/project_service.py create <name> <asset_type> <vision>")
        return
    name, asset_type, vision = args[0], args[1], args[2]
    result = create_project(name, asset_type, vision, auto_launch=False)
    if result.get("ok"):
        print(f"[Project] 作成しました：{result['id']} {result['name']}（{result['path']}）")
    else:
        print(f"[Project] 作成に失敗しました：{result.get('error')}")


def _cli_generate_assets(args: list[str]) -> None:
    if len(args) < 1:
        print("使い方: python services/project_service.py generate-assets <project_id>")
        return
    result = generate_project_assets(args[0])
    print(f"[Project] Asset生成：{result}")


if __name__ == "__main__":
    # Quest93/94: CLI導線。
    #   python services/project_service.py list
    #   python services/project_service.py create <name> <asset_type> <vision>
    #   python services/project_service.py generate-assets <project_id>
    argv = sys.argv[1:]
    if argv and argv[0] == "create":
        _cli_create(argv[1:])
    elif argv and argv[0] == "generate-assets":
        _cli_generate_assets(argv[1:])
    elif argv and argv[0] == "list":
        for p in list_projects():
            print(f"{p['id']} {p['name']}（{p['status']} / {p['asset_type']}）")
    else:
        print(get_project_summary())
