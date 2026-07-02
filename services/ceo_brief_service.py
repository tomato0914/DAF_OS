"""
DAF OS v2.4 Quest43 — CEOデイリーブリーフサービス

CEOが毎朝5分で状況を把握し、今日やることを迷わないようにするための
outputs/ceo_brief.md を生成する。

情報源：
- outputs/dashboard.md
- outputs/implementation_queue.md
- outputs/approvals/（pending / approved / rejected）
- products/*.md

LLM不使用・外部API不使用。すべてローカルファイルの読み取りのみで完結する。

安全設計：
- 外部APIを呼ばない
- 既存ファイルを削除しない（このサービスは ceo_brief.md への書き込みのみ行う）
- 各情報源が存在しない／壊れていても例外を出さず、空欄・デフォルト値で継続する
"""

import re
from datetime import datetime
from pathlib import Path


# ──────────────────────────────────────────
# 安全な読み取りヘルパー
# ──────────────────────────────────────────

def _read(path: Path) -> str:
    try:
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        pass
    return ""


def _safe(fn, default):
    """情報源の欠落・破損時に安全側へフォールバックする。"""
    try:
        return fn()
    except Exception:
        return default


# ──────────────────────────────────────────
# 📦 プロダクト状況
# ──────────────────────────────────────────

def _get_product_status(outputs: Path) -> list[dict]:
    def _load():
        from services.product_registry_service import load_products
        return load_products()
    return _safe(_load, [])


def _render_product_section(products: list[dict]) -> str:
    if not products:
        return "登録済みプロダクトなし（`products/*.md` を作成すると表示されます）\n"
    lines = []
    for p in products:
        mark = "✅" if p.get("path_exists") else "⚠️ パスなし"
        lines.append(f"- **{p.get('name', '?')}**（{p.get('type', '未分類')} / {p.get('status', 'unknown')}） {mark}")
    return "\n".join(lines) + "\n"


# ──────────────────────────────────────────
# ⚡ 最優先事項 TOP3（implementation_queue.md ベース、なければ issues/ にフォールバック）
# ──────────────────────────────────────────

def _parse_queue_issues(outputs: Path) -> list[dict]:
    text = _read(outputs / "implementation_queue.md")
    if not text:
        return []
    items = []
    for m in re.finditer(
        r"## Issue #(\d+)\s*\n\n"
        r"\*\*タイトル：\*\*\s*(.+?)\n"
        r"\*\*URL：\*\*\s*(\S+)\n"
        r"\*\*優先度：\*\*\s*(.+?)　",
        text,
    ):
        product_m = re.search(
            rf"## Issue #{m.group(1)}[\s\S]*?\*\*product：\*\*\s*(\S+)", text
        )
        items.append({
            "number": m.group(1),
            "title": m.group(2).strip(),
            "url": m.group(3).strip(),
            "priority": m.group(4).strip(),
            "product": product_m.group(1).strip() if product_m else "",
        })
    return items


def _parse_local_issues(outputs: Path) -> list[dict]:
    issues_dir = outputs / "issues"
    if not issues_dir.exists():
        return []
    items = []
    for f in sorted(issues_dir.glob("*.md")):
        text = _read(f)
        num_m = re.search(r"# Issue #(\d+)", text)
        title_m = re.search(r"## タイトル\s*\n(.+)", text)
        priority_m = re.search(r"## 優先度\s*\n(.+)", text)
        if not (num_m and title_m):
            continue
        items.append({
            "number": num_m.group(1),
            "title": title_m.group(1).strip(),
            "url": "",
            "priority": priority_m.group(1).strip() if priority_m else "—",
            "product": "",
        })
    return items


def _parse_dashboard_actions(outputs: Path) -> list[dict]:
    """dashboard.md の「3. 次にCEOがやること」を最終フォールバックとして使う。"""
    text = _read(outputs / "dashboard.md")
    if not text:
        return []
    m = re.search(r"## 3\. 次にCEOがやること\s*\n([\s\S]*?)(?=\n## |\Z)", text)
    if not m:
        return []
    items = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if re.match(r"\d+\.", line):
            title = re.sub(r"^\d+\.\s*", "", line)
            items.append({"number": "", "title": title, "priority": "—", "product": ""})
    return items


def _get_top_priority_items(outputs: Path, limit: int = 3) -> list[dict]:
    def _load():
        items = _parse_queue_issues(outputs)
        if not items:
            items = _parse_local_issues(outputs)
        if not items:
            # 実装キュー・ローカルIssueが両方とも無い場合のみ dashboard.md を最終フォールバックにする
            items = _parse_dashboard_actions(outputs)
        high = [i for i in items if "high" in i["priority"].lower() or i["priority"] == "高"]
        others = [i for i in items if i not in high]
        return (high + others)[:limit]
    return _safe(_load, [])


