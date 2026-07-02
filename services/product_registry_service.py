"""
DAF OS v2.1 Quest40 — マルチプロダクト対応サービス

products/*.md を読み込み、DAFが管理する複数プロダクトの一覧を構築する。
LLM不使用。.env は読み取らない。GitHub Token は表示しない（repository はURL文字列のみ扱う）。

products/*.md のフォーマット：

---
name: プロダクト名
path: 相対パス（DAF_OS/ からの相対 or 絶対パス）
type: internal-tool / mobile-app / web-app など自由記述
description: 概要
repository: GitHubリポジトリURL（トークン等は含めない）
status: active / planning / paused / archived など自由記述
---
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PRODUCTS_DIR = BASE_DIR / "products"

# Issue に product 指定がない場合のデフォルト（DAF OS 自身）
DEFAULT_PRODUCT = "DAF_OS"

_FIELDS = ["name", "path", "type", "description", "repository", "status"]


def _parse_product_file(path: Path) -> dict | None:
    """1つの products/*.md ファイルをパースする。"""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n([\s\S]*?)\n---\s*", text)
    frontmatter = m.group(1) if m else text

    data: dict[str, str] = {}
    for field in _FIELDS:
        fm = re.search(rf"^{field}:\s*(.+)$", frontmatter, re.MULTILINE)
        data[field] = fm.group(1).strip() if fm else ""

    if not data["name"]:
        # name がなければ無効なファイルとして扱う
        return None

    # path 存在チェック（DAF_OS ディレクトリ基準の相対パスを解決）
    raw_path = data["path"] or "."
    resolved = (BASE_DIR / raw_path).resolve()
    path_exists = resolved.exists()

    return {
        "name": data["name"],
        "path": raw_path,
        "resolved_path": str(resolved),
        "path_exists": path_exists,
        "type": data["type"] or "未分類",
        "description": data["description"] or "（説明なし）",
        "repository": data["repository"] or "",
        "status": data["status"] or "unknown",
        "source_file": path.name,
    }


def load_products(products_dir: Path | None = None) -> list[dict]:
    """
    products/ 配下の *.md をすべて読み込み、プロダクト一覧を返す。
    products/ が存在しない・空の場合は空リストを返す（エラーにしない）。
    """
    directory = products_dir or PRODUCTS_DIR
    if not directory.exists():
        return []

    products = []
    for f in sorted(directory.glob("*.md")):
        item = _parse_product_file(f)
        if item:
            products.append(item)
    return products


def print_product_status(products: list[dict]) -> None:
    """main.py 起動時のログ出力。存在しない path は警告表示する。"""
    if not products:
        print("[Products] products/*.md が見つかりません（マルチプロダクト機能は未使用）")
        return

    print(f"[Products] {len(products)}件のプロダクトを読み込みました")
    for p in products:
        mark = "✅" if p["path_exists"] else "⚠️ "
        print(f"  {mark} {p['name']}（{p['type']} / {p['status']}）— path: {p['path']}")
        if not p["path_exists"]:
            print(f"      → 警告: パスが見つかりません（{p['resolved_path']}）")


def get_product_by_name(name: str, products_dir: Path | None = None) -> dict | None:
    """
    名前でプロダクトを検索する（大文字小文字を区別しない）。
    見つからない場合は None を返す（呼び出し側で警告表示すること）。
    """
    if not name:
        return None
    target = name.strip().lower()
    for p in load_products(products_dir):
        if p["name"].strip().lower() == target:
            return p
    return None


def get_product_summary(products_dir: Path | None = None) -> list[dict]:
    """Web UI / dashboard 向けの要約（.env・トークン情報は一切含まない）。"""
    products = load_products(products_dir)
    return [
        {
            "name": p["name"],
            "path": p["path"],
            "path_exists": p["path_exists"],
            "type": p["type"],
            "description": p["description"],
            "repository": p["repository"],
            "status": p["status"],
        }
        for p in products
    ]


if __name__ == "__main__":
    print_product_status(load_products())
