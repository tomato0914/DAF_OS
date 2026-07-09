"""
DAF OS Quest113〜115 — Production Orchestrator（Universal Production）

Quest108〜111で完成した
  Prompt Builder v2 → Image Generation Pipeline → AI Review Engine → Export Engine
を、CEOが「🚀 このProjectを制作する」ボタン1つで最後まで実行できるように
オーケストレーションする。各Serviceの実装・責務には一切手を加えず、既存の
build_prompt() / generate_images() / review_images() / export_project()を
順番に呼ぶだけ（Production Orchestratorは新しい処理を書く場所ではなく、
AI社員の現場監督＝COOとして既存Serviceを束ねる役割）。

Quest115（Universal Production）：DAF OSは「LINEスタンプ制作ツール」では
なく「Digital Asset Production OS」であるという設計方針のもと、本Questで
Production Orchestratorの概念をLINEスタンプ専用から汎用化した。

  Project → Asset Type → Production → Export Adapter

という設計原則のうち、line_stickerは現時点で実際にProduction実行できる
最初のAsset Type（SUPPORTED_PRODUCTION_ASSET_TYPES）であり、wallpaper・
icon・sns素材等は将来追加される想定のAsset Typeとして扱う（本Questでは
実際の生成処理は実装しない）。Export先も将来的にはAsset Typeごとに
Export Adapterを切り替える設計になる想定：
  line_sticker → LineExportAdapter（services/export_engine.py、実装済み）
  wallpaper    → WallpaperExportAdapter（将来）
  icon         → IconExportAdapter（将来）
現時点のexport_engine.pyはplatform（"line"等）でAdapterを切り替える設計の
ままであり、本Questではexport_engine.py自体には手を加えない（Production
Pipelineの中核ロジックは壊さない方針のため）。将来Asset Type軸のAdapter
切り替えを追加する際は、この対応関係（ASSET_TYPE_LABELS・
SUPPORTED_PRODUCTION_ASSET_TYPES）を起点にすればよい。

実行フロー：
  ④ プロンプト生成 → ⑤ 画像生成 → ⑥ AIレビュー → ⑦ Export → 完了

途中のいずれかのステップが失敗（各Serviceがok=Falseを返す、または想定外の
例外が発生）した場合はそこで停止し、どのステップで失敗したか
（failed_step）とその理由（error）をレポートに記録する。AIレビューが
要確認（needs_fix）であっても停止しない（Export Engine, Quest111の
「Exportはブロックしない」設計をそのまま踏襲する）。

asset_typeが未対応（SUPPORTED_PRODUCTION_ASSET_TYPES未登録）の場合は、
どのステップも実行せず、安全に
  {"ok": False, "status": "unsupported_asset_type", "message": "...", "asset_type": "..."}
を返す（production_report.jsonへの保存も行わない＝実行していない工程の
レポートは残さない）。

保存先：
  outputs/production_reports/<project_id>/production_report.json

必要な関数：
- run_production(project_id, ip_name=None, asset_type=None, count=..., platform=...):
    asset_type未指定時はProject情報（services/project_service.py）から
    自動取得する。4ステップを順に実行し、production_report.jsonまで
    保存する
- save_production_report(project_id, report):  production_report.jsonを保存する
- load_production_report(project_id):          保存済みレポートを読み込む
- get_asset_type_label(asset_type):            Asset TypeのCEO向け日本語表示名を返す
- is_supported_production_asset_type(asset_type): 実際にProduction実行できるAsset Typeか判定する

CLI:
  python services/production_orchestrator.py <project_id> [ip_name]

各ステップの呼び出しは個別にtry/exceptで守られ、想定外の例外が発生しても
DAF OS全体を止めない（失敗したステップをfailed_stepとして記録するだけ）。
"""

import sys
import json
from datetime import datetime
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"
_REPORTS_DIR_NAME = "production_reports"
_REPORT_FILENAME = "production_report.json"

DEFAULT_ASSET_TYPE = "line_sticker"
DEFAULT_COUNT = 3
DEFAULT_PLATFORM = "line"

STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_UNSUPPORTED_ASSET_TYPE = "unsupported_asset_type"

_STEP_LABELS = {
    "prompt": "④ プロンプト生成",
    "image_generation": "⑤ 画像生成",
    "ai_review": "⑥ AIレビュー",
    "export": "⑦ Export",
}

# Quest115：Project作成フォーム（dashboard_web/templates/index.html）で
# 選べるAsset Type全種のCEO向け表示名。Production実行の可否とは独立に、
# Dashboard上で「種類：〇〇」を表示するために使う。
ASSET_TYPE_LABELS = {
    "line_sticker": "LINEスタンプ",
    "youtube_short": "YouTube Short",
    "blog": "ブログ素材",
    "ebook": "電子書籍素材",
    "ios_app": "iOSアプリ素材",
    "saas": "SaaS素材",
    "generic": "デジタル資産",
}

