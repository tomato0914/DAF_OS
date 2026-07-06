"""
DAF OS Quest59 — Reflection Loop サービス

AI経営会議の提案・CEO意思決定・KPI結果を振り返り、次回以降の提案精度を
高めるための仕組み（MVP）。LLMは使わず、既存のmemoryファイルをルールベースで
突き合わせるだけの決定的な処理にしている。

読み込む元データ：
- memory/ceo_decision_history.md（Quest57）：CEOが承認・却下した意思決定の履歴
- memory/kpi/decision_outcomes.md（Quest58）：意思決定とKPI影響の対応表
- memory/kpi/kpi_snapshots/（Quest58）：直近のKPIスナップショット

出力：
- outputs/reflection_report.md

必要な関数：
- evaluate_decision_outcomes(): 意思決定ごとにKPI状況を評価し分類する
- extract_lessons_for_next_meeting(): 次回会議への反映事項を抽出する
- generate_reflection_report(): 上記を1つのMarkdownにまとめて保存する

すべての関数は、参照元ファイル・ディレクトリが存在しなくても例外を投げず、
「データがまだない」ことが分かる出力を返す。

Quest64（KPI Rule Unification）：期待KPIの推定ロジックはここに独自定義せず、
services/kpi_suggestion_service.suggest_expected_kpis() に一本化した。
decision_outcome_service.py（雛形生成）とこのファイル（Reflection Report生成）が
同じキーワードルールを参照するようになっている。
"""

import re
from pathlib import Path

_BASE_DIR = Path(__file__).parent.parent
_MEMORY_DIR = _BASE_DIR / "memory"
_OUTPUTS_DIR = _BASE_DIR / "outputs"

# Quest64: 期待KPIが推定できなかった場合のフォールバック（分類ロジックの判定にも使う）
_DEFAULT_EXPECTED_KPI = "（未分類。個別に評価が必要）"
_DEFAULT_LESSON = "十分な評価情報がないため、次回KPI計測時に見直す"

_UNMEASURED_MARKERS = ("未計測", "—", "-", "")


def _infer_expected_kpi_and_lesson(title: str) -> tuple[str, str]:
    """
    Quest64: kpi_suggestion_service.suggest_expected_kpis() を単一の情報源として使い、
    Reflection Report向けの1行表示（カンマ区切り）に変換する。
    Quest65: 学びの文言もkpi_suggestion_service.suggest_lesson_from_kpis()
    （KPIカテゴリ別のLesson Template）に一本化し、ここでは独自の学び文を持たない。
    kpi_suggestion_service が無い・エラーになる場合でも例外を投げず、
    未分類（_DEFAULT_EXPECTED_KPI / _DEFAULT_LESSON）にフォールバックする。
    """
    try:
        from services.kpi_suggestion_service import suggest_expected_kpis
        raw = suggest_expected_kpis(title)
    except Exception:
        return _DEFAULT_EXPECTED_KPI, _DEFAULT_LESSON

    kpi_names = [line.lstrip("- ").strip() for line in raw.splitlines() if line.strip()]
    if not kpi_names or kpi_names == ["未設定"]:
        return _DEFAULT_EXPECTED_KPI, _DEFAULT_LESSON

    expected_kpi = "、".join(kpi_names)

    try:
        from services.kpi_suggestion_service import suggest_lesson_from_kpis
        lesson = suggest_lesson_from_kpis(kpi_names)
    except Exception:
        lesson = _DEFAULT_LESSON

    return expected_kpi, lesson


def _is_unmeasured(value: str) -> bool:
    value = (value or "").strip()
    return value in _UNMEASURED_MARKERS or "未計測" in value


