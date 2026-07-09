"""
Quest118 — AI Runtime Guard / APIコスト防止の動作確認用ミニテスト。
services/ai_runtime_guard.py（環境変数によるAI ON/OFF判定）と、
既存のAI呼び出し箇所（AI Review Engine・Image Generation Pipeline）が
Guard OFF時に安全にfallbackへ切り替わること、
dashboard_web/app.pyの GET /api/ai-runtime/status を対象とする。

重要：本テストファイルはOpenRouter / OpenAI / LiteLLMへ絶対に接続しない。
OPENROUTER_API_KEY・OPENAI_API_KEYをダミー値で設定した状態でも、
litellm.completion() / litellm.image_generation() が一度も呼ばれないことを
モックで直接検証する（Guardが本当にAPI呼び出し自体をブロックしている
ことの証明）。

実行:
  python -m unittest tests/test_ai_runtime_guard.py -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ai_runtime_guard import (
    is_ai_enabled,
    get_runtime_mode,
    require_ai_enabled,
    get_ai_status,
)


def _clean_env():
    """DAF_AI_ENABLED・DAF_RUNTIME_MODEを含まないベースの環境変数コピーを返す。"""
    env = dict(os.environ)
    env.pop("DAF_AI_ENABLED", None)
    env.pop("DAF_RUNTIME_MODE", None)
    return env


class AiRuntimeGuardDefaultTest(unittest.TestCase):
    def test_ai_is_off_when_env_vars_unset(self):
        with patch.dict(os.environ, _clean_env(), clear=True):
            self.assertFalse(is_ai_enabled())
            self.assertEqual(get_runtime_mode(), "development")

    def test_ai_is_off_when_daf_ai_enabled_false(self):
        env = _clean_env()
        env["DAF_AI_ENABLED"] = "false"
        env["DAF_RUNTIME_MODE"] = "production"
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(is_ai_enabled())

    def test_ai_is_off_when_true_but_test_mode(self):
        env = _clean_env()
        env["DAF_AI_ENABLED"] = "true"
        env["DAF_RUNTIME_MODE"] = "test"
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(is_ai_enabled())
            self.assertEqual(get_runtime_mode(), "test")

    def test_ai_is_off_in_development_mode_even_if_enabled_true(self):
        env = _clean_env()
        env["DAF_AI_ENABLED"] = "true"
        env["DAF_RUNTIME_MODE"] = "development"
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(is_ai_enabled())

    def test_ai_is_on_only_for_production_and_enabled_true(self):
        env = _clean_env()
        env["DAF_AI_ENABLED"] = "true"
        env["DAF_RUNTIME_MODE"] = "production"
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(is_ai_enabled())
            self.assertEqual(get_runtime_mode(), "production")

    def test_unknown_runtime_mode_falls_back_to_development(self):
        env = _clean_env()
        env["DAF_RUNTIME_MODE"] = "staging"
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(get_runtime_mode(), "development")
            self.assertFalse(is_ai_enabled())

    def test_require_ai_enabled_returns_false_when_off(self):
        with patch.dict(os.environ, _clean_env(), clear=True):
            self.assertFalse(require_ai_enabled("test feature"))

    def test_require_ai_enabled_returns_true_when_on(self):
        env = _clean_env()
        env["DAF_AI_ENABLED"] = "true"
        env["DAF_RUNTIME_MODE"] = "production"
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(require_ai_enabled("test feature"))

    def test_get_ai_status_shape_when_off(self):
        with patch.dict(os.environ, _clean_env(), clear=True):
            status = get_ai_status()
        self.assertFalse(status["ai_enabled"])
        self.assertEqual(status["runtime_mode"], "development")
        self.assertTrue(status["api_calls_blocked"])
        self.assertIn("reason", status)
        self.assertIn("provider", status)

    def test_get_ai_status_shape_when_on(self):
        env = _clean_env()
        env["DAF_AI_ENABLED"] = "true"
        env["DAF_RUNTIME_MODE"] = "production"
        with patch.dict(os.environ, env, clear=True):
            status = get_ai_status()
        self.assertTrue(status["ai_enabled"])
        self.assertFalse(status["api_calls_blocked"])


class AiReviewEngineFallbackTest(unittest.TestCase):
    """AI Runtime GuardがOFFの間は、OPENROUTER_API_KEYが設定されていても
    litellm.completion()が一度も呼ばれず、fallback_rule_reviewへ
    安全に切り替わることを確認する。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_ai_review_falls_back_to_rule_review_when_ai_off(self):
        from services.prompt_builder_v2 import build_prompt
        from services.image_generation_pipeline import generate_images
        from services.ai_review_engine import review_images

        env = _clean_env()
        env["OPENROUTER_API_KEY"] = "sk-dummy-should-never-be-used"
        env["DAF_AI_ENABLED"] = "false"
        env["DAF_RUNTIME_MODE"] = "development"

        with patch.dict(os.environ, env, clear=True):
            build_prompt("004", save=True, outputs_dir=self.outputs_dir)
            generate_images("004", count=1, outputs_dir=self.outputs_dir)

            with patch("litellm.completion", MagicMock(side_effect=AssertionError(
                "litellm.completion must not be called while AI Runtime Guard is OFF"
            ))) as mocked_completion:
                result = review_images("004", manual_request=True, outputs_dir=self.outputs_dir)

            mocked_completion.assert_not_called()

        self.assertTrue(result["ok"])
        self.assertEqual(result["report"]["review_mode"], "fallback_rule_review")


class ImageGenerationFallbackTest(unittest.TestCase):
    """AI Runtime GuardがOFFの間は、OPENAI_API_KEYが設定されていても
    litellm.image_generation()が一度も呼ばれず、fallback_pillowへ
    安全に切り替わることを確認する。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_image_generation_falls_back_to_pillow_when_ai_off(self):
        from services.prompt_builder_v2 import build_prompt
        from services.image_generation_pipeline import generate_images

        env = _clean_env()
        env["OPENAI_API_KEY"] = "sk-dummy-should-never-be-used"
        env["DAF_AI_ENABLED"] = "false"
        env["DAF_RUNTIME_MODE"] = "development"

        with patch.dict(os.environ, env, clear=True):
            build_prompt("004", save=True, outputs_dir=self.outputs_dir)

            with patch("litellm.image_generation", MagicMock(side_effect=AssertionError(
                "litellm.image_generation must not be called while AI Runtime Guard is OFF"
            ))) as mocked_image_generation:
                result = generate_images("004", count=1, outputs_dir=self.outputs_dir)

            mocked_image_generation.assert_not_called()

        self.assertTrue(result["ok"])
        self.assertEqual(result["generation_mode"], "fallback_pillow")


class AiRuntimeStatusApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_ai_runtime_status_endpoint_returns_expected_shape(self):
        resp = self.client.get("/api/ai-runtime/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("ai_enabled", data)
        self.assertIn("runtime_mode", data)
        self.assertIn("reason", data)
        self.assertIn("provider", data)
        self.assertIn("api_calls_blocked", data)

    def test_ai_runtime_status_endpoint_defaults_to_off(self):
        # このテストプロセス自体がDAF_AI_ENABLED=trueで起動されていない前提
        # （テスト全体の方針：AI APIを絶対に呼ばない）。
        env = _clean_env()
        with patch.dict(os.environ, env, clear=True):
            resp = self.client.get("/api/ai-runtime/status")
        data = resp.get_json()
        self.assertFalse(data["ai_enabled"])
        self.assertTrue(data["api_calls_blocked"])


if __name__ == "__main__":
    unittest.main()
