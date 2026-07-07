"""
DAF OS Quest98 — 設定の一元化（画像生成エンジン切替の第一弾）

将来、画像生成をPillow以外（OpenAI / Google / FLUX / Stability AI 等）へ
切り替えられるようにするため、「どのRendererを使うか」を.env経由で
差し替えられる構造にする。Quest98時点ではpillowのみ対応。

.env（またはOSの環境変数）に以下を設定すると切り替わる：
  IMAGE_RENDERER=pillow

未設定の場合は既定値 "pillow" を使う。
"""

import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_IMAGE_RENDERER = "pillow"

# Quest98時点で実装済みのRenderer一覧（services/renderers/配下のモジュール名と対応）。
# openai / google / flux / stability は将来追加予定（Quest98では未実装）。
AVAILABLE_IMAGE_RENDERERS = ("pillow",)


def get_image_renderer() -> str:
    """
    現在使用する画像生成Rendererの識別子を返す（既定値: "pillow"）。
    IMAGE_RENDERER環境変数が実装済みRenderer一覧に無い値の場合も、
    例外を投げずデフォルトへフォールバックする。
    """
    value = (os.getenv("IMAGE_RENDERER") or DEFAULT_IMAGE_RENDERER).strip().lower()
    if value not in AVAILABLE_IMAGE_RENDERERS:
        return DEFAULT_IMAGE_RENDERER
    return value
