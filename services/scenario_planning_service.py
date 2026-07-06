"""
DAF OS Quest83 — Scenario Planning サービス

Strategic Goals → Initiatives → KPI Alerts → Autonomous Issues → CEO Inbox →
CEO Decision → Weekly Board Meetingまでの仕組みは、すべて「実際に起きたこと」を
検知・記録・レビューするものだった。このサービスは逆に「まだ起きていないが
起こり得るリスク」を先回りしてシミュレーションし、問題が起きてから考えるのでは
なく事前に行動案を持てる状態を作る。

v1方針（あえてシンプルにする）：
- 4つの主要シナリオ（DAU急減・App Store審査落ち・初回ユーザー不足・
  Crash Rate急増）を固定で定義し、決定的に（LLMを使わず）レポートを組み立てる。
  シナリオ自体は「起こり得るリスク」の仮説であり、現在のKPI実測値には依存しない
  ため、KPIデータが無くても常にレポートを生成できる。
- Issueの自動生成やGitHub連携はここでは行わない（あくまで事前準備のための
  経営会議資料）。

必要な関数：
- generate_scenario_planning():         4シナリオを分析し、
                                         outputs/scenario_planning.md に保存して
                                         ファイルパスを返す
- generate_scenario_planning_summary(): AI会議へ注入する短いMarkdown要約
                                         （High Risk Scenarios・Recommended
                                         Preparation）を返す
- get_high_risk_scenarios():            severityが"High"のシナリオ一覧を
                                         構造化データで返す（Quest84
                                         capital_allocation_service.py から呼ばれる）

CLI:
  python services/scenario_planning_service.py

ファイル書き込み失敗のいずれでも例外を投げず、DAF OS全体を止めない。
"""

import sys
from datetime import datetime
from pathlib import Path

# `python services/scenario_planning_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/weekly_board_meeting_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"

_NO_DATA_SUMMARY = "## Scenario Planning Summary\n\n現在、Scenario Planningはまだ生成されていません。"

# 4つの主要シナリオ（v1固定定義）。
# severity: Critical > High > Medium > Low の4段階。
# preparation: 「起きたらどうするか」ではなく「起きる前に何を準備しておくか」を
# 一言で表したもの（generate_scenario_planning_summary()のRecommended Preparationで使う）。
_SCENARIOS = [
    {
        "id": 1,
        "title": "DAUが30%減少した場合",
        "short_title": "DAUが30%減少",
        "impact": [
            "North Star Metric低下",
            "User Acquisition見直し",
            "Onboarding問題の可能性",
        ],
        "recommended_actions": [
            "KPI深掘り",
            "離脱分析",
            "ユーザーヒアリング",
        ],
        "severity": "High",
        "preparation": "KPI分析手順の準備",
    },
    {
        "id": 2,
        "title": "App Store審査に落ちた場合",
        "short_title": "App Store審査落ち",
        "impact": [
            "Annual Goal遅延",
            "初期ユーザー獲得遅延",
        ],
        "recommended_actions": [
            "リジェクト理由の分析",
            "修正Issue生成",
            "再申請スケジュール策定",
        ],
        "severity": "High",
        "preparation": "App Store再申請手順の整備",
    },
    {
        "id": 3,
        "title": "初回ユーザーが10人未満の場合",
        "short_title": "初回ユーザー10人未満",
        "impact": [
            "Product Market Fit検証不足",
            "フィードバック不足",
        ],
        "recommended_actions": [
            "SNS募集",
            "知人テスト",
            "Dog communityへの展開",
        ],
        "severity": "Medium",
        "preparation": "初期ユーザー獲得チャネルの整備",
    },
    {
        "id": 4,
        "title": "Crash Rateが20%以上上昇した場合",
        "short_title": "Crash Rateが20%以上上昇",
        "impact": [
            "Review Rating低下",
            "User Trust低下",
        ],
        "recommended_actions": [
            "クラッシュ解析",
            "緊急修正",
            "リリース停止判断",
        ],
        "severity": "Critical",
        "preparation": "緊急修正フローの確認",
    },
]


