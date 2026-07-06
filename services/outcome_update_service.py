"""
DAF OS Quest72 — Decision Outcome Auto Update サービス

memory/kpi/decision_outcomes.md に登録された意思決定のうち Status: PENDING の
ものについて、Expected KPI と memory/kpi/kpi_snapshots/ の直近2件を比較し、
SUCCESS / FAILED / PENDING（維持）を自動判定する。LLMは使わない決定的な処理。

対象は見出し形式（Quest62で追加された "## #124" ブロック）のみ。
テーブル形式（Quest58）はStatusフィールドを持たないため対象外
（要件7の通り、まずは見出し形式エントリのみを主対象とする）。

判定ルール：
- Expected KPIが未設定、またはスナップショットが2件未満 → PENDINGのまま
- 期待KPIが改善している → Status: SUCCESS
- 期待KPIが悪化している → Status: FAILED
- 変化なし・比較不能 → PENDINGのまま

KPIごとの向き（上がると良い／下がると良い）は _DOWN_GOOD に列挙したもの以外は
「上がると良い」とみなす（Quest63/65で定義された10種は明示的に上がると良い側）。

自動更新時、Result欄に「KPI名: before → after (差分)」の形式で差分を追記する。
複数のExpected KPIが該当する場合は「; 」で連結する。

必要な関数：
- update_pending_outcomes(): Status: PENDINGのエントリを走査し、判定・更新する

CLI:
  python services/outcome_update_service.py

失敗時（ファイルI/Oエラー・スナップショット比較エラー等）は例外を外に投げず、
警告ログのみ出す（DAF OS全体を止めない）。
"""

import re
from pathlib import Path

_BASE_DIR = Path(__file__).parent.parent
_MEMORY_DIR = _BASE_DIR / "memory"

# 下がると良いKPI（このリストに無いものはすべて「上がると良い」とみなす）
_DOWN_GOOD = {"Crash Rate", "Error Rate", "Churn Rate"}

_BLOCK_RE = re.compile(
    r"^##\s*#(?P<issue>\d+)\s*\n"
    r"Decision:\s*\n(?P<decision>.*?)\n\n"
    r"Expected KPI:\s*\n(?P<expected_kpi>.*?)\n\n"
    r"Result:\s*\n(?P<result>.*?)\n\n"
    r"Status:\s*\n(?P<status>.*?)\n\n"
    r"Lesson:\s*\n(?P<lesson>.*?)"
    r"(?:\n（承認日[:：]\s*(?P<approved_date>.*?)）)?"
    r"\s*(?=\n---|\n##\s*#|\Z)",
    re.MULTILINE | re.DOTALL,
)


def parse_decision_blocks(text: str) -> list[dict]:
    """
    decision_outcomes.md の見出し形式ブロック（Quest62）をパースして返す。
    Quest73のfailed_decision_service.py等、他サービスが同じブロック構造を
    読む際にパース処理を二重管理しないための公開関数
    （Quest64のKPIルール一本化と同じ考え方）。
    """
    blocks = []
    for m in _BLOCK_RE.finditer(text):
        blocks.append({
            "issue": m.group("issue"),
            "decision": m.group("decision").strip(),
            "expected_kpi": m.group("expected_kpi").strip(),
            "result": m.group("result").strip(),
            "status": m.group("status").strip(),
            "lesson": m.group("lesson").strip(),
            "approved_date": (m.group("approved_date") or "").strip(),
        })
    return blocks


def _normalize_kpi_key(name: str) -> str:
    """
    KPI表示名（例: "D1 Retention"）をスナップショットのキー形式
    （例: "d1_retention"）に正規化する。save_snapshot()に渡すmetrics辞書の
    キーはこの形式（小文字・アンダースコア区切り）で統一することを想定している。
    """
    key = name.strip().lower()
    key = re.sub(r"[^a-z0-9]+", "_", key)
    return key.strip("_")


