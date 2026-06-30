import os
from pathlib import Path
from notion_client import Client
from notion_client.errors import APIResponseError


def _blocks_to_text(blocks: list) -> str:
    """NotionブロックリストをプレーンテキストまたはMarkdown文字列に変換する。"""
    lines = []
    for block in blocks:
        t = block.get("type")
        if t in ("paragraph", "quote"):
            texts = block[t].get("rich_text", [])
            line = "".join(r.get("plain_text", "") for r in texts)
            if t == "quote":
                line = f"> {line}"
            lines.append(line)
        elif t in ("heading_1", "heading_2", "heading_3"):
            level = int(t[-1])
            texts = block[t].get("rich_text", [])
            text = "".join(r.get("plain_text", "") for r in texts)
            lines.append(f"{'#' * level} {text}")
        elif t in ("bulleted_list_item", "numbered_list_item"):
            texts = block[t].get("rich_text", [])
            text = "".join(r.get("plain_text", "") for r in texts)
            lines.append(f"- {text}")
        elif t == "divider":
            lines.append("---")
        elif t == "code":
            texts = block[t].get("rich_text", [])
            text = "".join(r.get("plain_text", "") for r in texts)
            lang = block[t].get("language", "")
            lines.append(f"```{lang}\n{text}\n```")
    return "\n".join(lines)


def fetch_page_text(page_id: str, api_key: str) -> str:
    """NotionページIDからブロックテキストを取得して返す。"""
    client = Client(auth=api_key)
    response = client.blocks.children.list(block_id=page_id)
    blocks = response.get("results", [])
    return _blocks_to_text(blocks)


def load_handbook(
    notion_page_id: str | None,
    fallback_path: str,
    notion_api_key: str | None = None,
) -> tuple[str, str]:
    """
    Notionから社員手帳を取得する。失敗時はローカルファイルにフォールバック。
    戻り値: (handbook_text, source)  source は "notion" または "local"
    """
    if notion_page_id and notion_api_key:
        try:
            text = fetch_page_text(notion_page_id, notion_api_key)
            if text.strip():
                return text, "notion"
            print(f"[警告] Notionページが空です（{notion_page_id}）。ローカルにフォールバックします。")
        except APIResponseError as e:
            print(f"[警告] Notion API エラー: {e}。ローカルにフォールバックします。")
        except Exception as e:
            print(f"[警告] Notion 接続失敗: {e}。ローカルにフォールバックします。")

    text = Path(fallback_path).read_text(encoding="utf-8")
    return text, "local"
