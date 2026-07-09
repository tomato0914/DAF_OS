"""
Quest120 — 画像生成モデル設定可能化の動作確認用ミニテスト。
services/image_generation_pipeline.py（DAF_IMAGE_MODEL等の環境変数による
モデル設定）、services/production_orchestrator.py（get_image_generation_
capability()の拡張フィールド）、dashboard_web/app.pyのAPIレスポンス形状、
dashboard_web/templates/index.htmlのCEO向け表示を対象とする。

このテストファイルはOpenAI / OpenRouter / LiteLLMへの実接続を一切行わない。
litellm.image_generation()はunittest.mock.patchで完全に差し替え、実際の
ネットワーク呼び出しが発生しないことを明示的に検証する。AI Runtime Guard
（DAF_RUNTIME_MODE=production かつ DAF_AI_ENABLED=true）もテスト中は
常にOFFの前提で検証する（既定の安全側動作を確認するため）。

実行:
  python -m unittest tests/test_quest120_configurable_image_model.py -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.image_generation_pipeline import (
    get_image_generation_config,
    generate_images,
    _generate_via_ai,
    DEFAULT_IMAGE_MODEL,
    DEFAULT_IMAGE_SIZE,
    GENERATION_MODE_FALLBACK,
)
from services.prompt_builder_v2 import build_prompt


def _clean_env():
    """DAF_AI_ENABLED・DAF_RUNTIME_MODE・OPENAI_API_KEY・DAF_IMAGE_*を含まないベースの環境変数コピーを返す。"""
    env = dict(os.environ)
    for key in (
        "DAF_AI_ENABLED", "DAF_RUNTIME_MODE", "OPENAI_API_KEY",
        "DAF_IMAGE_MODEL", "DAF_IMAGE_SIZE", "DAF_IMAGE_QUALITY", "DAF_IMAGE_BACKGROUND",
    ):
        env.pop(key, None)
    return env


class ImageGenerationConfigTest(unittest.TestCase):
    """get_image_generation_config()が環境変数未設定時は既定値（従来どおり
    dall-e-2・256x256）を返し、設定時はそれを反映することを確認する。"""

    def test_defaults_when_env_unset(self):
        with patch.dict(os.environ, _clean_env(), clear=True):
            config = get_image_generation_config()
        self.assertEqual(config["model"], DEFAULT_IMAGE_MODEL)
        self.assertEqual(config["model"], "dall-e-2")
        self.assertEqual(config["size"], DEFAULT_IMAGE_SIZE)
        self.assertIsNone(config["quality"])
        self.assertIsNone(config["background"])

    def test_reflects_env_overrides(self):
        env = _clean_env()
        env["DAF_IMAGE_MODEL"] = "gpt-image-2"
        env["DAF_IMAGE_SIZE"] = "1024x1024"
        env["DAF_IMAGE_QUALITY"] = "high"
        env["DAF_IMAGE_BACKGROUND"] = "transparent"
        with patch.dict(os.environ, env, clear=True):
            config = get_image_generation_config()
        self.assertEqual(config["model"], "gpt-image-2")
        self.assertEqual(config["size"], "1024x1024")
        self.assertEqual(config["quality"], "high")
        self.assertEqual(config["background"], "transparent")


class GenerateViaAiKwargsTest(unittest.TestCase):
    """_generate_via_ai()がlitellm.image_generation()へ渡すkwargsを検証する。
    quality・backgroundは未設定時にkwargsから除外され（dall-e-2等の
    非対応モデルへ余計なパラメータを送らないため）、設定時のみ含まれる
    ことを確認する。litellmは完全にモック化し、実接続は発生しない。
    """

    def _fake_response(self):
        return {"data": [{"b64_json": self._tiny_png_b64()}]}

    @staticmethod
    def _tiny_png_b64():
        import base64
        import io
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGBA", (2, 2)).save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

    def test_quality_and_background_omitted_when_unset(self):
        config = {"model": "dall-e-2", "size": "256x256", "quality": None, "background": None}
        mock_litellm = MagicMock()
        mock_litellm.image_generation.return_value = self._fake_response()
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            _generate_via_ai("a cute cat sticker", 1, config=config)
        mock_litellm.image_generation.assert_called_once_with(
            prompt="a cute cat sticker", model="dall-e-2", n=1, size="256x256",
        )

    def test_quality_and_background_included_when_set(self):
        config = {"model": "gpt-image-2", "size": "1024x1024", "quality": "high", "background": "transparent"}
        mock_litellm = MagicMock()
        mock_litellm.image_generation.return_value = self._fake_response()
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            _generate_via_ai("a cute cat sticker", 1, config=config)
        mock_litellm.image_generation.assert_called_once_with(
            prompt="a cute cat sticker", model="gpt-image-2", n=1, size="1024x1024",
            quality="high", background="transparent",
        )

    def test_no_real_network_module_is_touched(self):
        # litellmを完全にモック化しているため、実際のimport済みlitellm
        # （インストール済みの本物）が呼ばれていないことを確認する。
        config = {"model": "dall-e-2", "size": "256x256", "quality": None, "background": None}
        mock_litellm = MagicMock()
        mock_litellm.image_generation.return_value = self._fake_response()
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            _generate_via_ai("prompt", 1, config=config)
        self.assertEqual(mock_litellm.image_generation.call_count, 1)


class GenerateImagesModelFieldTest(unittest.TestCase):
    """generate_images()の戻り値・metadata.jsonにgeneration_modelが記録され、
    AI Runtime GuardがOFF（既定）の間はPillow fallbackとなりmodelはNoneに
    なることを確認する（実API接続なし）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)
        self._env_patch = patch.dict(os.environ, _clean_env(), clear=True)
        self._env_patch.start()
        build_prompt("004", save=True, outputs_dir=self.outputs_dir)

    def tearDown(self):
        self._env_patch.stop()
        self._tmp.cleanup()

    def test_generation_model_is_none_for_fallback(self):
        result = generate_images("004", count=1, outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["generation_mode"], GENERATION_MODE_FALLBACK)
        self.assertIsNone(result["generation_model"])

    def test_metadata_json_includes_generation_model_key(self):
        import json
        result = generate_images("004", count=1, outputs_dir=self.outputs_dir)
        metadata = json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
        self.assertIn("generation_model", metadata)
        self.assertIsNone(metadata["generation_model"])

    def test_ai_runtime_guard_off_never_imports_litellm_for_real(self):
        # AI Runtime GuardがOFFの間は、OPENAI_API_KEYを設定してもAI経路へ
        # 進まないため、litellmは一切呼ばれない（Quest118の既存保証の再確認）。
        env = _clean_env()
        env["OPENAI_API_KEY"] = "sk-test-dummy"
        with patch.dict(os.environ, env, clear=True):
            with patch("services.image_generation_pipeline._generate_via_ai") as mock_ai:
                result = generate_images("004", count=1, outputs_dir=self.outputs_dir)
        mock_ai.assert_not_called()
        self.assertEqual(result["generation_mode"], GENERATION_MODE_FALLBACK)


