"""
DAF OS Quest98 — Image Generation Service

将来、画像生成AI（OpenAI・Google・FLUX・Stability AI等）へ切り替えられる
設計の入口。services/asset_generator_service.py はこのモジュールだけを
呼び出し、実際にどのRenderer（services/renderers/配下）が絵を描いている
かを知らない（責務分離）。

責務：
- 使用する画像生成エンジン（Renderer）の切替（config.get_image_renderer()、
  既定値 "pillow"。IMAGE_RENDERER環境変数で変更可能）
- Character Bible・Prompt（services/prompt_builder_service.py が組み立てた
  もの）を受け取り、Rendererへそのまま引き渡す
- Rendererへの処理委譲（render_stamp_image / render_icon_image）

Quest98では画像生成APIはまだ導入しない。Renderer実装はPillowのみ
（services/renderers/pillow_renderer.py）。Character Bible・Promptは
将来のAPI型Rendererのために受け取れるようにしてあるだけで、Pillow
Rendererはこれらの内容を使わず、Quest90〜97までと同じ決定的な描画を行う。

CLI:
  python services/image_generation_service.py
    → 現在のRenderer設定を表示する
"""

import importlib
import sys
from pathlib import Path

# `python services/image_generation_service.py` のように直接実行された場合、
# リポジトリルートが sys.path に無く `services.*` を解決できないため追加する
# （services/asset_generator_service.py と同じ対策）。
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Quest98時点で実装済みのRendererモジュール一覧。
# openai / google / flux / stability は将来追加予定（Quest98では未実装）。
_RENDERER_MODULES = {
    "pillow": "services.renderers.pillow_renderer",
    # "openai": "services.renderers.openai_renderer",
    # "google": "services.renderers.google_renderer",
    # "flux": "services.renderers.flux_renderer",
    # "stability": "services.renderers.stability_renderer",
}

_DEFAULT_RENDERER_ID = "pillow"


def get_active_renderer_id() -> str:
    """
    現在使用するRendererの識別子を返す。config.get_image_renderer()
    （IMAGE_RENDERER環境変数、既定値"pillow"）を優先し、configの読み込みに
    失敗した場合のみ既定値へフォールバックする（例外を投げない）。
    """
    try:
        from config import get_image_renderer
        return get_image_renderer()
    except Exception:
        return _DEFAULT_RENDERER_ID


def _load_renderer(renderer_id: str | None = None):
    """指定（または現在設定されている）Rendererモジュールをimportして返す。"""
    rid = (renderer_id or get_active_renderer_id() or _DEFAULT_RENDERER_ID).strip().lower()
    module_path = _RENDERER_MODULES.get(rid, _RENDERER_MODULES[_DEFAULT_RENDERER_ID])
    return importlib.import_module(module_path)


def render_stamp_image(
    phrase: str,
    index: int,
    character_bible: dict | None = None,
    prompt: str | None = None,
    renderer_id: str | None = None,
) -> "Image.Image":
    """
    1枚のスタンプ画像をRendererへ委譲して生成する。

    character_bible・promptは将来のAPI型Renderer（OpenAI等）向けの引数で、
    Pillow Rendererは現状これらを使わずQuest95までと同じ決定的な描画を行う
    （Character Bible・Promptを受け取れる形にだけしてあるという段階）。
    """
    renderer = _load_renderer(renderer_id)
    return renderer.render_stamp(phrase, index)


def render_icon_image(
    size: tuple[int, int],
    character_bible: dict | None = None,
    renderer_id: str | None = None,
) -> "Image.Image":
    """main.png / tab.png相当のアイコン画像をRendererへ委譲して生成する。"""
    renderer = _load_renderer(renderer_id)
    return renderer.render_icon(size)


def get_renderer_info(renderer_id: str | None = None) -> dict:
    """
    Dashboard表示向けに、現在（または指定）のRenderer情報を返す。
    戻り値: {"id": str, "display_name": str, "available": list[str]}
    Rendererモジュールの読み込みに失敗した場合もidをdisplay_nameとして
    フォールバックし、例外を投げない。
    """
    rid = (renderer_id or get_active_renderer_id() or _DEFAULT_RENDERER_ID).strip().lower()
    try:
        module = _load_renderer(rid)
        display_name = getattr(module, "RENDERER_DISPLAY_NAME", rid)
    except Exception:
        display_name = rid
    return {
        "id": rid,
        "display_name": display_name,
        "available": sorted(_RENDERER_MODULES.keys()),
    }


if __name__ == "__main__":
    # Quest98: 現在のRenderer設定を確認するためのCLI導線。
    #   python services/image_generation_service.py
    info = get_renderer_info()
    print(f"[Image Generation Service] 現在のRenderer: {info['display_name']}（id={info['id']}）")
    print(f"利用可能なRenderer一覧: {', '.join(info['available'])}")
