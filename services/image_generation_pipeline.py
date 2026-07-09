"""
DAF OS Quest109 — Image Generation Pipeline（Production Phaseの中核）

Quest108までで完成した
  Reference → IP Memory → IP DNA → IP Bible → Creative Style →
  Prompt Builder v2
の最後に、実際に画像を生成・保存し、Dashboardで確認できるところまで
つなげる。

パイプライン：
  最新Prompt取得（services/prompt_builder_v2.py） → 画像生成 → 画像保存 →
  metadata.json保存 → 画像一覧取得

Lean AI Firstを維持しつつ、本Questは画像生成AIの利用を許可する
（Production Phaseの中核のため）。ただし以下を必ず守る：
- AI画像生成API（`OPENAI_API_KEY`）が未設定、またはAPI呼び出しが失敗した
  場合でも例外を投げず、Pillowによるダミー画像生成（既存の
  services/image_generation_service.py・services/renderers/pillow_renderer.py
  をそのまま再利用、Quest98実装への変更なし）へフォールバックする。
- 生成枚数は安全のため最大3枚まで（`MAX_GENERATION_COUNT`）。将来
  40枚生成へ拡張する場合もこの定数を変えるだけで済む設計にしている。
- services/prompt_builder_v2.py（Quest108）・Asset Generator
  （services/asset_generator_service.py、Quest90〜97のLINEスタンプ生成）
  にはいずれも変更を加えない（完全に独立した新しいパイプライン）。

保存先：
  outputs/generated_assets/<asset_type>/<project_id>/
    sticker_001.png, sticker_002.png, ..., metadata.json
  （asset_type="line_sticker"の場合、既存のLINEスタンプ生成
  outputs/generated_assets/line_sticker/<project_id>/ と同じ場所を使う。
  ファイル名は"sticker_"prefixのため、既存Asset Generatorが使う
  stamp_*.png / main.png / tab.png / metadata.md とは衝突しない）。

  1回の実行で「その時点の生成結果」を表す（sticker_001.pngから連番で
  上書き保存し、metadata.jsonも都度上書きする。Quest108のプロンプト
  履歴のような連番保存はしない＝画像はAsset、プロンプトは履歴という
  役割の違いのため）。

必要な関数：
- get_latest_prompt(project_id):     保存済みプロンプトのうち最新のものを
                                      読み込む（services/prompt_builder_v2.py
                                      のload_prompt()をそのまま利用）
- generate_images(project_id, asset_type, count): 画像生成・保存・
                                      metadata.json保存までを行う
- import_external_images(project_id, file_bytes_list, asset_type, source):
                                      Quest121：Gemini等の外部画像生成
                                      サービスで手動生成した画像を取り込む
- list_generated_images(project_id, asset_type): 保存済み画像一覧・
                                      metadataを返す

Quest121（External Image Workflow）：DAF OSの目的は画像生成AIエンジンを
作ることではなく、Digital Asset Factoryとして商品を継続的に制作できる
ことにある。画像生成AIは進化が速いため、画像生成自体はGemini等の外部
サービスにCEOが手動で行わせ、DAFは制作管理・品質管理・提出までを担当する
設計へ拡張した（import_external_images()）。内部AI画像生成
（generate_images()・_generate_via_ai()）は削除せず、将来API接続で
「内部生成に戻す」判断ができるようそのまま維持している。

CLI:
  python services/image_generation_pipeline.py <project_id> [count] [asset_type]

Prompt未生成・AI呼び出し失敗・書き込み失敗のいずれでも例外を投げず、
DAF OS全体を止めない。
"""

import json
import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"
_GENERATED_ASSETS_DIR_NAME = "generated_assets"
_METADATA_FILENAME = "metadata.json"

DEFAULT_ASSET_TYPE = "line_sticker"
DEFAULT_COUNT = 1
# Quest109：安全のため、まずは最大3枚まで。将来40枚生成へ拡張する場合も
# この定数を変更するだけで済む（呼び出し側のロジックは変更不要）。
MAX_GENERATION_COUNT = 3