def _render_priority_section(items: list[dict]) -> str:
    if not items:
        return "現在、優先対応が必要なIssueはありません。\n"
    lines = []
    for i, item in enumerate(items, start=1):
        if item.get("number"):
            product_tag = f"（{item['product']}）" if item.get("product") else ""
            lines.append(f"{i}. **Issue #{item['number']}** {product_tag} — {item['title']}（優先度: {item['priority']}）")
        else:
            lines.append(f"{i}. {item['title']}")
    return "\n".join(lines) + "\n"


# ──────────────────────────────────────────
# 🚀 実装準備状況
# ──────────────────────────────────────────

def _get_implementation_status(outputs: Path) -> dict:
    def _load():
        from services.autonomous_flow_service import get_approved_implementation_count
        approved_impl_count = get_approved_implementation_count(outputs)
        return {
            "approved_impl_count": approved_impl_count,
            "autonomous_flow_exists": (outputs / "autonomous_flow.md").exists(),
            "claude_code_prompt_exists": (outputs / "claude_code_prompt.md").exists(),
            "pr_draft_exists": (outputs / "pr_draft.md").exists(),
        }
    return _safe(_load, {
        "approved_impl_count": 0,
        "autonomous_flow_exists": False,
        "claude_code_prompt_exists": False,
        "pr_draft_exists": False,
    })


def _render_implementation_section(status: dict) -> str:
    lines = []
    count = status.get("approved_impl_count", 0)
    if count > 0:
        lines.append(f"✅ 承認済み実装アイテム **{count}件** — 「🚀 実装開始」でClaude Codeへの受け渡し準備ができます。")
    else:
        lines.append("承認済みの実装アイテムはまだありません。承認センターで確認してください。")

    if status.get("claude_code_prompt_exists"):
        lines.append("📄 `outputs/claude_code_prompt.md` 生成済み — Claude Codeにそのまま貼り付け可能です。")
    if status.get("pr_draft_exists"):
        lines.append("🔀 `outputs/pr_draft.md` 生成済み — commit / push 前に内容を確認してください。")

    return "\n".join(f"- {l}" for l in lines) + "\n"


# ──────────────────────────────────────────
# 承認センター状況（今日やること・一言の材料として使用）
# ──────────────────────────────────────────

def _get_approval_counts(outputs: Path) -> dict:
    def _load():
        from services.approval_service import (
            get_pending_count, get_approved_count, get_rejected_count,
        )
        return {
            "pending": get_pending_count(outputs),
            "approved": get_approved_count(outputs),
            "rejected": get_rejected_count(outputs),
        }
    return _safe(_load, {"pending": 0, "approved": 0, "rejected": 0})


# ──────────────────────────────────────────
# 🤔 迷っているIssue（AIアドバイザーが「保留」を推奨した承認待ちアイテム）
# ──────────────────────────────────────────

def _get_undecided_items(outputs: Path, limit: int = 3) -> list[dict]:
    def _load():
        from services.approval_service import get_undecided_items
        return get_undecided_items(outputs, limit=limit)
    return _safe(_load, [])


def _render_undecided_section(items: list[dict]) -> str:
    if not items:
        return "現在、判断に迷っているIssueはありません。\n"
    lines = []
    for item in items:
        advisor = item.get("advisor") or {}
        action_label = advisor.get("action_label", "保留")
        reason = (advisor.get("reason") or "").splitlines()
        reason_first = reason[0] if reason else ""
        lines.append(f"- **{item['title']}** — AI推奨: {action_label}。{reason_first}")
    return "\n".join(lines) + "\n"


# ──────────────────────────────────────────
# 📋 今日やること（最大3つ）
# ──────────────────────────────────────────

def _get_today_actions(
    approval_counts: dict,
    priority_items: list[dict],
    impl_status: dict,
) -> list[str]:
    actions: list[str] = []

    if approval_counts.get("pending", 0) > 0:
        actions.append(
            f"承認センターで承認待ち {approval_counts['pending']}件 を確認する"
        )

    if priority_items:
        top = priority_items[0]
        if top.get("number"):
            actions.append(f"最優先Issue #{top['number']}「{top['title']}」の対応を検討する")
        else:
            actions.append(f"最優先事項「{top['title']}」の対応を検討する")

    if impl_status.get("claude_code_prompt_exists"):
        actions.append("`outputs/claude_code_prompt.md` を開き、実装をClaude Codeに依頼する")
    elif impl_status.get("approved_impl_count", 0) > 0:
        actions.append("Webダッシュボードの「🚀 実装開始」で実装準備を行う")

    if impl_status.get("pr_draft_exists"):
        actions.append("`outputs/pr_draft.md` を確認し、問題なければcommit / pushする")

    if not actions:
        actions.append("現在、緊急のアクションはありません。次の会議実行（`python main.py`）を待ってください。")

    return actions[:3]