# Quest115：実際にProduction Pipeline（④〜⑦）を実行できるAsset Type。
# 将来wallpaper・icon等を追加する場合は、対応するExport Adapter
# （services/export_engine.py）の実装とあわせてここへ追加する。
SUPPORTED_PRODUCTION_ASSET_TYPES = {
    "line_sticker": ASSET_TYPE_LABELS["line_sticker"],
}


def get_asset_type_label(asset_type: str | None) -> str:
    """Asset TypeのCEO向け日本語表示名を返す（未知のasset_typeはそのまま返す）。"""
    if not asset_type:
        return ASSET_TYPE_LABELS["generic"]
    return ASSET_TYPE_LABELS.get(asset_type, asset_type)


def is_supported_production_asset_type(asset_type: str | None) -> bool:
    """実際にProduction Pipelineを実行できるAsset Typeかどうかを返す。"""
    return bool(asset_type) and asset_type in SUPPORTED_PRODUCTION_ASSET_TYPES


def _resolve_asset_type(
    project_id: str,
    asset_type: str | None,
    projects_dir: Path | None,
) -> str:
    """
    asset_type未指定時に、Project情報（services/project_service.py）から
    自動取得する。Project未存在・取得失敗時はDEFAULT_ASSET_TYPEへ
    フォールバックする（例外を投げない）。
    """
    if asset_type:
        return asset_type
    try:
        from services.project_service import list_projects
        projects = list_projects(projects_dir=projects_dir)
        project = next((p for p in projects if p.get("id") == project_id), None)
        if project and project.get("asset_type"):
            return project["asset_type"]
    except Exception as e:
        print(f"[警告] Project情報からのAsset Type取得に失敗しました（{project_id}）：{e}")
    return DEFAULT_ASSET_TYPE


def _reports_dir(project_id: str, outputs_dir: Path | None = None) -> Path:
    return (outputs_dir or _OUTPUTS_DIR) / _REPORTS_DIR_NAME / project_id


def save_production_report(project_id: str, report: dict, outputs_dir: Path | None = None) -> dict:
    """
    production_report.jsonをoutputs/production_reports/<project_id>/へ保存する。

    戻り値: {"ok": bool, "path": str | None, "error": str | None}
    例外を投げない。
    """
    try:
        directory = _reports_dir(project_id, outputs_dir)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / _REPORT_FILENAME
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "path": str(path), "error": None}
    except Exception as e:
        print(f"[警告] production_report.jsonの保存に失敗しました（{project_id}）：{e}")
        return {"ok": False, "path": None, "error": str(e)}


def load_production_report(project_id: str, outputs_dir: Path | None = None) -> dict | None:
    """保存済みproduction_report.jsonを読み込む。未存在・破損時はNoneを返す（例外を投げない）。"""
    try:
        path = _reports_dir(project_id, outputs_dir) / _REPORT_FILENAME
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[警告] production_report.jsonの読み込みに失敗しました（{project_id}）：{e}")
        return None