def _parse_decision_history(memory_dir: Path) -> dict[str, dict]:
    """
    memory/ceo_decision_history.md の「承認した意思決定」「却下した意思決定」を
    Issue番号ごとにパースする。ファイルが無ければ空dictを返す。
    """
    path = memory_dir / "ceo_decision_history.md"
    if not path.exists():
        return {}

    text = path.read_text(encoding="utf-8")
    result: dict[str, dict] = {}

    for m in re.finditer(
        r"-\s+\*\*#(\d+)\s+(.+?)\*\*（(\d{4}-\d{2}-\d{2})\s*(承認|却下)",
        text,
    ):
        issue_no, title, date, action = m.groups()
        result[issue_no] = {
            "issue": issue_no,
            "title": title.strip(),
            "date": date,
            "action": "approved" if action == "承認" else "rejected",
        }

    return result


def _parse_decision_outcomes_table(text: str) -> list[dict]:
    """memory/kpi/decision_outcomes.md のテーブル行（Quest58形式）をパースする。"""
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 5:
            continue
        # ヘッダー行・区切り行（---）をスキップ
        if cells[0] in ("意思決定（Issue）",) or set(cells[0]) <= {"-"}:
            continue

        issue_m = re.search(r"#(\d+)", cells[0])
        if not issue_m:
            continue

        rows.append({
            "issue": issue_m.group(1),
            "title_cell": cells[0],
            "date": cells[1],
            "kpi_before": cells[2],
            "kpi_after": cells[3],
            "outcome_note": cells[4],
            "explicit_status": None,
        })
    return rows


