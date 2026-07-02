"""
DAF OS v1.0 — Web ダッシュボード
outputs/dashboard.md を読み取り、ブラウザで表示する Flask アプリ。
"""

import re
import os
import sys
from pathlib import Path
from flask import Flask, render_template, jsonify, request

# services/ を import パスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__)

BASE_DIR = Path(__file__).parent.parent
DASHBOARD_MD = BASE_DIR / "outputs" / "dashboard.md"


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
    )
    pending_items   = get_pending_items(BASE_DIR / "outputs")
    approved_count  = get_approved_count(BASE_DIR / "outputs")
    rejected_count  = get_rejected_count(BASE_DIR / "outputs")

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
        "pr_draft": pr_draft,
        "autonomous_flow": autonomous_flow,
        "products": products,
        "product_issue_stats": product_issue_stats,
        "approved_implementation_count": approved_implementation_count,
        "ceo_brief": ceo_brief,
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
    """承認待ち一覧 + 件数を返す。"""
    try:
        from services.approval_service import (
            get_pending_items, get_approved_count,
            get_rejected_count, get_pending_detail,
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
# ワンクリック実装準備 API（v2.3 Quest42）
# ──────────────────────────────────────────

@app.route("/api/start_implementation", methods=["POST"])
def api_start_implementation():
    """
    承認済み実装アイテムから autonomous_flow.md / claude_code_prompt.md を生成する。
    git commit / push / Claude Code起動は一切行わない。
    """
    try:
        from services.implementation_launcher_service import start_implementation
        result = start_implementation(OUTPUTS_DIR)
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"DAF OS Dashboard → http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
