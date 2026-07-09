"""
DAF OS Quest116 — Dashboard Review Package Service

DAF OSは「今どんな状態か・どんな画面構造か・どんなProjectがあるか・どこまで
Productionが進んでいるか・CEOが次に何を見るべきか」を、Executive Board
（CEO／ChatGPT等の外部レビュー）へ1クリックで提出できるパッケージとして
出力する。テーマ：「Dashboard Review Package — DAF OS can report its own
state.」

運用イメージ：
  CEOがDashboardを操作 → Review Packageを生成 →
  ChatGPT / Executive Boardがレビュー → 改善点を決定 → Claude Codeが実装

このServiceは既存Production Pipeline（Quest108〜115）のロジックを一切
変更せず、既存Service（project_service・production_status_service・
asset_generator_service・notification_service・issue_pipeline_service・
production_orchestrator）を読み取り専用で呼び出し、その場でMarkdown/JSON/
ZIPへまとめるだけ（新しい状態は既存データへ保存しない）。

保存先：
  outputs/review_packages/<package_id>/
    dashboard_structure.md      Dashboardのタブ構成・主要ボタン・CEO/Developer導線
    api_summary.md               dashboard_web/app.pyの主要API一覧
    project_summary.json         Project一覧（asset_type_label・next_action付き）
    production_status.json       Project別Production Status（Quest112を再利用）
    ceo_home_summary.json        CEO Home集計値（/api/dashboard/homeと同じ算出方法）
    ux_notes.md                  現在分かっているUX上の注意点・改善候補
    review_package_summary.md    Executive Boardが最初に読む要約
    review_package.zip           上記一式をまとめたZIP

package_idは"YYYY-MM-DD_HHMMSS"形式（生成日時、ソート可能な文字列）。

必要な関数：
- create_review_package(outputs_dir=None, projects_dir=None):
    Review Package一式を生成・保存し、manifestを返す
- list_review_packages(outputs_dir=None):
    生成済みReview Package一覧を新しい順で返す
- get_latest_review_package(outputs_dir=None):
    最新のReview Packageのmanifestを返す
- get_review_package_zip_path(package_id, outputs_dir=None):
    指定package_idのreview_package.zipのパスを返す（ダウンロードAPI向け）

dashboard_structure.md・api_summary.mdは、コードからの完全自動抽出が難しい
部分（画面構造の説明文・CEO向け導線の意図等）を含むため、現時点のDashboard
仕様（Quest112〜115で確定した構成）に基づく固定テンプレートとして生成する。
Project一覧・Production Status・CEO Home集計はすべて既存Serviceから都度
読み直すため、実データを反映する。

CLI:
  python services/dashboard_review_package_service.py

各収集処理は個別にtry/exceptで守られ、1つの情報源が読み込めなくても
Review Package全体の生成を止めない（該当ファイルはエラー情報を含めて
出力する）。
"""

import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"
_PACKAGES_DIR_NAME = "review_packages"
_ZIP_FILENAME = "review_package.zip"

_REQUIRED_FILES = (
    "dashboard_structure.md",
    "api_summary.md",
    "project_summary.json",
    "production_status.json",
    "ceo_home_summary.json",
    "ux_notes.md",
    "review_package_summary.md",
)


def _packages_dir(outputs_dir: Path | None = None) -> Path:
    return (outputs_dir or _OUTPUTS_DIR) / _PACKAGES_DIR_NAME


def _package_dir(package_id: str, outputs_dir: Path | None = None) -> Path:
    return _packages_dir(outputs_dir) / package_id


def _new_package_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


# ──────────────────────────────────────────
# 1. Project一覧・CEO Home集計（既存Serviceの読み取り専用呼び出し）
# ──────────────────────────────────────────

def _project_next_action(project: dict, pending_review_asset_types: set, has_pending_implementation: bool) -> str:
    """
    dashboard_web/templates/index.htmlの_projectNextAction()と同じ優先順位
    ルールをPython側に移植したもの（CEO Home / Projectsタブと同じ判定基準を
    Review Packageでも使うため）。
    """
    if project.get("status") in ("archived", "completed"):
        return "-"
    if project.get("asset_type") in pending_review_asset_types:
        return f"{project.get('asset_type')} をレビューしてください。"
    if has_pending_implementation:
        return "実装待ちIssueを確認してください。"
    if project.get("status") == "active":
        return "Execution Planを確認してください。"
    return "-"


