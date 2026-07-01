"""
DAF OS v1.1 — Notion 議事録保存サービス
経営会議の結果を Notion データベースに1件のページとして保存する。
NOTION_API_KEY または NOTION_LOG_DATABASE_ID が未設定の場合はスキップする。
"""

import re
from datetime import date, datetime
from pathlib import Path
from notion_client import Client
from notion_client.errors import APIResponseError


# ──────────────────────────────────────────
# markdown パーサー（dashboard.md / report.md）
# ──────────────────────────────────────────

def _section(text: str, heading: str) -> str:
    m = re.search(rf"## {re.escape(heading)}\s*\n([\s\S]*?)(?=\n## |\Z)", text)
    return m.group(1).strip() if m else ""


def _extract_proposal(report_text: str) -> str:
    m = re.search(r"## CEOへの最終提言\s*\n([\s\S]*?)(?=\n## |\Z)", report_text)
    if m:
        sentences = re.split(r"(?<=。)", m.group(1).strip())
        return "".join(sentences[:3]).strip()
    return ""


def _extract_actions(dashboard_text: str) -> list[str]:
    section = _section(dashboard_text, "3. 次にCEOがやること")
    actions = []
    for line in section.splitlines():
        line = line.strip()
        if re.match(r"\d+\.", line):
            actions.append(re.sub(r"^\d+\.\s*\*?\*?", "", line).replace("**", "").strip())
    return actions[:5]


def _count_github_issues(dashboard_text: str) -> int:
    rows = re.findall(r"\|\s*\[#\d+\]", dashboard_text)
    return len(rows)


# ──────────────────────────────────────────
# Notion ブロック生成ヘルパー
# ──────────────────────────────────────────

def _heading(level: int, text: str) -> dict:
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _paragraph(text: str) -> dict:
    # Notion の rich_text は1要素あたり2000文字上限
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": c}} for c in chunks]
        },
    }


def _bullet(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
        },
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _code_block(text: str, language: str = "markdown") -> dict:
    # Notionコードブロックは2000文字上限
    return {
        "object": "block",
        "type": "code",
        "code": {
            "language": language,
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
        },
    }


# ──────────────────────────────────────────
# メイン関数
# ──────────────────────────────────────────

def save_log(
    outputs: Path,
    notion_api_key: str,
    database_id: str,
) -> str | None:
    """
    outputs/ の成果物を読み込み、Notion データベースに議事録ページを作成する。
    成功時は作成されたページの URL を返す。失敗時は None。
    """
    report_text    = (outputs / "report.md").read_text(encoding="utf-8") \
                     if (outputs / "report.md").exists() else ""
    dashboard_text = (outputs / "dashboard.md").read_text(encoding="utf-8") \
                     if (outputs / "dashboard.md").exists() else ""
    gh_results     = (outputs / "github_issue_results.md").read_text(encoding="utf-8") \
                     if (outputs / "github_issue_results.md").exists() else ""

    today      = date.today().isoformat()
    now_str    = datetime.now().strftime("%Y-%m-%d %H:%M")
    title      = f"DAF OS 経営会議 {today}"
    proposal   = _extract_proposal(report_text)
    actions    = _extract_actions(dashboard_text)
    gh_count   = _count_github_issues(dashboard_text)

    # ── Notion ページプロパティ ──
    properties: dict = {
        "タイトル": {
            "title": [{"type": "text", "text": {"content": title}}]
        },
        "日付": {
            "date": {"start": today}
        },
        "GitHub Issue数": {
            "number": gh_count
        },
    }

    # ── ページ本文ブロック ──
    blocks: list[dict] = [
        _heading(2, "📋 今日の要約"),
        _paragraph(proposal or "（report.md に最終提言セクションが見つかりませんでした）"),
        _divider(),

        _heading(2, "✅ 次にCEOがやること"),
    ]
    if actions:
        blocks += [_bullet(a) for a in actions]
    else:
        blocks.append(_paragraph("（アクションなし）"))

    blocks.append(_divider())
    blocks.append(_heading(2, "📊 GitHub Issues 登録結果"))
    if gh_results:
        # 先頭2000文字まで掲載
        blocks.append(_code_block(gh_results[:2000], language="markdown"))
    else:
        blocks.append(_paragraph("（GITHUB_TOKEN 未設定のためスキップ）"))

    blocks.append(_divider())
    blocks.append(_heading(2, "📝 report.md 全文"))
    # report は長いので2000文字ずつ paragraph に分割
    if report_text:
        for i in range(0, min(len(report_text), 10000), 2000):
            blocks.append(_paragraph(report_text[i:i+2000]))
    else:
        blocks.append(_paragraph("（report.md が見つかりませんでした）"))

    # ── Notion API 呼び出し ──
    client = Client(auth=notion_api_key)

    page = client.pages.create(
        parent={"database_id": database_id},
        properties=properties,
        children=blocks,
    )
    return page.get("url") or page.get("id")


# ──────────────────────────────────────────
# main.py から呼ぶ公開関数
# ──────────────────────────────────────────

def try_save_log(outputs: Path, notion_api_key: str | None, database_id: str | None) -> None:
    """
    設定が揃っている場合のみ Notion に保存する。
    未設定・エラー時は警告を出してスキップする（例外を外に伝播させない）。
    """
    if not notion_api_key:
        print("[Notion Log] NOTION_API_KEY 未設定 → スキップ")
        return
    if not database_id:
        print("[Notion Log] NOTION_LOG_DATABASE_ID 未設定 → スキップ")
        print("  設定するには .env に NOTION_LOG_DATABASE_ID=<データベースID> を追加してください")
        return

    print("[Notion Log] 議事録を Notion に保存中...")
    try:
        url = save_log(outputs, notion_api_key, database_id)
        if url:
            print(f"  ✓ 保存完了: {url}")
        else:
            print("  ✓ 保存完了（URL取得不可）")
    except APIResponseError as e:
        print(f"  [警告] Notion API エラー: {e}")
        print("  → NOTION_API_KEY の権限とデータベースIDを確認してください")
    except Exception as e:
        print(f"  [警告] Notion 保存に失敗しました: {e}")