def _parse_decision_outcomes_headings(text: str) -> list[dict]:
    """
    Quest62（Decision Outcome Auto Link）で承認時に自動登録される見出し形式をパースする。

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
    """
    rows: list[dict] = []
    for m in re.finditer(
        r"^##\s*#(\d+)\s*\n"
        r"Decision:\s*\n(.*?)\n\n"
        r"Expected KPI:\s*\n(.*?)\n\n"
        r"Result:\s*\n(.*?)\n\n"
        r"Status:\s*\n(.*?)\n\n"
        r"Lesson:\s*\n(.*?)"
        r"(?:\n（承認日[:：]\s*(.*?)）)?"
        r"\s*(?=\n---|\n##\s*#|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    ):
        issue, decision, expected_kpi, result, status, lesson, approved_date = m.groups()
        rows.append({
            "issue": issue,
            "title_cell": f"#{issue} {decision.strip()}",
            "date": (approved_date or "").strip(),
            "kpi_before": expected_kpi.strip(),
            "kpi_after": result.strip(),
            "outcome_note": lesson.strip(),
            "explicit_status": status.strip(),
        })
    return rows


def _parse_decision_outcomes(kpi_dir: Path) -> list[dict]:
    """
    memory/kpi/decision_outcomes.md を読み込み、テーブル形式（Quest58）と
    見出し形式（Quest62・承認時に自動登録される形式）の両方をパースして返す。
    ファイルが無ければ空リストを返す。
    """
    path = kpi_dir / "decision_outcomes.md"
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    return _parse_decision_outcomes_table(text) + _parse_decision_outcomes_headings(text)


def _list_kpi_snapshots(kpi_dir: Path) -> list[Path]:
    snapshots_dir = kpi_dir / "kpi_snapshots"
    if not snapshots_dir.exists():
        return []
    return sorted(snapshots_dir.glob("*.md"))


def evaluate_decision_outcomes(memory_dir: Path | None = None) -> dict[str, list[dict]]:
    """
    CEO Decision History と decision_outcomes.md を突き合わせ、
    意思決定を「成功した判断」「改善が必要な判断」「却下した判断」に分類する。

    分類ルール（決定的・LLM不使用）：
    - KPIが未計測でも、プライバシー・セキュリティ等の重要領域に一致する承認決定は
      CEOの過去の傾向（ceo_decision_history.mdの「見える傾向」）から見て
      「良い判断だった」とみなし、成功した判断に分類する
    - KPIが実測されている場合は、数値の増減で成功／改善が必要を判定する
    - 却下された決定は別枠で扱う（成功/改善が必要のどちらにも含めない）

    参照元ファイルが無い場合は全て空リストを返す（例外を投げない）。
    """
    base = memory_dir or _MEMORY_DIR
    kpi_dir = base / "kpi"

    history = _parse_decision_history(base)
    outcomes = _parse_decision_outcomes(kpi_dir)

    success: list[dict] = []
    needs_review: list[dict] = []
    rejected: list[dict] = []

    for row in outcomes:
        issue = row["issue"]
        hist = history.get(issue, {})
        title = hist.get("title") or re.sub(r"^#\d+\s*", "", row["title_cell"])
        action = hist.get("action")

        if action == "rejected" or "却下" in row["title_cell"]:
            rejected.append({
                "issue": issue,
                "title": title,
                "date": row["date"],
                "note": row["outcome_note"],
            })
            continue

        expected_kpi, lesson = _infer_expected_kpi_and_lesson(title)

        entry = {
            "issue": issue,
            "title": title,
            "expected_kpi": expected_kpi,
            "kpi_before": row["kpi_before"],
            "kpi_after": row["kpi_after"],
            "lesson": lesson,
            "note": row["outcome_note"],
        }

        # Quest62: 見出し形式（自動登録）の Status フィールドを優先的に見る。
        # PENDING（未評価）はテーブル形式の「未計測」相当として扱い、
        # SUCCESS/FAILED（CEOやAIが後から手動更新した場合）はそのまま分類に使う。
        explicit_status = (row.get("explicit_status") or "").strip().upper()
        if explicit_status and explicit_status != "PENDING":
            if explicit_status in ("SUCCESS", "SUCCEEDED", "OK", "GOOD"):
                entry["status"] = f"{explicit_status}（手動評価）"
                success.append(entry)
                continue
            if explicit_status in ("FAILED", "FAILURE", "NEEDS_REVIEW", "BAD"):
                entry["status"] = f"{explicit_status}（手動評価）"
                needs_review.append(entry)
                continue
            # 未知のステータス文字列は下の通常ロジックにフォールスルーする

        unmeasured = (
            explicit_status == "PENDING"
            or (_is_unmeasured(row["kpi_before"]) and _is_unmeasured(row["kpi_after"]))
        )

        if unmeasured:
            # KPI未計測でも、既知の重要領域（プライバシー/セキュリティ等）に
            # 一致する承認決定は「良い判断だった」とみなす
            if expected_kpi != _DEFAULT_EXPECTED_KPI:
                entry["status"] = "リリース前のため未計測"
                success.append(entry)
            else:
                entry["status"] = "未分類・未計測"
                needs_review.append(entry)
            continue

        try:
            before_val = float(re.sub(r"[^\d.\-]", "", row["kpi_before"]))
            after_val = float(re.sub(r"[^\d.\-]", "", row["kpi_after"]))
            entry["status"] = f"{row['kpi_before']} → {row['kpi_after']}"
            if after_val >= before_val:
                success.append(entry)
            else:
                needs_review.append(entry)
        except ValueError:
            entry["status"] = f"{row['kpi_before']} → {row['kpi_after']}（未評価）"
            needs_review.append(entry)

    return {"success": success, "needs_review": needs_review, "rejected": rejected}


def extract_lessons_for_next_meeting(
    evaluated: dict[str, list[dict]] | None = None,
    memory_dir: Path | None = None,
) -> list[str]:
    """
    evaluate_decision_outcomes() の結果から、次回会議への反映事項を抽出する。
    evaluated を渡さない場合は内部で評価し直す。
    """
    base = memory_dir or _MEMORY_DIR
    if evaluated is None:
        evaluated = evaluate_decision_outcomes(memory_dir=base)

    lessons: list[str] = []

    has_unmeasured = any(
        e["status"].startswith(("リリース前のため未計測", "未分類・未計測"))
        for e in evaluated["success"] + evaluated["needs_review"]
    )
    if has_unmeasured:
        lessons.append("KPI未計測の施策は「仮説」として扱う")
        lessons.append("実測値が出た施策を優先的に再評価する")

    if evaluated["rejected"]:
        lessons.append("提案前にcompleted_issues.mdや既存の意思決定履歴との重複がないか確認する")

    if evaluated["needs_review"]:
        lessons.append("改善が必要な判断（KPIが悪化・未分類のもの）は次回会議で優先的に再検討する")

    kpi_dir = base / "kpi"
    snapshots = _list_kpi_snapshots(kpi_dir)
    if len(snapshots) >= 2:
        lessons.append(
            f"KPIスナップショットが{len(snapshots)}件蓄積されている。"
            "直近の比較結果（KPI Summary参照）を踏まえて提案の優先順位を調整する"
        )

    if not lessons:
        lessons.append("まだ振り返りに使える意思決定・KPIデータが十分にない")

    return lessons


def _format_entry(e: dict) -> str:
    lines = [f"- #{e['issue']} {e['title']}"]
    if "expected_kpi" in e:
        lines.append(f"  - 期待KPI：{e['expected_kpi']}")
    if "status" in e:
        lines.append(f"  - 状態：{e['status']}")
    if "lesson" in e:
        lines.append(f"  - 学び：{e['lesson']}")
    return "\n".join(lines)


def generate_reflection_report(
    outputs_dir: Path | None = None,
    memory_dir: Path | None = None,
) -> Path:
    """
    evaluate_decision_outcomes() と extract_lessons_for_next_meeting() の結果を
    1つのMarkdownにまとめ、outputs/reflection_report.md に保存する。
    参照元データが何もなくても、その旨を明記したレポートを生成する（例外を投げない）。
    """
    base_outputs = outputs_dir or _OUTPUTS_DIR
    base_memory = memory_dir or _MEMORY_DIR
    base_outputs.mkdir(parents=True, exist_ok=True)

    evaluated = evaluate_decision_outcomes(memory_dir=base_memory)
    lessons = extract_lessons_for_next_meeting(evaluated, memory_dir=base_memory)

    lines = ["## Reflection Report", ""]

    lines.append("### 成功した判断")
    if evaluated["success"]:
        for e in evaluated["success"]:
            lines.append(_format_entry(e))
    else:
        lines.append("- まだ十分なKPIデータなし")
    lines.append("")

    lines.append("### 改善が必要な判断")
    if evaluated["needs_review"]:
        for e in evaluated["needs_review"]:
            lines.append(_format_entry(e))
    else:
        lines.append("- まだ十分なKPIデータなし")
    lines.append("")

    if evaluated["rejected"]:
        lines.append("### 却下した判断（参考）")
        for e in evaluated["rejected"]:
            lines.append(f"- #{e['issue']} {e['title']}（{e['date']}却下） — {e['note']}")
        lines.append("")

    lines.append("### 次回会議への反映")
    for lesson in lessons:
        lines.append(f"- {lesson}")
    lines.append("")

    content = "\n".join(lines)
    path = base_outputs / "reflection_report.md"
    path.write_text(content, encoding="utf-8")
    return path


def get_reflection_summary(outputs: Path) -> dict | None:
    """
    Quest61: Dashboard向けに reflection_report.md の要点だけを抜き出す。
    「成功した判断」「改善が必要な判断」「次回会議への反映」の
    トップレベル箇条書きのみを返す（インデントされた詳細行は含めない）。
    ファイルが無ければ None を返す（Dashboard側で「まだ振り返りデータはありません」と表示する）。
    """
    path = outputs / "reflection_report.md"
    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8")

    def _top_level_bullets(heading: str) -> list[str]:
        m = re.search(rf"### {re.escape(heading)}\s*\n([\s\S]*?)(?=\n### |\Z)", text)
        if not m:
            return []
        bullets = []
        for line in m.group(1).splitlines():
            if line.startswith("- ") and not line.startswith("  "):
                bullets.append(line[2:].strip())
        return bullets

    return {
        "success": _top_level_bullets("成功した判断"),
        "needs_review": _top_level_bullets("改善が必要な判断"),
        "next_meeting": _top_level_bullets("次回会議への反映"),
    }


if __name__ == "__main__":
    # Quest60: Dashboard/main.pyの日次バッチを待たずに手動で再生成したい場合のCLI導線。
    #   python services/reflection_service.py
    path = generate_reflection_report()
    print(f"[Reflection] {path} を再生成しました。")
