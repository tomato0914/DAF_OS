"""
DAF OS v1.5 — CEO 承認サービス
AIが生成した提案をCEOが承認・却下できる仕組みを提供する。

ディレクトリ構造:
  outputs/approvals/pending/    承認待ちファイル（実行ごとに再生成）
  outputs/approvals/approved/   承認済みファイル（Claude Codeでの実装待ち）
  outputs/approvals/rejected/   却下済みファイル（永続保存・履歴）
  outputs/approvals/completed/  実装完了ファイル（Quest47。autonomous_flow.mdから除外される）

CLI:
  python services/approval_service.py list
  python services/approval_service.py approve <id>
  python services/approval_service.py approve-all
  python services/approval_service.py reject <id> [理由]
  python services/approval_service.py complete <id>
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# `python services/approval_service.py ...` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from services.approval_advisor_service import (
    analyze_item,
    build_advisor_frontmatter,
    parse_advisor_frontmatter,
)

BASE_DIR      = Path(__file__).parent.parent
OUTPUTS       = BASE_DIR / "outputs"
PENDING_DIR   = OUTPUTS / "approvals" / "pending"
APPROVED_DIR  = OUTPUTS / "approvals" / "approved"
REJECTED_DIR  = OUTPUTS / "approvals" / "rejected"
COMPLETED_DIR = OUTPUTS / "approvals" / "completed"


# ──────────────────────────────────────────
# ファイル生成ヘルパー
# ──────────────────────────────────────────

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _date_prefix() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _write_pending(approval_id: str, title: str, type_: str, source: str, body: str) -> Path:
    PENDING_DIR.mkdir(parents=True, exist_ok=True)

    # AI承認アドバイザー（ルールベース・LLM不使用）。失敗しても承認生成自体は止めない。
    try:
        advice = analyze_item(title=title, body=body)
    except Exception:
        advice = analyze_item(title="", body="")
    advisor_frontmatter = build_advisor_frontmatter(advice)

    content = (
        f"---\n"
        f"id: {approval_id}\n"
        f"type: {type_}\n"
        f"title: {title}\n"
        f"created_at: {_now()}\n"
        f"source: {source}\n"
        f"status: pending\n"
        f"{advisor_frontmatter}"
        f"---\n\n"
        f"{body}\n\n"
        f"---\n\n"
        f"## ✅ 承認するには\n\n"
        f"```bash\n"
        f"python services/approval_service.py approve {approval_id}\n"
        f"```\n\n"
        f"## ❌ 却下するには\n\n"
        f"```bash\n"
        f'python services/approval_service.py reject {approval_id} "却下理由"\n'
        f"```\n"
    )
    path = PENDING_DIR / f"{approval_id}.md"
    path.write_text(content, encoding="utf-8")
    return path


# ──────────────────────────────────────────
# パーサー群
# ──────────────────────────────────────────

def _parse_memory_suggestions(outputs: Path) -> list[dict]:
    """memory_update_suggestions.md から承認アイテムを生成する。"""
    path = outputs / "memory_update_suggestions.md"
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    items = []

    # 見直し候補セクションを抽出
    m = re.search(r"## 見直し候補\s*\n([\s\S]*?)(?=\n## |\Z)", text)
    candidates_text = m.group(1).strip() if m else ""

    # 新規追加候補セクション
    m2 = re.search(r"## 新しく追加した方がよい項目\s*\n([\s\S]*?)(?=\n## |\Z)", text)
    additions_text = m2.group(1).strip() if m2 else ""

    # CEOへのメモ
    m3 = re.search(r"## CEOへのメモ\s*\n([\s\S]*?)(?=\n## |\n---|\Z)", text)
    ceo_memo = m3.group(1).strip() if m3 else ""

    # 見直し候補が1件以上あれば1つの承認アイテムにまとめる
    if candidates_text or additions_text:
        body = (
            "# 🧠 会社メモリ 見直し提案の承認\n\n"
            "> **承認すると `approved/` に記録されます。**  \n"
            "> 実際の `memory/` ファイルへの反映は手動で行ってください。\n\n"
        )
        if candidates_text:
            body += f"## 見直し候補\n\n{candidates_text}\n\n"
        if additions_text:
            body += f"## 新しく追加した方がよい項目\n\n{additions_text}\n\n"
        if ceo_memo:
            body += f"## CEOへのメモ\n\n{ceo_memo}\n\n"
        body += (
            "## 承認後の作業\n\n"
            "1. `memory/company_memory.md` などを上記提案に従い手動編集する\n"
            "2. 次回 `python main.py` 実行時に新しいメモリが反映される\n"
        )
        items.append({
            "id": f"{_date_prefix()}_memory_review",
            "title": "会社メモリ 見直し提案",
            "type": "memory_review",
            "source": "outputs/memory_update_suggestions.md",
            "body": body,
        })

    return items


def _parse_implementation_queue(outputs: Path) -> list[dict]:
    """implementation_queue.md から Issue ごとに承認アイテムを生成する。"""
    path = outputs / "implementation_queue.md"
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    items = []

    for m in re.finditer(
        r"## Issue #(\d+)\s*\n\n"
        r"\*\*タイトル：\*\* (.+?)\n"
        r"\*\*URL：\*\* (\S+)\n"
        r"([\s\S]*?)\n\n"
        r"### 実装目的\s*\n\n([\s\S]*?)"
        r"### Claude Code への推奨プロンプト\s*\n\n```\s*\n([\s\S]*?)```",
        text,
    ):
        num     = m.group(1)
        title   = m.group(2).strip()
        url     = m.group(3).strip()
        meta_block = m.group(4)
        purpose = m.group(5).strip()
        prompt  = m.group(6).strip()

        product_m = re.search(r"\*\*product：\*\*\s*(\S+)　\*\*path：\*\*\s*(\S+)", meta_block)
        product  = product_m.group(1).strip() if product_m else ""
        work_dir = product_m.group(2).strip() if product_m else ""

        product_line = (
            f"**対象プロダクト:** {product}　**作業ディレクトリ:** {work_dir}\n\n"
            if product else ""
        )
        body = (
            f"# ⚡ 実装承認: Issue #{num} — {title}\n\n"
            f"**GitHub Issue:** [{url}]({url})\n\n"
            f"{product_line}"
            f"## 実装目的\n\n{purpose}\n\n"
            f"## Claude Code への推奨プロンプト\n\n"
            f"承認後、以下のプロンプトを Claude Code に貼り付けて実装してください：\n\n"
            f"```\n{prompt}\n```\n"
        )
        items.append({
            "id": f"{_date_prefix()}_impl_issue_{num}",
            "title": f"実装: Issue #{num} — {title}",
            "type": "implementation",
            "source": "outputs/implementation_queue.md",
            "body": body,
        })

    return items


# ──────────────────────────────────────────
# 承認アイテム生成
# ──────────────────────────────────────────

def generate_pending_approvals(outputs: Path) -> list[Path]:
    """
    outputs/ を読み取り、承認待ちファイルを pending/ に生成する。
    前回の pending ファイルはクリアしてから再生成する。
    approved/ は触らない。
    """
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)
    COMPLETED_DIR.mkdir(parents=True, exist_ok=True)

    # pending をクリア（前回分）
    cleared = 0
    for f in PENDING_DIR.glob("*.md"):
        f.unlink()
        cleared += 1

    # 承認アイテムを収集
    all_items = (
        _parse_memory_suggestions(outputs)
        + _parse_implementation_queue(outputs)
    )

    if not all_items:
        print("  [承認] 承認待ちアイテムなし")
        return []

    created: list[Path] = []
    for item in all_items:
        path = _write_pending(
            approval_id=item["id"],
            title=item["title"],
            type_=item["type"],
            source=item["source"],
            body=item["body"],
        )
        created.append(path)
        print(f"  ✓ pending: {path.name}")

    return created


# ──────────────────────────────────────────
# 承認 / 却下
# ──────────────────────────────────────────

def _load_pending_file(approval_id: str) -> Path | None:
    # .md 拡張子の有無を両方許容
    for suffix in ["", ".md"]:
        p = PENDING_DIR / f"{approval_id}{suffix}"
        if p.exists():
            return p
    return None


def approve(approval_id: str) -> bool:
    """指定した承認アイテムを approved/ に移動する。"""
    src = _load_pending_file(approval_id)
    if not src:
        print(f"[承認] ❌ 見つかりません: {approval_id}")
        return False

    APPROVED_DIR.mkdir(parents=True, exist_ok=True)

    content = src.read_text(encoding="utf-8")
    content = content.replace(
        "status: pending",
        f"status: approved\napproved_at: {_now()}",
    )
    content += f"\n\n> ✅ **承認済み** — {_now()}\n"

    dst = APPROVED_DIR / src.name
    dst.write_text(content, encoding="utf-8")
    src.unlink()
    print(f"[承認] ✅ 承認しました: {src.name} → approved/")
    return True


def reject(approval_id: str, reason: str = "（理由なし）") -> bool:
    """指定した承認アイテムを rejected/ に移動する（理由付き）。"""
    src = _load_pending_file(approval_id)
    if not src:
        print(f"[承認] ❌ 見つかりません: {approval_id}")
        return False

    REJECTED_DIR.mkdir(parents=True, exist_ok=True)

    content = src.read_text(encoding="utf-8")
    content = content.replace(
        "status: pending",
        f"status: rejected\nrejected_at: {_now()}\nreason: {reason}",
    )
    content += f"\n\n> ❌ **却下** — {_now()}  \n> 理由: {reason}\n"

    dst = REJECTED_DIR / src.name
    dst.write_text(content, encoding="utf-8")
    src.unlink()
    print(f"[承認] ❌ 却下しました: {src.name}（理由: {reason}）")
    return True


def _load_approved_file(approval_id: str) -> Path | None:
    for suffix in ["", ".md"]:
        p = APPROVED_DIR / f"{approval_id}{suffix}"
        if p.exists():
            return p
    return None


def _extract_github_url(text: str) -> str:
    m = re.search(r"\*\*GitHub Issue:\*\*\s*\[([^\]]+)\]", text)
    return m.group(1).strip() if m else ""


def complete(approval_id: str) -> bool:
    """
    承認済み（approved/）の実装アイテムを completed/ に移動する。
    Claude Codeでの実装が終わったIssueをここに移すことで、
    autonomous_flow.md（実装準備完了リスト）から自動的に除外される。

    GitHub Issue に紐づくアイテムの場合、Issueをクローズするための
    コマンドを「Close候補」としてファイルに記録する（自動クローズはしない）。
    """
    src = _load_approved_file(approval_id)
    if not src:
        print(f"[実装完了] ❌ approved/ に見つかりません: {approval_id}")
        return False

    COMPLETED_DIR.mkdir(parents=True, exist_ok=True)

    content = src.read_text(encoding="utf-8")
    content = content.replace(
        "status: approved",
        f"status: completed\ncompleted_at: {_now()}",
    )

    github_url = _extract_github_url(content)
    footer = f"\n\n> ✅ **実装完了** — {_now()}\n"
    if github_url:
        footer += (
            f"\n> 🔒 **GitHub Issue Close候補：** [{github_url}]({github_url})\n"
            f"> DAF OSは自動でIssueをクローズしません。必要であれば以下のいずれかで手動クローズしてください：\n\n"
            f"```bash\n"
            f"gh issue close {github_url.rstrip('/').split('/')[-1]} "
            f"--repo {'/'.join(github_url.rstrip('/').split('/')[-4:-2])}\n"
            f"```\n\n"
            f"またはブラウザで {github_url} を開いて「Close issue」を押してください。\n"
        )
    content += footer

    dst = COMPLETED_DIR / src.name
    dst.write_text(content, encoding="utf-8")
    src.unlink()
    print(f"[実装完了] ✅ 実装完了にしました: {src.name} → completed/")
    if github_url:
        print(f"  → GitHub IssueのClose候補: {github_url}（自動クローズはしません）")
    return True


def approve_all() -> int:
    """pending のすべてのファイルを承認する。承認件数を返す。"""
    files = list(PENDING_DIR.glob("*.md"))
    if not files:
        print("[承認] 承認待ちアイテムはありません")
        return 0
    count = sum(1 for f in files if approve(f.stem))
    print(f"[承認] ✅ {count}件を承認しました")
    return count


# ──────────────────────────────────────────
# ステータス取得（dashboard / web 向け）
# ──────────────────────────────────────────

def get_pending_count(outputs: Path) -> int:
    pending = outputs / "approvals" / "pending"
    if not pending.exists():
        return 0
    return len(list(pending.glob("*.md")))


def get_pending_items(outputs: Path) -> list[dict]:
    """pending ファイル一覧をメタデータ付きで返す。"""
    pending = outputs / "approvals" / "pending"
    if not pending.exists():
        return []
    items = []
    for f in sorted(pending.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        id_m     = re.search(r"^id: (.+)$", text, re.MULTILINE)
        title_m  = re.search(r"^title: (.+)$", text, re.MULTILINE)
        type_m   = re.search(r"^type: (.+)$", text, re.MULTILINE)
        items.append({
            "id":       id_m.group(1).strip()    if id_m    else f.stem,
            "title":    title_m.group(1).strip() if title_m else f.stem,
            "type":     type_m.group(1).strip()  if type_m  else "unknown",
            "file":     f.name,
            "advisor":  parse_advisor_frontmatter(text),
        })
    return items


def get_undecided_items(outputs: Path, limit: int = 3) -> list[dict]:
    """
    AIアドバイザーが「保留」を推奨した承認待ちアイテム（＝CEOが迷いやすい項目）を返す。
    CEO Daily Brief の「迷っているIssue」向け。
    """
    try:
        items = get_pending_items(outputs)
        undecided = [
            i for i in items
            if i.get("advisor") and i["advisor"].get("action") == "hold"
        ]
        return undecided[:limit]
    except Exception:
        return []


def get_approved_count(outputs: Path) -> int:
    approved = outputs / "approvals" / "approved"
    if not approved.exists():
        return 0
    return len(list(approved.glob("*.md")))


def get_rejected_count(outputs: Path) -> int:
    rejected = outputs / "approvals" / "rejected"
    if not rejected.exists():
        return 0
    return len(list(rejected.glob("*.md")))


def get_completed_count(outputs: Path) -> int:
    completed = outputs / "approvals" / "completed"
    if not completed.exists():
        return 0
    return len(list(completed.glob("*.md")))


def get_completed_items(outputs: Path) -> list[dict]:
    """completed ファイル一覧をメタデータ付きで返す。"""
    completed = outputs / "approvals" / "completed"
    if not completed.exists():
        return []
    items = []
    for f in sorted(completed.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        id_m    = re.search(r"^id: (.+)$", text, re.MULTILINE)
        title_m = re.search(r"^title: (.+)$", text, re.MULTILINE)
        completed_at_m = re.search(r"^completed_at: (.+)$", text, re.MULTILINE)
        items.append({
            "id":           id_m.group(1).strip()    if id_m    else f.stem,
            "title":        title_m.group(1).strip() if title_m else f.stem,
            "completed_at": completed_at_m.group(1).strip() if completed_at_m else "",
            "github_url":   _extract_github_url(text),
        })
    return items


def get_pending_detail(approval_id: str, outputs: Path) -> dict | None:
    """pending ファイルの本文プレビューを含む詳細を返す（Web UI 向け）。"""
    pending = outputs / "approvals" / "pending"
    # ID の正規化（.md 有無を両方試す）
    for suffix in ["", ".md"]:
        path = pending / f"{approval_id}{suffix}"
        if path.exists():
            text = path.read_text(encoding="utf-8")
            # フロントマターを除いた本文
            body_m = re.search(r"---\n[\s\S]*?---\n([\s\S]*)", text)
            body = body_m.group(1).strip() if body_m else text
            id_m    = re.search(r"^id: (.+)$",    text, re.MULTILINE)
            title_m = re.search(r"^title: (.+)$", text, re.MULTILINE)
            type_m  = re.search(r"^type: (.+)$",  text, re.MULTILINE)
            src_m   = re.search(r"^source: (.+)$",text, re.MULTILINE)
            return {
                "id":      id_m.group(1).strip()    if id_m    else approval_id,
                "title":   title_m.group(1).strip() if title_m else approval_id,
                "type":    type_m.group(1).strip()  if type_m  else "unknown",
                "source":  src_m.group(1).strip()   if src_m   else "",
                "preview": body[:1500],   # 1500文字でプレビューを打ち切る
                "advisor": parse_advisor_frontmatter(text),
            }
    return None


# ──────────────────────────────────────────
# list コマンド
# ──────────────────────────────────────────

def list_pending() -> None:
    items = get_pending_items(OUTPUTS)
    if not items:
        print("承認待ちアイテムはありません。")
        return
    print(f"\n承認待ち ({len(items)}件)\n" + "─" * 40)
    for item in items:
        emoji = "🧠" if item["type"] == "memory_review" else "⚡"
        print(f"  {emoji} [{item['id']}]\n     {item['title']}")
    print()
    print("承認: python services/approval_service.py approve <id>")
    print("全承認: python services/approval_service.py approve-all")
    print()


# ──────────────────────────────────────────
# main.py から呼ぶ公開関数
# ──────────────────────────────────────────

def run_approval_generation(outputs: Path) -> list[Path]:
    """main.py のパイプラインから呼び出す。pending を再生成して返す。"""
    print("[承認センター] 承認待ちアイテムを生成中...")
    created = generate_pending_approvals(outputs)
    count = len(created)
    if count:
        print(f"  → {count}件の承認待ちアイテムを生成しました")
        print(f"  → 確認: python services/approval_service.py list")
    return created


# ──────────────────────────────────────────
# CLI エントリーポイント
# ──────────────────────────────────────────

def _cli():
    args = sys.argv[1:]
    if not args or args[0] == "list":
        list_pending()
    elif args[0] == "approve-all":
        approve_all()
    elif args[0] == "approve" and len(args) >= 2:
        approve(args[1])
    elif args[0] == "reject" and len(args) >= 2:
        reason = args[2] if len(args) >= 3 else "（理由なし）"
        reject(args[1], reason)
    elif args[0] == "complete" and len(args) >= 2:
        complete(args[1])
    else:
        print("使い方:")
        print("  python services/approval_service.py list")
        print("  python services/approval_service.py approve <id>")
        print("  python services/approval_service.py approve-all")
        print('  python services/approval_service.py reject <id> "理由"')
        print("  python services/approval_service.py complete <id>")


if __name__ == "__main__":
    _cli()