GENERATION_MODE_AI = "ai"
GENERATION_MODE_FALLBACK = "fallback_pillow"
# Quest121：Gemini等の外部画像生成サービスでCEOが手動生成し、DAFへ
# アップロードした画像のバッチ（External Image Import）。
GENERATION_MODE_EXTERNAL = "external_upload"

# Quest121：画像1枚ごとの生成元（Production Source）。内部AI画像生成機能は
# 削除せず、将来API接続を戻せるよう維持する（GENERATION_MODE_AI・
# _generate_via_ai()はそのまま残す）。現時点の内部AI経路はOpenAI系
# （litellm image_generation, DAF_IMAGE_MODEL）のためSOURCE_OPENAIを使う。
SOURCE_OPENAI = "openai"
SOURCE_GEMINI = "gemini"
SOURCE_EXTERNAL_UPLOAD = "external_upload"
SOURCE_FALLBACK = "fallback"
_EXTERNAL_UPLOAD_SOURCES = (SOURCE_GEMINI, SOURCE_EXTERNAL_UPLOAD)

SOURCE_LABELS = {
    SOURCE_OPENAI: "OpenAI（内部AI画像生成）",
    SOURCE_GEMINI: "Gemini（手動）",
    SOURCE_EXTERNAL_UPLOAD: "外部アップロード（手動）",
    SOURCE_FALLBACK: "Pillow fallback（テスト用の簡易画像）",
}

# Quest121：外部アップロードも安全のため、内部AI生成と同じ上限を使う。
MAX_EXTERNAL_UPLOAD_COUNT = MAX_GENERATION_COUNT
_ALLOWED_UPLOAD_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}

# Quest120：画像生成モデルをdall-e-2固定からDAF_IMAGE_MODEL等の環境変数で
# 差し替え可能にする（コード変更なしでgpt-image-2等の高品質モデルへ
# 切り替えられるようにするため）。既定値は従来どおりdall-e-2で、
# 環境変数が未設定なら挙動は一切変わらない。
DEFAULT_IMAGE_MODEL = "dall-e-2"
DEFAULT_IMAGE_SIZE = "256x256"


def get_image_generation_config() -> dict:
    """
    DAF_IMAGE_MODEL / DAF_IMAGE_SIZE / DAF_IMAGE_QUALITY / DAF_IMAGE_BACKGROUND
    環境変数から画像生成設定を返す（読み取り専用、API接続は行わない）。
    quality・backgroundは未設定ならNone（dall-e-2等、対応していないモデル
    に不要なパラメータを送らないため）。

    戻り値: {"model": str, "size": str, "quality": str | None, "background": str | None}
    """
    import os

    return {
        "model": os.getenv("DAF_IMAGE_MODEL") or DEFAULT_IMAGE_MODEL,
        "size": os.getenv("DAF_IMAGE_SIZE") or DEFAULT_IMAGE_SIZE,
        "quality": os.getenv("DAF_IMAGE_QUALITY") or None,
        "background": os.getenv("DAF_IMAGE_BACKGROUND") or None,
    }


def get_latest_prompt(project_id: str, outputs_dir: Path | None = None) -> dict:
    """
    Quest108で保存済みの最新プロンプトを読み込む（Prompt Builder v2の
    load_prompt()をそのまま利用し、Quest108側には一切手を加えない）。

    戻り値: {"ok": bool, "prompt": str | None, "filename": str | None,
             "error": str | None}
    未生成・読み込み失敗でも例外を投げない。
    """
    try:
        from services.prompt_builder_v2 import list_prompts, load_prompt

        prompts = list_prompts(project_id, outputs_dir=outputs_dir)
        if not prompts:
            return {"ok": False, "prompt": None, "filename": None,
                     "error": "保存済みのプロンプトがありません（先に「④ プロンプト生成」を実行してください）"}

        latest = prompts[-1]
        prompt_text = load_prompt(project_id, filename=latest["filename"], outputs_dir=outputs_dir)
        if not prompt_text:
            return {"ok": False, "prompt": None, "filename": None, "error": "プロンプトの読み込みに失敗しました"}

        return {"ok": True, "prompt": prompt_text, "filename": latest["filename"], "error": None}
    except Exception as e:
        print(f"[警告] 最新プロンプトの取得に失敗しました（{project_id}）：{e}")
        return {"ok": False, "prompt": None, "filename": None, "error": str(e)}


