"""
DAF OS Quest76 — Strategic Goal Memory サービス

会社の目標（North Star Metric・年次目標・四半期目標・今月目標・現在の優先事項）を
memory/strategic_goals.md から読み込み、AI経営会議が常に参照できるようにする
MVP実装。LLMは使わない読み込み専用の処理（CEOがファイルを直接編集して更新する）。

必要な関数：
- load_strategic_goals():            strategic_goals.md をパースして構造化データを返す
- generate_strategic_goal_summary(): AI会議へ注入する短いMarkdown要約を返す

CLI:
  python services/strategic_goal_service.py

すべての関数は例外を投げず、ファイル未存在・全項目「未設定」・空ファイルの
いずれでも安全に動作する（未設定として扱う）。
"""

import re
import sys
from pathlib import Path

# `python services/strategic_goal_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/approval_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_MEMORY_DIR = _BASE_DIR / "memory"

_UNSET = "未設定"
_NO_DATA_SUMMARY = "## Strategic Goal Summary\n\n現在、明確な経営目標は登録されていません。"

_EMPTY_GOALS = {
    "north_star_metric": None,
    "annual_goals": [],
    "quarterly_goals": [],
    "monthly_goals": [],
    "current_priorities": [],
}


def _section(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\s*\n([\s\S]*?)(?=\n## |\Z)", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _parse_list(section_text: str) -> list[str]:
    items = []
    for line in section_text.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        value = line[2:].strip()
        if value and value != _UNSET:
            items.append(value)
    return items


def _parse_single(section_text: str) -> str | None:
    value = section_text.strip()
    if not value or value == _UNSET:
        return None
    return value


def load_strategic_goals(memory_dir: Path | None = None) -> dict:
    """
    memory/strategic_goals.md を読み込み、構造化データとして返す。

    戻り値: {
        "north_star_metric": str | None,
        "annual_goals": list[str],
        "quarterly_goals": list[str],
        "monthly_goals": list[str],
        "current_priorities": list[str],
    }
    「未設定」（単独行または箇条書き1件のみの場合）は未設定として扱う
    （north_star_metricはNone、リスト系は空リストになる）。
    ファイルが無い・パース失敗の場合も例外を投げず、全て未設定の辞書を返す。
    """
    try:
        base = memory_dir or _MEMORY_DIR
        path = base / "strategic_goals.md"
        if not path.exists():
            return dict(_EMPTY_GOALS)

        text = path.read_text(encoding="utf-8")

        return {
            "north_star_metric": _parse_single(_section(text, "North Star Metric")),
            "annual_goals": _parse_list(_section(text, "Annual Goals")),
            "quarterly_goals": _parse_list(_section(text, "Quarterly Goals")),
            "monthly_goals": _parse_list(_section(text, "Monthly Goals")),
            "current_priorities": _parse_list(_section(text, "Current Priorities")),
        }
    except Exception as e:
        print(f"[警告] Strategic Goalsの読み込みに失敗しました：{e}")
        return dict(_EMPTY_GOALS)


def generate_strategic_goal_summary(memory_dir: Path | None = None) -> str:
    """
    load_strategic_goals() の結果をAI会議へ注入する短いMarkdown要約に整形する。
    未設定の項目は出力に含めない。全項目が未設定の場合は
    「現在、明確な経営目標は登録されていません。」を返す。例外を投げない。
    """
    try:
        goals = load_strategic_goals(memory_dir=memory_dir)

        has_any = (
            goals["north_star_metric"]
            or goals["annual_goals"]
            or goals["quarterly_goals"]
            or goals["monthly_goals"]
            or goals["current_priorities"]
        )
        if not has_any:
            return _NO_DATA_SUMMARY

        lines = ["## Strategic Goal Summary", ""]

        if goals["north_star_metric"]:
            lines.append("North Star Metric:")
            lines.append(goals["north_star_metric"])
            lines.append("")

        if goals["annual_goals"]:
            lines.append("Annual Goals:")
            lines.extend(f"- {g}" for g in goals["annual_goals"])
            lines.append("")

        if goals["quarterly_goals"]:
            lines.append("Quarterly Goals:")
            lines.extend(f"- {g}" for g in goals["quarterly_goals"])
            lines.append("")

        if goals["monthly_goals"]:
            lines.append("Monthly Goals:")
            lines.extend(f"- {g}" for g in goals["monthly_goals"])
            lines.append("")

        if goals["current_priorities"]:
            lines.append("Current Priorities:")
            lines.extend(f"- {g}" for g in goals["current_priorities"])
            lines.append("")

        return "\n".join(lines).rstrip()
    except Exception as e:
        print(f"[警告] Strategic Goal Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


if __name__ == "__main__":
    goals = load_strategic_goals()
    print("[Strategic Goals]", goals)
    print()
    print(generate_strategic_goal_summary())
