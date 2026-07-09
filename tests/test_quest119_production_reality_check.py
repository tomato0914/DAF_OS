"""
Quest119 — Production Reality Checkの動作確認用ミニテスト。
services/production_orchestrator.py（画像生成方式の可視化・commercial_ready
フラグ・AI画像生成が実際に使える状態かどうかの判定）と、
dashboard_web/app.pyの GET /api/production/image-generation-status、
および dashboard_web/templates/index.html側のCEO向け警告表示・導線を
対象とする。

AI画像生成が実際に使えるかどうかの判定基準は、Quest118のAI Runtime Guard
（services/ai_runtime_guard.py）に統一されている。以下の3条件をすべて
満たす場合のみAI画像生成が使える：
  1. DAF_RUNTIME_MODE=production
  2. DAF_AI_ENABLED=true
  3. OPENAI_API_KEY環境変数が設定されている
（Quest118以前はOPENAI_API_KEYの有無だけで判定していたが、開発・テスト中に
APIキーさえ設定されていればAI呼び出し可能と誤認識される問題があったため、
Quest119でAI Runtime Guard基準に統一した）。

実際のAI呼び出しへは接続しない（テスト中はOPENAI_API_KEY/OPENROUTER_API_KEY
にダミー値を設定するケースを含め、litellm等への実接続は一切発生しない）。
既存Production Pipeline本体（prompt_builder_v2 / image_generation_pipeline /
ai_review_engine / export_engine）のロジックは変更していない。

実行:
  python -m unittest tests/test_quest119_production_reality_check.py -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.production_orchestrator import (
    run_production,
    load_production_report,
    get_image_generation_capability,
    STATUS_SUCCESS,
)


def _clean_env():
    """DAF_AI_ENABLED・DAF_RUNTIME_MODE・OPENAI_API_KEYを含まないベースの環境変数コピーを返す。"""
    env = dict(os.environ)
    env.pop("DAF_AI_ENABLED", None)
    env.pop("DAF_RUNTIME_MODE", None)
    env.pop("OPENAI_API_KEY", None)
    return env


class ImageGenerationCapabilityTest(unittest.TestCase):
    """get_image_generation_capability()がAI Runtime Guard基準
    （DAF_RUNTIME_MODE=production かつ DAF_AI_ENABLED=true かつ
    OPENAI_API_KEY設定済み）で判定することを確認する。"""

    def test_unconfigured_when_api_key_missing(self):
        env = _clean_env()
        env["DAF_RUNTIME_MODE"] = "production"
        env["DAF_AI_ENABLED"] = "true"
        with patch.dict(os.environ, env, clear=True):
            capability = get_image_generation_capability()
        self.assertFalse(capability["ai_configured"])
        self.assertIsNotNone(capability["fallback_reason"])
        self.assertEqual(capability["model"], "dall-e-2")

    def test_unconfigured_when_api_key_present_but_guard_off(self):
        # Quest119の核心：APIキーがあってもAI Runtime GuardがOFF
        # （development等）ならai_configuredにならない。
        env = _clean_env()
        env["OPENAI_API_KEY"] = "sk-test-dummy"
        env["DAF_RUNTIME_MODE"] = "development"
        env["DAF_AI_ENABLED"] = "false"
        with patch.dict(os.environ, env, clear=True):
            capability = get_image_generation_capability()
        self.assertFalse(capability["ai_configured"])
        self.assertIn("AI Runtime Guard", capability["fallback_reason"])

    def test_unconfigured_when_guard_on_but_test_mode(self):
        env = _clean_env()
        env["OPENAI_API_KEY"] = "sk-test-dummy"
        env["DAF_AI_ENABLED"] = "true"
        env["DAF_RUNTIME_MODE"] = "test"
        with patch.dict(os.environ, env, clear=True):
            capability = get_image_generation_capability()
        self.assertFalse(capability["ai_configured"])

    def test_configured_when_all_three_conditions_met(self):
        env = _clean_env()
        env["OPENAI_API_KEY"] = "sk-test-dummy"
        env["DAF_RUNTIME_MODE"] = "production"
        env["DAF_AI_ENABLED"] = "true"
        with patch.dict(os.environ, env, clear=True):
            capability = get_image_generation_capability()
        self.assertTrue(capability["ai_configured"])
        self.assertIsNone(capability["fallback_reason"])


class ProductionRealityCheckTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name) / "outputs"
        self.projects_dir = Path(self._tmp.name) / "projects"
        # このテストファイルはAI呼び出しへ接続しない前提のため、
        # AI Runtime Guardが確実にOFFの状態（development・未設定）で検証する。
        self._env_patch = patch.dict(os.environ, _clean_env(), clear=True)
        self._env_patch.start()

    def tearDown(self):
        self._env_patch.stop()
        self._tmp.cleanup()

    def test_image_generation_mode_is_fallback_pillow_without_api_key(self):
        result = run_production("004", count=2, outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], STATUS_SUCCESS)
        self.assertEqual(result["image_generation_mode"], "fallback_pillow")

    def test_commercial_ready_is_false_for_fallback_pillow(self):
        result = run_production("004", count=2, outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertFalse(result["commercial_ready"])
        self.assertIn("Pillow fallback", result["commercial_ready_reason"])

    def test_next_action_prompts_ai_setup_check_for_fallback(self):
        result = run_production("004", count=2, outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertIn("AI画像生成API設定", result["next_action"])

    def test_production_report_records_image_generation_mode(self):
        run_production("004", count=2, outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        report = load_production_report("004", outputs_dir=self.outputs_dir)
        self.assertEqual(report["image_generation_mode"], "fallback_pillow")
        self.assertFalse(report["commercial_ready"])
        self.assertIn("commercial_ready_reason", report)

    def test_commercial_ready_true_when_ai_mode(self):
        # 実際のAI呼び出しへは接続しない。実画像（Pillowフォールバック経路）を
        # 生成させたうえで、Production Orchestratorのcommercial_ready判定
        # だけがgeneration_mode="ai"の場合にTrueになることを検証する
        # （後続のAIレビュー・Exportが実ファイルを参照できるようにするため、
        # generate_images自体は実装をそのまま呼び、戻り値のgeneration_mode
        # だけを差し替える）。
        from services.image_generation_pipeline import generate_images as real_generate_images

        def _generate_images_reporting_ai(*args, **kwargs):
            result = real_generate_images(*args, **kwargs)
            result["generation_mode"] = "ai"
            return result

        with patch(
            "services.image_generation_pipeline.generate_images",
            side_effect=_generate_images_reporting_ai,
        ):
            result = run_production("004", count=1, outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertTrue(result["ok"])
        self.assertTrue(result["commercial_ready"])
        self.assertEqual(result["image_generation_mode"], "ai")
        self.assertEqual(result["next_action"], "LINE Creators Marketへ提出してください")

    def test_line_sticker_production_flow_still_works(self):
        # 既存のQuest113〜115の制作フロー自体（プロンプト→画像→確認→Export）
        # が壊れていないことを確認する。
        result = run_production("004", count=2, outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertEqual(
            result["completed_steps"],
            ["prompt", "image_generation", "ai_review", "export"],
        )
        self.assertIsNotNone(result["zip_filename"])


class ImageGenerationStatusApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_image_generation_status_endpoint_returns_expected_shape(self):
        resp = self.client.get("/api/production/image-generation-status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("ai_configured", data)
        self.assertIn("model", data)
        self.assertIn("fallback_reason", data)


class DashboardCeoWarningWordingTest(unittest.TestCase):
    """dashboard_web/templates/index.htmlにPillow fallback向けのCEO警告・
    導線（画像生成方式表示・生成画像を見る・結果を見る）が実装されている
    ことを確認する（文字列検証のみ）。"""

    @classmethod
    def setUpClass(cls):
        template_path = Path(__file__).parent.parent / "dashboard_web" / "templates" / "index.html"
        cls.template_text = template_path.read_text(encoding="utf-8")

    def test_image_generation_mode_is_displayed(self):
        self.assertIn("画像生成方式", self.template_text)

    def test_non_commercial_warning_is_present(self):
        self.assertIn("販売用画像ではありません", self.template_text)

    def test_view_generated_images_action_is_present(self):
        self.assertIn("🎨 生成画像を見る", self.template_text)

    def test_view_result_without_rerun_action_is_present(self):
        self.assertIn("🔍 結果を見る", self.template_text)

    def test_ai_generation_status_banner_container_is_present(self):
        self.assertIn('id="imageGenerationStatusBanner"', self.template_text)


if __name__ == "__main__":
    unittest.main()