def _generated_assets_dir(project_id: str, asset_type: str, outputs_dir: Path | None = None) -> Path:
    return (outputs_dir or _OUTPUTS_DIR) / _GENERATED_ASSETS_DIR_NAME / asset_type / project_id


def _generate_via_ai(prompt_text: str, index: int, config: dict | None = None) -> "Image.Image":
    """
    画像生成AI（現状はOPENAI_API_KEY経由のDALL-E系モデルをlitellm経由で
    呼ぶ）を使って1枚生成する。失敗時は例外をそのまま呼び出し元へ伝える
    （呼び出し側でPillowフォールバックへ切り替える判断に使うため）。

    litellm.image_generation()を使うのは、将来Google・Stability AI等の
    他プロバイダへ切り替える際も同じインターフェースで呼べるようにする
    ため（Lean AI Firstの「複数プロバイダへ接続できる独立したコンポーネント」
    という設計方針、Quest108のPrompt Builder v2と同じ考え方）。

    configはget_image_generation_config()の戻り値（省略時は取得する）。
    quality・backgroundはNoneの場合、litellmへのキーワード引数から除外する
    （dall-e-2等、対応していないモデルに不要なパラメータを送らないため）。
    """
    import base64
    import io
    from PIL import Image
    import litellm

    config = config or get_image_generation_config()
    kwargs = {"prompt": prompt_text, "model": config["model"], "n": 1, "size": config["size"]}
    if config.get("quality"):
        kwargs["quality"] = config["quality"]
    if config.get("background"):
        kwargs["background"] = config["background"]

    response = litellm.image_generation(**kwargs)
    data = response["data"][0]

    if data.get("b64_json"):
        image_bytes = base64.b64decode(data["b64_json"])
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    if data.get("url"):
        import urllib.request
        with urllib.request.urlopen(data["url"], timeout=30) as resp:
            image_bytes = resp.read()
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    raise ValueError("画像生成APIの応答に画像データがありません")


def _generate_via_fallback(prompt_text: str, index: int) -> "Image.Image":
    """
    Pillowによるダミー画像生成（既存のservices/image_generation_service.py
    render_stamp_image()をそのまま再利用、Quest98実装への変更なし）。
    promptはCharacter Bible同様、将来のAPI型Rendererのために渡すだけで、
    Pillow Rendererは決定的な描画のみ行う。
    """
    from services.image_generation_service import render_stamp_image
    return render_stamp_image(phrase="", index=index, prompt=prompt_text)