def _evaluate_entry_kpis(expected_kpis: list[str], diff: dict) -> tuple[str, list[str]]:
    """
    Expected KPIのリストと、kpi_memory_service.compare_snapshot()の差分結果から
    このエントリの判定（SUCCESS/FAILED/PENDING）と差分行のリストを返す。

    複数のKPIが該当する場合は「改善件数 vs 悪化件数」の多数決で判定する。
    どのKPIもスナップショットに存在しない・数値化できない場合はPENDING（差分無し）。
    """
    diff_lines: list[str] = []
    improved = 0
    worsened = 0

    for kpi in expected_kpis:
        key = _normalize_kpi_key(kpi)
        entry = diff.get(key)
        if not entry or "delta" not in entry:
            continue

        delta = entry["delta"]
        before = entry.get("before")
        after = entry.get("after")
        down_is_good = kpi in _DOWN_GOOD

        if down_is_good:
            if delta < 0:
                improved += 1
            elif delta > 0:
                worsened += 1
        else:
            if delta > 0:
                improved += 1
            elif delta < 0:
                worsened += 1

        sign = "+" if delta >= 0 else ""
        diff_lines.append(f"{kpi}: {before} → {after} ({sign}{delta:g})")

    if not diff_lines:
        return "PENDING", []
    if improved > worsened:
        return "SUCCESS", diff_lines
    if worsened > improved:
        return "FAILED", diff_lines
    return "PENDING", diff_lines


def update_pending_outcomes(memory_dir: Path | None = None) -> dict:
    """
    memory/kpi/decision_outcomes.md の見出し形式エントリのうち Status: PENDING を
    走査し、Expected KPIとkpi_snapshots/の直近2件の比較から自動判定する。

    戻り値: {"checked": [...issue番号...], "updated": [...issue番号...], "skipped": [...issue番号...]}
    （checked = PENDINGとして検査対象になった件数、updated = 実際にSUCCESS/FAILEDへ
    更新された件数、skipped = データ不足・変化なしでPENDINGのまま据え置いた件数）

    ファイルが無い・スナップショットが無い・パース失敗などいかなる場合も例外を
    投げず、安全な既定値を返す（DAF OS全体を止めない）。
    """
    try:
        base = memory_dir or _MEMORY_DIR
        kpi_dir = base / "kpi"
        path = kpi_dir / "decision_outcomes.md"
        if not path.exists():
            return {"checked": [], "updated": [], "skipped": []}

        text = path.read_text(encoding="utf-8")

        snapshots_dir = kpi_dir / "kpi_snapshots"
        snapshots = sorted(snapshots_dir.glob("*.md")) if snapshots_dir.exists() else []

        diff: dict = {}
        if len(snapshots) >= 2:
            try:
                from services.kpi_memory_service import compare_snapshot
                diff = compare_snapshot(snapshots[-2], snapshots[-1])
            except Exception as e:
                print(f"[警告] KPIスナップショットの比較に失敗しました：{e}")
                diff = {}

        checked: list[str] = []
        updated: list[str] = []
        skipped: list[str] = []
        edits: list[tuple[int, int, str]] = []

        for m in _BLOCK_RE.finditer(text):
            issue = m.group("issue")
            status = m.group("status").strip().upper()
            if status != "PENDING":
                continue

            checked.append(issue)

            expected_kpi_text = m.group("expected_kpi").strip()
            expected_kpis = [
                line.lstrip("- ").strip()
                for line in expected_kpi_text.splitlines()
                if line.strip()
            ]

            if not expected_kpis or expected_kpis == ["未設定"] or not diff:
                skipped.append(issue)
                continue

            verdict, diff_lines = _evaluate_entry_kpis(expected_kpis, diff)
            if verdict == "PENDING" or not diff_lines:
                skipped.append(issue)
                continue

            result_text = "; ".join(diff_lines)
            edits.append((m.start("result"), m.end("result"), result_text))
            edits.append((m.start("status"), m.end("status"), verdict))
            updated.append(issue)

        if edits:
            # 後ろのオフセットから適用することで、前方の置換によるズレを避ける
            edits.sort(key=lambda e: e[0], reverse=True)
            for start, end, replacement in edits:
                text = text[:start] + replacement + text[end:]
            path.write_text(text, encoding="utf-8")

        return {"checked": checked, "updated": updated, "skipped": skipped}
    except Exception as e:
        print(f"[警告] Decision Outcomeの自動更新に失敗しました：{e}")
        return {"checked": [], "updated": [], "skipped": [], "error": str(e)}


if __name__ == "__main__":
    result = update_pending_outcomes()
    if "error" in result:
        print(f"[Outcome Update] 失敗: {result['error']}")
    else:
        print(
            f"[Outcome Update] 検査: {len(result['checked'])}件 / "
            f"更新: {len(result['updated'])}件 / 保留: {len(result['skipped'])}件"
        )
        if result["updated"]:
            print("更新されたIssue:", ", ".join(f"#{i}" for i in result["updated"]))
