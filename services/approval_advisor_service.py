"""
DAF OS v2.5 Quest44 — AI承認アドバイザーサービス

承認待ちアイテムごとに、優先度・推定工数・リスク・推奨アクション・理由を
ルールベース（LLM不使用）で自動判定し、CEOの承認判断を助ける。

安全設計：
- 外部APIを呼ばない
- LLMを使わない（キーワードマッチのみ）
- タイトル・本文が空でも例外を出さず、デフォルト値（中程度）にフォールバックする
- 既存の承認データ（approved/ rejected/ の内容）は一切変更しない
"""

import re

# ──────────────────────────────────────────
# 判定ルール（キーワードベース）
# ──────────────────────────────────────────

_HIGH_PRIORITY_KEYWORDS = [
    "privacy", "security", "encryption", "gdpr",
    "プライバシー", "セキュリティ", "暗号化", "個人情報",
    "脆弱性", "同意", "情報漏洩", "認証", "権限",
]

_LOW_PRIORITY_KEYWORDS = [
    "ui", "style", "refactor", "design",
    "デザイン", "スタイル", "リファクタ", "見た目",
    "文言", "表記", "レイアウト", "配色",
]

_LARGE_EFFORT_KEYWORDS = [
    "全面", "刷新", "移行", "再設計", "アーキテクチャ", "基盤",
    "migration", "architecture",
]

_SMALL_EFFORT_KEYWORDS = [
    "確認", "チェック", "レビュー", "軽微", "文言修正", "調査",
    "check", "review",
]

_REJECT_HINT_KEYWORDS = [
    "重複", "不要", "duplicate", "obsolete", "対応済み", "解決済み",
]


_PRIORITY_LABELS = {
    "high":   "🔴 高",
    "medium": "🟡 中",
    "low":    "🟢 低",
}

_EFFORT_LABELS = {
    "small":  "小（1〜2時間）",
    "medium": "中（半日〜1日）",
    "large":  "大（複数日）",
}

_RISK_LABELS = {
    "high":   "高",
    "medium": "中",
    "low":    "低",
}

_ACTION_LABELS = {
    "approve": "承認",
    "hold":    "保留",
    "reject":  "却下",
}


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(kw.lower() in text for kw in keywords)


def _judge_priority(text: str) -> str:
    if _contains_any(text, _HIGH_PRIORITY_KEYWORDS):
        return "high"
    if _contains_any(text, _LOW_PRIORITY_KEYWORDS):
        return "low"
    return "medium"


def _judge_effort(text: str) -> str:
    if _contains_any(text, _LARGE_EFFORT_KEYWORDS):
        return "large"
    if _contains_any(text, _SMALL_EFFORT_KEYWORDS):
        return "small"
    return "medium"


def _judge_risk(text: str, priority: str) -> str:
    # 優先度が高い（セキュリティ/プライバシー系）ものは対応を誤ったときの影響が大きいためリスクも高め
    if priority == "high":
        return "high"
    if priority == "low":
        return "low"
    return "medium"


def _judge_action(text: str, priority: str, risk: str) -> str:
    if _contains_any(text, _REJECT_HINT_KEYWORDS):
        return "reject"
    if priority == "high":
        return "approve"
    if priority == "low":
        return "hold"
    # medium priority: リスクが高ければ一旦保留、低ければ承認
    return "hold" if risk == "high" else "approve"


def _build_reason(priority: str, effort: str, risk: str, action: str) -> str:
    """2〜3行程度の理由文を生成する。"""
    lines = []

    if priority == "high":
        lines.append("プライバシー・セキュリティ等、重要度の高い分野に関わる項目です。")
        lines.append("対応が遅れるとリスクが拡大するため、早めの判断を推奨します。")
    elif priority == "low":
        lines.append("UI/デザイン等、緊急性の低い分野に関わる項目です。")
        lines.append("App Store公開後でも対応可能なため、現在は他タスクを優先しても問題ありません。")
    else:
        lines.append("優先度は中程度で、通常の判断フローで問題ありません。")
        if risk == "high":
            lines.append("ただし影響範囲が読みにくいため、詳細を確認してから判断することを推奨します。")
        else:
            lines.append("大きなリスクは見当たらないため、承認して進めても問題ないと考えられます。")

    if effort == "large":
        lines.append("実装には複数日かかる見込みのため、スケジュールに余裕を持って着手してください。")
    elif effort == "small":
        lines.append("想定工数は小さく、短時間で対応可能です。")

    return "\n".join(lines[:3])


