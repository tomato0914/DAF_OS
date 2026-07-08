"""
DAF OS v1.0 — Web ダッシュボード
outputs/dashboard.md を読み取り、ブラウザで表示する Flask アプリ。
"""

import re
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request, send_from_directory, abort

# services/ を import パスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

app = Flask(__name__)

BASE_DIR = Path(__file__).parent.parent
DASHBOARD_MD = BASE_DIR / "outputs" / "dashboard.md"

# main.py と同様にCWDをDAF_OSルートへ固定する。
# agents/*.py が memory/*.md を相対パスで参照するため、起動時のCWDに依存してしまうと
# （Quest52で発見）Flaskをどこから起動したかによって FileNotFoundError になる。
os.chdir(BASE_DIR)


# ──────────────────────────────────────────
# markdown パーサー
# ──────────────────────────────────────────

def _section(text: str, heading: str) -> str:
    """## heading の内容を返す。"""
    m = re.search(
        rf"## {re.escape(heading)}\s*\n([\s\S]*?)(?=\n## |\Z)",
        text,
    )
    return m.group(1).strip() if m else ""


def _table_rows(md_table: str) -> list[dict]:
    """
    markdown テーブルを [{col: val, ...}] に変換する。
    セクション末尾の "---"（区切り線）などテーブル行ではない行が
    まぎれ込んだ場合は無視する（"|" で始まらない行、列数が
    ヘッダーと一致しない行、値が空の行はスキップ）。
    """
    lines = [l.strip() for l in md_table.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return []
    headers = [h.strip() for h in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[2:]:          # skip separator
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        if not any(cells):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def _progress_blocks(text: str) -> list[dict]:
    """進捗バーブロックをパースする。"""
    results = []
    for m in re.finditer(
        r"\*\*(.+?)\*\*\s*\n```\s*\n([█░]+)\s+(\d+)%\s+([\d/]+\s*.+?)\n```",
        text,
    ):
        results.append({
            "label": m.group(1),
            "bar": m.group(2),
            "pct": int(m.group(3)),
            "detail": m.group(4).strip(),
        })
    return results


def _read_raw_or_none(path: Path) -> str | None:
    """
    ファイルが存在すれば内容をそのまま返し、無ければNoneを返す。読み込み
    失敗時もNoneを返し、例外を投げない（Dashboard最新化・Quest80〜87の
    生成物をそのまま表示するための最小限のヘルパー）。
    """
    try:
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8").strip() or None
    except Exception:
        return None


def _agent_status(text: str) -> list[dict]:
    """- ✅/⬜ エージェント名 の一覧を返す。"""
    agents = []
    for m in re.finditer(r"- (✅|⬜) (.+)", text):
        agents.append({"name": m.group(2).strip(), "active": m.group(1) == "✅"})
    return agents


def _github_rows(text: str) -> list[dict]:
    """GitHub Issue テーブル行を返す。"""
    m = re.search(r"## 5\. GitHub.+?\n([\s\S]*?)(?=\n## |\Z)", text)
    if not m:
        return []
    block = m.group(1)
    issues = []
    for row in re.finditer(r"\|\s*\[#(\d+)\]\(([^)]+)\)\s*\|\s*(.+?)\s*\|", block):
        issues.append({
            "number": int(row.group(1)),
            "url": row.group(2),
            "title": row.group(3),
        })
    return issues


def parse_dashboard() -> dict:
    """dashboard.md を読み込み、構造化した dict を返す。"""
    if not DASHBOARD_MD.exists():
        return {"error": "dashboard.md が見つかりません。`python main.py` を実行してください。"}

    text = DASHBOARD_MD.read_text(encoding="utf-8")

    # 最終更新
    updated_m = re.search(r"> 最終更新: (.+)", text)
    updated = updated_m.group(1).strip() if updated_m else "—"

    # 1. 今日の状況
    status_section = _section(text, "1. 今日の状況")
    status_rows = _table_rows(status_section)

    # 2. AI提案
    proposal = _section(text, "2. 最新のAI提案")

    # 3. 次のアクション
    next_section = _section(text, "3. 次にCEOがやること")
    actions = []
    for line in next_section.splitlines():
        line = line.strip()
        if re.match(r"\d+\.", line):
            actions.append(re.sub(r"^\d+\.\s*", "", line))

    # 4. 進捗バー + AI社員
    progress_section = _section(text, "4. 進捗バー")
    progress = _progress_blocks(progress_section)
    agents = _agent_status(progress_section)

    # 5. GitHub Issues
    gh_issues = _github_rows(text)
    gh_enabled = bool(gh_issues) or bool(
        re.search(r"## 5\. GitHub Open Issues（\w", text)
    )

    # 7. メモリ見直し提案
    memory_suggestions = (BASE_DIR / "outputs" / "memory_update_suggestions.md").exists()

    # 承認センター
    from services.approval_service import (
        get_pending_items, get_approved_count, get_rejected_count,
        get_completed_count, get_completed_items,
    )
    pending_items   = get_pending_items(BASE_DIR / "outputs")
    approved_count  = get_approved_count(BASE_DIR / "outputs")
    rejected_count  = get_rejected_count(BASE_DIR / "outputs")
    completed_count = get_completed_count(BASE_DIR / "outputs")
    completed_items = get_completed_items(BASE_DIR / "outputs")

    # PRドラフト（v1.7）
    from services.pr_preparation_service import get_pr_draft_summary
    pr_draft = get_pr_draft_summary(BASE_DIR / "outputs")

    # 半自律実装フロー（v2.0 Phase2）
    from services.autonomous_flow_service import get_autonomous_flow_summary
    autonomous_flow = get_autonomous_flow_summary(BASE_DIR / "outputs")

    # 管理中プロダクト（v2.1 Quest40）
    from services.product_registry_service import get_product_summary
    products = get_product_summary()

    # プロダクト別Issue状況（v2.2 Quest41）
    from services.dashboard_generator import get_product_issue_stats
    product_issue_stats = get_product_issue_stats(BASE_DIR / "outputs")

    # ワンクリック実装準備（v2.3 Quest42）
    from services.autonomous_flow_service import get_approved_implementation_count
    approved_implementation_count = get_approved_implementation_count(BASE_DIR / "outputs")

    # CEOデイリーブリーフ（v2.4 Quest43）
    from services.ceo_brief_service import get_ceo_brief_summary
    ceo_brief = get_ceo_brief_summary(BASE_DIR / "outputs")

    # Reflection Summary（Quest61・読み取り専用。reflection_report.md が無ければ None）
    from services.reflection_service import get_reflection_summary
    reflection = get_reflection_summary(BASE_DIR / "outputs")

    # Dashboard最新化（Quest80〜87の生成物を読み取り専用でそのまま表示する）。
    # それぞれ個別にtry/exceptで守り、1つが読み込めなくてもDashboard全体を
    # 落とさない。v1はMarkdown本文をそのまま表示するだけなので、生の文字列
    # （存在しなければNone）をそのまま返す。
    ceo_inbox = _read_raw_or_none(BASE_DIR / "outputs" / "ceo_inbox.md")
    capital_allocation = _read_raw_or_none(BASE_DIR / "outputs" / "capital_allocation.md")
    issue_pipeline = _read_raw_or_none(BASE_DIR / "outputs" / "issue_pipeline" / "generated_issues.md")
    weekly_board_meeting = _read_raw_or_none(BASE_DIR / "outputs" / "weekly_board_meeting.md")
    self_improvement = _read_raw_or_none(BASE_DIR / "outputs" / "self_improvement_suggestions.md")

    return {
        "updated": updated,
        "status": status_rows,
        "proposal": proposal,
        "actions": actions,
        "progress": progress,
        "agents": agents,
        "github_issues": gh_issues,
        "github_enabled": gh_enabled,
        "memory_suggestions": memory_suggestions,
        "pending_approvals": pending_items,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "completed_count": completed_count,
        "completed_items": completed_items,
        "pr_draft": pr_draft,
        "autonomous_flow": autonomous_flow,
        "products": products,
        "product_issue_stats": product_issue_stats,
        "approved_implementation_count": approved_implementation_count,
        "ceo_brief": ceo_brief,
        "reflection": reflection,
        "ceo_inbox": ceo_inbox,
        "capital_allocation": capital_allocation,
        "issue_pipeline": issue_pipeline,
        "weekly_board_meeting": weekly_board_meeting,
        "self_improvement": self_improvement,
        "raw": text,
    }


# ──────────────────────────────────────────
# ルート
# ──────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    return jsonify(parse_dashboard())


# ──────────────────────────────────────────
# 承認センター API
# ──────────────────────────────────────────

OUTPUTS_DIR = BASE_DIR / "outputs"
PENDING_DIR = OUTPUTS_DIR / "approvals" / "pending"

def _safe_approval_id(raw_id: str) -> str | None:
    """
    approval_id がファイル名として安全かチェックする。
    パストラバーサルを防ぐため、スラッシュ・ドット連続・空文字を拒否する。
    """
    if not raw_id:
        return None
    import re as _re
    # 英数字・ハイフン・アンダースコアのみ許可
    if not _re.match(r'^[\w\-]+$', raw_id):
        return None
    return raw_id


@app.route("/api/approvals")
def api_approvals():
    """承認待ち一覧 + 件数 + 承認済み/却下済み/実装完了の一覧を返す。"""
    try:
        from services.approval_service import (
            get_pending_items, get_approved_count, get_approved_items,
            get_rejected_count, get_rejected_items,
            get_pending_detail, get_completed_count, get_completed_items,
        )
        items = get_pending_items(OUTPUTS_DIR)
        # 各アイテムにプレビューを付加
        detailed = []
        for item in items:
            detail = get_pending_detail(item["id"], OUTPUTS_DIR)
            detailed.append(detail or item)

        return jsonify({
            "pending": detailed,
            "approved_count": get_approved_count(OUTPUTS_DIR),
            "rejected_count": get_rejected_count(OUTPUTS_DIR),
            "completed_count": get_completed_count(OUTPUTS_DIR),
            "approved_items": get_approved_items(OUTPUTS_DIR),
            "rejected_items": get_rejected_items(OUTPUTS_DIR),
            "completed_items": get_completed_items(OUTPUTS_DIR),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/approvals/approve", methods=["POST"])
def api_approve():
    """指定 ID のアイテムを承認する。"""
    try:
        data = request.get_json(force=True) or {}
        raw_id = data.get("id", "")
        approval_id = _safe_approval_id(raw_id)
        if not approval_id:
            return jsonify({"ok": False, "error": "無効なIDです"}), 400

        from services.approval_service import approve
        ok = approve(approval_id)
        return jsonify({"ok": ok, "id": approval_id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/approvals/reject", methods=["POST"])
def api_reject():
    """指定 ID のアイテムを却下する。"""
    try:
        data = request.get_json(force=True) or {}
        raw_id = data.get("id", "")
        reason = str(data.get("reason", "（理由なし）"))[:500]  # 理由は500文字に制限
        approval_id = _safe_approval_id(raw_id)
        if not approval_id:
            return jsonify({"ok": False, "error": "無効なIDです"}), 400

        from services.approval_service import reject
        ok = reject(approval_id, reason)
        return jsonify({"ok": ok, "id": approval_id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/approvals/complete", methods=["POST"])
def api_complete():
    """
    実装が完了した承認済みアイテムを completed/ に移動する（Quest47）。
    GitHub Issue は自動クローズしない（Close候補として記録するのみ）。
    """
    try:
        data = request.get_json(force=True) or {}
        raw_id = data.get("id", "")
        approval_id = _safe_approval_id(raw_id)
        if not approval_id:
            return jsonify({"ok": False, "error": "無効なIDです"}), 400

        from services.approval_service import complete
        ok = complete(approval_id)
        return jsonify({"ok": ok, "id": approval_id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ──────────────────────────────────────────
# PRドラフト API（v1.7・読み取り専用）
# ──────────────────────────────────────────

@app.route("/api/pr_draft")
def api_pr_draft():
    """pr_draft.md の内容を返す（存在しない場合は exists: false）。"""
    try:
        path = OUTPUTS_DIR / "pr_draft.md"
        if not path.exists():
            return jsonify({"exists": False})
        return jsonify({"exists": True, "content": path.read_text(encoding="utf-8")})
    except Exception as e:
        return jsonify({"exists": False, "error": str(e)}), 500


# ──────────────────────────────────────────
# 半自律実装フロー API（v2.0 Phase2・読み取り専用）
# ──────────────────────────────────────────

@app.route("/api/autonomous_flow")
def api_autonomous_flow():
    """autonomous_flow.md の内容を返す（存在しない場合は exists: false）。"""
    try:
        path = OUTPUTS_DIR / "autonomous_flow.md"
        if not path.exists():
            return jsonify({"exists": False})
        return jsonify({"exists": True, "content": path.read_text(encoding="utf-8")})
    except Exception as e:
        return jsonify({"exists": False, "error": str(e)}), 500


# ──────────────────────────────────────────
# 管理中プロダクト API（v2.1 Quest40・読み取り専用）
# ──────────────────────────────────────────

@app.route("/api/products")
def api_products():
    """products/*.md から読み込んだプロダクト一覧を返す。"""
    try:
        from services.product_registry_service import get_product_summary
        return jsonify({"products": get_product_summary()})
    except Exception as e:
        return jsonify({"products": [], "error": str(e)}), 500


# ──────────────────────────────────────────
# ワンクリック実装準備 API（v2.3 Quest42 / Quest48で選択実装に対応）
# ──────────────────────────────────────────

@app.route("/api/start_implementation", methods=["POST"])
def api_start_implementation():
    """
    承認済み実装アイテムから autonomous_flow.md / claude_code_prompt.md を生成する。
    リクエストボディに "approval_ids": [...] を指定すると、そのIssueだけを
    claude_code_prompt.md に含める（Quest48）。指定しなければ従来どおり全件が対象。
    git commit / push / Claude Code起動は一切行わない。
    """
    try:
        data = request.get_json(silent=True) or {}
        raw_ids = data.get("approval_ids") or []
        if not isinstance(raw_ids, list):
            return jsonify({"ok": False, "message": "approval_ids はリストで指定してください"}), 400

        approval_ids = []
        for raw_id in raw_ids:
            safe_id = _safe_approval_id(str(raw_id))
            if not safe_id:
                return jsonify({"ok": False, "message": f"無効なIDです: {raw_id}"}), 400
            approval_ids.append(safe_id)

        from services.implementation_launcher_service import start_implementation
        result = start_implementation(OUTPUTS_DIR, approval_ids=approval_ids or None)
        return jsonify(result), (200 if result["ok"] else 400)
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


# ──────────────────────────────────────────
# CEOデイリーブリーフ API（v2.4 Quest43・読み取り専用）
# ──────────────────────────────────────────

@app.route("/api/ceo_brief")
def api_ceo_brief():
    """ceo_brief.md の内容を返す（存在しない場合は exists: false）。"""
    try:
        path = OUTPUTS_DIR / "ceo_brief.md"
        if not path.exists():
            return jsonify({"exists": False})
        return jsonify({"exists": True, "content": path.read_text(encoding="utf-8")})
    except Exception as e:
        return jsonify({"exists": False, "error": str(e)}), 500


# ──────────────────────────────────────────
# AI経営会議UI API（v2.7 Quest52・MVP）
# ──────────────────────────────────────────

@app.route("/api/meeting/start", methods=["POST"])
def api_meeting_start():
    """
    CEOの相談テキストを相談専用のMeeting Crew（run_meeting_crew、Quest55）へ渡し、
    outputs/meeting_log.md を上書き生成する。
    App Store説明文・SNS投稿・チェックリスト・GitHub Issue生成などの固定テンプレートは扱わない
    （それらは main.py / ./run_daf.sh が使う run_launch_crew の役割のまま）。
    """
    try:
        data = request.get_json(force=True) or {}
        message = str(data.get("message", "")).strip()[:2000]
        if not message:
            return jsonify({"ok": False, "message": "相談内容を入力してください"}), 400

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return jsonify({
                "ok": False,
                "message": "OPENROUTER_API_KEY が設定されていません。.env ファイルを確認してください。",
            }), 400

        from crews.meeting_crew import run_meeting_crew
        from services.memory_service import load_company_memory

        company_memory = load_company_memory()

        try:
            results = run_meeting_crew(
                ceo_input=message,
                openrouter_api_key=api_key,
                notion_api_key=os.getenv("NOTION_API_KEY") or None,
                company_memory=company_memory,
            )
        except Exception as e:
            return jsonify({
                "ok": False,
                "message": f"AI経営会議の実行中にエラーが発生しました：{e}",
            }), 500

        meeting_log = results["meeting_log"]
        (OUTPUTS_DIR / "meeting_log.md").write_text(meeting_log, encoding="utf-8")

        return jsonify({"ok": True, "meeting_log": meeting_log})
    except Exception as e:
        return jsonify({"ok": False, "message": f"予期しないエラーが発生しました：{e}"}), 500


# ──────────────────────────────────────────
# Project Management API（Quest93）
# 指示書は POST /projects/create・GET /projects・POST /projects/archive を
# 挙げていたが、既存APIがすべて /api/ 配下に統一されているため
# （/api/approvals・/api/pr_draft 等）、既存構成に合わせて /api/projects... とした。
# ──────────────────────────────────────────

PROJECTS_DIR = BASE_DIR / "projects"


@app.route("/api/projects")
def api_projects():
    """登録済みProject一覧を返す。"""
    try:
        from services.project_service import list_projects
        return jsonify({"projects": list_projects(projects_dir=PROJECTS_DIR)})
    except Exception as e:
        return jsonify({"projects": [], "error": str(e)}), 500


@app.route("/api/projects/create", methods=["POST"])
def api_projects_create():
    """新規Projectを作成する（New Projectフォームから呼ばれる）。"""
    try:
        data = request.get_json(force=True) or {}
        name = str(data.get("name", "")).strip()[:200]
        asset_type = str(data.get("asset_type", "generic")).strip()[:50]
        vision = str(data.get("vision", "")).strip()[:2000]
        raw_metrics = data.get("success_metrics") or []

        if not name:
            return jsonify({"ok": False, "error": "Project Nameを入力してください"}), 400

        success_metrics = None
        if isinstance(raw_metrics, list):
            success_metrics = [str(m).strip()[:200] for m in raw_metrics if str(m).strip()]
        elif isinstance(raw_metrics, str) and raw_metrics.strip():
            success_metrics = [line.strip() for line in raw_metrics.splitlines() if line.strip()]

        from services.project_service import create_project
        result = create_project(
            name=name,
            asset_type=asset_type,
            vision=vision,
            success_metrics=success_metrics,
            projects_dir=PROJECTS_DIR,
        )
        return jsonify(result), (200 if result.get("ok") else 400)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/projects/archive", methods=["POST"])
def api_projects_archive():
    """指定ProjectのStatusをarchivedにする。"""
    try:
        data = request.get_json(force=True) or {}
        project_id = str(data.get("id", "")).strip()
        if not re.match(r"^[\w\-]+$", project_id):
            return jsonify({"ok": False, "error": "無効なProject IDです"}), 400

        from services.project_service import archive_project
        result = archive_project(project_id, projects_dir=PROJECTS_DIR)
        return jsonify(result), (200 if result.get("ok") else 400)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/projects/generate-assets", methods=["POST"])
def api_projects_generate_assets():
    """
    Quest94：指定Projectを起点にExecution Plan登録→Asset生成→
    Notification更新まで進める（Projectsタブの「Generate Assets」ボタン
    から呼ばれる）。v1ではasset_typeがline_stickerのProjectのみ対応する。
    """
    try:
        data = request.get_json(force=True) or {}
        project_id = str(data.get("id", "")).strip()
        if not re.match(r"^[\w\-]+$", project_id):
            return jsonify({"ok": False, "error": "無効なProject IDです"}), 400

        from services.project_service import generate_project_assets
        result = generate_project_assets(project_id, projects_dir=PROJECTS_DIR, outputs_dir=OUTPUTS_DIR)
        return jsonify(result), (200 if result.get("ok") else 400)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ──────────────────────────────────────────
# Dashboard v1（試験運用版）API
# CEO Home・Generated Assets・Notificationsタブ向け（読み取り専用）。
# 各エンドポイントは情報源ごとに個別にtry/exceptで守り、1つが読み込めなくても
# Dashboard全体を落とさない。
# ──────────────────────────────────────────

@app.route("/api/generated-assets")
def api_generated_assets():
    """outputs/generated_assets/*/metadata.md を集計して返す。"""
    try:
        from services.asset_generator_service import list_generated_assets
        return jsonify({"assets": list_generated_assets(outputs_dir=OUTPUTS_DIR)})
    except Exception as e:
        return jsonify({"assets": [], "error": str(e)}), 500


@app.route("/api/renderer")
def api_renderer():
    """
    Quest98：現在使用中の画像生成Renderer（既定はPillow Renderer）と、
    将来切替可能なRenderer一覧を返す。
    """
    try:
        from services.image_generation_service import get_renderer_info
        return jsonify(get_renderer_info())
    except Exception as e:
        return jsonify({"id": "unknown", "display_name": "unknown", "available": [], "error": str(e)}), 500


# ──────────────────────────────────────────
# Vega Creative Direction（Quest99・読み取り専用）
# ──────────────────────────────────────────

@app.route("/api/creative-briefs")
def api_creative_briefs():
    """生成済みの全Creative Brief（Vega Creative Director）を一覧で返す。"""
    try:
        from services.creative_brief_service import list_creative_briefs
        return jsonify({"briefs": list_creative_briefs(outputs_dir=OUTPUTS_DIR)})
    except Exception as e:
        return jsonify({"briefs": [], "error": str(e)}), 500


@app.route("/api/creative-briefs/<project_id>")
def api_creative_brief_detail(project_id):
    """指定ProjectのCreative Brief詳細を返す。"""
    safe_id = _safe_project_id(project_id)
    if not safe_id:
        return jsonify({"exists": False, "error": "無効なProject IDです"}), 400
    try:
        from services.creative_brief_service import get_creative_brief
        return jsonify(get_creative_brief(safe_id, outputs_dir=OUTPUTS_DIR))
    except Exception as e:
        return jsonify({"exists": False, "project_id": safe_id, "error": str(e)}), 500


@app.route("/api/reference-library")
def api_reference_library():
    """
    Quest101：Reference Library（outputs/reference_library/）の集計
    （登録画像数・タグ一覧・最新登録画像・Reference Summary）を返す。
    """
    try:
        from services.reference_analysis_service import get_reference_library_summary
        return jsonify(get_reference_library_summary(outputs_dir=OUTPUTS_DIR))
    except Exception as e:
        return jsonify({"count": 0, "tags": [], "latest": None, "summary": "", "error": str(e)}), 500


# ──────────────────────────────────────────
# Reference Upload UI API（Quest102）
# 画像解析AIは使わない。タグ・説明文はCEOが手動入力する前提。
# ──────────────────────────────────────────

_REFERENCE_LIBRARY_DIR = OUTPUTS_DIR / "reference_library"
_REFERENCE_ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp"}


@app.route("/api/references")
def api_references():
    """
    登録済み参考画像の一覧・既定カテゴリ・登録済みProject一覧を返す
    （Referencesタブのアップロードフォーム・一覧表示向け）。
    """
    try:
        from services.reference_analysis_service import list_reference_images, get_default_categories
        from services.project_service import list_projects

        references = list_reference_images(outputs_dir=OUTPUTS_DIR)

        projects = []
        try:
            projects = list_projects(projects_dir=PROJECTS_DIR)
        except Exception:
            pass  # Project一覧が取れなくても参考画像一覧は返す

        return jsonify({
            "references": references,
            "categories": get_default_categories(),
            "projects": projects,
        })
    except Exception as e:
        return jsonify({"references": [], "categories": [], "projects": [], "error": str(e)}), 500


@app.route("/api/references/upload", methods=["POST"])
def api_references_upload():
    """
    参考画像をアップロードし、outputs/reference_library/<category>/ へ保存、
    合わせてreference.jsonを登録する（Referencesタブのアップロードフォームから呼ばれる）。
    画像解析は行わない。tags はカンマ区切りテキストを配列化して保存する。
    """
    try:
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            return jsonify({"ok": False, "error": "画像ファイルを選択してください"}), 400

        ext = Path(uploaded.filename).suffix.lower()
        if ext not in _REFERENCE_ALLOWED_EXT:
            allowed = "/".join(sorted(e.lstrip(".") for e in _REFERENCE_ALLOWED_EXT))
            return jsonify({"ok": False, "error": f"対応していない画像形式です（対応形式: {allowed}）"}), 400

        category = str(request.form.get("category", "")).strip()[:50] or "uncategorized"
        project_id = str(request.form.get("project", "")).strip()[:100] or None
        description = str(request.form.get("description", "")).strip()[:1000]
        raw_tags = str(request.form.get("tags", ""))
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

        file_bytes = uploaded.read()

        from services.reference_analysis_service import save_reference_image
        result = save_reference_image(
            file_bytes=file_bytes,
            original_filename=uploaded.filename,
            category=category,
            project_id=project_id,
            tags=tags,
            description=description,
            outputs_dir=OUTPUTS_DIR,
        )
        return jsonify(result), (200 if result.get("ok") else 400)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/references/summary/refresh", methods=["POST"])
def api_references_summary_refresh():
    """
    Reference Summary（Vega Reference Report）を再生成する。
    project_idを指定すればそのProjectのみ、未指定なら参考画像が登録済みの
    全Projectをまとめて更新する。
    """
    try:
        data = request.get_json(silent=True) or {}
        project_id = str(data.get("project_id", "")).strip()

        from services.reference_analysis_service import (
            generate_vega_reference_report, refresh_all_reference_summaries,
        )

        if project_id:
            result = generate_vega_reference_report(project_id, outputs_dir=OUTPUTS_DIR)
            return jsonify({"ok": result.get("ok", False), "results": [result]})

        results = refresh_all_reference_summaries(outputs_dir=OUTPUTS_DIR)
        return jsonify({"ok": True, "results": results})
    except Exception as e:
        return jsonify({"ok": False, "results": [], "error": str(e)}), 500


@app.route("/reference-library/<path:filename>")
def serve_reference_image(filename):
    """
    outputs/reference_library/ 配下の画像ファイルを返す（Referencesタブの一覧表示用）。
    許可された画像拡張子以外・reference.jsonは404にする。
    """
    ext = Path(filename).suffix.lower()
    if ext not in _REFERENCE_ALLOWED_EXT:
        abort(404)
    return send_from_directory(_REFERENCE_LIBRARY_DIR, filename)


def _safe_reference_component(name: str) -> str | None:
    """
    Reference画像解析/更新API向けのcategory・filenameの安全性チェック。
    スラッシュ・".."・空文字を拒否する（_safe_project_idと同じ方針だが、
    filenameには"."を許可する必要があるため専用の正規表現を使う）。
    """
    if not name or not re.match(r"^[\w\-.]+$", name) or ".." in name:
        return None
    return name


@app.route("/api/references/analyze", methods=["POST"])
def api_references_analyze():
    """
    Quest103：指定した参考画像をAI解析し、tags/animal/color/mood/memoの
    提案を返す（reference.jsonへは保存しない。CEOが確認・編集した上で
    /api/references/update を呼んで初めて保存される）。
    """
    try:
        data = request.get_json(force=True) or {}
        category = _safe_reference_component(str(data.get("category", "")))
        filename = _safe_reference_component(str(data.get("filename", "")))
        if not category or not filename:
            return jsonify({"success": False, "error": "無効なcategory/filenameです"}), 400

        image_path = _REFERENCE_LIBRARY_DIR / category / filename
        if not image_path.exists():
            return jsonify({"success": False, "error": "指定された画像が見つかりません"}), 404

        from services.reference_analysis_service import analyze_reference_image
        analysis = analyze_reference_image(str(image_path))

        return jsonify({"success": bool(analysis.get("ok")), "analysis": analysis})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/references/update", methods=["POST"])
def api_references_update():
    """
    Quest103：既存参考画像のtags/animal/color/mood/memoを更新する
    （AI解析結果・CEOの手動編集を保存するためのAPI）。
    指定しなかったフィールド・title/project_id等はそのまま保持される。
    対象が存在しない場合は404を返す。
    """
    try:
        data = request.get_json(force=True) or {}
        category = _safe_reference_component(str(data.get("category", "")))
        filename = _safe_reference_component(str(data.get("filename", "")))
        if not category or not filename:
            return jsonify({"ok": False, "error": "無効なcategory/filenameです"}), 400

        raw_tags = data.get("tags")
        if isinstance(raw_tags, str):
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        elif isinstance(raw_tags, list):
            tags = [str(t).strip() for t in raw_tags if str(t).strip()]
        else:
            tags = None

        from services.reference_analysis_service import update_reference_metadata
        result = update_reference_metadata(
            category=category,
            filename=filename,
            tags=tags,
            animal=data.get("animal") if "animal" in data else None,
            color=data.get("color") if "color" in data else None,
            mood=data.get("mood") if "mood" in data else None,
            memo=data.get("memo") if "memo" in data else None,
            outputs_dir=OUTPUTS_DIR,
        )
        if result.get("error") == "not_found":
            return jsonify({"ok": False, "error": "指定された参考画像が見つかりません"}), 404
        return jsonify(result), (200 if result.get("ok") else 400)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ──────────────────────────────────────────
# LINEスタンプ生成結果（Quest94 v2で追加、Quest97でProject別対応）
# フォルダを開かなくてもDashboard上でProject別に40枚のスタンプ・main/tab・
# zip・metadataを確認できるようにするためのAPI。
# ──────────────────────────────────────────

_LINE_STICKER_DIR = OUTPUTS_DIR / "generated_assets" / "line_sticker"
_LINE_STICKER_ALLOWED_EXT = {".png", ".zip", ".md"}


def _safe_project_id(raw_id: str) -> str | None:
    """project_idがフォルダ名として安全かチェックする（_safe_approval_idと同じ方針）。"""
    if not raw_id or not re.match(r"^[\w\-]+$", raw_id):
        return None
    return raw_id


@app.route("/api/generated-assets/line-sticker")
def api_generated_assets_line_sticker():
    """
    Quest97：outputs/generated_assets/line_sticker/ 配下の全Project
    （新形式のサブフォルダ＋後方互換のlegacyフラット形式）の一覧を返す。
    """
    try:
        from services.asset_generator_service import list_line_sticker_projects
        return jsonify({"projects": list_line_sticker_projects(outputs_dir=OUTPUTS_DIR)})
    except Exception as e:
        return jsonify({"projects": [], "error": str(e)}), 500


@app.route("/api/generated-assets/line-sticker/<project_id>")
def api_generated_assets_line_sticker_detail(project_id):
    """
    指定Project（project_id="legacy"の場合はQuest90〜96時代のフラット形式）の
    詳細（metadata.md・phrases.md・スタンプ画像一覧・main/tab/zip有無）を返す。
    """
    safe_id = _safe_project_id(project_id)
    if not safe_id:
        return jsonify({"exists": False, "error": "無効なProject IDです"}), 400
    try:
        from services.asset_generator_service import get_line_sticker_detail
        return jsonify(get_line_sticker_detail(outputs_dir=OUTPUTS_DIR, project_id=safe_id))
    except Exception as e:
        return jsonify({"exists": False, "project_id": safe_id, "error": str(e)}), 500


@app.route("/generated-assets/line-sticker/<path:filename>")
def serve_line_sticker_file(filename):
    """
    outputs/generated_assets/line_sticker/ 配下のファイルを返す。
    Dashboardのサムネイル表示・ZIPダウンロードから参照される。

    Quest97：<path:filename>はスラッシュを含む複数セグメントにもマッチする
    ため、このルート1つで旧形式（例：main.png）とProject別新形式
    （例：<project_id>/main.png）の両方を兼用できる（新形式専用のルートを
    別途増やす必要が無い）。ディレクトリトラバーサル対策はFlaskの
    send_from_directory（パス正規化・親ディレクトリ脱出防止）に委ね、
    許可された拡張子（png/zip/md）以外は404にする。
    """
    ext = Path(filename).suffix.lower()
    if ext not in _LINE_STICKER_ALLOWED_EXT:
        abort(404)
    return send_from_directory(_LINE_STICKER_DIR, filename)


@app.route("/api/notifications")
def api_notifications():
    """outputs/notifications.md を新しい順で返す。"""
    try:
        from services.notification_service import get_notifications
        return jsonify({"notifications": get_notifications(outputs_dir=OUTPUTS_DIR)})
    except Exception as e:
        return jsonify({"notifications": [], "error": str(e)}), 500


def _compute_next_action(pending_review_assets, pending_implementation_count, active_projects_count):
    """CEO Homeの「Next Action」を優先順位ルールに従って決定する。"""
    if pending_review_assets:
        return f"{pending_review_assets[0]['asset_type']} をレビューしてください。"
    if pending_implementation_count > 0:
        return "実装待ちIssueがあります。"
    if active_projects_count > 0:
        return "Execution Planを確認してください。"
    return "新しいProjectを作成してください。"


@app.route("/api/dashboard/home")
def api_dashboard_home():
    """
    CEO Home向けの集計値（Active Projects・Pending Reviews・Notifications・
    Pending Implementation・Next Action）を返す。各情報源の取得は個別に
    try/exceptで守り、1つが失敗しても他の値・Next Action判定には影響しない
    （失敗した項目は0件・空扱いにフォールバックする）。
    """
    try:
        active_projects_count = 0
        try:
            from services.project_service import list_projects
            projects = list_projects(projects_dir=PROJECTS_DIR)
            active_projects_count = len([p for p in projects if p.get("status") == "active"])
        except Exception:
            pass

        pending_review_assets = []
        try:
            from services.asset_generator_service import list_generated_assets
            assets = list_generated_assets(outputs_dir=OUTPUTS_DIR)
            pending_review_assets = [a for a in assets if a.get("status") == "pending_review"]
        except Exception:
            pass

        notifications_count = 0
        try:
            from services.notification_service import get_notifications
            notifications_count = len(get_notifications(outputs_dir=OUTPUTS_DIR))
        except Exception:
            pass

        pending_implementation_count = 0
        try:
            from services.issue_pipeline_service import load_generated_issues
            issues = load_generated_issues(outputs_dir=OUTPUTS_DIR)
            pending_implementation_count = len([i for i in issues if i.get("status") == "pending_implementation"])
        except Exception:
            pass

        next_action = _compute_next_action(pending_review_assets, pending_implementation_count, active_projects_count)

        return jsonify({
            "active_projects": active_projects_count,
            "pending_reviews": len(pending_review_assets),
            "notifications": notifications_count,
            "pending_implementation": pending_implementation_count,
            "next_action": next_action,
        })
    except Exception as e:
        return jsonify({
            "active_projects": 0,
            "pending_reviews": 0,
            "notifications": 0,
            "pending_implementation": 0,
            "next_action": "新しいProjectを作成してください。",
            "error": str(e),
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"DAF OS Dashboard → http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
