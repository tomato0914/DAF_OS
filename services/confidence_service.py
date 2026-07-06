"""
DAF OS Quest66 — Decision Confidence Score サービス

AIの提案（Issue）に対して、過去の類似施策（同じKPIカテゴリ）の成功実績をもとに
「どのくらい信頼できるか」を0〜100のスコアで示すMVP実装。LLMは使わない決定的な処理。

データソース：
- memory/kpi/decision_outcomes.md（services/reflection_service.evaluate_decision_outcomes()経由）
- outputs/reflection_report.md（同じ evaluate_decision_outcomes() の結果から生成されるため、
  実質的に同一のデータソースを参照する。二重にファイルを読み直すことはしない）

必要な関数：
- calculate_confidence():        タイトル・本文からConfidence Scoreと理由を算出する
- get_category_success_rate():   同じKPIカテゴリの過去実績（成功件数・総件数・成功率）を集計する
- generate_confidence_reason():  成功件数・総件数から理由文を生成する

カテゴリ判定は services/kpi_suggestion_service.get_categories_for_issue() を利用し、
キーワードルールをここで二重管理しない（Quest64/65と同じ一本化方針）。

すべての関数は例外を投げず、失敗時・データ不足時は
{"confidence": 30, "reason": "十分な過去データがありません"} 相当にフォールバックする。

Quest68（Decision Self-Count Exclusion）：issue_number を渡すことで、
評価対象のIssue自身が decision_outcomes.md に既に登録されていても、
過去実績として自己カウントしないよう除外できるようにした。
"""

from pathlib import Path

_NO_DATA_CONFIDENCE = 30
_NO_DATA_REASON = "十分な過去データがありません"

# 類似施策の件数 → 信頼度の重み（Quest66で指定された初期アルゴリズム）
_DATA_COUNT_MODIFIER = {
    1: 0.4,
    2: 0.6,
    3: 0.8,
    4: 0.9,
}
_DATA_COUNT_MODIFIER_MAX = 1.0  # 5件以上


def _data_count_modifier(count: int) -> float:
    if count >= 5:
        return _DATA_COUNT_MODIFIER_MAX
    return _DATA_COUNT_MODIFIER.get(count, 0.0)


def get_category_success_rate(
    title: str,
    body: str = "",
    memory_dir: Path | None = None,
    issue_number: str | None = None,
) -> dict:
    """
    タイトル・本文から判定したKPIカテゴリについて、過去の意思決定
    （memory/kpi/decision_outcomes.md）のうち同じカテゴリのものを集計し、
    成功件数・総件数・成功率を返す。

    「成功」は services/reflection_service.evaluate_decision_outcomes() の
    success バケットに分類された件数、「総件数」は success + needs_review
    （却下＝rejectedは対象外。実施されなかった意思決定のため成功率の計算には含めない）。

    Quest68: issue_number を渡すと、decision_outcomes.md 内の同じIssue番号の
    行・ブロックを集計対象から除外する（評価対象のIssue自身を過去実績として
    二重カウントしないため）。

    カテゴリが判定できない・過去データが無い場合は全て0を返す。例外を投げない。
    """
    try:
        from services.kpi_suggestion_service import get_categories_for_issue
        from services.reflection_service import evaluate_decision_outcomes

        categories = get_categories_for_issue(title, body)
        if not categories:
            return {"success_count": 0, "total_count": 0, "success_rate": 0.0, "categories": []}

        evaluated = evaluate_decision_outcomes(memory_dir=memory_dir)
        category_set = set(categories)
        self_issue = str(issue_number).strip() if issue_number else ""

        success_count = 0
        total_count = 0

        for entry in evaluated.get("success", []):
            if self_issue and str(entry.get("issue", "")).strip() == self_issue:
                continue
            if category_set & set(get_categories_for_issue(entry.get("title", ""))):
                total_count += 1
                success_count += 1

        for entry in evaluated.get("needs_review", []):
            if self_issue and str(entry.get("issue", "")).strip() == self_issue:
                continue
            if category_set & set(get_categories_for_issue(entry.get("title", ""))):
                total_count += 1

        success_rate = (success_count / total_count) if total_count else 0.0

        return {
            "success_count": success_count,
            "total_count": total_count,
            "success_rate": success_rate,
            "categories": categories,
        }
    except Exception as e:
        print(f"[警告] カテゴリ別成功率の計算に失敗しました：{e}")
        return {"success_count": 0, "total_count": 0, "success_rate": 0.0, "categories": []}


def generate_confidence_reason(success_count: int, total_count: int) -> str:
    """
    成功件数・総件数からConfidence Scoreの理由文を生成する。
    総件数が0（過去データなし）の場合は既定文言を返す。例外を投げない。
    """
    try:
        if total_count <= 0:
            return _NO_DATA_REASON
        return f"過去{total_count}件の類似施策のうち{success_count}件で成功"
    except Exception as e:
        print(f"[警告] Confidence理由文の生成に失敗しました：{e}")
        return _NO_DATA_REASON


def calculate_confidence(
    title: str,
    body: str = "",
    memory_dir: Path | None = None,
    issue_number: str | None = None,
) -> dict:
    """
    タイトル・本文からConfidence Score（0〜100）と理由文を算出する。

    アルゴリズム（Quest66の初期版）：
        confidence = success_rate × data_count_modifier × 100

    data_count_modifier（類似施策の件数に応じた重み）：
        1件 → 0.4 / 2件 → 0.6 / 3件 → 0.8 / 4件 → 0.9 / 5件以上 → 1.0

    Quest68: issue_number を渡すと、評価対象のIssue自身が
    decision_outcomes.md に既に登録されていても、過去実績として
    自己カウントしないよう除外する。

    KPIカテゴリが判定できない、または同カテゴリの過去データが無い場合は
    {"confidence": 30, "reason": "十分な過去データがありません"} を返す。
    例外はここで捕捉し、同じフォールバック値を返す（呼び出し元を止めない）。
    """
    try:
        stats = get_category_success_rate(title, body, memory_dir=memory_dir, issue_number=issue_number)
        total_count = stats["total_count"]

        if total_count <= 0:
            return {"confidence": _NO_DATA_CONFIDENCE, "reason": _NO_DATA_REASON}

        success_count = stats["success_count"]
        success_rate = stats["success_rate"]
        modifier = _data_count_modifier(total_count)

        confidence = round(success_rate * modifier * 100)
        reason = generate_confidence_reason(success_count, total_count)

        return {"confidence": confidence, "reason": reason}
    except Exception as e:
        print(f"[警告] Confidence Scoreの計算に失敗しました：{e}")
        return {"confidence": _NO_DATA_CONFIDENCE, "reason": _NO_DATA_REASON}