def run_production(
    project_id: str,
    ip_name: str | None = None,
    asset_type: str | None = None,
    count: int = DEFAULT_COUNT,
    platform: str = DEFAULT_PLATFORM,
    outputs_dir: Path | None = None,
    projects_dir: Path | None = None,
) -> dict:
    """
    Quest113〜115：プロンプト生成 → 画像生成 → AIレビュー → Exportを1回で
    実行し、production_report.jsonまで保存する（Dashboardの「🚀 この
    Projectを制作する」ボタンから呼ばれる）。

    asset_type未指定時はProject情報から自動取得する（_resolve_asset_type）。
    解決したasset_typeがSUPPORTED_PRODUCTION_ASSET_TYPESに無い場合は、
    どのステップも実行せず、production_report.jsonへの保存も行わずに
    status="unsupported_asset_type"を返す。

    いずれかのステップが失敗した場合はそこで停止し、failed_step・errorを
    記録する（後続のステップは実行しない）。AIレビューが要確認
    （needs_fix）でも停止しない（Export Engineの設計を踏襲）。

    戻り値: {"ok": bool, "project_id": str, "asset_type": str,
             "asset_type_label": str, "started_at": str, "finished_at": str,
             "status": "success"|"failed"|"unsupported_asset_type",
             "completed_steps": list[str], "failed_step": str | None,
             "error": str | None, "image_count": int, "review_mode": str | None,
             "review_needs_fix": bool, "zip_filename": str | None,
             "next_action": str}
    （status="unsupported_asset_type"の場合はmessageのみを含む簡略な戻り値）
    例外を投げない。
    """
    resolved_asset_type = _resolve_asset_type(project_id, asset_type, projects_dir)

    if not is_supported_production_asset_type(resolved_asset_type):
        return {
            "ok": False,
            "status": STATUS_UNSUPPORTED_ASSET_TYPE,
            "message": "この種類の制作フローは現在準備中です。",
            "asset_type": resolved_asset_type,
            "asset_type_label": get_asset_type_label(resolved_asset_type),
        }

    started_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    completed_steps: list[str] = []
    image_count = 0
    review_mode = None
    review_needs_fix = False
    zip_filename = None

    def _finish(status: str, failed_step: str | None, error: str | None) -> dict:
        report = {
            "project_id": project_id,
            "asset_type": resolved_asset_type,
            "asset_type_label": get_asset_type_label(resolved_asset_type),
            "started_at": started_at,
            "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": status,
            "completed_steps": list(completed_steps),
            "failed_step": failed_step,
            "error": error,
            "image_count": image_count,
            "review_mode": review_mode,
            "review_needs_fix": review_needs_fix,
            "zip_filename": zip_filename,
            "next_action": (
                "LINE Creators Marketへ提出してください"
                if status == STATUS_SUCCESS
                else f"{_STEP_LABELS.get(failed_step, failed_step)}が失敗しました。内容を確認して再実行してください。"
            ),
        }
        save_production_report(project_id, report, outputs_dir=outputs_dir)
        return {"ok": status == STATUS_SUCCESS, **report}

    # ④ プロンプト生成
    try:
        from services.prompt_builder_v2 import build_prompt
        prompt_result = build_prompt(
            project_id, ip_name=ip_name, save=True,
            outputs_dir=outputs_dir, projects_dir=projects_dir,
        )
        if not prompt_result.get("ok"):
            return _finish(STATUS_FAILED, "prompt", prompt_result.get("error") or "プロンプト生成に失敗しました")
    except Exception as e:
        return _finish(STATUS_FAILED, "prompt", str(e))
    completed_steps.append("prompt")

    # ⑤ 画像生成
    try:
        from services.image_generation_pipeline import generate_images
        image_result = generate_images(
            project_id, asset_type=resolved_asset_type, count=count, outputs_dir=outputs_dir,
        )
        if not image_result.get("ok"):
            return _finish(STATUS_FAILED, "image_generation", image_result.get("error") or "画像生成に失敗しました")
        image_count = len(image_result.get("image_files") or [])
    except Exception as e:
        return _finish(STATUS_FAILED, "image_generation", str(e))
    completed_steps.append("image_generation")

    # ⑥ AIレビュー（要確認があっても停止しない）
    try:
        from services.ai_review_engine import review_images
        review_result = review_images(
            project_id, ip_name=ip_name, manual_request=True,
            asset_type=resolved_asset_type, outputs_dir=outputs_dir,
        )
        if not review_result.get("ok"):
            return _finish(STATUS_FAILED, "ai_review", review_result.get("error") or "AIレビューに失敗しました")
        review_report = review_result.get("report") or {}
        review_mode = review_report.get("review_mode")
        review_needs_fix = any(i.get("needs_fix") for i in (review_report.get("items") or []))
    except Exception as e:
        return _finish(STATUS_FAILED, "ai_review", str(e))
    completed_steps.append("ai_review")

    # ⑦ Export（Asset TypeごとのExport Adapter選択はexport_engine.py側の責務。
    # 現時点ではplatform="line"固定でLineExportAdapterを使う。将来Asset Type
    # ごとにAdapterを切り替える場合も、Production Orchestrator側の呼び出し
    # 方は変えず、export_engine.py側でasset_type→Adapterの対応を追加すればよい）
    try:
        from services.export_engine import export_project
        export_result = export_project(
            project_id, asset_type=resolved_asset_type, platform=platform, outputs_dir=outputs_dir,
        )
        if not export_result.get("ok"):
            return _finish(STATUS_FAILED, "export", export_result.get("error") or "Exportに失敗しました")
        zip_filename = export_result.get("zip_filename")
    except Exception as e:
        return _finish(STATUS_FAILED, "export", str(e))
    completed_steps.append("export")

    return _finish(STATUS_SUCCESS, None, None)


if __name__ == "__main__":
    # Quest113〜115: 動作確認用のCLI導線。
    #   python services/production_orchestrator.py <project_id> [ip_name]
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
        ip_name = sys.argv[2] if len(sys.argv) > 2 else None
        result = run_production(project_id, ip_name=ip_name)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("使い方: python services/production_orchestrator.py <project_id> [ip_name]")
