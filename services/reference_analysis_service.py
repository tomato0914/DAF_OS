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
import uuid
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

# Quest102：Reference Upload UIが受け付ける画像形式（画像解析AIは使わない、
# 保存のみの最低限のホワイトリスト）。
_ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

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


def get_default_categories() -> list[str]:
    """Quest101既定の6カテゴリをコピーで返す（Dashboardのカテゴリ選択用）。"""
    return list(_DEFAULT_CATEGORIES)


def save_reference_image(
    file_bytes: bytes,
    original_filename: str,
    category: str = "",
    project_id: str | None = None,
    tags: list[str] | None = None,
    description: str = "",
    outputs_dir: Path | None = None,
) -> dict:
    """
    Quest102：Reference Upload UIから受け取った画像バイナリを
    outputs/reference_library/<category>/ へ保存し、reference.jsonも
    合わせて登録する（register_reference_metadata()を利用、画像解析は行わない）。

    拡張子はpng/jpg/jpeg/webpのみ許可。ファイル名は衝突・パストラバーサル
    防止のため、タイムスタンプ+ランダムIDを付与した安全な名前に丸める。
    descriptionはreference.jsonのmemo項目（既存スキーマ）に保存する。

    戻り値: {"ok": bool, "path": str | None, "metadata": dict | None,
             "error": str | None}
    書き込み失敗時も例外を投げない。
    """
    try:
        ext = Path(original_filename or "").suffix.lower()
        if ext not in _ALLOWED_IMAGE_EXTENSIONS:
            allowed = "/".join(sorted(e.lstrip(".") for e in _ALLOWED_IMAGE_EXTENSIONS))
            return {"ok": False, "path": None, "metadata": None,
                    "error": f"対応していない画像形式です（対応形式: {allowed}）"}

        safe_cat = _safe_category(category)
        root = ensure_reference_library(outputs_dir)
        cat_dir = root / safe_cat
        cat_dir.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique = uuid.uuid4().hex[:8]
        stem = re.sub(r"[^\w\-]", "_", Path(original_filename or "").stem).strip("_") or "reference"
        stem = stem[:60]
        safe_filename = f"ref_{stamp}_{unique}_{stem}{ext}"

        image_path = cat_dir / safe_filename
        image_path.write_bytes(file_bytes)

        title = Path(original_filename or "").stem or safe_filename
        return register_reference_metadata(
            category=safe_cat,
            filename=safe_filename,
            project_id=project_id or None,
            title=title,
            tags=tags,
            memo=description,
            outputs_dir=outputs_dir,
        )
    except Exception as e:
        print(f"[警告] Reference画像の保存に失敗しました（{original_filename}）：{e}")
        return {"ok": False, "path": None, "metadata": None, "error": str(e)}


def refresh_all_reference_summaries(outputs_dir: Path | None = None) -> list[dict]:
    """
    Quest102：登録済み参考画像に紐づく全project_idについて、
    generate_vega_reference_report()を呼び直しReference Summaryを更新する。
    project_id未紐づけ（None）の画像はレポート対象に含めない
    （generate_vega_reference_report()がproject_id必須のため）。

    戻り値: generate_vega_reference_report()の戻り値のリスト。
    project_idが1件も無い場合は空リストを返す。例外を投げない。
    """
    try:
        images = list_reference_images(outputs_dir=outputs_dir)
        project_ids = sorted({img["project_id"] for img in images if img.get("project_id")})
        return [generate_vega_reference_report(pid, outputs_dir=outputs_dir) for pid in project_ids]
    except Exception as e:
        print(f"[警告] Reference Summaryの一括更新に失敗しました：{e}")
        return []


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


# ──────────────────────────────────────────
# Quest103：Reference Image Analysis AI
#
# Quest101〜102では「画像解析AIは使わない」方針だったが、Quest103でVega
# （Creative Director）視点の画像解析を導入する。ただしAI解析は"自動確定"
# ではなく、CEOが確認・修正できる"提案"にとどめる（reference.jsonへの
# 反映はupdate_reference_metadata()を明示的に呼んだ時のみ）。
# ──────────────────────────────────────────

_REFERENCE_ANALYSIS_REQUIRED_KEYS = ("tags", "animal", "color", "mood", "memo")

_VEGA_ANALYSIS_PROMPT = """あなたはVega、DAF OS（デジタルアセットファクトリー）のCreative Director（CDO）です。
添付された参考画像を、キャラクター性・配色・線の太さ・雰囲気・かわいさの観点で分析してください。
あわせて、この画像がどんな商品・Asset（LINEスタンプ等）に向いているか、
mofulog（犬向けプロダクト）のようなペット向けプロダクトに使いやすいかも考慮してください。

結果は必ず次のキーだけを持つJSONオブジェクトで返してください（説明文やコードブロック記法は不要）：
{
  "tags": ["キーワードを3〜6個程度の配列"],
  "animal": "画像の主役となる動物（無ければ空文字）",
  "color": "配色の説明（例: pastel brown, cream, soft pink）",
  "mood": "雰囲気の説明（例: warm, gentle, friendly）",
  "memo": "日本語で2〜3文程度の解析メモ（キャラクター性・線の太さ・向いている用途を含める）"
}
"""


def _empty_reference_analysis(memo: str, error: str | None = None) -> dict:
    return {
        "tags": [], "animal": "", "color": "", "mood": "", "memo": memo,
        "ok": error is None, "error": error,
    }


