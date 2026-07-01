"""
DAF OS v1.3 — 会社メモリ読み込みサービス
memory/ フォルダの3ファイルを読み込み、
AI社員のタスク description に注入するためのテキストを返す。
"""

from pathlib import Path


_MEMORY_FILES = [
    ("company_memory.md",  "【会社の価値観】"),
    ("ceo_preferences.md", "【CEOの意思決定スタイル】"),
    ("lessons_learned.md", "【過去の学び・教訓】"),
]

_MEMORY_DIR = Path(__file__).parent.parent / "memory"


def load_company_memory(memory_dir: Path | None = None) -> str:
    """
    memory/ の3ファイルを読み込み、AI社員に渡す1つのコンテキスト文字列を返す。
    ファイルが存在しない場合はそのセクションをスキップする。
    """
    base = memory_dir or _MEMORY_DIR
    sections: list[str] = []

    for filename, label in _MEMORY_FILES:
        path = base / filename
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8").strip()
        if content:
            sections.append(f"{label}\n\n{content}")

    if not sections:
        return ""

    header = (
        "=== DAF 会社メモリ ===\n"
        "以下は会社の価値観・CEOの好み・過去の学びです。"
        "すべての提案・判断においてこれらを考慮してください。\n\n"
    )
    return header + "\n\n---\n\n".join(sections) + "\n\n=== 会社メモリ ここまで ==="


def print_memory_status(memory: str) -> None:
    """読み込み状況を標準出力に表示する。"""
    if memory:
        lines = memory.count("\n")
        print(f"[Memory] 会社メモリを読み込みました（{lines}行）")
    else:
        print("[Memory] 会社メモリなし（memory/*.md が見つかりません）")
