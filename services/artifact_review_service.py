"""
DAF OS Quest91 — Artifact Review Center サービス

Asset Generator（Quest90）はデジタル資産を`pending_review`状態で生成する
ところまでで、その後は手動で判断するしかなかった。このサービスは
「生成 → レビュー → 承認 → 公開準備」という状態管理を行い、CEOが
approve / revision / reject / publish のいずれかを選ぶだけで完結する
レビューセンターを提供する。

このQuestのゴールは「Digital Asset → Human Approval」を完成させること。
Quest92で「AI社員への自動タスク割当」へ進む前提。

状態一覧：
  pending_review → approved | revision_requested | rejected → published

ディレクトリ構造:
  outputs/reviews/approved/            approve記録（永続保存・履歴）
  outputs/reviews/revision_requested/  revision記録（永続保存・履歴）
  outputs/reviews/rejected/            reject記録（永続保存・履歴）
  outputs/reviews/published/           publish記録（永続保存・履歴）

対象のAsset Typeは outputs/generated_assets/<asset_type>/metadata.md を
読み書きする（Quest90 asset_generator_service.py が生成するファイル）。

必要な関数：
- review_asset(asset_type, decision, reason=None): 1件のレビュー判断を
                                                     metadata.mdへ反映し、
                                                     outputs/reviews/に記録する
- get_review_history():             記録済みのレビュー履歴を一覧として返す
- generate_artifact_review_summary(): AI会議へ注入する短いMarkdown要約を返す

CLI:
  python services/artifact_review_service.py approve line_sticker
  python services/artifact_review_service.py revision line_sticker "画像品質改善"
  python services/artifact_review_service.py reject line_sticker
  python services/artifact_review_service.py publish line_sticker

main.pyの自動実行フローには追加しない（レビューはCEOが明示的に呼んだ時のみ
実行される想定のため）。metadata.md未存在・不正なdecision・書き込み失敗の
いずれでも例外を投げず、DAF OS全体を止めない。
"""

import re
import sys
from datetime import datetime
from pathlib import Path

# `python services/artifact_review_service.py ...` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/asset_generator_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"
_REVIEWS_DIR_NAME = "reviews"
_GENERATED_ASSETS_DIR_NAME = "generated_assets"

_UNSET = "（未定）"
_REVIEWER = "CEO"

# decision（CEOの入力語）→ 新しいStatus・記録先フォルダ名。
_DECISION_TO_STATUS = {
    "approve": "approved",
    "revision": "revision_requested",
    "reject": "rejected",
    "publish": "published",
}

_NO_DATA_SUMMARY = "## Artifact Review Summary\n\n現在、レビュー対象のAssetはありません。"


def _reviews_dir(outputs_dir: Path) -> Path:
    return outputs_dir / _REVIEWS_DIR_NAME


def _generated_assets_dir(outputs_dir: Path) -> Path:
    return outputs_dir / _GENERATED_ASSETS_DIR_NAME


def _metadata_path(asset_type: str, outputs_dir: Path) -> Path:
    return _generated_assets_dir(outputs_dir) / asset_type / "metadata.md"


