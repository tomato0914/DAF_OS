"""
DAF OS Quest58 — KPI Memory サービス

CEOの意思決定とKPI変化を紐付けて記録し、過去の成功・失敗から学習できるように
するためのMVP実装。

- save_snapshot():        現在のKPIをタイムスタンプ付きスナップショットとして保存する
- compare_snapshot():     2つのスナップショットを比較し、増減を返す
- generate_kpi_summary(): mofulog_metrics.md / decision_outcomes.md / 直近の
                          スナップショット差分を1つのMarkdownサマリーにまとめる
                          （Executive Summary注入に使う。services/memory_service.py参照）

将来のReflection Loop（Quest59予定）で「意思決定 → KPI変化」を突き合わせられるよう、
memory/kpi/decision_outcomes.md はmemory/ceo_decision_history.mdのIssue番号と
対応づける設計にしている（このファイルではその紐付けの読み込み・比較のみを担い、
実際の対応表はmemory/kpi/decision_outcomes.md側で手動管理する）。
"""

import re
from datetime import datetime
from pathlib import Path

_KPI_DIR = Path(__file__).parent.parent / "memory" / "kpi"
_SNAPSHOTS_DIR = _KPI_DIR / "kpi_snapshots"


def save_snapshot(
    metrics: dict[str, str | int | float],
    product: str = "mofulog",
    kpi_dir: Path | None = None,
) -> Path:
    """
    現在のKPI値をタイムスタンプ付きスナップショットとして保存する。
    ファイル名: kpi_snapshots/{product}_{YYYY-MM-DD_HHMMSS}.md
    （同名ファイルが既に存在する場合は連番を付与し、上書きを防ぐ）
    """
    base = kpi_dir or _SNAPSHOTS_DIR
    base.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    stem = f"{product}_{now.strftime('%Y-%m-%d_%H%M%S')}"
    path = base / f"{stem}.md"
    suffix = 2
    while path.exists():
        path = base / f"{stem}_{suffix}.md"
        suffix += 1

    lines = [
        "---",
        f"product: {product}",
        f"timestamp: {now.strftime('%Y-%m-%d %H:%M')}",
        "---",
        "",
    ]
    for key, value in metrics.items():
        lines.append(f"{key}: {value}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _parse_snapshot(path: Path) -> dict[str, str]:
    """スナップショットファイルの本体（frontmatter除く）をkey: value形式でパースする。"""
    text = path.read_text(encoding="utf-8")
    body = re.sub(r"^---[\s\S]*?---\s*", "", text, count=1)
    result: dict[str, str] = {}
    for line in body.strip().splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip()
    return result


def _list_snapshots(product: str | None = None, kpi_dir: Path | None = None) -> list[Path]:
    """スナップショット一覧をファイル名（日時）昇順で返す。"""
    base = kpi_dir or _SNAPSHOTS_DIR
    if not base.exists():
        return []
    files = sorted(base.glob("*.md"))
    if product:
        files = [f for f in files if f.name.startswith(f"{product}_")]
    return files


def compare_snapshot(snapshot_a: Path, snapshot_b: Path) -> dict[str, dict]:
    """
    2つのスナップショットを比較し、項目ごとの増減を返す。
    戻り値: {metric_name: {"before": ..., "after": ..., "delta": ...}}
    数値に変換できない項目は before/after のみ返す（delta なし）。
    """
    before = _parse_snapshot(snapshot_a)
    after = _parse_snapshot(snapshot_b)

    result: dict[str, dict] = {}
    for key in sorted(set(before) | set(after)):
        b, a = before.get(key), after.get(key)
        entry: dict = {"before": b, "after": a}
        try:
            entry["delta"] = float(a) - float(b)
        except (TypeError, ValueError):
            pass
        result[key] = entry
    return result


def generate_kpi_summary(kpi_dir: Path | None = None) -> str:
    """
    mofulog_metrics.md / decision_outcomes.md / 直近2件のスナップショット差分を
    1つのMarkdownサマリーにまとめる。Executive Summaryへの注入に使う
    （services/memory_service.py の load_company_memory() から呼ばれる）。
    ファイル・スナップショットが無い場合は空文字を返す（既存の仕組みを壊さない）。
    """
    base = kpi_dir or _KPI_DIR
    sections: list[str] = []

    metrics_path = base / "mofulog_metrics.md"
    if metrics_path.exists():
        content = metrics_path.read_text(encoding="utf-8").strip()
        if content:
            sections.append(f"### mofulog指標\n\n{content}")

    outcomes_path = base / "decision_outcomes.md"
    if outcomes_path.exists():
        content = outcomes_path.read_text(encoding="utf-8").strip()
        if content:
            sections.append(f"### 意思決定とKPIの紐付け\n\n{content}")

    snapshots = _list_snapshots(kpi_dir=base / "kpi_snapshots")
    if len(snapshots) >= 2:
        prev, latest = snapshots[-2], snapshots[-1]
        diff = compare_snapshot(prev, latest)
        diff_lines = [f"### 直近スナップショット比較（{prev.stem} → {latest.stem}）", ""]
        for key, entry in diff.items():
            if "delta" in entry:
                sign = "+" if entry["delta"] >= 0 else ""
                diff_lines.append(f"- {key}: {entry['before']} → {entry['after']}（{sign}{entry['delta']:g}）")
            else:
                diff_lines.append(f"- {key}: {entry['before']} → {entry['after']}")
        sections.append("\n".join(diff_lines))

    if not sections:
        return ""

    return "## KPI Summary\n\n" + "\n\n".join(sections)
