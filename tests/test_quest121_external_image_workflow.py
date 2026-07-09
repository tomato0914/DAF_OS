"""
Quest121 — External Image Workflow（Gemini手動制作対応）の動作確認用ミニテスト。

DAF OSの目的は画像生成AIエンジンを作ることではなく、Digital Asset Factory
として商品を継続的に制作できることにある。画像生成AIは進化が速いため、
本Questでは画像生成自体をGemini等の外部サービスにCEOが手動で行わせ、
DAFは制作管理（③画像アップロード）・品質管理（④品質チェック）・提出
（⑤Export）までを担当する設計へ拡張した。

対象：
- services/image_generation_pipeline.py（import_external_images()・
  Production Source: external_upload/openai/gemini/fallback）
- services/production_orchestrator.py（_commercial_readiness()の
  external_upload対応）
- services/production_status_service.py（画像生成方式のdetail表示）
- services/dashboard_review_package_service.py（Review Packageへの
  画像生成方法表示）
- dashboard_web/app.py（POST /api/projects/upload-images）
- dashboard_web/templates/index.html（①〜⑤の制作フローUI）

このテストファイルはOpenAI / OpenRouter / LiteLLMへの実接続を一切行わない
（外部アップロードはファイルI/Oのみで、AI APIを呼ばない機能のため、本Quest
の実装自体がAPIコストと無縁）。既存Production Pipeline（内部AI画像生成・
AI Review Engine・Export Engine）は変更せず、削除もしていないことを
あわせて確認する。

実行:
  python -m unittest tests/test_quest121_external_image_workflow.py -v
"""

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image

from services.image_generation_pipeline import (
    import_external_images,
    generate_images,
    GENERATION_MODE_AI,
    GENERATION_MODE_FALLBACK,
    GENERATION_MODE_EXTERNAL,
    SOURCE_OPENAI,
    SOURCE_GEMINI,
    SOURCE_EXTERNAL_UPLOAD,
    SOURCE_FALLBACK,
    MAX_EXTERNAL_UPLOAD_COUNT,
)
from services.prompt_builder_v2 import build_prompt


def _clean_env():
    env = dict(os.environ)
    for key in ("DAF_AI_ENABLED", "DAF_RUNTIME_MODE", "OPENAI_API_KEY", "OPENROUTER_API_KEY"):
        env.pop(key, None)
    return env


def _png_bytes(color=(255, 0, 0, 255), size=(4, 4)):
    buf = io.BytesIO()
    Image.new("RGBA", size, color).save(buf, format="PNG")
    return buf.getvalue()