def collect_project_summary(projects_dir: Path | None = None, outputs_dir: Path | None = None) -> dict:
    """
    Project一覧をasset_type_label・next_action付きで収集する。

    戻り値: {"generated_at": str, "count": int, "projects": [{"project_id": str,
             "name": str, "asset_type": str, "asset_type_label": str,
             "status": str, "created_at": str | None, "next_action": str}, ...]}
    例外を投げない。
    """
    try:
        from services.project_service import list_projects
        from services.production_orchestrator import get_asset_type_label

        projects = list_projects(projects_dir=projects_dir)

        pending_review_asset_types: set = set()
        try:
            from services.asset_generator_service import list_generated_assets
            assets = list_generated_assets(outputs_dir=outputs_dir)
            pending_review_asset_types = {a.get("asset_type") for a in assets if a.get("status") == "pending_review"}
        except Exception as e:
            print(f"[警告] Generated Assets（レビュー待ち判定）の取得に失敗しました：{e}")

        has_pending_implementation = False
        try:
            from services.issue_pipeline_service import load_generated_issues
            issues = load_generated_issues(outputs_dir=outputs_dir)
            has_pending_implementation = any(i.get("status") == "pending_implementation" for i in issues)
        except Exception as e:
            print(f"[警告] 実装待ちIssueの取得に失敗しました：{e}")

        rows = []
        for p in projects:
            rows.append({
                "project_id": p.get("id"),
                "name": p.get("name"),
                "asset_type": p.get("asset_type"),
                "asset_type_label": get_asset_type_label(p.get("asset_type")),
                "status": p.get("status"),
                "created_at": p.get("created_at"),
                "next_action": _project_next_action(p, pending_review_asset_types, has_pending_implementation),
            })

        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "count": len(rows),
            "projects": rows,
        }
    except Exception as e:
        print(f"[警告] Project一覧の収集に失敗しました：{e}")
        return {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "count": 0, "projects": [], "error": str(e)}


def collect_ceo_home_summary(projects_dir: Path | None = None, outputs_dir: Path | None = None) -> dict:
    """
    CEO Home集計値を収集する。dashboard_web/app.pyのapi_dashboard_home()と
    同じ算出方法（同じ既存Serviceの組み合わせ）を使う。

    戻り値: {"active_projects": int, "pending_reviews": int, "notifications": int,
             "pending_implementation": int, "next_action": str}
    例外を投げない（各情報源は個別に守られ、失敗しても他の値は返す）。
    """
    active_projects_count = 0
    try:
        from services.project_service import list_projects
        projects = list_projects(projects_dir=projects_dir)
        active_projects_count = len([p for p in projects if p.get("status") == "active"])
    except Exception as e:
        print(f"[警告] Active Projects集計に失敗しました：{e}")

    pending_review_assets = []
    try:
        from services.asset_generator_service import list_generated_assets
        assets = list_generated_assets(outputs_dir=outputs_dir)
        pending_review_assets = [a for a in assets if a.get("status") == "pending_review"]
    except Exception as e:
        print(f"[警告] Pending Reviews集計に失敗しました：{e}")

    notifications_count = 0
    try:
        from services.notification_service import get_notifications
        notifications_count = len(get_notifications(outputs_dir=outputs_dir))
    except Exception as e:
        print(f"[警告] Notifications集計に失敗しました：{e}")

    pending_implementation_count = 0
    try:
        from services.issue_pipeline_service import load_generated_issues
        issues = load_generated_issues(outputs_dir=outputs_dir)
        pending_implementation_count = len([i for i in issues if i.get("status") == "pending_implementation"])
    except Exception as e:
        print(f"[警告] Pending Implementation集計に失敗しました：{e}")

    if pending_review_assets:
        next_action = f"{pending_review_assets[0]['asset_type']} をレビューしてください。"
    elif pending_implementation_count > 0:
        next_action = "実装待ちIssueがあります。"
    elif active_projects_count > 0:
        next_action = "Execution Planを確認してください。"
    else:
        next_action = "新しいProjectを作成してください。"

    return {
        "active_projects": active_projects_count,
        "pending_reviews": len(pending_review_assets),
        "notifications": notifications_count,
        "pending_implementation": pending_implementation_count,
        "next_action": next_action,
    }


