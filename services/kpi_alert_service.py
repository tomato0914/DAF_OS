"""
DAF OS Quest78 — KPI Alert System サービス

KPI Memory（Quest58）はスナップショットを記録するだけで、悪化の検知・通知は
していなかった。このサービスは直近2件のKPIスナップショットを比較し、
悪化しているKPIをWARNING / CRITICALとして検知し、Strategic Goals（Quest76）・
Initiative Tracking（Quest77）と紐付けてCEOが早めに気づけるようにする。

必要な関数：
- detect_kpi_alerts():        直近2件のスナップショットを比較し、悪化KPIのリストを返す
- get_active_kpi_alerts():    detect_kpi_alerts()の公開エイリアス
                              （Quest79 autonomous_issue_service.py から呼ばれる）
- generate_kpi_alert_report(): outputs/kpi_alerts.md にMarkdownレポートを生成する
- get_kpi_alert_summary():     AI会議へ注入する短いMarkdown要約を返す

CLI:
  python services/kpi_alert_service.py

services/kpi_memory_service.py の compare_snapshot() を再利用する。
LLMは使わない読み込み専用の判定処理。ファイル未存在・スナップショット0件/1件・
パース失敗のいずれでも例外を投げず、安全に動作する（アラート無し扱い）。
"""

import sys
from pathlib import Path

# `python services/kpi_alert_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/strategic_goal_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_MEMORY_DIR = _BASE_DIR / "memory"
_KPI_DIR = _MEMORY_DIR / "kpi"
_OUTPUTS_DIR = _BASE_DIR / "outputs"

# 下がると悪いKPI（減少を悪化として検知する）
_NEGATIVE_IS_BAD = frozenset({
    "Downloads",
    "New Users",
    "DAU",
    "Retention",
    "D1 Retention",
    "Record Completion Rate",
    "App Store Review Success",
    "User Trust",
    "Crash Free Rate",
    "Review Rating",
})

# 上がると悪いKPI（増加を悪化として検知する）
_POSITIVE_IS_BAD = frozenset({
    "Crash Rate",
    "Error Rate",
    "Churn Rate",
})

_WARNING_THRESHOLD = 10.0
_CRITICAL_THRESHOLD = 20.0

_NO_DATA_REPORT = "## KPI Alert Report\n\n現在、重大なKPI悪化は検出されていません。"
_NO_DATA_SUMMARY = "## KPI Alert Summary\n\n現在、重大なKPI悪化は検出されていません。"


def _list_snapshots(kpi_dir: Path) -> list[Path]:
    """スナップショット一覧をファイル名（日時）昇順で返す。"""
    snapshots_dir = kpi_dir / "kpi_snapshots"
    if not snapshots_dir.exists():
        return []
    return sorted(snapshots_dir.glob("*.md"))


def _safe_load_initiatives(memory_dir: Path) -> list[dict]:
    """initiative_serviceが無い・エラーになる場合でも空リストを返す。"""
    try:
        from services.initiative_service import load_initiatives
        return load_initiatives(memory_dir=memory_dir)
    except Exception:
        return []


def _find_related(metric: str, initiatives: list[dict]) -> tuple[str | None, str | None]:
    """
    metricをSuccess KPIに含むInitiativeを探し、(関連Goal, 関連Initiative名) を返す。
    見つからない場合は (None, None) を返す。
    """
    metric_lower = metric.strip().lower()
    for item in initiatives:
        for kpi in item.get("success_kpi", []):
            if kpi.strip().lower() == metric_lower:
                return item.get("goal"), item.get("name")
    return None, None


def detect_kpi_alerts(kpi_dir: Path | None = None, memory_dir: Path | None = None) -> list[dict]:
    """
    直近2件のKPIスナップショットを比較し、悪化しているKPIを検知する。

    戻り値: [{
        "metric": str,
        "before": str,          # 元のスナップショットの表記のまま
        "after": str,
        "change_pct": float,    # 符号付き変化率（悪化方向がマイナス／プラスかはKPIの性質に依存）
        "level": "WARNING" | "CRITICAL",
        "related_goal": str | None,
        "related_initiative": str | None,
    }, ...]

    CRITICAL → WARNINGの順、同レベル内は変化幅が大きい順にソートする。
    スナップショットが2件未満・ファイル無し・パース失敗のいずれでも例外を投げず、
    空リストを返す（＝アラード無し扱い）。
    """
    try:
        base_kpi_dir = kpi_dir or _KPI_DIR
        base_memory_dir = memory_dir or _MEMORY_DIR

        snapshots = _list_snapshots(base_kpi_dir)
        if len(snapshots) < 2:
            return []

        from services.kpi_memory_service import compare_snapshot
        prev, latest = snapshots[-2], snapshots[-1]
        diff = compare_snapshot(prev, latest)

        initiatives = _safe_load_initiatives(base_memory_dir)

        alerts = []
        for metric, entry in diff.items():
            if metric not in _NEGATIVE_IS_BAD and metric not in _POSITIVE_IS_BAD:
                continue
            if "delta" not in entry:
                continue

            try:
                before = float(entry["before"])
                after = float(entry["after"])
            except (TypeError, ValueError):
                continue
            if before == 0:
                continue

            change_pct = (after - before) / abs(before) * 100

            if metric in _NEGATIVE_IS_BAD:
                is_bad_direction = change_pct < 0
            else:
                is_bad_direction = change_pct > 0

            if not is_bad_direction:
                continue

            magnitude = abs(change_pct)
            if magnitude >= _CRITICAL_THRESHOLD:
                level = "CRITICAL"
            elif magnitude >= _WARNING_THRESHOLD:
                level = "WARNING"
            else:
                continue

            related_goal, related_initiative = _find_related(metric, initiatives)

            alerts.append({
                "metric": metric,
                "before": entry["before"],
                "after": entry["after"],
                "change_pct": change_pct,
                "level": level,
                "related_goal": related_goal,
                "related_initiative": related_initiative,
            })

        level_order = {"CRITICAL": 0, "WARNING": 1}
        alerts.sort(key=lambda a: (level_order[a["level"]], -abs(a["change_pct"])))
        return alerts
    except Exception as e:
        print(f"[警告] KPI Alertsの検知に失敗しました：{e}")
        return []