class ImportExternalImagesTest(unittest.TestCase):
    """import_external_images()がGemini等で手動生成した画像を、内部AI生成
    （generate_images()）と同じ保存先・metadata形式で取り込むことを確認する。
    実API接続は発生しない（ファイルI/Oのみ）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_saves_valid_png_files(self):
        result = import_external_images("004", [_png_bytes(), _png_bytes((0, 255, 0, 255))], outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["image_files"], ["sticker_001.png", "sticker_002.png"])
        self.assertEqual(result["generation_mode"], GENERATION_MODE_EXTERNAL)
        self.assertIsNone(result["generation_model"])
        self.assertEqual(result["source"], SOURCE_GEMINI)

        target_dir = Path(result["path"])
        for filename in result["image_files"]:
            self.assertTrue((target_dir / filename).exists())

    def test_default_source_is_gemini(self):
        result = import_external_images("004", [_png_bytes()], outputs_dir=self.outputs_dir)
        self.assertEqual(result["source"], SOURCE_GEMINI)

    def test_source_external_upload_is_accepted(self):
        result = import_external_images("004", [_png_bytes()], source=SOURCE_EXTERNAL_UPLOAD, outputs_dir=self.outputs_dir)
        self.assertEqual(result["source"], SOURCE_EXTERNAL_UPLOAD)

    def test_unknown_source_falls_back_to_external_upload(self):
        result = import_external_images("004", [_png_bytes()], source="some_other_service", outputs_dir=self.outputs_dir)
        self.assertEqual(result["source"], SOURCE_EXTERNAL_UPLOAD)

    def test_metadata_json_records_source_and_mode(self):
        import json
        result = import_external_images("004", [_png_bytes()], outputs_dir=self.outputs_dir)
        metadata = json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
        self.assertEqual(metadata["generation_mode"], GENERATION_MODE_EXTERNAL)
        self.assertEqual(metadata["source"], SOURCE_GEMINI)
        self.assertIsNone(metadata["generation_model"])

    def test_count_is_capped_at_max_external_upload_count(self):
        files = [_png_bytes() for _ in range(10)]
        result = import_external_images("004", files, outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["image_files"]), MAX_EXTERNAL_UPLOAD_COUNT)
        self.assertGreater(result["skipped_count"], 0)

    def test_invalid_image_bytes_are_skipped_not_raised(self):
        result = import_external_images("004", [b"not a real image", _png_bytes()], outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["image_files"]), 1)
        self.assertEqual(result["skipped_count"], 1)

    def test_all_invalid_returns_error_without_raising(self):
        result = import_external_images("004", [b"garbage", b"also garbage"], outputs_dir=self.outputs_dir)
        self.assertFalse(result["ok"])
        self.assertEqual(result["image_files"], [])
        self.assertIsNotNone(result["error"])

    def test_empty_file_list_returns_error_without_raising(self):
        result = import_external_images("004", [], outputs_dir=self.outputs_dir)
        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["error"])

    def test_never_raises_for_unexpected_project_id(self):
        result = import_external_images("../../etc", [_png_bytes()], outputs_dir=self.outputs_dir)
        self.assertIsInstance(result, dict)
        self.assertIn("ok", result)

    def test_upload_records_latest_prompt_file_when_available(self):
        build_prompt("004", save=True, outputs_dir=self.outputs_dir)
        result = import_external_images("004", [_png_bytes()], outputs_dir=self.outputs_dir)
        self.assertEqual(result["prompt_file"], "prompt_001.txt")

    def test_upload_works_without_prompt(self):
        # プロンプト未生成でも外部生成画像だけを取り込めることを確認する
        # （Geminiで先に画像だけ作った場合もブロックしない）。
        result = import_external_images("no_prompt_project", [_png_bytes()], outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertIsNone(result["prompt_file"])


class InternalGenerationStillWorksTest(unittest.TestCase):
    """Quest121は内部AI画像生成機能を削除しない。既存のgenerate_images()
    （AI/Pillow fallback）が変更なく動作し、新たにsourceフィールドも
    返すことを確認する。実API接続は発生しない（OPENAI_API_KEY未設定）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)
        self._env_patch = patch.dict(os.environ, _clean_env(), clear=True)
        self._env_patch.start()
        build_prompt("004", save=True, outputs_dir=self.outputs_dir)

    def tearDown(self):
        self._env_patch.stop()
        self._tmp.cleanup()

    def test_generate_images_still_works_and_reports_fallback_source(self):
        result = generate_images("004", count=1, outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["generation_mode"], GENERATION_MODE_FALLBACK)
        self.assertEqual(result["source"], SOURCE_FALLBACK)

    def test_generate_images_function_still_exists_and_is_callable(self):
        # 内部AI生成のエントリポイント自体が削除されていないことを確認する
        # （将来API接続を戻す判断ができるように維持されている、Quest121要件）。
        from services.image_generation_pipeline import _generate_via_ai
        self.assertTrue(callable(_generate_via_ai))
        self.assertTrue(callable(generate_images))


class CommercialReadinessExternalUploadTest(unittest.TestCase):
    """production_orchestrator._commercial_readiness()がexternal_uploadを
    Pillow fallbackとは区別し、販売用候補として扱うことを確認する。"""

    def test_external_upload_is_commercial_ready(self):
        from services.production_orchestrator import _commercial_readiness, COMMERCIAL_READY_REASON_EXTERNAL
        ready, reason = _commercial_readiness(GENERATION_MODE_EXTERNAL)
        self.assertTrue(ready)
        self.assertEqual(reason, COMMERCIAL_READY_REASON_EXTERNAL)

    def test_fallback_pillow_still_not_commercial_ready(self):
        from services.production_orchestrator import _commercial_readiness
        ready, _ = _commercial_readiness(GENERATION_MODE_FALLBACK)
        self.assertFalse(ready)

    def test_ai_still_commercial_ready(self):
        from services.production_orchestrator import _commercial_readiness
        ready, _ = _commercial_readiness(GENERATION_MODE_AI)
        self.assertTrue(ready)