def collect_production_status(
    projects: list[dict],
    outputs_dir: Path | None = None,
) -> dict:
    """
    Project別のProduction Status（Quest112 services/production_status_service.py
    を再利用）を収集する。ProjectとIPを紐づける仕組みがまだ無いため
    （Quest112と同じ制約）、ip_nameは指定しない。

    戻り値: {"generated_at": str, "count": int, "projects": [{"project_id": str,
             "asset_type": str, "current_status": str, "next_action": str,
             "ready_for_submission": bool, "steps": list[dict]}, ...]}
    1つのProjectの取得に失敗しても他のProjectには影響しない。
    """
    from services.production_status_service import get_production_status, DEFAULT_ASSET_TYPE

    rows = []
    for p in projects:
        project_id = p.get("project_id") or p.get("id")
        asset_type = p.get("asset_type") or DEFAULT_ASSET_TYPE
        try:
            status = get_production_status(project_id, asset_type=asset_type, outputs_dir=outputs_dir)
            rows.append({
                "project_id": project_id,
                "asset_type": asset_type,
                "current_status": status.get("current_status"),
                "next_action": status.get("next_action"),
                "ready_for_submission": status.get("ready_for_submission", False),
                "steps": status.get("steps", []),
            })
        except Exception as e:
            print(f"[警告] Production Statusの取得に失敗しました（{project_id}）：{e}")
            rows.append({
                "project_id": project_id,
                "asset_type": asset_type,
                "current_status": None,
                "next_action": None,
                "ready_for_submission": False,
                "steps": [],
                "error": str(e),
            })

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "count": len(rows),
        "projects": rows,
    }


# ──────────────────────────────────────────
# 2. dashboard_structure.md / api_summary.md（固定テンプレート）
# 完全自動抽出が難しい画面構造の説明・意図はテンプレートとして持つ
# （Quest112〜115で確定したDashboard仕様に基づく）。
# ──────────────────────────────────────────

def build_dashboard_structure_markdown() -> str:
    """現時点のDashboard仕様に基づく画面構造のMarkdownを返す（固定テンプレート）。"""
    return """# Dashboard構造（Quest112〜117時点）

## タブ一覧
- 📊 ダッシュボード：CEO Mode（① 今日やること〜⑤ 最近完了した制作の5項目＋
  Executive Boardレビュー資料。開発者・AI社員向け詳細は「🔧 詳細情報を見る」へ）
- ✅ 承認センター：AI起票Issue等の承認・却下・実装完了への遷移
- 🗂️ プロジェクト：Project作成・Production実行・進捗確認（DAF OSの制作業務の中心タブ）
- 🎨 生成物：生成済みLINEスタンプ成果物の確認・Quality Check
- 🔔 通知：システム通知一覧（読み取り専用）
- 🖼️ 参考画像：参考画像アップロード・AI解析・Reference Summary更新
- 🧬 キャラクター管理：IP DNA・IP Bible・Style Guideの作成・確認・保存

## 各タブの役割
- ダッシュボード：CEOが最初に見る画面。Quest117（CEO Mode）で
  「①今日やること→②AI社員からの重要報告→③進行中Project→④要承認事項→
  ⑤最近完了した制作」の優先順位に整理。API・Prompt・Production Step等の
  技術詳細は表示せず、「🔧 詳細情報を見る」に集約した。
- 承認センター：承認待ちアイテムを確認し、承認／却下／実装完了を判断する。
- プロジェクト：新規Project作成、制作（プロンプト生成→画像生成→確認→
  提出データ作成）の実行、進捗確認を行う。
- 生成物：Project別の生成済みスタンプ画像・Quality Checkを確認する。
- 通知：システムからの通知を一覧表示する。
- 参考画像：IP制作の元になる画像をアップロードし、AI解析する。
- キャラクター管理：IPのDNA・設定資料・描き方ルールを作成・確認する。

## 主要ボタン一覧（CEO向け）
- 🚀 このProjectを制作する（プロジェクトタブ・各Project行）：制作を
  1クリックで実行する主導線（Quest113〜115）
- ⬇ 提出データをダウンロード（プロジェクトタブ・各Project行、制作完了時のみ表示）
- 承認センターへ／Inboxを見る／📦 Executive Boardレビュー資料を作成
  （ダッシュボードタブ、Quest117）
- アーカイブ（プロジェクトタブ・各Project行、控えめなテキストリンク）
- 承認／却下（承認センター）

## Projectsタブの操作導線
1. 上部フォームでProjectを作成
2. Project行の「🚀 このProjectを制作する」を押す
3. 完了後、結果パネルで生成画像枚数・確認結果・提出データ状況・次にやることを確認
4. 「⬇ 提出データをダウンロード」から提出データを取得

## CEO向け導線
- Projectsタブの主ボタンは「🚀 このProjectを制作する」に統一（Quest115）
- Projectごとの表示はProject名／種類／状態／次にやること／🚀ボタンのみ
  （Quest117、詳細操作はDeveloper Modeへ）
- Asset Typeが未対応の場合は「種類：〇〇（制作フロー準備中）」と表示し、
  実行しても安全に「準備中」メッセージを返す（エラー扱いにしない）
- ダッシュボードタブから、承認センター・CEO Inbox・Executive Boardレビュー
  資料作成へ直接遷移できる（Quest117）

## Developer Modeに退避した操作（Quest114・117）
- Generate Assets（旧UI）
- 📊 進行状況を見る／④ プロンプト生成／⑤ 画像生成／⑥ 確認（AIレビュー）／
  ⑦ 提出データ作成（各Project行の「🔧 詳細操作を表示（開発者向け）」内に
  折りたたみ、CEO通常画面では非表示）
- 🚀 スタンプを作る（Quest96・旧v1系パイプライン）：ダッシュボードタブの
  「🔧 詳細情報を見る」内に格納し、初期状態で折りたたみ
- CEO Inbox全文・資本配分・Issue Pipeline・週次取締役会・自己改善提案・
  AI経営会議・実装準備・自律実装フロー・PRドラフト・ログ等（Quest117で
  「🔧 詳細情報を見る」へ集約、CEO Home本体には出さない）
"""


