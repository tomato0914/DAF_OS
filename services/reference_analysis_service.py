"""
DAF OS Quest101 — Reference Analysis Service（Vega Reference Report）

CEOが持つ「こんな雰囲気にしたい」という参考画像を、Vega（Creative
Director、docs/organization.md参照）が理解できる形に変換するための
最初の一歩。画像そのものを解析・複製する仕組みではなく、CEOが登録した
メタデータ（reference.json：タイトル・タグ・動物・色・雰囲気・メモ）から、
配色・線の太さ・キャラクター性・世界観・デザインキーワードを人が編集
しやすいMarkdown（Vega Reference Report）へまとめるところまでを実装する。

Quest101ではAI画像解析（Vision API・マルチモーダルLLM等）は使わない。
将来これらへ差し替えられるよう、「メタデータからレポートを組み立てる」
という入口の形だけを決定的な処理で実装する（_keywords_from_images()等の
集計ロジックを差し替えるだけで、Reportの出力形式は変えずに済む設計）。

著作権保護のため、画像そのものを複製・模倣する仕組みは持たない。
outputs/reference_library/には画像ファイルの保存場所（カテゴリフォルダ）を
用意するのみで、このサービスは画像バイナリを一切読み書きしない
（reference.jsonというメタデータのみを扱う）。

保存先：
  outputs/reference_library/<category>/<画像ファイル名>.reference.json
    （画像ファイル自体は同じフォルダへCEOが別途保存する想定。Quest101では
    アップロードUIは実装しない）
  outputs/reference_library/<project_id>/vega_reference_report.md
    （Projectごとに集計したVega Reference Report）

必要な関数：
- ensure_reference_library():          カテゴリフォルダを作成する
- register_reference_metadata(...):    1件のreference.jsonを保存する
- list_reference_images(project_id):   登録済み参考画像のメタデータ一覧を返す
- get_reference_library_summary():     Dashboard向けの集計を返す
- generate_vega_reference_report(project_id): Reference SummaryをMarkdownで
                                        組み立てて保存する
- get_reference_summary_for_brief(project_id): Creative Brief埋め込み用の
                                        短い要約を返す

CLI:
  python services/reference_analysis_service.py

ディレクトリ未存在・JSON破損・書き込み失敗のいずれでも例外を投げず、
DAF OS全体を止めない。
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"
_REFERENCE_LIBRARY_DIR_NAME = "reference_library"

# Quest101のv1固定カテゴリ。将来増やす場合もensure_reference_library()の
# 引数を変えるだけで対応できる。
_DEFAULT_CATEGORIES = ["animals", "cute", "simple", "pastel", "manga", "realistic"]

_NO_REFERENCE_TEXT = "参考画像はまだ登録されていません。"
_NO_REFERENCE_SUMMARY = "まだ参考画像が登録されていません。"


def _library_root(outputs_dir: Path | None = None) -> Path:
    return (outputs_dir or _OUTPUTS_DIR) / _REFERENCE_LIBRARY_DIR_NAME


def _safe_category(category: str) -> str:
    """カテゴリ名をフォルダ名として安全な形（英数字・アンダースコア）に丸める。"""
    safe = re.sub(r"[^\w\-]", "_", (category or "uncategorized").strip()) or "uncategorized"
    return safe


def ensure_reference_library(outputs_dir: Path | None = None) -> Path:
    """
    outputs/reference_library/ とQuest101既定の6カテゴリフォルダ
    （animals/cute/simple/pastel/manga/realistic）を作成する
    （既に存在する場合は何もしない）。ルートPathを返す。
    """
    root = _library_root(outputs_dir)
    try:
        for category in _DEFAULT_CATEGORIES:
            (root / category).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[警告] Reference Libraryの作成に失敗しました：{e}")
    return root


def register_reference_metadata(
    category: str,
    filename: str,
    project_id: str | None = None,
    title: str = "",
    tags: list[str] | None = None,
    animal: str = "",
    color: str = "",
    mood: str = "",
    memo: str = "",
    outputs_dir: Path | None = None,
) -> dict:
    """
    1件の参考画像に対応するreference.jsonを保存する。画像ファイル自体
    （filename）はCEOが同じカテゴリフォルダへ別途保存する想定で、この
    関数は画像バイナリを一切扱わない（メタデータのみ）。

    戻り値: {"ok": bool, "path": str | None, "metadata": dict | None,
             "error": str | None}
    書き込み失敗時も例外を投げない。
    """
    try:
        root = ensure_reference_library(outputs_dir)
        safe_cat = _safe_category(category)
        cat_dir = root / safe_cat
        cat_dir.mkdir(parents=True, exist_ok=True)

        stem = Path(filename).stem or "reference"
        metadata = {
            "title": title or filename,
            "tags": list(tags) if tags else [],
            "animal": animal,
            "color": color,
            "mood": mood,
            "memo": memo,
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "project_id": project_id,
            "category": safe_cat,
            "filename": filename,
        }
        path = cat_dir / f"{stem}.reference.json"
        path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "path": str(path), "metadata": metadata, "error": None}
    except Exception as e:
        print(f"[警告] Reference Metadataの登録に失敗しました（{filename}）：{e}")
        return {"ok": False, "path": None, "metadata": None, "error": str(e)}


def list_reference_images(project_id: str | None = None, outputs_dir: Path | None = None) -> list[dict]:
    """
    outputs/reference_library/<category>/*.reference.json を読み込み専用で
    スキャンし、登録済み参考画像のメタデータ一覧を返す（registered_atの
    新しい順）。project_idを指定すると、そのProjectに紐づくものだけに絞る。

    戻り値: [{"title": str, "tags": list[str], "animal": str, "color": str,
              "mood": str, "memo": str, "registered_at": str,
              "project_id": str | None, "category": str, "filename": str}, ...]
    ディレクトリ未存在・JSON破損のいずれでも例外を投げず、空リストを返す
    （壊れたファイルはスキップする）。
    """
    try:
        root = _library_root(outputs_dir)
        if not root.exists():
            return []

        results = []
        for cat_dir in sorted(root.iterdir()):
            if not cat_dir.is_dir():
                continue
            for meta_path in sorted(cat_dir.glob("*.reference.json")):
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if project_id is not None and meta.get("project_id") != project_id:
                    continue
                results.append(meta)

        results.sort(key=lambda m: m.get("registered_at") or "", reverse=True)
        return results
    except Exception as e:
        print(f"[警告] Reference Imageの一覧取得に失敗しました：{e}")
        return []


def _keywords_from_images(images: list[dict]) -> list[str]:
    """タグ・雰囲気から重複除去したデザインキーワード一覧を作る（登場順）。"""
    keywords: list[str] = []
    for img in images:
        for tag in (img.get("tags") or []):
            if tag and tag not in keywords:
                keywords.append(tag)
        mood = img.get("mood")
        if mood and mood not in keywords:
            keywords.append(mood)
    return keywords


def _line_style_keywords(images: list[dict]) -> list[str]:
    """タグの中から線の太さ・タッチに関するキーワード（"線"を含むもの）を抽出する。"""
    keywords = []
    for img in images:
        for tag in (img.get("tags") or []):
            if tag and ("線" in tag or "line" in tag.lower()) and tag not in keywords:
                keywords.append(tag)
    return keywords


def get_reference_library_summary(outputs_dir: Path | None = None) -> dict:
    """
    Dashboardの「🎨 Reference Library」カード向けに、登録画像数・タグ一覧・
    最新登録画像・Reference Summaryを集計して返す。

    戻り値: {"count": int, "tags": list[str], "latest": dict | None,
             "summary": str}
    例外を投げない（0件の場合もsummaryに固定文言を返す）。
    """
    try:
        images = list_reference_images(outputs_dir=outputs_dir)
        tags = sorted({tag for img in images for tag in (img.get("tags") or [])})
        latest = images[0] if images else None
        keywords = _keywords_from_images(images)[:8]
        summary = "、".join(keywords) if keywords else _NO_REFERENCE_SUMMARY
        return {"count": len(images), "tags": tags, "latest": latest, "summary": summary}
    except Exception as e:
        print(f"[警告] Reference Library Summaryの生成に失敗しました：{e}")
        return {"count": 0, "tags": [], "latest": None, "summary": _NO_REFERENCE_SUMMARY}


def generate_vega_reference_report(project_id: str, outputs_dir: Path | None = None) -> dict:
    """
    指定Projectに紐づく参考画像メタデータ（reference.json群）から、配色・
    線の太さ・キャラクター性・世界観・デザインキーワードを人が編集しやすい
    Markdown（Vega Reference Report）へまとめ、
    outputs/reference_library/<project_id>/vega_reference_report.md へ保存する。

    Quest101ではAI画像解析は使わない。登録済みのタグ・色・雰囲気メタデータを
    集計する決定的な処理のみ（将来Vision API・マルチモーダルLLMへ差し替える
    場合も、この関数の出力形式は維持できる設計にしている）。

    戻り値: {"ok": bool, "project_id": str, "path": str | None,
             "image_count": int, "error": str | None}
    参考画像が1件も無い場合も、その旨を記したレポートを生成する
    （例外を投げない）。
    """
    try:
        images = list_reference_images(project_id=project_id, outputs_dir=outputs_dir)
        root = _library_root(outputs_dir)
        report_dir = root / project_id
        report_dir.mkdir(parents=True, exist_ok=True)

        lines = ["# Vega Reference Report", "", "Project ID:", project_id, ""]

        if not images:
            lines.extend([
                "参考画像数:",
                "0",
                "",
                "---",
                "",
                _NO_REFERENCE_TEXT,
                "",
                "outputs/reference_library/<category>/ に画像と reference.json",
                "（タイトル・タグ・動物・色・雰囲気・メモ）を登録すると、",
                "配色・線の太さ・キャラクター性・世界観・デザインキーワードが",
                "ここにまとまります。",
            ])
        else:
            colors = sorted({img["color"] for img in images if img.get("color")})
            animals = sorted({img["animal"] for img in images if img.get("animal")})
            moods = sorted({img["mood"] for img in images if img.get("mood")})
            line_styles = _line_style_keywords(images)
            keywords = _keywords_from_images(images)

            lines.extend(["参考画像数:", str(len(images)), "", "---", ""])

            lines.append("## 配色（Color Palette）")
            lines.append("")
            lines.extend(f"- {c}" for c in colors) if colors else lines.append("- （未登録）")

            lines.extend(["", "## 線の太さ・タッチ（Line Style）", ""])
            lines.extend(f"- {ls}" for ls in line_styles) if line_styles else lines.append(
                "- （未登録・タグに「線」を含むキーワードを追加すると表示されます）"
            )

            lines.extend(["", "## キャラクター性（Animal / Character）", ""])
            lines.extend(f"- {a}" for a in animals) if animals else lines.append("- （未登録）")

            lines.extend(["", "## 世界観（Mood）", ""])
            lines.extend(f"- {m}" for m in moods) if moods else lines.append("- （未登録）")

            lines.extend(["", "## デザインキーワード", ""])
            lines.extend(f"- {k}" for k in keywords) if keywords else lines.append("- （未登録）")

            lines.extend(["", "## 参考画像一覧", ""])
            for img in images:
                label = img.get("title") or img.get("filename") or "（無題）"
                memo = img.get("memo") or ""
                suffix = f" — {memo}" if memo else ""
                lines.append(f"- {label}（{img.get('category', '-')}）{suffix}")

        lines.extend([
            "",
            "## Notes",
            "Quest101時点ではAI画像解析は使わず、登録済みメタデータの集計のみ。",
            "将来Vision API・マルチモーダルLLMで自動抽出に置き換え予定。",
            "画像そのものの複製・模倣は行わない（著作権保護のため）。",
        ])

        path = report_dir / "vega_reference_report.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return {"ok": True, "project_id": project_id, "path": str(path), "image_count": len(images), "error": None}
    except Exception as e:
        print(f"[警告] Vega Reference Reportの生成に失敗しました（{project_id}）：{e}")
        return {"ok": False, "project_id": project_id, "path": None, "image_count": 0, "error": str(e)}


def get_reference_summary_for_brief(project_id: str, outputs_dir: Path | None = None) -> str:
    """
    Creative Brief（services/creative_brief_service.py）へ埋め込む短い
    Reference Summaryを返す。参考画像が無い場合は固定文言を返す。
    例外を投げない。
    """
    try:
        images = list_reference_images(project_id=project_id, outputs_dir=outputs_dir)
        if not images:
            return _NO_REFERENCE_TEXT
        keywords = _keywords_from_images(images)[:6]
        if keywords:
            return "、".join(keywords)
        return f"参考画像{len(images)}件を登録済み（タグ・雰囲気は未設定）。"
    except Exception as e:
        print(f"[警告] Reference Summary（Creative Brief用）の生成に失敗しました（{project_id}）：{e}")
        return _NO_REFERENCE_TEXT


if __name__ == "__main__":
    # Quest101: 動作確認用のCLI導線。
    #   python services/reference_analysis_service.py [project_id]
    ensure_reference_library()
    pid = sys.argv[1] if len(sys.argv) > 1 else None
    if pid:
        result = generate_vega_reference_report(pid)
        print(f"[Reference Analysis] {result}")
    else:
        summary = get_reference_library_summary()
        print(f"[Reference Analysis] 登録画像数: {summary['count']}件")
        print(f"タグ一覧: {', '.join(summary['tags']) if summary['tags'] else '（なし）'}")
        print(f"Summary: {summary['summary']}")