def _parse_reference_analysis_json(raw_text: str) -> dict:
    """
    AIの応答テキストからJSONオブジェクトを取り出す。前後に説明文や
    ```json コードフェンスが付いていても、最初の{〜最後の}の範囲を
    抜き出してパースする。必須キーが欠けていても安全な既定値で補う。
    """
    text = (raw_text or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("AI応答からJSONを抽出できませんでした")
    data = json.loads(text[start:end + 1])

    tags = data.get("tags")
    if not isinstance(tags, list):
        tags = [t.strip() for t in str(tags or "").split(",") if t.strip()]
    tags = [str(t).strip() for t in tags if str(t).strip()]

    return {
        "tags": tags,
        "animal": str(data.get("animal") or "").strip(),
        "color": str(data.get("color") or "").strip(),
        "mood": str(data.get("mood") or "").strip(),
        "memo": str(data.get("memo") or "").strip(),
    }


def analyze_reference_image(image_path: str) -> dict:
    """
    Quest103：Vega視点で参考画像1件をAI解析し、tags/animal/color/mood/memoの
    "提案"を返す（reference.jsonへの自動反映は行わない。呼び出し側＝
    Dashboard/APIがCEOに提示し、update_reference_metadata()で明示保存する）。

    OPENROUTER_API_KEY未設定の場合は、その旨をmemoに含めた空の提案
    （Stub）を返す。画像未存在・AI呼び出し失敗時も例外を投げず、
    {"ok": False, "error": str}を含む安全な戻り値を返す。

    戻り値: {"tags": list[str], "animal": str, "color": str, "mood": str,
             "memo": str, "ok": bool, "error": str | None}
    """
    import os

    path = Path(image_path)
    if not path.exists() or not path.is_file():
        return _empty_reference_analysis(
            "画像ファイルが見つからないため、AI解析を実行できませんでした。",
            error="image file not found",
        )

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return _empty_reference_analysis(
            "OPENROUTER_API_KEYが未設定のため、AI解析は実行されていません"
            "（tags/animal/color/moodは手動で入力してください）。",
            error="OPENROUTER_API_KEY not set",
        )

    from services.ai_runtime_guard import require_ai_enabled
    if not require_ai_enabled("Reference AI Analysis"):
        return _empty_reference_analysis(
            "AI Runtime GuardによりAI呼び出しが無効化されています"
            "（tags/animal/color/moodは手動で入力してください）。",
            error="AI runtime guard: AI disabled",
        )

    try:
        import base64
        import litellm

        ext = path.suffix.lstrip(".").lower()
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        data_url = f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"

        # crews/meeting_crew.pyと同じOpenRouter経由のgpt-4o-miniを使う
        # （画像入力対応・DAF OS内で既に使用実績のあるモデル）。
        response = litellm.completion(
            model="openrouter/openai/gpt-4o-mini",
            api_key=api_key,
            api_base="https://openrouter.ai/api/v1",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": _VEGA_ANALYSIS_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }],
            temperature=0.4,
            timeout=60,
        )
        content = response["choices"][0]["message"]["content"]
        result = _parse_reference_analysis_json(content)
        result["ok"] = True
        result["error"] = None
        return result
    except Exception as e:
        print(f"[警告] Reference画像のAI解析に失敗しました（{image_path}）：{e}")
        return _empty_reference_analysis(f"AI解析に失敗しました：{e}", error=str(e))


def _reference_json_path_for(category: str, filename: str, outputs_dir: Path | None = None) -> Path | None:
    """
    category/filenameから対応するreference.jsonのPathを組み立てる。
    パストラバーサル対策として、category・filenameのいずれかにスラッシュや
    ".."が含まれる場合はNoneを返す（呼び出し側は不正入力として扱う）。
    """
    if not category or not filename:
        return None
    if any(c in category for c in ("/", "\\")) or ".." in category:
        return None
    if any(c in filename for c in ("/", "\\")) or ".." in filename:
        return None

    root = _library_root(outputs_dir)
    stem = Path(filename).stem
    if not stem:
        return None
    return root / _safe_category(category) / f"{stem}.reference.json"


def update_reference_metadata(
    category: str,
    filename: str,
    tags: list[str] | None = None,
    animal: str | None = None,
    color: str | None = None,
    mood: str | None = None,
    memo: str | None = None,
    outputs_dir: Path | None = None,
) -> dict:
    """
    Quest103：既存reference.json（Quest102 save_reference_image()等で登録済み）
    のtags/animal/color/mood/memoだけを更新する（AI解析結果・CEOの手動編集を
    保存するためのAPI。Analyze自体はこの関数を呼ばない＝自動確定しない）。

    指定した引数（Noneでないもの）だけを上書きし、title/filename/category/
    project_id/registered_at等の既存フィールドはそのまま保持する。
    対象ファイルが存在しない場合はエラー（"not_found"）を返す。

    戻り値: {"ok": bool, "path": str | None, "metadata": dict | None,
             "error": str | None}
    例外を投げない。
    """
    try:
        path = _reference_json_path_for(category, filename, outputs_dir)
        if path is None:
            return {"ok": False, "path": None, "metadata": None, "error": "invalid_category_or_filename"}
        if not path.exists():
            return {"ok": False, "path": None, "metadata": None, "error": "not_found"}

        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            return {"ok": False, "path": str(path), "metadata": None, "error": f"invalid_json: {e}"}

        if tags is not None:
            metadata["tags"] = [str(t).strip() for t in tags if str(t).strip()]
        if animal is not None:
            metadata["animal"] = animal
        if color is not None:
            metadata["color"] = color
        if mood is not None:
            metadata["mood"] = mood
        if memo is not None:
            metadata["memo"] = memo

        path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "path": str(path), "metadata": metadata, "error": None}
    except Exception as e:
        print(f"[警告] Reference Metadataの更新に失敗しました（{category}/{filename}）：{e}")
        return {"ok": False, "path": None, "metadata": None, "error": str(e)}


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