def _render_scenario(scenario: dict) -> str:
    lines = [
        f"## Scenario {scenario['id']}",
        scenario["title"],
        "",
        "### Impact",
    ]
    lines.extend(f"- {i}" for i in scenario["impact"])
    lines.append("")
    lines.append("### Recommended Actions")
    lines.extend(f"{i}. {a}" for i, a in enumerate(scenario["recommended_actions"], start=1))
    lines.append("")
    lines.append("### Severity")
    lines.append(scenario["severity"])
    return "\n".join(lines)


def generate_scenario_planning(outputs_dir: Path | None = None) -> Path:
    """
    4つの主要シナリオ（DAU急減・App Store審査落ち・初回ユーザー不足・
    Crash Rate急増）を分析し、outputs/scenario_planning.md に保存する。
    シナリオ定義は固定（現在のKPI実測値には依存しない）ため、
    KPIデータが無くても常に生成できる。書き込みに失敗した場合も例外を投げず、
    最低限のフォールバック内容でファイルを生成する。
    """
    base = outputs_dir or _OUTPUTS_DIR

    try:
        base.mkdir(parents=True, exist_ok=True)

        generated_at = datetime.now().strftime("%Y-%m-%d")

        lines = [
            "# Scenario Planning",
            "",
            "Generated At:",
            generated_at,
            "",
            "---",
            "",
        ]
        sections = [_render_scenario(s) for s in _SCENARIOS]
        lines.append("\n\n---\n\n".join(sections))

        path = base / "scenario_planning.md"
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return path
    except Exception as e:
        print(f"[警告] Scenario Planningの生成に失敗しました：{e}")
        try:
            base.mkdir(parents=True, exist_ok=True)
            path = base / "scenario_planning.md"
            path.write_text("# Scenario Planning\n\n生成に失敗しました。\n", encoding="utf-8")
            return path
        except Exception:
            return base / "scenario_planning.md"


def generate_scenario_planning_summary(outputs_dir: Path | None = None) -> str:
    """
    固定のシナリオ定義（_SCENARIOS）から、AI会議へ注入する短いMarkdown要約を返す。
    - High Risk Scenarios: severityが"High"のシナリオ一覧
    - Recommended Preparation: severityが"Critical"または"High"のシナリオの
      事前準備アクション一覧
    シナリオ定義自体は現在のKPI実測値に依存しないため、常に生成できる
    （例外を投げない）。outputs_dirはAPIの一貫性のため受け取るが、
    このサマリーはファイルではなく固定定義から直接組み立てる。
    """
    try:
        high_risk = [s for s in _SCENARIOS if s["severity"] == "High"]
        preparation_targets = [s for s in _SCENARIOS if s["severity"] in ("Critical", "High")]

        lines = ["## Scenario Planning Summary", ""]

        lines.append("### High Risk Scenarios")
        if high_risk:
            lines.extend(f"- {s['short_title']}" for s in high_risk)
        else:
            lines.append("- 現在、High Riskに分類されるシナリオはありません。")
        lines.append("")

        lines.append("### Recommended Preparation")
        if preparation_targets:
            lines.extend(f"- {s['preparation']}" for s in preparation_targets)
        else:
            lines.append("- 現在、事前準備が必要なシナリオはありません。")

        return "\n".join(lines).rstrip()
    except Exception as e:
        print(f"[警告] Scenario Planning Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


def get_high_risk_scenarios() -> list[dict]:
    """
    severityが"High"のシナリオ一覧を構造化データとして返す
    （Quest84 capital_allocation_service.py が、_SCENARIOSという内部定義に
    直接依存せず利用するための公開関数）。例外を投げず、失敗時は空リストを返す。
    """
    try:
        return [dict(s) for s in _SCENARIOS if s["severity"] == "High"]
    except Exception:
        return []


if __name__ == "__main__":
    # Quest83: Dashboard/main.pyの日次バッチを待たずに手動で再生成したい場合のCLI導線。
    #   python services/scenario_planning_service.py
    path = generate_scenario_planning()
    print(f"[Scenario Planning] {path} を生成しました。")
    print()
    print(generate_scenario_planning_summary())
