"""
DAF OS Quest74 — Decision Confidence History サービス

過去のDecision Confidence Score（Quest66/70で承認待ちファイルのfrontmatterに
記録されたconfidence/confidence_reason）と、実際のOutcome（Quest72で
decision_outcomes.mdに記録されるSUCCESS/FAILED）を突き合わせ、
DAF OS自身の「予測精度」を学習できるようにするMVP実装。LLMは使わない決定的な処理。

データソース：
- memory/kpi/decision_outcomes.md（見出し形式、Status: SUCCESS/FAILEDのみ対象）
- outputs/approvals/completed/ 、outputs/approvals/approved/
  （Quest70でファイル生成時に埋め込まれたconfidence/confidence_reasonを参照する。
  completed/ を優先し、無ければapproved/ を見る）

必要な関数：
- extract_confidence_history():          上記2つを突き合わせて履歴候補を抽出する
- update_confidence_history():           未登録のものだけをconfidence_history.mdに追記する
- generate_confidence_history_summary(): AI会議へ注入する短いMarkdown要約を返す
- calculate_prediction_accuracy():       Correct/Incorrect/Neutralの集計と精度を返す

判定ルール：
- Confidence >= 70 → SUCCESS予測
- Confidence <= 40 → FAILED予測
- 41〜69          → Neutral（中立、予測なしとして扱う）

評価：
- 高Confidence予測 かつ 実際SUCCESS → Correct
- 低Confidence予測 かつ 実際FAILED → Correct
- 高Confidence予測 かつ 実際FAILED → Incorrect
- 低Confidence予測 かつ 実際SUCCESS → Incorrect
- 中立（41〜69） → Neutral

CLI:
  python services/confidence_history_service.py

すべての関数は例外を投げず、ファイル未存在・confidence未設定・
SUCCESS/FAILED未確定（PENDING）・テーブル形式のみ・空ファイルのいずれでも
安全に動作する（対象なしとして扱う）。
"""

import re
import sys
from datetime import datetime
from pathlib import Path

# `python services/confidence_history_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/approval_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_MEMORY_DIR = _BASE_DIR / "memory"
_OUTPUTS_DIR = _BASE_DIR / "outputs"

_NO_DATA_SUMMARY = "## Confidence History Summary\n\n現時点では十分な履歴がありません。"