def build_api_summary_markdown() -> str:
    """dashboard_web/app.pyの主要APIをまとめたMarkdownを返す（固定テンプレート）。"""
    rows = [
        ("GET", "/api/projects", "登録済みProject一覧を返す", "プロジェクトタブ表示"),
        ("POST", "/api/projects/create", "新規Projectを作成する", "「作成」ボタン"),
        ("POST", "/api/projects/archive", "ProjectをArchived化する", "「アーカイブ」リンク"),
        ("POST", "/api/projects/run-production", "Production Orchestratorを1回実行する（Quest113〜115）", "「🚀 このProjectを制作する」"),
        ("GET", "/api/projects/<id>/production-report", "保存済みproduction_report.jsonを返す", "制作結果パネル"),
        ("GET", "/api/projects/<id>/production-status", "7ステップ進捗・次のおすすめActionを返す（Quest112）", "「📊 進行状況を見る」（Developer Mode）"),
        ("GET", "/api/projects/<id>/download-export", "提出データ（ZIP）をダウンロードさせる", "「⬇ 提出データをダウンロード」"),
        ("GET", "/api/dashboard/home", "CEO Home向け集計値を返す", "③ 進行中Project"),
        ("GET", "/api/approvals", "承認待ち一覧・件数を返す", "④ 要承認事項"),
        ("GET", "/api/generated-assets", "生成済みAsset一覧を返す", "生成物タブ"),
        ("GET", "/api/notifications", "通知一覧を返す", "通知タブ"),
        ("GET", "/api/references", "参考画像一覧・カテゴリ・Project一覧を返す", "参考画像タブ"),
        ("GET", "/api/ip-memory", "登録済みIP一覧を返す", "キャラクター管理タブ"),
        ("POST", "/api/dashboard/review-package/create", "Executive Boardレビュー資料を生成する（Quest116〜117）", "「📦 Executive Boardレビュー資料を作成」"),
        ("GET", "/api/dashboard/review-package/latest", "最新のReview Package情報を返す（Quest116）", "Review Package結果表示"),
        ("GET", "/api/dashboard/review-package/download/<package_id>", "指定Review PackageのZIPをダウンロードさせる（Quest116）", "「⬇ ダウンロード」"),
    ]
    lines = ["# API Summary（主要APIのみ、完全自動抽出ではなく手動整理）", "", "| Method | Path | 役割 | 対応するDashboard操作 |", "|---|---|---|---|"]
    for method, path, role, op in rows:
        lines.append(f"| {method} | {path} | {role} | {op} |")
    return "\n".join(lines) + "\n"


