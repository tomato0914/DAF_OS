"""
DAF OS Quest75 — Meeting Quality Score サービス

AI経営会議が「会社の記憶（KPI・Reflection・Failed Decision・Confidence History）を
どれだけ活用できているか」と「提案の質（提案数・重複の少なさ）」を100点満点で
自己評価し、継続的に記録するMVP実装。LLMは使わない決定的な処理。

評価項目（各20点）：
① KPI活用          — kpi_memory_service.generate_kpi_summary() に実データがあるか
② Reflection活用    — reflection_service.evaluate_decision_outcomes() に評価済み意思決定があるか
③ Failed Decision活用 — memory/failed_decisions.md が整備されているか
④ Confidence活用    — memory/confidence_history.md に実績があるか
⑤+⑥ 提案の質       — outputs/issues/ に提案が生成されているか（0件は減点）、
                       completed_issues.md と重複するタイトルが無いか（重複ごとに減点）

注意（設計上の制約）：
このスコアは「AIが実際にその文脈を読んで判断に活かしたか」をLLM的に検証するもの
ではなく、「その情報が会議時点で参照可能な状態だったか（＝活用できる土台が
整っていたか）」を機械的に判定する近似指標である。

必要な関数：
- evaluate_meeting_quality():         上記の評価を行いスコア・強み・改善点を返す
- generate_meeting_quality_summary(): AI会議へ注入する短いMarkdown要約を返す
- update_meeting_quality_history():   memory/meeting_quality_history.md に記録する
                                      （同じ日付は上書き更新、重複登録しない）

CLI:
  python services/meeting_quality_service.py

すべての関数は例外を投げず、ファイル未存在・データ不足でも安全に動作する。
"""

import re
import sys
from datetime import datetime
from pathlib import Path

# `python services/meeting_quality_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/approval_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_MEMORY_DIR = _BASE_DIR / "memory"
_OUTPUTS_DIR = _BASE_DIR / "outputs"

_NO_DATA_SUMMARY = "## Meeting Quality Summary\n\n現時点では十分な履歴がありません。"

_ENTRY_RE = re.compile(
    r"^##\s*(?P<date>\d{4}-\d{2}-\d{2})\s*\n"
    r"Score:\s*\n(?P<score>.*?)\n\n"
    r"Rating:\s*\n(?P<rating>.*?)\n\n"
    r"Strengths:\s*\n(?P<strengths>.*?)\n\n"
    r"Improvements:\s*\n(?P<improvements>.*?)"
    r"\s*(?=\n---|\Z)",
    re.MULTILINE | re.DOTALL,
)


def evaluate_meeting_quality(outputs_dir: Path | None = None, memory_dir: Path | None = None) -> dict:
    """
    会議品質を100点満点で評価する。5項目（各20点）の合計をscoreとして返す。

    戻り値: {
        "score": int, "rating": float,
        "breakdown": {"kpi":..,"reflection":..,"failed_decision":..,"confidence":..,"issue_quality":..},
        "strengths": [...], "improvements": [...],
    }
    例外を投げない。失敗時は全項目0点・改善点に失敗理由を含めて返す。
    """
    try:
        base_outputs = outputs_dir or _OUTPUTS_DIR
        base_memory = memory_dir or _MEMORY_DIR

        strengths: list[str] = []
        improvements: list[str] = []

        # ① KPI活用（20点）
        kpi_points = 0
        try:
            from services.kpi_memory_service import generate_kpi_summary
            kpi_summary = generate_kpi_summary(kpi_dir=base_memory / "kpi")
        except Exception:
            kpi_summary = ""
        if kpi_summary:
            kpi_points = 20
            strengths.append("KPIを考慮した提案ができている")
        else:
            improvements.append("KPIデータがまだ少なく、活用できていない")

        # ② Reflection活用（20点）
        reflection_points = 0
        try:
            from services.reflection_service import evaluate_decision_outcomes
            evaluated = evaluate_decision_outcomes(memory_dir=base_memory)
            has_reflection_data = bool(
                evaluated.get("success") or evaluated.get("needs_review") or evaluated.get("rejected")
            )
        except Exception:
            has_reflection_data = False
        if has_reflection_data:
            reflection_points = 20
            strengths.append("過去の意思決定を振り返った提案ができている")
        else:
            improvements.append("Reflectionに使える意思決定データがまだ少ない")

        # ③ Failed Decision活用（20点）
        failed_points = 0
        failed_path = base_memory / "failed_decisions.md"
        if failed_path.exists():
            failed_points = 20
            try:
                from services.failed_decision_service import extract_failed_decisions
                if extract_failed_decisions(memory_dir=base_memory):
                    strengths.append("過去の失敗を参照できている")
            except Exception:
                pass
        else:
            improvements.append("Failed Decision Memoryがまだ整備されていない")

        # ④ Confidence活用（20点）
        confidence_points = 0
        try:
            from services.confidence_history_service import calculate_prediction_accuracy
            stats = calculate_prediction_accuracy(memory_dir=base_memory)
            total_history = stats["correct"] + stats["incorrect"] + stats["neutral"]
        except Exception:
            total_history = 0
        if total_history > 0:
            confidence_points = 20
            strengths.append("Confidence履歴を蓄積し、予測精度を検証できている")
        else:
            improvements.append("Confidence履歴がまだ少ない")

        # ⑤+⑥ 提案の質（20点）：提案数（0件は0点）＋ 重複Issue率（重複1件につき-10点）
        issue_points = 0
        issues_dir = base_outputs / "issues"
        issue_files = list(issues_dir.glob("*.md")) if issues_dir.exists() else []
        issue_count = len(issue_files)

        if issue_count == 0:
            improvements.append("今回の会議でIssue提案が生成されていない")
        else:
            duplicate_count = 0
            completed_path = base_memory / "completed_issues.md"
            completed_text = completed_path.read_text(encoding="utf-8") if completed_path.exists() else ""
            for f in issue_files:
                text = f.read_text(encoding="utf-8")
                title_m = re.search(r"## タイトル\s*\n(.+)", text)
                title = title_m.group(1).strip() if title_m else ""
                if title and completed_text and title in completed_text:
                    duplicate_count += 1

            if duplicate_count == 0:
                issue_points = 20
                strengths.append("重複Issueを再提案せず、新規性のある提案ができている")
            else:
                issue_points = max(0, 20 - duplicate_count * 10)
                improvements.append("完了済みIssueの再提案がある。重複Issueをさらに減らせる")

        score = kpi_points + reflection_points + failed_points + confidence_points + issue_points
        rating = round(score / 10, 1)

        if not strengths:
            strengths.append("特筆すべき強みはまだ確認できていない")
        if not improvements:
            improvements.append("特に大きな改善点はない")

        return {
            "score": score,
            "rating": rating,
            "breakdown": {
                "kpi": kpi_points,
                "reflection": reflection_points,
                "failed_decision": failed_points,
                "confidence": confidence_points,
                "issue_quality": issue_points,
            },
            "strengths": strengths,
            "improvements": improvements,
        }
    except Exception as e:
        print(f"[警告] Meeting Qualityの評価に失敗しました：{e}")
        return {
            "score": 0,
            "rating": 0.0,
            "breakdown": {"kpi": 0, "reflection": 0, "failed_decision": 0, "confidence": 0, "issue_quality": 0},
            "strengths": [],
            "improvements": [f"評価に失敗しました：{e}"],
        }