# ──────────────────────────────────────────
# 🌱 CEOへの一言
# ──────────────────────────────────────────

def _get_ceo_message(approval_counts: dict, priority_items: list[dict]) -> str:
    if approval_counts.get("pending", 0) > 0:
        return "承認待ちのアイテムがあります。判断はCEOにしかできません、確認をお願いします。"
    if priority_items:
        return "優先対応のIssueがあります。無理のない範囲で、今日1つだけでも前に進めましょう。"
    return "今のところ滞りはありません。焦らず、今日も一歩ずつ進めていきましょう。"


# ──────────────────────────────────────────
# メイン生成関数
# ──────────────────────────────────────────

def generate_ceo_brief(outputs: Path) -> Path:
    """
    outputs/ceo_brief.md を生成する。
    情報源が欠けていても例外を出さず、空欄・デフォルト値で生成を続ける。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    products = _get_product_status(outputs)
    priority_items = _get_top_priority_items(outputs)
    impl_status = _get_implementation_status(outputs)
    approval_counts = _get_approval_counts(outputs)
    undecided_items = _get_undecided_items(outputs)
    today_actions = _get_today_actions(approval_counts, priority_items, impl_status)
    ceo_message = _get_ceo_message(approval_counts, priority_items)

    content = (
        f"# ☀️ CEO Daily Brief\n\n"
        f"> 生成日時: {now}\n\n"
        f"---\n\n"
        f"## 📦 プロダクト状況\n\n"
        f"{_render_product_section(products)}\n"
        f"## ⚡ 最優先事項 TOP3\n\n"
        f"{_render_priority_section(priority_items)}\n"
        f"## 🚀 実装準備状況\n\n"
        f"{_render_implementation_section(impl_status)}\n"
        f"## 🤔 迷っているIssue\n\n"
        f"{_render_undecided_section(undecided_items)}\n"
        f"## 📋 今日やること（3つまで）\n\n"
        + "\n".join(f"{i}. {a}" for i, a in enumerate(today_actions, start=1)) + "\n\n"
        f"## 🌱 CEOへの一言\n\n"
        f"{ceo_message}\n\n"
        f"---\n\n"
        f"> 承認: {approval_counts.get('pending', 0)}件待ち / "
        f"{approval_counts.get('approved', 0)}件承認済み / "
        f"{approval_counts.get('rejected', 0)}件却下済み\n"
    )

    path = outputs / "ceo_brief.md"
    path.write_text(content, encoding="utf-8")
    print(f"[CEOブリーフ] ✓ {path}")
    return path


def get_ceo_brief_summary(outputs: Path) -> dict | None:
    """Web UI 向けの要約を返す（ceo_brief.md 未生成なら None）。"""
    path = outputs / "ceo_brief.md"
    if not path.exists():
        return None
    text = _read(path)

    def _section(heading: str) -> str:
        m = re.search(rf"## {re.escape(heading)}\s*\n([\s\S]*?)(?=\n## |\n---|\Z)", text)
        return m.group(1).strip() if m else ""

    actions = []
    for line in _section("📋 今日やること（3つまで）").splitlines():
        line = line.strip()
        if re.match(r"\d+\.", line):
            actions.append(re.sub(r"^\d+\.\s*", "", line))

    updated_m = re.search(r"> 生成日時: (.+)", text)

    return {
        "updated": updated_m.group(1).strip() if updated_m else "—",
        "products": _section("📦 プロダクト状況"),
        "priorities": _section("⚡ 最優先事項 TOP3"),
        "implementation": _section("🚀 実装準備状況"),
        "undecided": _section("🤔 迷っているIssue"),
        "actions": actions,
        "message": _section("🌱 CEOへの一言"),
    }


def try_generate_ceo_brief(outputs: Path) -> Path | None:
    """main.py のパイプラインから呼び出す。失敗しても例外を投げない。"""
    print("[CEOブリーフ] 生成中...")
    try:
        return generate_ceo_brief(outputs)
    except Exception as e:
        print(f"[CEOブリーフ] 生成に失敗しました: {e} → スキップ")
        return None


if __name__ == "__main__":
    generate_ceo_brief(Path(__file__).parent.parent / "outputs")
