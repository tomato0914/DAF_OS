"""
DAF OS Quest73 — Failed Decision Memory サービス

過去に失敗した意思決定（memory/kpi/decision_outcomes.md の Status: FAILED）を
memory/failed_decisions.md に記録し、AI経営会議が同じ失敗を繰り返さないように
参照できるようにするMVP実装。LLMは使わない決定的な処理。

必要な関数：
- extract_failed_decisions():      decision_outcomes.md からStatus: FAILEDを抽出する
- update_failed_decision_memory(): 未登録の失敗のみをfailed_decisions.mdに追記する
- generate_failed_decision_summary(): AI会議へ注入する短いMarkdown要約を返す

対象は見出し形式（Quest62以降）のみ。テーブル形式（Quest58）はStatusフィールドを
持たないため対象外。ブロックのパースは services/outcome_update_service.parse_decision_blocks()
を利用し、ルールを二重管理しない。

CLI:
  python services/failed_decision_service.py

すべての関数は例外を投げず、ファイル未存在・空ファイル・テーブル形式のみ・
FAILEDが1件も無い場合でも安全に動作する。
"""

import re
import sys
from datetime import datetime
from pathlib import Path

# `python services/failed_decision_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/approval_service.py と同じ対策。Quest74で発見・修正）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_MEMORY_DIR = _BASE_DIR / "memory"

_INITIAL_CONTENT = (
    "# Failed Decision Memory\n\n"
    "このファイルは、過去に失敗した意思決定を記録し、\n"
    "AI経営会議で同じ失敗を繰り返さないためのメモリです。\n\n"
    "現時点で記録された失敗判断はありません。\n"
)

_PLACEHOLDER_LINE = "現時点で記録された失敗判断はありません。"

_NO_DATA_SUMMARY = "## Failed Decision Summary\n\n現時点で記録された失敗判断はありません。"


def extract_failed_decisions(memory_dir: Path | None = None) -> list[dict]:
    """
    memory/kpi/decision_outcomes.md から Status: FAILED の意思決定を抽出する。
    見出し形式（Quest62以降）のみを対象とする。ファイルが無い・パースできる
    エントリが無い場合は空リストを返す。例外を投げない。
    """
    try:
        base = memory_dir or _MEMORY_DIR
        path = base / "kpi" / "decision_outcomes.md"
        if not path.exists():
            return []

        text = path.read_text(encoding="utf-8")

        from services.outcome_update_service import parse_decision_blocks
        blocks = parse_decision_blocks(text)

        failed = []
        for b in blocks:
            if b["status"].strip().upper() == "FAILED":
                failed.append({
                    "issue": b["issue"],
                    "decision": b["decision"],
                    "expected_kpi": b["expected_kpi"],
                    "result": b["result"],
                    "lesson": b["lesson"],
                })
        return failed
    except Exception as e:
        print(f"[警告] 失敗判断の抽出に失敗しました：{e}")
        return []


def update_failed_decision_memory(memory_dir: Path | None = None) -> dict:
    """
    extract_failed_decisions() の結果のうち、まだ memory/failed_decisions.md に
    登録されていないもの（同じIssue番号が無いもの）だけを追記する。

    戻り値: {"added": [...issue番号...], "skipped_existing": [...issue番号...], "total_failed": N}

    ファイルが無ければ初期内容で新規作成する。失敗データが無くても例外を投げず、
    ファイルが無ければ初期内容を書き込むだけで正常終了する。
    """
    try:
        base = memory_dir or _MEMORY_DIR
        path = base / "failed_decisions.md"

        failed = extract_failed_decisions(memory_dir=base)

        text = path.read_text(encoding="utf-8") if path.exists() else _INITIAL_CONTENT
        existing_issues = set(re.findall(r"^##\s*#(\d+)\b", text, re.MULTILINE))

        new_entries = [f for f in failed if f["issue"] not in existing_issues]
        skipped_existing = [f["issue"] for f in failed if f["issue"] in existing_issues]

        if not new_entries:
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(_INITIAL_CONTENT, encoding="utf-8")
            return {
                "added": [],
                "skipped_existing": skipped_existing,
                "total_failed": len(failed),
            }

        # 初回の追記時、「現時点で記録された失敗判断はありません。」のプレースホルダー文言を取り除く
        if not existing_issues and _PLACEHOLDER_LINE in text:
            text = text.replace(_PLACEHOLDER_LINE, "").rstrip() + "\n"

        today = datetime.now().strftime("%Y-%m-%d")
        blocks_text = []
        for entry in new_entries:
            blocks_text.append(
                f"\n---\n\n"
                f"## #{entry['issue']} {entry['decision']}\n"
                f"Date:\n{today}\n\n"
                f"Expected KPI:\n{entry['expected_kpi']}\n\n"
                f"Result:\n{entry['result']}\n\n"
                f"Lesson:\n{entry['lesson']}\n"
            )

        text = text.rstrip() + "\n" + "".join(blocks_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

        return {
            "added": [e["issue"] for e in new_entries],
            "skipped_existing": skipped_existing,
            "total_failed": len(failed),
        }
    except Exception as e:
        print(f"[警告] Failed Decision Memoryの更新に失敗しました：{e}")
        return {"added": [], "skipped_existing": [], "total_failed": 0, "error": str(e)}


def generate_failed_decision_summary(memory_dir: Path | None = None) -> str:
    """
    memory/failed_decisions.md からAI会議へ注入する短いMarkdown要約を生成する。
    ファイルが無い・失敗判断が1件も登録されていない場合は
    「現時点で記録された失敗判断はありません。」を返す。例外を投げない。
    """
    try:
        base = memory_dir or _MEMORY_DIR
        path = base / "failed_decisions.md"
        if not path.exists():
            return _NO_DATA_SUMMARY

        text = path.read_text(encoding="utf-8")

        entries = []
        for m in re.finditer(
            r"^##\s*#(?P<issue>\d+)\s+(?P<decision>.+?)\s*\n"
            r"Date:\s*\n.*?\n\n"
            r"Expected KPI:\s*\n.*?\n\n"
            r"Result:\s*\n.*?\n\n"
            r"Lesson:\s*\n(?P<lesson>.*?)"
            r"\s*(?=\n---|\Z)",
            text,
            re.MULTILINE | re.DOTALL,
        ):
            entries.append({
                "issue": m.group("issue"),
                "decision": m.group("decision").strip(),
                "lesson": m.group("lesson").strip(),
            })

        if not entries:
            return _NO_DATA_SUMMARY

        lines = ["## Failed Decision Summary", ""]
        for e in entries:
            lines.append(f"- #{e['issue']} {e['decision']}")
            lines.append(f"  - 学び：{e['lesson']}")
        return "\n".join(lines)
    except Exception as e:
        print(f"[警告] Failed Decision Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


if __name__ == "__main__":
    result = update_failed_decision_memory()
    if "error" in result:
        print(f"[Failed Decision Memory] 失敗: {result['error']}")
    else:
        print(
            f"[Failed Decision Memory] 追加: {len(result['added'])}件 / "
            f"既存: {len(result['skipped_existing'])}件 / "
            f"総失敗数: {result['total_failed']}件"
        )
        if result["added"]:
            print("新規登録:", ", ".join(f"#{i}" for i in result["added"]))