def build_ux_notes_markdown() -> str:
    """現在分かっているUX上の注意点・改善候補を返す（固定テンプレート、Quest114〜117時点）。"""
    return """# UX Notes（Quest114〜117時点）

- CEO向け導線とDeveloper Modeは分離済み（Quest114）
- 旧v1系「🚀 スタンプを作る」パイプラインはDeveloper Modeへ退避済み（Quest114）
- 🚀ボタンの意味は「🚀 このProjectを制作する」に統一済み（Quest115）
- 未対応Asset Type（line_sticker以外）は「準備中」と安全に表示される（Quest115）
- production_report.jsonにasset_type/asset_type_labelが記録されるようになった（Quest115）
- CEO Homeを「①今日やること→②AI社員からの重要報告→③進行中Project→
  ④要承認事項→⑤最近完了した制作」の意思決定優先順位に整理済み（Quest117）
- API・Prompt・Production Step等の技術詳細はCEO Homeから排除し、
  「🔧 詳細情報を見る」1箇所に集約済み（Quest117）
- Projectsタブの行はProject名／種類／状態／次にやること／🚀ボタンのみに
  簡素化し、進行状況確認・④〜⑦の個別工程はDeveloper Modeへ移動済み（Quest117）
- 「⑤ 最近完了した制作」はProject一覧＋各Projectのproduction-reportを
  都度フロントエンドで集計しており、Project数が増えると初回表示が遅くなる
  可能性がある（専用の集計APIは未整備、将来対応候補）
- スクリーンショット自動撮影は未対応（Review Package v1の対象外、将来対応）
- dashboard_structure.md・api_summary.mdは完全自動抽出ではなく、現時点の
  仕様に基づく固定テンプレート（Dashboard側の変更に追従するには手動更新が必要）
- Project × IP Memoryの紐付けがまだ無いため、Production Statusの①②③
  （IP DNA/IP Bible/Style Guide）はip_name未指定の場合すべてpending表示になる
"""


def build_review_package_summary_markdown(
    project_summary: dict,
    production_status: dict,
    ceo_home_summary: dict,
    generated_at: str,
) -> str:
    """Executive Boardが最初に読む要約Markdownを組み立てる。"""
    from services.production_orchestrator import (
        SUPPORTED_PRODUCTION_ASSET_TYPES, get_asset_type_label, get_image_generation_capability,
    )

    projects = project_summary.get("projects", [])
    asset_types_in_use = {p.get("asset_type") for p in projects if p.get("asset_type")}
    supported_in_use = sorted(t for t in asset_types_in_use if t in SUPPORTED_PRODUCTION_ASSET_TYPES)
    unsupported_in_use = sorted(t for t in asset_types_in_use if t not in SUPPORTED_PRODUCTION_ASSET_TYPES)

    production_possible_count = sum(1 for p in projects if p.get("asset_type") in SUPPORTED_PRODUCTION_ASSET_TYPES)
    ready_count = sum(1 for p in production_status.get("projects", []) if p.get("ready_for_submission"))

    def _label_list(types: list[str]) -> str:
        if not types:
            return "（なし）"
        return "、".join(f"{get_asset_type_label(t)}（{t}）" for t in types)

    # Quest119：制作結果が「動いているだけ」ではなく、実際に販売可能な
    # 画像（AI画像生成）になっているかをExecutive Boardが最初に判断できる
    # ようにする。
    image_gen = get_image_generation_capability()
    ai_status_line = (
        f"AI画像生成API：{'設定済み' if image_gen.get('ai_configured') else '未設定'}"
        f"／使用予定モデル：{image_gen.get('model')}"
    )
    if not image_gen.get("ai_configured"):
        ai_status_line += f"／fallback理由：{image_gen.get('fallback_reason')}"

    lines = [
        "# Review Package Summary",
        "",
        f"- 作成日時：{generated_at}",
        f"- Project数：{project_summary.get('count', 0)}",
        f"- 対応済みAsset Type：{_label_list(supported_in_use)}",
        f"- 未対応Asset Type：{_label_list(unsupported_in_use)}",
        f"- Production可能Project数：{production_possible_count}",
        f"- 提出準備済みProject数：{ready_count}",
        f"- {ai_status_line}",
        "",
        "## 主な次アクション",
        f"- {ceo_home_summary.get('next_action', '-')}",
    ]

    blocking_projects = [
        p for p in production_status.get("projects", [])
        if p.get("next_action") and not p.get("ready_for_submission")
    ][:5]
    if blocking_projects:
        lines.append("")
        lines.append("## Project別の次アクション（抜粋）")
        for p in blocking_projects:
            lines.append(f"- Project {p.get('project_id')}：{p.get('next_action')}")

    return "\n".join(lines) + "\n"


# ──────────────────────────────────────────
# 3. Review Package本体
# ──────────────────────────────────────────

