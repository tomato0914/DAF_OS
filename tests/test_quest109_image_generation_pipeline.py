"""
Quest109 — Image Generation Pipelineの動作確認用ミニテスト。
services/image_generation_pipeline.py（最新Prompt取得・画像生成・保存・
metadata.json保存・一覧取得）と、dashboard_web/app.py の
/api/projects/generate-image・/generated-images の入力バリデーションを
対象とする。

AI画像生成API（OPENAI_API_KEY）は本テストでは未設定のまま実行し、
Pillowフォールバック経路のみを検証する（実際のAI画像生成APIへは接続
しない。ネットワーク非依存・再現性を優先するため）。

実行:
  python -m unittest tests/test_quest109_image_generation_pipeline.py -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.prompt_builder_v2 import build_prompt
from services.image_generation_pipeline import (
    get_latest_prompt,
    generate_images,
    list_generated_images,
    MAX_GENERATION_COUNT,
    GENERATION_MODE_FALLBACK,
)


class GetLatestPromptTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_returns_error_when_no_prompt_saved(self):
        result = get_latest_prompt("no_such_project", outputs_dir=self.outputs_dir)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["prompt"])
        self.assertIsNotNone(result["error"])

    def test_loads_latest_saved_prompt(self):
        build_prompt("001", save=True, outputs_dir=self.outputs_dir)
        build_prompt("001", save=True, outputs_dir=self.outputs_dir)  # prompt_002.txt

        result = get_latest_prompt("001", outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["filename"], "prompt_002.txt")
        self.assertTrue(result["prompt"].strip())


class GenerateImagesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)
        self._had_key = os.environ.pop("OPENAI_API_KEY", None)
        # プロンプトを1件保存しておく（Prompt Builder v2は既存Project 004を
        # 参照する設計のため、実プロジェクトIDを使う）
        build_prompt("004", save=True, outputs_dir=self.outputs_dir)

    def tearDown(self):
        self._tmp.cleanup()
        if self._had_key is not None:
            os.environ["OPENAI_API_KEY"] = self._had_key

    def test_generate_images_can_be_called(self):
        result = generate_images("004", count=1, outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])

    def test_generate_images_saves_files_and_uses_fallback_without_api_key(self):
        result = generate_images("004", count=2, outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["generation_mode"], GENERATION_MODE_FALLBACK)
        self.assertEqual(result["image_files"], ["sticker_001.png", "sticker_002.png"])

        target_dir = Path(result["path"])
        for filename in result["image_files"]:
            self.assertTrue((target_dir / filename).exists())
            self.assertGreater((target_dir / filename).stat().st_size, 0)

    def test_generate_images_saves_metadata_json_with_required_fields(self):
        result = generate_images("004", count=1, outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])

        metadata_path = Path(result["metadata_path"])
        self.assertTrue(metadata_path.exists())

        import json
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        for key in ("project_id", "asset_type", "prompt_file", "image_files", "generated_at", "generation_mode"):
            self.assertIn(key, metadata)
        self.assertEqual(metadata["project_id"], "004")
        self.assertEqual(metadata["generation_mode"], GENERATION_MODE_FALLBACK)

    def test_count_is_capped_at_max_generation_count(self):
        result = generate_images("004", count=999, outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["image_files"]), MAX_GENERATION_COUNT)

    def test_count_below_one_defaults_to_one(self):
        result = generate_images("004", count=0, outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["image_files"]), 1)

    def test_returns_error_when_no_prompt_exists(self):
        result = generate_images("no_prompt_project", count=1, outputs_dir=self.outputs_dir)
        self.assertFalse(result["ok"])
        self.assertEqual(result["image_files"], [])
        self.assertIsNotNone(result["error"])

    def test_never_raises_for_unexpected_project_id(self):
        # 例外を投げずに安全なdictを返すことを確認する
        result = generate_images("../../etc", count=1, outputs_dir=self.outputs_dir)
        self.assertIsInstance(result, dict)
        self.assertIn("ok", result)


class ListGeneratedImagesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)
        os.environ.pop("OPENAI_API_KEY", None)

    def tearDown(self):
        self._tmp.cleanup()

    def test_returns_exists_false_when_nothing_generated(self):
        result = list_generated_images("004", outputs_dir=self.outputs_dir)
        self.assertFalse(result["exists"])
        self.assertEqual(result["image_files"], [])

    def test_returns_generated_images_after_generation(self):
        build_prompt("004", save=True, outputs_dir=self.outputs_dir)
        generate_images("004", count=3, outputs_dir=self.outputs_dir)

        result = list_generated_images("004", outputs_dir=self.outputs_dir)
        self.assertTrue(result["exists"])
        self.assertEqual(len(result["image_files"]), 3)
        self.assertIsNotNone(result["metadata"])


class ImageGenerationApiValidationTest(unittest.TestCase):
    """
    Flask APIレベルのバリデーション、およびDashboard APIが画像一覧を
    返せることを確認する（実データを書き換えないケースに限定）。
    """

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_generate_image_rejects_invalid_project_id(self):
        resp = self.client.post("/api/projects/generate-image", json={"id": "../../etc"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_generate_image_returns_error_for_project_without_prompt(self):
        resp = self.client.post("/api/projects/generate-image", json={"id": "definitely_no_prompt_project"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_generated_images_endpoint_returns_dict_for_missing_project(self):
        resp = self.client.get("/api/projects/definitely_does_not_exist/generated-images")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()["exists"])

    def test_generated_images_endpoint_rejects_invalid_project_id(self):
        resp = self.client.get("/api/projects/../../etc/generated-images")
        self.assertIn(resp.status_code, (400, 404))

    def test_image_serving_route_rejects_non_png(self):
        resp = self.client.get("/api/generated-assets/image/line_sticker/001/metadata.json")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
