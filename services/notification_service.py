"""
DAF OS v1.2 — Mac 通知サービス
osascript を使って通知センターに結果を表示する。
失敗してもエラー停止しない。

Quest92（Notification Center）で、上記のMac通知（notify()）とは別に、
DAF OS内の重要イベントを1つのMarkdown通知ログ（outputs/notifications.md）に
集約する機能を追加した。v1ではSlack・メール・Discordなどの外部通知は行わない
（目的は「DAF OS内で重要イベントを見逃さないこと」）。

通知は2種類の発生源を持つ：
1. イベント駆動：Asset Generator（Quest90）・Artifact Review Center（Quest91）が、
   成果物生成・レビュー判断のタイミングでadd_notification()を直接呼ぶ
   （"Asset Generated" / "Review Decision"）。
2. 状態スキャン駆動：generate_notifications()がoutputs/以下の現在の状態
   （レビュー待ちAsset・Critical KPI Alert・実装待ちIssue）を確認し、
   該当すれば通知を追加する（"Review Requested" / "Critical KPI Alert" /
   "Pending Implementation"）。

重複通知防止：同じ (title, source, message) の組み合わせが既に
outputs/notifications.md に存在する場合は追加しない。

通知レベル： info / warning / critical / success

必要な関数：
- add_notification(title, message, level="info", source="system"):
    通知を outputs/notifications.md に追記する（重複していれば追加しない）
- generate_notifications():
    現在の状態を確認し、必要な通知を生成する（Review Requested /
    Critical KPI Alert / Pending Implementation）
- generate_notification_summary():
    AI会議へ注入する短いMarkdown要約を返す

CLI:
  python services/notification_service.py
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# `python services/notification_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/artifact_review_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_MEMORY_DIR = _BASE_DIR / "memory"
_OUTPUTS_DIR = _BASE_DIR / "outputs"
_NOTIFICATIONS_FILENAME = "notifications.md"

_LEVELS = ("info", "warning", "critical", "success")
_LEVEL_DISPLAY_ORDER = ("critical", "warning", "info", "success")
_LEVEL_SECTION_LABEL = {
    "critical": "Critical",
    "warning": "Warning",
    "info": "Info",
    "success": "Success",
}

_NO_DATA_SUMMARY = "## Notification Summary\n\n現在、通知はありません。"


def _extract_actions(dashboard_text: str) -> list[str]:
    m = re.search(r"## 3\. 次にCEOがやること\s*\n([\s\S]*?)(?=\n## |\Z)", dashboard_text)
    if not m:
        return []
    actions = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if re.match(r"\d+\.", line):
            clean = re.sub(r"^\d+\.\s*\*?\*?", "", line).replace("**", "").strip()
            # Issue番号だけ残してタイトルを短縮
            clean = re.sub(r"（担当:.+）", "", clean).strip()
            actions.append(clean)
    return actions[:2]


def _extract_ceo_brief_actions(outputs: Path, limit: int = 3) -> list[str]:
    """
    CEOデイリーブリーフ（v2.4）の「📋 今日やること」を通知用に抽出する。
    ceo_brief.md が無い・壊れている場合は空リストを返し、呼び出し側で従来のフォールバックへ委ねる。
    """
    try:
        path = outputs / "ceo_brief.md"
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8")
        m = re.search(r"## 📋 今日やること（3つまで）\s*\n([\s\S]*?)(?=\n## |\Z)", text)
        if not m:
            return []
        actions = []
        for line in m.group(1).splitlines():
            line = line.strip()
            if re.match(r"\d+\.", line):
                clean = re.sub(r"^\d+\.\s*", "", line).replace("`", "").strip()
                actions.append(clean)
        return actions[:limit]
    except Exception:
        return []


def _osa_escape(text: str) -> str:
    """AppleScript 文字列内でのエスケープ（ダブルクォート・バックスラッシュ）。"""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def notify(
    outputs: Path,
    issue_count: int = 0,
) -> bool:
    """
    Mac 通知センターに DAF OS の実行結果を表示する。
    戻り値: 通知成功なら True。
    """
    dashboard_path = outputs / "dashboard.md"

    # 今日やることTOP3（CEOデイリーブリーフ優先。無ければ従来のダッシュボード抽出にフォールバック）
    actions: list[str] = _extract_ceo_brief_actions(outputs)
    if not actions and dashboard_path.exists():
        actions = _extract_actions(dashboard_path.read_text(encoding="utf-8"))

    # 通知本文を組み立て
    lines = [f"Issue {issue_count}件を生成しました。"]
    if actions:
        lines.append("今日やることTOP3:" if len(actions) > 1 else "今日やること:")
        for a in actions:
            lines.append(f"• {a}")
    lines.append(f"📋 {dashboard_path}")

    title   = "DAF OS 実行完了"
    message = "\n".join(lines)

    script = (
        f'display notification "{_osa_escape(message)}" '
        f'with title "{_osa_escape(title)}" '
        f'sound name "Glass"'
    )

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print("[通知] Mac通知を送信しました")
            return True
        else:
            print(f"[通知] osascript エラー: {result.stderr.strip()}")
            return False
    except FileNotFoundError:
        print("[通知] osascript が見つかりません（Mac以外の環境）→ スキップ")
        return False
    except subprocess.TimeoutExpired:
        print("[通知] osascript タイムアウト → スキップ")
        return False
    except Exception as e:
        print(f"[通知] 通知送信に失敗しました: {e} → スキップ")
        return False


# ──────────────────────────────────────────
# Quest92: Notification Center（Markdown通知ログ）
# 上記のnotify()（Mac通知センターへの単発通知）とは独立した機能。
# ──────────────────────────────────────────

def _notifications_path(outputs_dir: Path) -> Path:
    return outputs_dir / _NOTIFICATIONS_FILENAME


def _parse_notifications(content: str) -> list[dict]:
    """
    既存の outputs/notifications.md を再度構造化データに戻す。重複通知防止
    （(title, source, message)の既存チェック）とSummary集計に使う。
    パース失敗の場合も例外を投げず、空リストを返す。
    """
    try:
        text = re.sub(r"^# Notifications\s*\n+", "", content.strip())
        blocks = re.split(r"\n-{3,}\n", text)

        notifications = []
        for block in blocks:
            block = block.strip()
            if not block.startswith("## "):
                continue

            m = re.match(r"^## (\S+ \S+) - (.+)", block)
            if not m:
                continue
            timestamp, title = m.group(1).strip(), m.group(2).strip()

            level_m = re.search(r"^Level:\s*(.+)$", block, re.MULTILINE)
            source_m = re.search(r"^Source:\s*(.+)$", block, re.MULTILINE)
            level = level_m.group(1).strip() if level_m else "info"
            source = source_m.group(1).strip() if source_m else "system"

            message_m = re.search(r"^Source:.*\n\n([\s\S]+)$", block, re.MULTILINE)
            message = message_m.group(1).strip() if message_m else ""

            notifications.append({
                "timestamp": timestamp,
                "title": title,
                "level": level,
                "source": source,
                "message": message,
            })
        return notifications
    except Exception:
        return []


def _render_notification(timestamp: str, title: str, level: str, source: str, message: str) -> str:
    return "\n".join([
        f"## {timestamp} - {title}",
        "",
        f"Level: {level}",
        f"Source: {source}",
        "",
        message,
    ])


def add_notification(
    title: str,
    message: str,
    level: str = "info",
    source: str = "system",
    outputs_dir: Path | None = None,
) -> bool:
    """
    通知を outputs/notifications.md に追記する。同じ (title, source, message)
    の通知が既に存在する場合は追加しない（重複通知防止）。

    戻り値: 実際に追記した場合はTrue、重複によりスキップした場合・
    書き込みに失敗した場合はFalse（例外を投げない）。
    """
    try:
        base = outputs_dir or _OUTPUTS_DIR
        base.mkdir(parents=True, exist_ok=True)
        path = _notifications_path(base)

        existing_content = path.read_text(encoding="utf-8") if path.exists() else ""
        existing = _parse_notifications(existing_content) if existing_content else []
        existing_keys = {(n["title"], n["source"], n["message"]) for n in existing}

        if (title, source, message) in existing_keys:
            return False

        level_key = (level or "info").strip().lower()
        if level_key not in _LEVELS:
            level_key = "info"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_block = _render_notification(timestamp, title, level_key, source, message)

        if existing_content.strip():
            content = existing_content.rstrip() + "\n\n---\n\n" + new_block + "\n"
        else:
            content = "# Notifications\n\n" + new_block + "\n"

        path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"[警告] 通知の追加に失敗しました（{title}）：{e}")
        return False


def _metadata_status(metadata_path: Path) -> str | None:
    if not metadata_path.exists():
        return None
    try:
        text = metadata_path.read_text(encoding="utf-8")
    except Exception:
        return None
    m = re.search(r"^Status:\s*\n(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _pending_review_asset_types(outputs_dir: Path) -> list[str]:
    """
    outputs/generated_assets/*/metadata.md からStatusがpending_reviewの
    Asset Typeを返す。Quest97：line_stickerがProject別サブフォルダ
    （outputs/generated_assets/line_sticker/<project_id>/metadata.md）を
    持つようになったため、直下にmetadata.mdが無い場合は1階層下の
    サブフォルダも確認する（フラット形式・Project別形式の両対応）。
    """
    try:
        assets_dir = outputs_dir / "generated_assets"
        if not assets_dir.exists():
            return []
        pending = []
        for asset_dir in sorted(assets_dir.iterdir()):
            if not asset_dir.is_dir():
                continue

            found_pending = _metadata_status(asset_dir / "metadata.md") == "pending_review"

            if not found_pending:
                for sub in asset_dir.iterdir():
                    if not sub.is_dir():
                        continue
                    if _metadata_status(sub / "metadata.md") == "pending_review":
                        found_pending = True
                        break

            if found_pending:
                pending.append(asset_dir.name)
        return pending
    except Exception as e:
        print(f"[警告] Review Requestedの取得に失敗しました：{e}")
        return []


def _has_critical_kpi_alert(kpi_dir: Path | None, memory_dir: Path) -> bool:
    try:
        from services.kpi_alert_service import get_active_kpi_alerts
        alerts = get_active_kpi_alerts(kpi_dir=kpi_dir, memory_dir=memory_dir)
        return any(a.get("level") == "CRITICAL" for a in alerts)
    except Exception as e:
        print(f"[警告] KPI Alertsの取得に失敗しました：{e}")
        return False


def _has_pending_implementation(outputs_dir: Path) -> bool:
    try:
        from services.issue_pipeline_service import load_generated_issues
        issues = load_generated_issues(outputs_dir=outputs_dir)
        return any(i.get("status") == "pending_implementation" for i in issues)
    except Exception as e:
        print(f"[警告] Issue Pipelineの取得に失敗しました：{e}")
        return False


def generate_notifications(
    kpi_dir: Path | None = None,
    outputs_dir: Path | None = None,
    memory_dir: Path | None = None,
) -> list[dict]:
    """
    現在の状態（レビュー待ちAsset・Critical KPI Alert・実装待ちIssue）を
    確認し、該当する通知を outputs/notifications.md に追加する。
    add_notification()自体が重複防止を行うため、状態が変わらない限り
    何度実行しても通知は増え続けない。

    参照対象：outputs/generated_assets/・outputs/reviews/（Statusの参照元）・
    KPI Alert（services/kpi_alert_service経由）・
    outputs/issue_pipeline/generated_issues.md

    戻り値: 今回の実行で新しく追加された通知のリスト（追加が無ければ空リスト）。
    各情報源の読み込みは個別にtry/exceptで守られており、DAF OS全体を止めない。
    """
    base_outputs_dir = outputs_dir or _OUTPUTS_DIR
    base_memory_dir = memory_dir or _MEMORY_DIR

    added = []

    try:
        for asset_type in _pending_review_asset_types(base_outputs_dir):
            title = "Review Requested"
            message = f"{asset_type} がレビュー待ちです。"
            source = "artifact_review"
            if add_notification(title, message, level="info", source=source, outputs_dir=base_outputs_dir):
                added.append({"title": title, "message": message, "level": "info", "source": source})
    except Exception as e:
        print(f"[警告] Review Requested通知の生成に失敗しました：{e}")

    try:
        if _has_critical_kpi_alert(kpi_dir, base_memory_dir):
            title = "Critical KPI Alert"
            message = "Critical KPI Alertがあります。CEO確認が必要です。"
            source = "kpi_alert"
            if add_notification(title, message, level="critical", source=source, outputs_dir=base_outputs_dir):
                added.append({"title": title, "message": message, "level": "critical", "source": source})
    except Exception as e:
        print(f"[警告] Critical KPI Alert通知の生成に失敗しました：{e}")

    try:
        if _has_pending_implementation(base_outputs_dir):
            title = "Pending Implementation"
            message = "実装待ちIssueが存在します。"
            source = "issue_pipeline"
            if add_notification(title, message, level="warning", source=source, outputs_dir=base_outputs_dir):
                added.append({"title": title, "message": message, "level": "warning", "source": source})
    except Exception as e:
        print(f"[警告] Pending Implementation通知の生成に失敗しました：{e}")

    return added


def generate_notification_summary(outputs_dir: Path | None = None) -> str:
    """
    outputs/notifications.md を読み込み、AI会議へ注入する短いMarkdown要約に
    整形する（services/memory_service.py の load_company_memory() から
    呼ばれる）。レベル別（Critical → Warning → Info → Success）にメッセージを
    列挙する。通知が1件も無い場合は「現在、通知はありません。」を返す。
    例外を投げない。
    """
    try:
        base = outputs_dir or _OUTPUTS_DIR
        path = _notifications_path(base)
        if not path.exists():
            return _NO_DATA_SUMMARY

        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return _NO_DATA_SUMMARY

        notifications = _parse_notifications(content)
        if not notifications:
            return _NO_DATA_SUMMARY

        by_level: dict[str, list[str]] = {level: [] for level in _LEVELS}
        for n in notifications:
            level = n.get("level") if n.get("level") in _LEVELS else "info"
            message = n.get("message") or n.get("title")
            if message not in by_level[level]:
                by_level[level].append(message)

        lines = ["## Notification Summary"]
        for level in _LEVEL_DISPLAY_ORDER:
            messages = by_level.get(level) or []
            if not messages:
                continue
            lines.append("")
            lines.append(f"### {_LEVEL_SECTION_LABEL[level]}")
            lines.extend(f"- {m}" for m in messages)

        if len(lines) == 1:
            return _NO_DATA_SUMMARY

        return "\n".join(lines).rstrip()
    except Exception as e:
        print(f"[警告] Notification Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


def get_notifications(outputs_dir: Path | None = None) -> list[dict]:
    """
    outputs/notifications.md を読み込み専用でパースし、Dashboard
    （試験運用版）の「Notifications」タブ向けに新しい順（timestamp降順）で
    返す（Dashboard/CEO Home APIから呼ばれる）。

    戻り値: [{"timestamp": str, "title": str, "level": str, "source": str,
              "message": str}, ...]
    ファイル未存在・パース失敗のいずれでも例外を投げず、空リストを返す。
    """
    try:
        base = outputs_dir or _OUTPUTS_DIR
        path = _notifications_path(base)
        if not path.exists():
            return []
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        notifications = _parse_notifications(content)
        notifications.sort(key=lambda n: n.get("timestamp") or "", reverse=True)
        return notifications
    except Exception as e:
        print(f"[警告] Notificationsの取得に失敗しました：{e}")
        return []


if __name__ == "__main__":
    # Quest92: Dashboard/main.pyの日次バッチを待たずに手動で再生成したい場合のCLI導線。
    #   python services/notification_service.py
    added = generate_notifications()
    print(f"[Notification Center] 新規通知: {len(added)}件")
    for n in added:
        print(f"  - [{n['level']}] {n['title']}: {n['message']}")
    print()
    print(generate_notification_summary())