class ProductionStatusShowsGenerationSourceTest(unittest.TestCase):
    """production_status_service._check_image_generation()が画像生成方式
    （Gemini手動／内部AI／Pillow fallback）をdetailへ記録し、CEOと
    Review Packageの両方から確認できることを確認する。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_detail_shows_gemini_label_after_external_upload(self):
        from services.production_status_service import get_production_status
        import_external_images("004", [_png_bytes()], outputs_dir=self.outputs_dir)
        status = get_production_status("004", outputs_dir=self.outputs_dir)
        image_step = next(s for s in status["steps"] if s["id"] == "image_generation")
        self.assertEqual(image_step["status"], "done")
        self.assertIn("Gemini", image_step["detail"])

    def test_detail_is_empty_when_nothing_generated(self):
        from services.production_status_service import get_production_status
        status = get_production_status("no_such_project", outputs_dir=self.outputs_dir)
        image_step = next(s for s in status["steps"] if s["id"] == "image_generation")
        self.assertEqual(image_step["status"], "pending")
        self.assertEqual(image_step["detail"], "")


class ReviewPackageShowsGenerationMethodTest(unittest.TestCase):
    """Review Package Summary（Executive Board向け）に、Projectごとの
    画像生成方法（Gemini手動／OpenAI／Pillow fallback）が表示されることを
    確認する。"""

    def test_summary_markdown_includes_per_project_generation_method(self):
        from services.dashboard_review_package_service import build_review_package_summary_markdown

        project_summary = {"projects": [{"id": "004", "asset_type": "line_sticker"}], "count": 1}
        production_status = {
            "projects": [
                {
                    "project_id": "004",
                    "next_action": "-",
                    "ready_for_submission": True,
                    "steps": [
                        {"id": "image_generation", "label": "画像生成", "status": "done",
                         "detail": "画像生成方式：Gemini（手動）"},
                    ],
                },
            ],
        }
        ceo_home_summary = {"next_action": "-"}

        markdown = build_review_package_summary_markdown(
            project_summary, production_status, ceo_home_summary, "2026-07-09 12:00",
        )
        self.assertIn("画像生成方法（Projectごと）", markdown)
        self.assertIn("Gemini（手動）", markdown)

    def test_summary_markdown_omits_section_when_nothing_generated(self):
        from services.dashboard_review_package_service import build_review_package_summary_markdown

        project_summary = {"projects": [], "count": 0}
        production_status = {"projects": []}
        ceo_home_summary = {"next_action": "-"}

        markdown = build_review_package_summary_markdown(
            project_summary, production_status, ceo_home_summary, "2026-07-09 12:00",
        )
        self.assertNotIn("画像生成方法（Projectごと）", markdown)


class UploadImagesApiTest(unittest.TestCase):
    """POST /api/projects/upload-images の入力バリデーション・正常系を確認
    する。実API接続は発生しない（ファイルアップロードのみ）。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_rejects_invalid_project_id(self):
        resp = self.client.post(
            "/api/projects/upload-images",
            data={"id": "../../etc"},
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_rejects_missing_files(self):
        resp = self.client.post(
            "/api/projects/upload-images",
            data={"id": "004"},
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_rejects_disallowed_extension(self):
        from io import BytesIO
        resp = self.client.post(
            "/api/projects/upload-images",
            data={"id": "004", "files": (BytesIO(b"not an image"), "malware.exe")},
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_accepts_valid_png_upload(self):
        from io import BytesIO
        resp = self.client.post(
            "/api/projects/upload-images",
            data={"id": "004", "files": (BytesIO(_png_bytes()), "gemini_output.png")},
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["generation_mode"], GENERATION_MODE_EXTERNAL)


class ExistingPipelineNotBrokenTest(unittest.TestCase):
    """Quest121の注意事項「既存Pipelineは壊さない」の確認：Review・Exportは
    画像の生成元（内部AI／外部アップロード）を区別せず、外部アップロード
    画像に対しても変更なく動作することを確認する。実API接続は発生しない。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)
        self._env_patch = patch.dict(os.environ, _clean_env(), clear=True)
        self._env_patch.start()

    def tearDown(self):
        self._env_patch.stop()
        self._tmp.cleanup()

    def test_review_and_export_work_on_externally_uploaded_images(self):
        from services.ai_review_engine import review_images
        from services.export_engine import export_project
        from services.production_status_service import get_production_status

        build_prompt("004", save=True, outputs_dir=self.outputs_dir)
        upload_result = import_external_images("004", [_png_bytes() for _ in range(3)], outputs_dir=self.outputs_dir)
        self.assertTrue(upload_result["ok"])

        review_result = review_images("004", manual_request=True, outputs_dir=self.outputs_dir)
        self.assertTrue(review_result["ok"])

        export_result = export_project("004", outputs_dir=self.outputs_dir)
        self.assertTrue(export_result["ok"])
        self.assertIsNotNone(export_result["zip_filename"])

        status = get_production_status("004", outputs_dir=self.outputs_dir)
        self.assertTrue(status["ready_for_submission"])


if __name__ == "__main__":
    unittest.main()