# ──────────────────────────────────────────
# 公開関数
# ──────────────────────────────────────────

def analyze_item(title: str = "", body: str = "") -> dict:
    """
    承認待ちアイテムのタイトル・本文からAIアドバイスを生成する。
    情報が空でも必ず値を返す（例外を出さない）。
    """
    try:
        text = f"{title or ''}\n{body or ''}".lower()

        priority = _judge_priority(text)
        effort = _judge_effort(text)
        risk = _judge_risk(text, priority)
        action = _judge_action(text, priority, risk)
        reason = _build_reason(priority, effort, risk, action)

        return {
            "priority": priority,
            "priority_label": _PRIORITY_LABELS[priority],
            "effort": effort,
            "effort_label": _EFFORT_LABELS[effort],
            "risk": risk,
            "risk_label": _RISK_LABELS[risk],
            "action": action,
            "action_label": _ACTION_LABELS[action],
            "reason": reason,
        }
    except Exception:
        # 情報不足・想定外の入力でも安全側のデフォルトを返す
        return {
            "priority": "medium",
            "priority_label": _PRIORITY_LABELS["medium"],
            "effort": "medium",
            "effort_label": _EFFORT_LABELS["medium"],
            "risk": "medium",
            "risk_label": _RISK_LABELS["medium"],
            "action": "hold",
            "action_label": _ACTION_LABELS["hold"],
            "reason": "情報が不足しているため、内容を確認の上で判断してください。",
        }


_REASON_LINE_SEP = " ／ "  # frontmatterは複数行を扱えないため、1行に結合して保存する


def serialize_reason(reason: str) -> str:
    """複数行の理由を frontmatter 用の1行文字列に変換する。"""
    return _REASON_LINE_SEP.join(
        line.strip() for line in reason.splitlines() if line.strip()
    )


def deserialize_reason(reason_line: str) -> str:
    """frontmatterの1行文字列を、表示用に複数行へ戻す。"""
    if not reason_line:
        return ""
    return "\n".join(part.strip() for part in reason_line.split(_REASON_LINE_SEP) if part.strip())


def build_advisor_frontmatter(advice: dict) -> str:
    """approval_service._write_pending() に渡すfrontmatter断片を生成する。"""
    reason_line = serialize_reason(advice.get("reason", ""))
    return (
        f"advisor_priority: {advice.get('priority', 'medium')}\n"
        f"advisor_effort: {advice.get('effort', 'medium')}\n"
        f"advisor_risk: {advice.get('risk', 'medium')}\n"
        f"advisor_action: {advice.get('action', 'hold')}\n"
        f"advisor_reason: {reason_line}\n"
    )


def parse_advisor_frontmatter(text: str) -> dict | None:
    """
    pending/approved/rejected ファイルの本文から advisor_* フィールドを読み取る。
    フィールドが無い（旧形式のファイルなど）場合は None を返す。
    """
    try:
        priority_m = re.search(r"^advisor_priority: (.+)$", text, re.MULTILINE)
        if not priority_m:
            return None
        effort_m = re.search(r"^advisor_effort: (.+)$", text, re.MULTILINE)
        risk_m = re.search(r"^advisor_risk: (.+)$", text, re.MULTILINE)
        action_m = re.search(r"^advisor_action: (.+)$", text, re.MULTILINE)
        reason_m = re.search(r"^advisor_reason: (.*)$", text, re.MULTILINE)

        priority = priority_m.group(1).strip()
        effort = effort_m.group(1).strip() if effort_m else "medium"
        risk = risk_m.group(1).strip() if risk_m else "medium"
        action = action_m.group(1).strip() if action_m else "hold"
        reason_line = reason_m.group(1).strip() if reason_m else ""

        return {
            "priority": priority,
            "priority_label": _PRIORITY_LABELS.get(priority, priority),
            "effort": effort,
            "effort_label": _EFFORT_LABELS.get(effort, effort),
            "risk": risk,
            "risk_label": _RISK_LABELS.get(risk, risk),
            "action": action,
            "action_label": _ACTION_LABELS.get(action, action),
            "reason": deserialize_reason(reason_line),
        }
    except Exception:
        return None
