"""
DAF OS Quest77 — Initiative Tracking サービス

Strategic Goals（Quest76）だけでは「目標」止まりで、実際にどの施策が
どのIssueに紐づいて進んでいるかをAI経営会議が追跡できなかった。
このサービスは memory/initiatives.md から施策一覧を読み込み、
Goal → Initiative → Issue → KPI の繋がりをAI社員が参照できるようにする。

必要な関数：
- load_initiatives():                    initiatives.md をパースして構造化データ（リスト）を返す
- generate_initiative_summary():         AI会議へ注入する短いMarkdown要約を返す
- find_related_initiatives(issue_title): Issueタイトルから関連するInitiative名を探す

CLI:
  python services/initiative_service.py

strategic_goal_service.py と同じ方針で、LLMは使わない読み込み専用の処理
（CEOがファイルを直接編集して更新する）。ファイル未存在・空・パース失敗・
Initiative未設定のいずれでも例外を投げず、安全に動作する。
"""

import re
import sys
from pathlib import Path

# `python services/initiative_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/strategic_goal_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_MEMORY_DIR = _BASE_DIR / "memory"

_UNSET = "未設定"
_TEMPLATE_NAME = "Initiative Template"
_NO_DATA_SUMMARY = "## Initiative Summary\n\n現在、登録されている施策はありません。"


def _parse_block(name: str, block_text: str) -> dict:
    """
    1つのInitiativeブロック（見出し行を除いた本文）をパースする。
    Goal: / Description: は次の非空行を値として扱い、
    Related Issues: / Success KPI: は続く "- " 箇条書きをリストとして扱う。
    """
    goal_lines: list[str] = []
    description_lines: list[str] = []
    related_issues: list[str] = []
    success_kpi: list[str] = []
    current = None

    for raw_line in block_text.splitlines():
        line = raw_line.strip()
        if line == "":
            continue
        if line in ("Goal:", "### Goal"):
            current = "goal"
            continue
        if line in ("Description:", "### Description"):
            current = "description"
            continue
        if line in ("Related Issues:", "### Related Issues"):
            current = "related"
            continue
        if line in ("Success KPI:", "### Success KPI"):
            current = "kpi"
            continue
        if line == "---":
            continue
        if line.startswith("- "):
            value = line[2:].strip()
            if value and value != _UNSET:
                if current == "related":
                    related_issues.append(value)
                elif current == "kpi":
                    success_kpi.append(value)
            continue
        if current == "goal" and line != _UNSET:
            goal_lines.append(line)
        elif current == "description" and line != _UNSET:
            description_lines.append(line)

    goal = " ".join(goal_lines).strip() or None
    description = " ".join(description_lines).strip() or None

    return {
        "name": name,
        "goal": goal,
        "description": description,
        "related_issues": related_issues,
        "success_kpi": success_kpi,
    }


def load_initiatives(memory_dir: Path | None = None) -> list[dict]:
    """
    memory/initiatives.md を読み込み、施策の一覧を構造化データとして返す。

    戻り値: [{
        "name": str,
        "goal": str | None,
        "description": str | None,
        "related_issues": list[str],
        "success_kpi": list[str],
    }, ...]

    「## Initiative Template」のテンプレート見出しは実際の施策として扱わず除外する。
    ファイルが無い・パース失敗の場合も例外を投げず、空リストを返す。
    """
    try:
        base = memory_dir or _MEMORY_DIR
        path = base / "initiatives.md"
        if not path.exists():
            return []

        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return []

        blocks = re.split(r"^## ", text, flags=re.MULTILINE)[1:]

        initiatives = []
        for block in blocks:
            lines = block.splitlines()
            if not lines:
                continue
            name = lines[0].strip()
            if not name or name == _TEMPLATE_NAME:
                continue
            body = "\n".join(lines[1:])
            parsed = _parse_block(name, body)
            if not (parsed["goal"] or parsed["description"] or parsed["related_issues"] or parsed["success_kpi"]):
                continue
            initiatives.append(parsed)

        return initiatives
    except Exception as e:
        print(f"[警告] Initiativesの読み込みに失敗しました：{e}")
        return []


def generate_initiative_summary(memory_dir: Path | None = None) -> str:
    """
    load_initiatives() の結果をAI会議へ注入する短いMarkdown要約に整形する。
    施策が1件も無い場合は「現在、登録されている施策はありません。」を返す。例外を投げない。
    """
    try:
        initiatives = load_initiatives(memory_dir=memory_dir)
        if not initiatives:
            return _NO_DATA_SUMMARY

        lines = ["## Initiative Summary", ""]
        for item in initiatives:
            lines.append(item["name"])
            if item["goal"]:
                lines.append("Goal:")
                lines.append(item["goal"])
                lines.append("")
            if item["success_kpi"]:
                lines.append("Success KPI:")
                lines.extend(f"- {kpi}" for kpi in item["success_kpi"])
                lines.append("")

        return "\n".join(lines).rstrip()
    except Exception as e:
        print(f"[警告] Initiative Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


def find_related_initiatives(issue_title: str, memory_dir: Path | None = None) -> list[str]:
    """
    Issueタイトルを受け取り、Related Issuesに一致・部分一致する施策名の一覧を返す。
    大文字小文字を無視し、どちらかがどちらかを含む場合も一致とみなす
    （表記ゆれに対応するため）。一致が無い場合・issue_titleが空の場合は空リストを返す。
    例外を投げない。
    """
    try:
        title = (issue_title or "").strip()
        if not title:
            return []

        title_lower = title.lower()
        initiatives = load_initiatives(memory_dir=memory_dir)

        matched = []
        for item in initiatives:
            for related in item["related_issues"]:
                related_lower = related.strip().lower()
                if not related_lower:
                    continue
                if related_lower == title_lower or related_lower in title_lower or title_lower in related_lower:
                    matched.append(item["name"])
                    break

        return matched
    except Exception as e:
        print(f"[警告] find_related_initiativesの実行に失敗しました：{e}")
        return []


if __name__ == "__main__":
    initiatives = load_initiatives()
    print("[Initiatives]", initiatives)
    print()
    print(generate_initiative_summary())
    print()
    sample_title = "SNS告知投稿準備"
    print(f"[find_related_initiatives('{sample_title}')]", find_related_initiatives(sample_title))