def get_active_kpi_alerts(kpi_dir: Path | None = None, memory_dir: Path | None = None) -> list[dict]:
    """
    detect_kpi_alerts() の公開エイリアス。Quest79（Autonomous Issue Generation）が
    「現在アクティブなKPI Alertの一覧」を取得するためのエントリーポイントとして使う。
    戻り値・安全性の仕様は detect_kpi_alerts() と同じ。
    """
    return detect_kpi_alerts(kpi_dir=kpi_dir, memory_dir=memory_dir)


def generate_kpi_alert_report(
    kpi_dir: Path | None = None,
    memory_dir: Path | None = None,
    outputs_dir: Path | None = None,
) -> Path:
    """
    detect_kpi_alerts() の結果を outputs/kpi_alerts.md にMarkdownレポートとして保存する。
    アラートが無い場合も「現在、重大なKPI悪化は検出されていません。」を書き込む
    （例外を投げず、必ずファイルを生成する）。
    """
    try:
        alerts = detect_kpi_alerts(kpi_dir=kpi_dir, memory_dir=memory_dir)
        base_outputs_dir = outputs_dir or _OUTPUTS_DIR
        base_outputs_dir.mkdir(parents=True, exist_ok=True)
        path = base_outputs_dir / "kpi_alerts.md"

        if not alerts:
            path.write_text(_NO_DATA_REPORT + "\n", encoding="utf-8")
            return path

        lines = ["## KPI Alert Report", ""]
        for level in ("CRITICAL", "WARNING"):
            level_alerts = [a for a in alerts if a["level"] == level]
            if not level_alerts:
                continue
            lines.append(f"### {level}")
            for a in level_alerts:
                sign = "+" if a["change_pct"] >= 0 else ""
                lines.append(f"- {a['metric']}: {a['before']} → {a['after']} ({sign}{a['change_pct']:.0f}%)")
                if a["related_goal"]:
                    lines.append(f"  - 関連Goal: {a['related_goal']}")
                if a["related_initiative"]:
                    lines.append(f"  - 関連Initiative: {a['related_initiative']}")
            lines.append("")

        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return path
    except Exception as e:
        print(f"[警告] KPI Alert Reportの生成に失敗しました：{e}")
        base_outputs_dir = outputs_dir or _OUTPUTS_DIR
        base_outputs_dir.mkdir(parents=True, exist_ok=True)
        path = base_outputs_dir / "kpi_alerts.md"
        path.write_text(_NO_DATA_REPORT + "\n", encoding="utf-8")
        return path


def get_kpi_alert_summary(kpi_dir: Path | None = None, memory_dir: Path | None = None) -> str:
    """
    detect_kpi_alerts() の結果をAI会議へ注入する短いMarkdown要約に整形する。
    アラートが無い場合は「現在、重大なKPI悪化は検出されていません。」を返す。例外を投げない。
    """
    try:
        alerts = detect_kpi_alerts(kpi_dir=kpi_dir, memory_dir=memory_dir)
        if not alerts:
            return _NO_DATA_SUMMARY

        lines = ["## KPI Alert Summary", ""]
        for level in ("CRITICAL", "WARNING"):
            level_alerts = [a for a in alerts if a["level"] == level]
            if not level_alerts:
                continue
            threshold = "20%以上" if level == "CRITICAL" else "10%以上"
            lines.append(f"{level}:")
            for a in level_alerts:
                if a["related_initiative"]:
                    advice = f"{a['related_initiative']}を優先してください。"
                else:
                    advice = "早めの対応を検討してください。"
                lines.append(f"- {a['metric']}が{threshold}悪化しています。{advice}")
            lines.append("")

        return "\n".join(lines).rstrip()
    except Exception as e:
        print(f"[警告] KPI Alert Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


if __name__ == "__main__":
    # Quest78: Dashboard/main.pyの日次バッチを待たずに手動で再生成したい場合のCLI導線。
    #   python services/kpi_alert_service.py
    report_path = generate_kpi_alert_report()
    print(f"[KPI Alert] {report_path} を生成しました。")
    print()
    print(get_kpi_alert_summary())