class ImageGenerationCapabilityFieldsTest(unittest.TestCase):
    """production_orchestrator.get_image_generation_capability()がQuest120で
    追加したmodel/size/quality/background/runtime_mode/ai_enabledを
    正しく返すことを確認する（実API接続なし）。"""

    def test_unconfigured_response_includes_new_fields(self):
        from services.production_orchestrator import get_image_generation_capability

        with patch.dict(os.environ, _clean_env(), clear=True):
            capability = get_image_generation_capability()
        self.assertFalse(capability["ai_configured"])
        self.assertEqual(capability["model"], "dall-e-2")
        self.assertEqual(capability["size"], "256x256")
        self.assertIsNone(capability["quality"])
        self.assertIsNone(capability["background"])
        self.assertEqual(capability["runtime_mode"], "development")
        self.assertFalse(capability["ai_enabled"])
        self.assertIsNotNone(capability["fallback_reason"])

    def test_custom_model_env_is_reflected_even_when_unconfigured(self):
        from services.production_orchestrator import get_image_generation_capability

        env = _clean_env()
        env["DAF_IMAGE_MODEL"] = "gpt-image-2"
        with patch.dict(os.environ, env, clear=True):
            capability = get_image_generation_capability()
        self.assertEqual(capability["model"], "gpt-image-2")
        self.assertFalse(capability["ai_configured"])

    def test_configured_response_includes_new_fields(self):
        from services.production_orchestrator import get_image_generation_capability

        env = _clean_env()
        env["OPENAI_API_KEY"] = "sk-test-dummy"
        env["DAF_RUNTIME_MODE"] = "production"
        env["DAF_AI_ENABLED"] = "true"
        env["DAF_IMAGE_MODEL"] = "gpt-image-2"
        env["DAF_IMAGE_QUALITY"] = "high"
        with patch.dict(os.environ, env, clear=True):
            capability = get_image_generation_capability()
        self.assertTrue(capability["ai_configured"])
        self.assertEqual(capability["model"], "gpt-image-2")
        self.assertEqual(capability["quality"], "high")
        self.assertTrue(capability["ai_enabled"])
        self.assertEqual(capability["runtime_mode"], "production")
        self.assertIsNone(capability["fallback_reason"])


class ImageGenerationStatusApiFieldsTest(unittest.TestCase):
    """GET /api/production/image-generation-status のレスポンスに
    Quest120の新フィールドが含まれることを確認する。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_response_includes_runtime_and_size_fields(self):
        resp = self.client.get("/api/production/image-generation-status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        for key in ("ai_configured", "model", "size", "quality", "background", "runtime_mode", "ai_enabled", "fallback_reason"):
            self.assertIn(key, data)


class DashboardCeoDisplayTest(unittest.TestCase):
    """dashboard_web/templates/index.htmlに、Quest120で追加したCEO向け
    表示（使用モデル・AI Runtime状態・fallback理由の表示ロジック）が
    実装されていることを確認する（文字列検証のみ）。"""

    @classmethod
    def setUpClass(cls):
        template_path = Path(__file__).parent.parent / "dashboard_web" / "templates" / "index.html"
        cls.template_text = template_path.read_text(encoding="utf-8")

    def test_ai_runtime_label_is_displayed_in_banner(self):
        self.assertIn("AI Runtime:", self.template_text)

    def test_used_model_line_is_displayed_in_result(self):
        self.assertIn("使用モデル", self.template_text)

    def test_commercial_ready_reason_is_used_in_warning(self):
        self.assertIn("data.commercial_ready_reason", self.template_text)


if __name__ == "__main__":
    unittest.main()