def generate_images(
    project_id: str,
    asset_type: str = DEFAULT_ASSET_TYPE,
    count: int = DEFAULT_COUNT,
    outputs_dir: Path | None = None,
) -> dict:
    """
    Quest109：最新Prompt取得 → 画像生成 → 画像保存 → metadata.json保存まで
    を1回で行う。

    countは1〜MAX_GENERATION_COUNT（既定3）に丸める。AI画像生成
    （OPENAI_API_KEY設定時）を先頭1枚で試行し、失敗した場合はバッチ全体を
    Pillowフォールバックへ切り替える（一部の画像だけAI・残りPillowという
    混在を避け、generation_modeを常にバッチ単位で一貫させるため）。

    戻り値: {"ok": bool, "project_id": str, "asset_type": str,
             "image_files": list[str], "generation_mode": str | None,
             "path": str | None, "metadata_path": str | None,
             "prompt_file": str | None, "error": str | None}
    Prompt未生成・AI呼び出し失敗・書き込み失敗のいずれでも例外を投げない。
    """
    try:
        safe_count = max(1, min(int(count or DEFAULT_COUNT), MAX_GENERATION_COUNT))

        prompt_result = get_latest_prompt(project_id, outputs_dir=outputs_dir)
        if not prompt_result.get("ok"):
            return {"ok": False, "project_id": project_id, "asset_type": asset_type,
                     "image_files": [], "generation_mode": None, "generation_model": None, "source": None,
                     "path": None, "metadata_path": None, "prompt_file": None, "error": prompt_result.get("error")}

        prompt_text = prompt_result["prompt"]
        prompt_file = prompt_result["filename"]

        target_dir = _generated_assets_dir(project_id, asset_type, outputs_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        images = []
        generation_mode = GENERATION_MODE_AI
        generation_model = None
        source = SOURCE_OPENAI
        try:
            import os
            if not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY not set")
            from services.ai_runtime_guard import require_ai_enabled
            if not require_ai_enabled("Image Generation Pipeline"):
                raise RuntimeError("AI runtime guard: AI disabled")
            config = get_image_generation_config()
            for i in range(1, safe_count + 1):
                images.append(_generate_via_ai(prompt_text, i, config=config))
            generation_model = config["model"]
        except Exception as e:
            print(f"[情報] AI画像生成を利用できないため、Pillowフォールバックで生成します（{project_id}）：{e}")
            images = []
            generation_mode = GENERATION_MODE_FALLBACK
            generation_model = None
            source = SOURCE_FALLBACK
            for i in range(1, safe_count + 1):
                images.append(_generate_via_fallback(prompt_text, i))

        image_files = []
        for i, img in enumerate(images, start=1):
            filename = f"sticker_{i:03d}.png"
            img.save(target_dir / filename, format="PNG")
            image_files.append(filename)

        metadata = {
            "project_id": project_id,
            "asset_type": asset_type,
            "prompt_file": prompt_file,
            "image_files": image_files,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "generation_mode": generation_mode,
            "generation_model": generation_model,
            "source": source,
        }
        metadata_path = target_dir / _METADATA_FILENAME
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        return {
            "ok": True, "project_id": project_id, "asset_type": asset_type,
            "image_files": image_files, "generation_mode": generation_mode,
            "generation_model": generation_model, "source": source,
            "path": str(target_dir), "metadata_path": str(metadata_path),
            "prompt_file": prompt_file, "error": None,
        }
    except Exception as e:
        print(f"[警告] 画像生成Pipelineの実行に失敗しました（{project_id}）：{e}")
        return {"ok": False, "project_id": project_id, "asset_type": asset_type,
                 "image_files": [], "generation_mode": None, "generation_model": None, "source": None,
                 "path": None, "metadata_path": None, "prompt_file": None, "error": str(e)}


def import_external_images(
    project_id: str,
    file_bytes_list: list[bytes],
    asset_type: str = DEFAULT_ASSET_TYPE,
    source: str = SOURCE_GEMINI,
    outputs_dir: Path | None = None,
) -> dict:
    """
    Quest121 — External Image Import：CEOがGemini等の外部画像生成サービスで
    手動生成したPNG/JPEG/WebPを、内部AI生成（generate_images()）と同じ
    保存先・metadata形式で取り込む。実API接続は一切行わない
    （ファイルの検証・変換・保存のみ）。

    generate_images()と同じく「1回の実行で現在の生成結果を表す」設計を
    踏襲し、sticker_001.pngから連番で上書き保存する（既存のAI生成
    画像があれば置き換わる。混在させると画像ごとにgeneration_modeが
    ばらばらになりCEOの判断を誤らせるため）。

    sourceは"gemini"（既定）または"external_upload"のみ許可し、それ以外は
    "external_upload"に丸める（Production Sourceを常に既知の値に保つため）。

    最大枚数はMAX_EXTERNAL_UPLOAD_COUNT（内部AI生成と同じ上限）に丸める。
    画像として開けないファイルはスキップする（1件も有効な画像が無い場合は
    エラーを返す）。

    戻り値: {"ok": bool, "project_id": str, "asset_type": str,
             "image_files": list[str], "generation_mode": "external_upload" | None,
             "generation_model": None, "source": str | None,
             "path": str | None, "metadata_path": str | None,
             "prompt_file": str | None, "error": str | None,
             "skipped_count": int}
    例外を投げない。
    """
    try:
        from PIL import Image
        import io

        safe_source = source if source in _EXTERNAL_UPLOAD_SOURCES else SOURCE_EXTERNAL_UPLOAD

        valid_images = []
        skipped_count = 0
        for raw_bytes in (file_bytes_list or [])[:MAX_EXTERNAL_UPLOAD_COUNT]:
            try:
                img = Image.open(io.BytesIO(raw_bytes))
                img.load()
                valid_images.append(img.convert("RGBA"))
            except Exception as e:
                skipped_count += 1
                print(f"[警告] アップロード画像を開けませんでした（{project_id}）：{e}")

        if len(file_bytes_list or []) > MAX_EXTERNAL_UPLOAD_COUNT:
            skipped_count += len(file_bytes_list) - MAX_EXTERNAL_UPLOAD_COUNT

        if not valid_images:
            return {"ok": False, "project_id": project_id, "asset_type": asset_type,
                     "image_files": [], "generation_mode": None, "generation_model": None, "source": None,
                     "path": None, "metadata_path": None, "prompt_file": None,
                     "error": "有効な画像ファイルがありません（PNG/JPEG/WebPを選択してください）",
                     "skipped_count": skipped_count}

        # プロンプトはGeminiへの参照用として記録するだけで、無くても
        # アップロードをブロックしない（先にプロンプト生成していなくても
        # 外部で生成した画像だけを取り込みたいケースがあるため）。
        prompt_result = get_latest_prompt(project_id, outputs_dir=outputs_dir)
        prompt_file = prompt_result.get("filename") if prompt_result.get("ok") else None

        target_dir = _generated_assets_dir(project_id, asset_type, outputs_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        image_files = []
        for i, img in enumerate(valid_images, start=1):
            filename = f"sticker_{i:03d}.png"
            img.save(target_dir / filename, format="PNG")
            image_files.append(filename)

        metadata = {
            "project_id": project_id,
            "asset_type": asset_type,
            "prompt_file": prompt_file,
            "image_files": image_files,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "generation_mode": GENERATION_MODE_EXTERNAL,
            "generation_model": None,
            "source": safe_source,
        }
        metadata_path = target_dir / _METADATA_FILENAME
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        return {
            "ok": True, "project_id": project_id, "asset_type": asset_type,
            "image_files": image_files, "generation_mode": GENERATION_MODE_EXTERNAL,
            "generation_model": None, "source": safe_source,
            "path": str(target_dir), "metadata_path": str(metadata_path),
            "prompt_file": prompt_file, "error": None, "skipped_count": skipped_count,
        }
    except Exception as e:
        print(f"[警告] External Image Importの実行に失敗しました（{project_id}）：{e}")
        return {"ok": False, "project_id": project_id, "asset_type": asset_type,
                 "image_files": [], "generation_mode": None, "generation_model": None, "source": None,
                 "path": None, "metadata_path": None, "prompt_file": None, "error": str(e), "skipped_count": 0}


def list_generated_images(
    project_id: str,
    asset_type: str = DEFAULT_ASSET_TYPE,
    outputs_dir: Path | None = None,
) -> dict:
    """
    保存済みのmetadata.json・画像一覧を返す（読み取り専用）。

    戻り値: {"exists": bool, "project_id": str, "asset_type": str,
             "image_files": list[str], "metadata": dict | None}
    未生成・読み込み失敗の場合はexists=Falseを返す。例外を投げない。
    """
    try:
        target_dir = _generated_assets_dir(project_id, asset_type, outputs_dir)
        metadata_path = target_dir / _METADATA_FILENAME
        if not metadata_path.exists():
            return {"exists": False, "project_id": project_id, "asset_type": asset_type,
                     "image_files": [], "metadata": None}

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        image_files = [f for f in (metadata.get("image_files") or []) if (target_dir / f).exists()]
        return {"exists": True, "project_id": project_id, "asset_type": asset_type,
                 "image_files": image_files, "metadata": metadata}
    except Exception as e:
        print(f"[警告] 生成済み画像一覧の取得に失敗しました（{project_id}）：{e}")
        return {"exists": False, "project_id": project_id, "asset_type": asset_type,
                 "image_files": [], "metadata": None}


if __name__ == "__main__":
    # Quest109: 動作確認用のCLI導線。
    #   python services/image_generation_pipeline.py <project_id> [count] [asset_type]
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
        count = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_COUNT
        asset_type = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_ASSET_TYPE
        result = generate_images(project_id, asset_type=asset_type, count=count)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("使い方: python services/image_generation_pipeline.py <project_id> [count] [asset_type]")