def create_review_package(outputs_dir: Path | None = None, projects_dir: Path | None = None) -> dict:
    """
    Quest116：Dashboard構造・API一覧・Project一覧・Production Status・
    CEO Home集計・UX Notesを収集し、Markdown/JSONとして保存した上でZIP化する
    （Dashboardの「📦 Review Packageを作成」ボタンから呼ばれる）。

    戻り値: {"ok": bool, "package_id": str, "path": str, "files": list[str],
             "zip_path": str, "created_at": str, "error": str | None}
    例外を投げない（各収集処理は個別にtry/exceptで守られる）。
    """
    package_id = _new_package_id()
    directory = _package_dir(package_id, outputs_dir)

    try:
        directory.mkdir(parents=True, exist_ok=True)
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        project_summary = collect_project_summary(projects_dir=projects_dir, outputs_dir=outputs_dir)
        production_status = collect_production_status(project_summary.get("projects", []), outputs_dir=outputs_dir)
        ceo_home_summary = collect_ceo_home_summary(projects_dir=projects_dir, outputs_dir=outputs_dir)

        (directory / "dashboard_structure.md").write_text(build_dashboard_structure_markdown(), encoding="utf-8")
        (directory / "api_summary.md").write_text(build_api_summary_markdown(), encoding="utf-8")
        (directory / "project_summary.json").write_text(
            json.dumps(project_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        (directory / "production_status.json").write_text(
            json.dumps(production_status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        (directory / "ceo_home_summary.json").write_text(
            json.dumps(ceo_home_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        (directory / "ux_notes.md").write_text(build_ux_notes_markdown(), encoding="utf-8")
        (directory / "review_package_summary.md").write_text(
            build_review_package_summary_markdown(project_summary, production_status, ceo_home_summary, generated_at),
            encoding="utf-8",
        )

        files = [f for f in _REQUIRED_FILES if (directory / f).exists()]

        zip_path = directory / _ZIP_FILENAME
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename in files:
                zf.write(directory / filename, arcname=filename)

        return {
            "ok": True,
            "package_id": package_id,
            "path": str(directory),
            "files": files + [_ZIP_FILENAME],
            "zip_path": str(zip_path),
            "created_at": generated_at,
            "error": None,
        }
    except Exception as e:
        print(f"[警告] Review Packageの生成に失敗しました：{e}")
        return {
            "ok": False, "package_id": package_id, "path": str(directory),
            "files": [], "zip_path": None, "created_at": None, "error": str(e),
        }


def list_review_packages(outputs_dir: Path | None = None) -> list[dict]:
    """
    生成済みReview Package一覧を新しい順（package_id降順＝生成日時降順）で返す。
    戻り値: [{"package_id": str, "path": str, "has_zip": bool}, ...]
    ディレクトリ未存在・読み込み失敗時は空リストを返す。例外を投げない。
    """
    try:
        base = _packages_dir(outputs_dir)
        if not base.exists():
            return []
        packages = []
        for entry in sorted(base.iterdir(), reverse=True):
            if not entry.is_dir():
                continue
            packages.append({
                "package_id": entry.name,
                "path": str(entry),
                "has_zip": (entry / _ZIP_FILENAME).exists(),
            })
        return packages
    except Exception as e:
        print(f"[警告] Review Package一覧の取得に失敗しました：{e}")
        return []


def get_latest_review_package(outputs_dir: Path | None = None) -> dict | None:
    """最新のReview Packageのmanifest（package_id・含まれるファイル一覧）を返す。無ければNone。"""
    try:
        packages = list_review_packages(outputs_dir)
        if not packages:
            return None
        latest = packages[0]
        directory = Path(latest["path"])
        files = [f.name for f in sorted(directory.iterdir()) if f.is_file()]
        return {"package_id": latest["package_id"], "path": latest["path"], "files": files}
    except Exception as e:
        print(f"[警告] 最新Review Packageの取得に失敗しました：{e}")
        return None


def get_review_package_zip_path(package_id: str, outputs_dir: Path | None = None) -> Path | None:
    """指定package_idのreview_package.zipのパスを返す。存在しない場合はNone。例外を投げない。"""
    try:
        zip_path = _package_dir(package_id, outputs_dir) / _ZIP_FILENAME
        return zip_path if zip_path.exists() else None
    except Exception as e:
        print(f"[警告] Review Package ZIPのパス取得に失敗しました（{package_id}）：{e}")
        return None


if __name__ == "__main__":
    # Quest116: 動作確認用のCLI導線。
    #   python services/dashboard_review_package_service.py
    result = create_review_package()
    print(json.dumps(result, ensure_ascii=False, indent=2))