_ENTRY_RE = re.compile(
    r"^##\s*#(?P<issue>\d+)\s+(?P<decision>.+?)\s*\n\n"
    r"Date:\s*\n.*?\n\n"
    r"Predicted Confidence:\s*\n(?P<confidence>.*?)\n\n"
    r"(?:Predicted Reason:\s*\n(?P<reason>.*?)\n\n)?"
    r"Actual Outcome:\s*\n(?P<outcome>.*?)\n\n"
    r"Prediction:\s*\n(?P<prediction>.*?)"
    r"\s*(?=\n---|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _classify_prediction(confidence: int, status: str) -> str:
    """Confidenceの値から予測（SUCCESS/FAILED/中立）を判定し、実際の結果と照らす。"""
    if confidence >= 70:
        predicted = "SUCCESS"
    elif confidence <= 40:
        predicted = "FAILED"
    else:
        return "Neutral"
    return "Correct" if predicted == status else "Incorrect"


def _find_approval_confidence(issue_number: str, outputs_dir: Path) -> dict | None:
    """
    outputs/approvals/completed/ → approved/ の順にIssue番号のファイルを探し、
    Quest70で埋め込まれたconfidence/confidence_reasonを取り出す。
    見つからない・confidence未設定の場合は None を返す。
    """
    for subdir in ("completed", "approved"):
        d = outputs_dir / "approvals" / subdir
        if not d.exists():
            continue
        for f in d.glob(f"*impl_issue_{issue_number}.md"):
            text = f.read_text(encoding="utf-8")
            conf_m = re.search(r"^confidence: (.+)$", text, re.MULTILINE)
            reason_m = re.search(r"^confidence_reason: (.+)$", text, re.MULTILINE)
            if not conf_m:
                continue
            try:
                confidence = int(conf_m.group(1).strip())
            except ValueError:
                continue
            return {
                "confidence": confidence,
                "confidence_reason": reason_m.group(1).strip() if reason_m else "",
            }
    return None


def extract_confidence_history(memory_dir: Path | None = None, outputs_dir: Path | None = None) -> list[dict]:
    """
    memory/kpi/decision_outcomes.md（Status: SUCCESS/FAILEDのみ）と、
    outputs/approvals/{completed,approved}/ のconfidence情報を突き合わせ、
    履歴候補のリストを返す。

    - Statusが SUCCESS/FAILED 以外（PENDING等）のエントリは未確定として対象外
    - 対応する承認ファイルが見つからない・confidenceが埋め込まれていない場合も対象外
    - 見出し形式（Quest62以降）のみ対象。テーブル形式（Quest58）はStatusを
      持たないため対象外

    例外を投げない。データが無ければ空リストを返す。
    """
    try:
        base_memory = memory_dir or _MEMORY_DIR
        base_outputs = outputs_dir or _OUTPUTS_DIR

        path = base_memory / "kpi" / "decision_outcomes.md"
        if not path.exists():
            return []

        text = path.read_text(encoding="utf-8")

        from services.outcome_update_service import parse_decision_blocks
        blocks = parse_decision_blocks(text)

        history: list[dict] = []
        for b in blocks:
            status = b["status"].strip().upper()
            if status not in ("SUCCESS", "FAILED"):
                continue

            approval_info = _find_approval_confidence(b["issue"], base_outputs)
            if not approval_info:
                continue

            prediction = _classify_prediction(approval_info["confidence"], status)
            history.append({
                "issue": b["issue"],
                "decision": b["decision"],
                "status": status,
                "confidence": approval_info["confidence"],
                "confidence_reason": approval_info["confidence_reason"],
                "prediction": prediction,
            })

        return history
    except Exception as e:
        print(f"[警告] Confidence Historyの抽出に失敗しました：{e}")
        return []


def update_confidence_history(memory_dir: Path | None = None, outputs_dir: Path | None = None) -> dict:
    """
    extract_confidence_history() の結果のうち、まだ memory/confidence_history.md に
    登録されていないもの（同じIssue番号が無いもの）だけを追記する。

    戻り値: {"added": [...issue番号...], "skipped_existing": [...issue番号...], "total": N}

    ファイルが無ければ初期内容で新規作成する。例外を投げない。
    """
    try:
        base_memory = memory_dir or _MEMORY_DIR
        base_outputs = outputs_dir or _OUTPUTS_DIR
        path = base_memory / "confidence_history.md"

        history = extract_confidence_history(memory_dir=base_memory, outputs_dir=base_outputs)

        initial_content = (
            "# Decision Confidence History\n\n"
            "このファイルは、\n"
            "DAF OSが過去のConfidence予測と\n"
            "実際の結果を比較し、\n"
            "予測精度を学習するための履歴です。\n\n"
            "現時点では十分な履歴がありません。\n"
        )

        text = path.read_text(encoding="utf-8") if path.exists() else initial_content
        existing_issues = set(re.findall(r"^##\s*#(\d+)\b", text, re.MULTILINE))

        new_entries = [h for h in history if h["issue"] not in existing_issues]
        skipped_existing = [h["issue"] for h in history if h["issue"] in existing_issues]

        if not new_entries:
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(initial_content, encoding="utf-8")
            return {"added": [], "skipped_existing": skipped_existing, "total": len(history)}

        placeholder = "現時点では十分な履歴がありません。"
        if not existing_issues and placeholder in text:
            text = text.replace(placeholder, "").rstrip() + "\n"

        today = datetime.now().strftime("%Y-%m-%d")
        blocks_text = []
        for h in new_entries:
            blocks_text.append(
                f"\n---\n\n"
                f"## #{h['issue']} {h['decision']}\n\n"
                f"Date:\n{today}\n\n"
                f"Predicted Confidence:\n{h['confidence']}\n\n"
                f"Predicted Reason:\n{h['confidence_reason']}\n\n"
                f"Actual Outcome:\n{h['status']}\n\n"
                f"Prediction:\n{h['prediction']}\n"
            )

        text = text.rstrip() + "\n" + "".join(blocks_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

        return {
            "added": [h["issue"] for h in new_entries],
            "skipped_existing": skipped_existing,
            "total": len(history),
        }
    except Exception as e:
        print(f"[警告] Confidence Historyの更新に失敗しました：{e}")
        return {"added": [], "skipped_existing": [], "total": 0, "error": str(e)}


def calculate_prediction_accuracy(memory_dir: Path | None = None) -> dict:
    """
    memory/confidence_history.md に登録済みのPredictionを集計し、
    Correct / Incorrect / Neutral の件数と予測精度（%）を返す。

    accuracy = correct / (correct + incorrect) * 100（Neutralは分母に含めない）。
    Correct・Incorrectがともに0件の場合は accuracy を 0.0 とする。
    ファイルが無い・エントリが無い場合も例外を投げず全て0を返す。
    """
    try:
        base = memory_dir or _MEMORY_DIR
        path = base / "confidence_history.md"
        if not path.exists():
            return {"correct": 0, "incorrect": 0, "neutral": 0, "accuracy": 0.0}

        text = path.read_text(encoding="utf-8")

        correct = 0
        incorrect = 0
        neutral = 0
        for m in _ENTRY_RE.finditer(text):
            prediction = m.group("prediction").strip()
            if prediction == "Correct":
                correct += 1
            elif prediction == "Incorrect":
                incorrect += 1
            elif prediction == "Neutral":
                neutral += 1

        denominator = correct + incorrect
        accuracy = round((correct / denominator) * 100, 1) if denominator else 0.0

        return {"correct": correct, "incorrect": incorrect, "neutral": neutral, "accuracy": accuracy}
    except Exception as e:
        print(f"[警告] 予測精度の計算に失敗しました：{e}")
        return {"correct": 0, "incorrect": 0, "neutral": 0, "accuracy": 0.0}


def generate_confidence_history_summary(memory_dir: Path | None = None) -> str:
    """
    memory/confidence_history.md からAI会議へ注入する短いMarkdown要約を生成する。
    履歴が1件も無い場合は「現時点では十分な履歴がありません。」を返す。
    例外を投げない。
    """
    try:
        base = memory_dir or _MEMORY_DIR
        path = base / "confidence_history.md"
        if not path.exists():
            return _NO_DATA_SUMMARY

        stats = calculate_prediction_accuracy(memory_dir=base)
        total = stats["correct"] + stats["incorrect"] + stats["neutral"]
        if total == 0:
            return _NO_DATA_SUMMARY

        return (
            "## Confidence History Summary\n\n"
            "予測精度：\n"
            f"{stats['accuracy']}%\n\n"
            "Correct:\n"
            f"{stats['correct']}件\n\n"
            "Incorrect:\n"
            f"{stats['incorrect']}件\n\n"
            "Neutral:\n"
            f"{stats['neutral']}件"
        )
    except Exception as e:
        print(f"[警告] Confidence History Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


if __name__ == "__main__":
    result = update_confidence_history()
    if "error" in result:
        print(f"[Confidence History] 失敗: {result['error']}")
    else:
        print(
            f"[Confidence History] 追加: {len(result['added'])}件 / "
            f"既存: {len(result['skipped_existing'])}件 / "
            f"総件数: {result['total']}件"
        )
        if result["added"]:
            print("新規登録:", ", ".join(f"#{i}" for i in result["added"]))
        accuracy = calculate_prediction_accuracy()
        print(
            f"[Confidence History] 予測精度: {accuracy['accuracy']}% "
            f"(Correct: {accuracy['correct']} / Incorrect: {accuracy['incorrect']} / Neutral: {accuracy['neutral']})"
        )