def _get_field(text: str, label: str) -> str | None:
    m = re.search(rf"^{re.escape(label)}:\s*\n(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _set_field(text: str, label: str, value: str) -> str:
    """
    「Label:\\n値」という単一行フィールドを書き換える。フィールドが存在しない
    場合（Quest90より前の古いmetadata.mdなど）は「## Files」の直前に挿入する。
    どちらも見つからない場合は末尾に追記する（例外は投げない設計を維持するため、
    ここでは常に何らかの形でフィールドを反映する）。
    """
    pattern = re.compile(rf"^{re.escape(label)}:\s*\n.+$", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(f"{label}:\n{value}", text, count=1)

    insertion = f"{label}:\n{value}\n\n"
    if "## Files" in text:
        return text.replace("## Files", insertion + "## Files", 1)
    return text.rstrip() + "\n\n" + insertion.rstrip() + "\n"


def review_asset(
    asset_type: str,
    decision: str,
    reason: str | None = None,
    outputs_dir: Path | None = None,
) -> dict:
    """
    1件のAsset Typeに対するCEOのレビュー判断（approve / revision / reject /
    publish）を反映する。

    - outputs/generated_assets/<asset_type>/metadata.md のStatus・Reviewer・
      Reviewed At・Review Decision・Review Reasonを更新する
      （decision=="publish"の場合はPublished Atも更新する）
    - outputs/reviews/{approved,revision_requested,rejected,published}/ に
      レビュー記録（frontmatter付きMarkdown）を保存する

    引数:
        asset_type: レビュー対象（v1では"line_sticker"のみ実データが存在する）
        decision:   "approve" | "revision" | "reject" | "publish"
        reason:     レビュー理由（任意）

    戻り値: {"ok": bool, "asset_type": str, "status": str | None,
             "reviewed_at": str | None, "error": str | None}
    metadata.md未存在・不正なdecision・書き込み失敗のいずれでも例外を投げず、
    "ok": False を返す（DAF OS全体を止めない）。
    """
    base_outputs_dir = outputs_dir or _OUTPUTS_DIR

    try:
        decision_key = (decision or "").strip().lower()
        new_status = _DECISION_TO_STATUS.get(decision_key)
        if not new_status:
            return {"ok": False, "asset_type": asset_type, "error": f"不正なdecisionです：{decision}"}

        metadata_path = _metadata_path(asset_type, base_outputs_dir)
        if not metadata_path.exists():
            return {"ok": False, "asset_type": asset_type, "error": "metadata.mdが見つかりません"}

        text = metadata_path.read_text(encoding="utf-8")
        reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        text = _set_field(text, "Status", new_status)
        text = _set_field(text, "Reviewer", _REVIEWER)
        text = _set_field(text, "Reviewed At", reviewed_at)
        text = _set_field(text, "Review Decision", decision_key)
        text = _set_field(text, "Review Reason", reason or "（理由なし）")
        if decision_key == "publish":
            text = _set_field(text, "Published At", reviewed_at)

        metadata_path.write_text(text, encoding="utf-8")

        # レビュー記録（履歴）を保存する
        folder = _reviews_dir(base_outputs_dir) / new_status
        folder.mkdir(parents=True, exist_ok=True)
        stem = f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_{asset_type}"
        record_path = folder / f"{stem}.md"
        suffix = 2
        while record_path.exists():
            record_path = folder / f"{stem}_{suffix}.md"
            suffix += 1

        record_lines = [
            "---",
            f"asset_type: {asset_type}",
            f"decision: {decision_key}",
            f"reason: {reason or '（理由なし）'}",
            f"reviewed_at: {reviewed_at}",
            "---",
            "",
            f"# Artifact Review: {asset_type}",
            "",
            f"- Decision: {decision_key}",
            f"- Reason: {reason or '（理由なし）'}",
            f"- Reviewed At: {reviewed_at}",
        ]
        record_path.write_text("\n".join(record_lines) + "\n", encoding="utf-8")

        # Notification Center（Quest92）へ通知する。失敗してもレビュー記録自体は成功として扱う。
        try:
            from services.notification_service import add_notification
            add_notification(
                "Review Decision",
                f"{asset_type} が {new_status} になりました。",
                level="info",
                source="artifact_review",
                outputs_dir=base_outputs_dir,
            )
        except Exception as e:
            print(f"[警告] Notification Centerへの通知に失敗しました：{e}")

        return {"ok": True, "asset_type": asset_type, "status": new_status, "reviewed_at": reviewed_at}
    except Exception as e:
        print(f"[警告] Artifact Reviewの記録に失敗しました（{asset_type}）：{e}")
        return {"ok": False, "asset_type": asset_type, "error": str(e)}


def _parse_review_record(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
        fm_match = re.search(r"^---\n([\s\S]*?)\n---", text)
        if not fm_match:
            return None
        fm = fm_match.group(1)

        def _field(key: str) -> str | None:
            m = re.search(rf"^{re.escape(key)}:\s*(.+)$", fm, re.MULTILINE)
            return m.group(1).strip() if m else None

        return {
            "asset_type": _field("asset_type"),
            "decision": _field("decision"),
            "reason": _field("reason"),
            "reviewed_at": _field("reviewed_at"),
        }
    except Exception:
        return None


def get_review_history(outputs_dir: Path | None = None) -> list[dict]:
    """
    outputs/reviews/{approved,revision_requested,rejected,published}/ 配下の
    全レビュー記録を読み込み、reviewed_atの新しい順で一覧として返す。

    戻り値: [{"asset_type": str, "decision": str, "reason": str,
              "reviewed_at": str}, ...]
    ディレクトリ未存在・ファイル無し・パース失敗のいずれでも例外を投げず、
    空リストを返す。
    """
    try:
        base = outputs_dir or _OUTPUTS_DIR
        reviews_dir = _reviews_dir(base)
        if not reviews_dir.exists():
            return []

        records = []
        for status in _DECISION_TO_STATUS.values():
            folder = reviews_dir / status
            if not folder.exists():
                continue
            for path in folder.glob("*.md"):
                record = _parse_review_record(path)
                if record:
                    records.append(record)

        records.sort(key=lambda r: r.get("reviewed_at") or "", reverse=True)
        return records
    except Exception as e:
        print(f"[警告] Review Historyの取得に失敗しました：{e}")
        return []


def _scan_asset_statuses(outputs_dir: Path) -> dict[str, str]:
    """outputs/generated_assets/*/metadata.md から、現在のAsset Type別Statusを集計する。"""
    statuses: dict[str, str] = {}
    try:
        assets_dir = _generated_assets_dir(outputs_dir)
        if not assets_dir.exists():
            return statuses

        for asset_dir in sorted(assets_dir.iterdir()):
            metadata_path = asset_dir / "metadata.md"
            if not metadata_path.exists():
                continue
            try:
                text = metadata_path.read_text(encoding="utf-8")
            except Exception:
                continue
            status = _get_field(text, "Status") or "unknown"
            statuses[asset_dir.name] = status
    except Exception as e:
        print(f"[警告] Asset Statusの取得に失敗しました：{e}")
    return statuses


def generate_artifact_review_summary(outputs_dir: Path | None = None) -> str:
    """
    outputs/generated_assets/*/metadata.md のStatusを集計し、AI会議へ注入する
    短いMarkdown要約に整形する（services/memory_service.py の
    load_company_memory() から呼ばれる）。生成済みAssetが1件も無い場合は
    「現在、レビュー対象のAssetはありません。」を返す。例外を投げない。
    """
    try:
        base = outputs_dir or _OUTPUTS_DIR
        statuses = _scan_asset_statuses(base)
        if not statuses:
            return _NO_DATA_SUMMARY

        pending = [t for t, s in statuses.items() if s == "pending_review"]
        approved_count = len([t for t, s in statuses.items() if s == "approved"])
        published_count = len([t for t, s in statuses.items() if s == "published"])

        lines = ["## Artifact Review Summary", "", "### Pending Review", ""]
        if pending:
            lines.extend(f"- {t}" for t in pending)
        else:
            lines.append("- 現在、レビュー待ちのAssetはありません。")
        lines.append("")
        lines.append("### Approved Assets")
        lines.append("")
        lines.append(f"- {approved_count}")
        lines.append("")
        lines.append("### Published Assets")
        lines.append("")
        lines.append(f"- {published_count}")
        lines.append("")
        lines.append("### Recommendation")
        if pending:
            lines.append("生成物を確認し、")
            lines.append("approveまたはrevisionを実施してください。")
        else:
            lines.append("現在、対応が必要なレビューはありません。")

        return "\n".join(lines).rstrip()
    except Exception as e:
        print(f"[警告] Artifact Review Summaryの生成に失敗しました：{e}")
        return _NO_DATA_SUMMARY


def _cli_review(command: str, args: list[str]) -> None:
    if not args:
        print(f"使い方: python services/artifact_review_service.py {command} <asset_type> [理由]")
        return
    asset_type = args[0]
    reason = " ".join(args[1:]) if len(args) > 1 else None
    result = review_asset(asset_type, command, reason=reason)
    if result.get("ok"):
        print(f"[Artifact Review] {asset_type} を {result['status']} にしました（{result['reviewed_at']}）。")
    else:
        print(f"[Artifact Review] 失敗しました：{result.get('error')}")


if __name__ == "__main__":
    # Quest91: CLI導線。
    #   python services/artifact_review_service.py approve line_sticker
    #   python services/artifact_review_service.py revision line_sticker "画像品質改善"
    #   python services/artifact_review_service.py reject line_sticker
    #   python services/artifact_review_service.py publish line_sticker
    argv = sys.argv[1:]
    if argv and argv[0] in _DECISION_TO_STATUS:
        _cli_review(argv[0], argv[1:])
    else:
        print(generate_artifact_review_summary())
