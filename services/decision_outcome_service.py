"""
DAF OS Quest62 — Decision Outcome Auto Link サービス

CEOがIssueを承認した際に、memory/kpi/decision_outcomes.md へ自動で雛形を追加し、
KPI Memory（Quest58）・Reflection Loop（Quest59）へ自然に接続できるようにする。

必要な関数：
- register_decision_outcome(): 雛形を追記する（重複があれば何もしない）
- find_existing_outcome():     指定Issue番号が既に登録済みかを判定する
- generate_outcome_template():  Issue番号・タイトル・承認日から雛形テキストを生成する

追記される雛形（見出し形式）：

## #124
Decision:
オンボーディング改善

Expected KPI:
未設定

Result:
未計測

Status:
PENDING

Lesson:
-
（承認日: 2026-07-05 12:00）

この形式は services/reflection_service.py 側で読み込めるよう、
テーブル形式（Quest58）と並行して解析できるようにパーサーを拡張済み。

失敗時（ファイルI/Oエラー等）は例外を外に投げず、警告ログのみ出してFalseを返す。
呼び出し元（services/approval_service.py の approve()）の処理は止めない。

Quest63（Expected KPI Auto Suggest）：expected_kpi を明示的に渡さない場合、
services/kpi_suggestion_service.suggest_expected_kpis() でタイトル（＋任意で本文）から
自動推定する。推定に失敗しても「未設定」にフォールバックし、雛形生成自体は止めない。
"""

import re
from pathlib import Path

_BASE_DIR = Path(__file__).parent.parent
_DEFAULT_PATH = _BASE_DIR / "memory" / "kpi" / "decision_outcomes.md"

_DEFAULT_EXPECTED_KPI = "未設定"
_DEFAULT_RESULT = "未計測"
_DEFAULT_STATUS = "PENDING"
_DEFAULT_LESSON = "-"


def _safe_suggest_expected_kpi(title: str, body: str = "") -> str:
    """
    Quest63: kpi_suggestion_serviceが無い・エラーになる場合でも
    雛形生成全体を壊さないよう、失敗時は「未設定」にフォールバックする。
    """
    try:
        from services.kpi_suggestion_service import suggest_expected_kpis
        return suggest_expected_kpis(title, body)
    except Exception as e:
        print(f"[警告] Expected KPIの自動推定に失敗しました：{e}")
        return f"- {_DEFAULT_EXPECTED_KPI}"


def generate_outcome_template(
    issue_number: str,
    title: str,
    approved_date: str,
    expected_kpi: str | None = None,
    body: str = "",
) -> str:
    """
    Issue番号・タイトル・承認日から decision_outcomes.md 用の雛形テキストを生成する。
    Result・Status・Lessonは承認直後のためすべて未評価（PENDING）で生成し、
    KPIが計測できるようになった時点でCEO/AI社員が手動で更新する想定。

    expected_kpi を明示的に渡さない（None のままの）場合、Quest63の
    kpi_suggestion_service.suggest_expected_kpis() でタイトル・本文から自動推定する。
    """
    if expected_kpi is None:
        expected_kpi = _safe_suggest_expected_kpi(title, body)

    return (
        f"## #{issue_number}\n"
        f"Decision:\n{title}\n\n"
        f"Expected KPI:\n{expected_kpi}\n\n"
        f"Result:\n{_DEFAULT_RESULT}\n\n"
        f"Status:\n{_DEFAULT_STATUS}\n\n"
        f"Lesson:\n{_DEFAULT_LESSON}\n"
        f"（承認日: {approved_date}）\n"
    )


def find_existing_outcome(issue_number: str, path: Path | None = None) -> bool:
    """
    decision_outcomes.md に指定Issue番号が既に登録済みかを判定する。
    テーブル形式（Quest58: "| #90 ..."）・見出し形式（Quest62: "## #124"）の
    両方をチェックする。ファイルが無ければ False を返す。
    """
    if not issue_number:
        return False

    target = path or _DEFAULT_PATH
    if not target.exists():
        return False

    text = target.read_text(encoding="utf-8")
    patterns = [
        rf"^##\s*#{re.escape(issue_number)}\b",
        rf"\|\s*#{re.escape(issue_number)}\b",
    ]
    return any(re.search(p, text, re.MULTILINE) for p in patterns)


def register_decision_outcome(
    issue_number: str,
    title: str,
    approved_date: str,
    path: Path | None = None,
    expected_kpi: str | None = None,
    body: str = "",
) -> bool:
    """
    decision_outcomes.md へ雛形を追記する。承認フロー（services/approval_service.py の
    approve()）から呼ばれることを想定している。

    - issue_number が空文字の場合は何もせず False を返す
      （Issue番号を持たない承認アイテム＝memory_review等は対象外）
    - 既に同じIssue番号が登録済みの場合は重複登録せず False を返す
    - ファイルが存在しない場合は見出し付きで新規作成する
    - expected_kpi を明示的に渡さない場合、Quest63のキーワード推定
      （タイトル＋body）で自動設定する
    - 想定外の例外はここで捕捉し、警告ログのみ出してFalseを返す
      （承認フロー全体を止めないため）
    """
    try:
        if not issue_number:
            return False

        target = path or _DEFAULT_PATH
        target.parent.mkdir(parents=True, exist_ok=True)

        if find_existing_outcome(issue_number, target):
            print(f"[Decision Outcome] #{issue_number} は既に登録済み → スキップ")
            return False

        template = generate_outcome_template(issue_number, title, approved_date, expected_kpi, body)

        if not target.exists():
            header = (
                "# 意思決定とKPIの紐付け（Decision Outcomes）\n\n"
                "CEOの承認時に自動登録された項目です。KPIが計測可能になったら、"
                "Result・Status・Lessonを手動で更新してください\n"
                "（Status: PENDING → SUCCESS / FAILED）。\n\n"
                "---\n\n"
            )
            target.write_text(header + template, encoding="utf-8")
        else:
            with target.open("a", encoding="utf-8") as f:
                f.write("\n---\n\n" + template)

        print(f"[Decision Outcome] #{issue_number} を登録しました → {target}")
        return True
    except Exception as e:
        print(f"[警告] Decision Outcomeの自動登録に失敗しました：{e}")
        return False