def generate_meeting_quality_summary(outputs_dir: Path | None = None, memory_dir: Path | None = None) -> str:
    """
    evaluate_meeting_quality() の結果をAI会議へ注入する短いMarkdown要約に整形する。
    例外を投げない。
    """
    try:
        result = evaluate_meeting_quality(outputs_dir=outputs_dir, memory_dir=memory_dir)
        strengths_text = "\n".join(f"- {s}" for s in result["strengths"])
        improvements_text = "\n".join(f"- {i}" for i in result["improvements"])
        return (
            "## Meeting Quality Summary\n\n"
            "Meeting Score:\n"
            f"{result['score']} / 100\n\n"
            "Rating:\n"
            f"{result['rating']} / 10\n\n"
            "Strengths:\n"
            f"{strengths_text}\n\n"
            "Improvements:\n"
            f"{improvements_text}"
        )
    except Exception as e:
        print(f"[警告] Meeting Quality Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


def update_meeting_quality_history(outputs_dir: Path | None = None, memory_dir: Path | None = None) -> dict:
    """
    evaluate_meeting_quality() の結果を memory/meeting_quality_history.md に記録する。
    同じ日付（今日の日付）のエントリが既に存在する場合は上書き更新し、
    重複登録はしない。

    戻り値: {"date": "YYYY-MM-DD", "score": int, "rating": float, "action": "added"|"updated"}
    例外を投げない。
    """
    try:
        base_memory = memory_dir or _MEMORY_DIR
        path = base_memory / "meeting_quality_history.md"

        result = evaluate_meeting_quality(outputs_dir=outputs_dir, memory_dir=base_memory)
        today = datetime.now().strftime("%Y-%m-%d")

        initial_content = (
            "# Meeting Quality History\n\n"
            "このファイルは、\n"
            "AI経営会議の品質推移を記録するための履歴です。\n\n"
            "現時点では十分な履歴がありません。\n"
        )

        text = path.read_text(encoding="utf-8") if path.exists() else initial_content

        strengths_text = "\n".join(f"- {s}" for s in result["strengths"])
        improvements_text = "\n".join(f"- {i}" for i in result["improvements"])
        entry_body = (
            f"## {today}\n"
            f"Score:\n{result['score']}\n\n"
            f"Rating:\n{result['rating']}\n\n"
            f"Strengths:\n{strengths_text}\n\n"
            f"Improvements:\n{improvements_text}\n"
        )

        existing_match = None
        for m in _ENTRY_RE.finditer(text):
            if m.group("date") == today:
                existing_match = m
                break

        placeholder = "現時点では十分な履歴がありません。"

        if existing_match:
            text = text[:existing_match.start()] + entry_body + text[existing_match.end():]
            action = "updated"
        else:
            if placeholder in text and not list(_ENTRY_RE.finditer(text)):
                text = text.replace(placeholder, "").rstrip() + "\n"
            text = text.rstrip() + "\n\n---\n\n" + entry_body
            action = "added"

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

        return {"date": today, "score": result["score"], "rating": result["rating"], "action": action}
    except Exception as e:
        print(f"[警告] Meeting Quality Historyの更新に失敗しました：{e}")
        return {"date": "", "score": 0, "rating": 0.0, "action": "failed", "error": str(e)}


if __name__ == "__main__":
    result = update_meeting_quality_history()
    if "error" in result:
        print(f"[Meeting Quality] 失敗: {result['error']}")
    else:
        action_label = "新規登録" if result["action"] == "added" else "更新"
        print(
            f"[Meeting Quality] {action_label}（{result['date']}）: "
            f"Score {result['score']} / 100（Rating {result['rating']} / 10）"
        )
