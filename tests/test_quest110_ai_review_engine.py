"""
Quest110 — AI Review Engineの動作確認用ミニテスト。
services/ai_review_engine.py（レビュー実行・保存・読込・AI未設定時の
fallback_rule_review）と、dashboard_web/app.py の
/api/projects/review-images・/review-report の入力バリデーションを対象と
する。

AI画像レビュー自体は本テストでは実行しない（OPENROUTER_API_KEYを
テスト内で明示的に空にして検証する。実際のAI呼び出しへは接続しない。
ネットワーク非依存・再現性を優先するため）。

注意：`services/image_generation_service.py`が内部で使う`config.py`は
import時に`load_dotenv()`を呼ぶため、テスト内で
`os.environ.pop("OPENROUTER_API_KEY")`した直後に`generate_images()`等を
呼ぶと、.envに実際のキーがある環境ではconfig.pyの初回importタイミングで
再度環境変数へ復元されることがある。そのため、レビュー対象の画像生成
（前提セットアップ）を終えた後、`review_images()`を呼ぶ直前に改めて
OPENROUTER_API_KEYを取り除く。

実行:
  python -m unittest tests/test_quest110_ai_review_engine.py -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.prompt_builder_v2 import build_prompt
from services.image_generation_pipeline import generate_images
from services.ai_review_engine import (
    review_images,
    save_review_report,
    load_review_report,
    should_run_ai_review,
    REVIEW_MODE_FALLBACK,
    REVIEW_ITEM_NAMES,
)


def _clear_openrouter_key():
    os.environ.pop("OPENROUTER_API_KEY", None)


class ShouldRunAiReviewTest(unittest.TestCase):
    def test_manual_request_always_runs(self):
        self.assertTrue(should_run_ai_review(True, None))
        self.assertTrue(should_run_ai_review(True, {"checks": []}))

    def test_no_manual_request_and_no_quality_report_skips(self):
        self.assertFalse(should_run_ai_review(False, None))

    def test_no_manual_request_but_quality_warning_runs(self):
        quality_report = {"checks": [{"name": "Metadata", "status": "WARNING"}]}
        self.assertTrue(should_run_ai_review(False, quality_report))

    def test_no_manual_request_all_pass_skips(self):
        quality_report = {"checks": [{"name": "PNG", "status": "PASS"}]}
        self.assertFalse(should_run_ai_review(False, quality_report))


class ReviewImagesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)
        self._had_key = os.environ.get("OPENROUTER_API_KEY")
        build_prompt("004", save=True, outputs_dir=self.outputs_dir)
        generate_images("004", count=2, outputs_dir=self.outputs_dir)

    def tearDown(self):
        self._tmp.cleanup()
        if self._had_key is not None:
            os.environ["OPENROUTER_API_KEY"] = self._had_key

    def test_review_report_is_saved(self):
        _clear_openrouter_key()
        result = review_images("004", manual_request=True, outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["path"])
        self.assertTrue(Path(result["path"]).exists())

        saved = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
        self.assertEqual(saved["project_id"], "004")

    def test_succeeds_with_fallback_rule_review_when_api_key_missing(self):
        _clear_openrouter_key()
        result = review_images("004", manual_request=True, outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["report"]["review_mode"], REVIEW_MODE_FALLBACK)

    def test_review_mode_is_recorded(self):
        _clear_openrouter_key()
        result = review_images("004", manual_request=True, outputs_dir=self.outputs_dir)
        self.assertIn("review_mode", result["report"])
        self.assertIn(result["report"]["review_mode"], ("ai", REVIEW_MODE_FALLBACK))

    def test_overall_score_is_returned(self):
        _clear_openrouter_key()
        result = review_images("004", manual_request=True, outputs_dir=self.outputs_dir)
        score = result["report"]["overall_score"]
        self.assertIsInstance(score, int)
        self.assertGreaterEqual(score, 1)
        self.assertLessEqual(score, 5)

    def test_items_are_returned_for_all_review_categories(self):
        _clear_openrouter_key()
        result = review_images("004", manual_request=True, outputs_dir=self.outputs_dir)
        items = result["report"]["items"]
        self.assertEqual(len(items), len(REVIEW_ITEM_NAMES))
        names = {i["name"] for i in items}
        self.assertEqual(names, set(REVIEW_ITEM_NAMES))
        for item in items:
            self.assertIn("score", item)
            self.assertIn("comment", item)
            self.assertIn("needs_fix", item)

    def test_report_contains_required_top_level_fields(self):
        _clear_openrouter_key()
        result = review_images("004", manual_request=True, outputs_dir=self.outputs_dir)
        report = result["report"]
        for key in ("project_id", "reviewed_at", "review_mode", "summary", "overall_score", "items"):
            self.assertIn(key, report)

    def test_returns_error_when_no_generated_images(self):
        _clear_openrouter_key()
        result = review_images("no_images_project", manual_request=True, outputs_dir=self.outputs_dir)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["report"])
        self.assertIsNotNone(result["error"])

    def test_never_raises_for_unexpected_project_id(self):
        _clear_openrouter_key()
        result = review_images("../../etc", manual_request=True, outputs_dir=self.outputs_dir)
        self.assertIsInstance(result, dict)
        self.assertIn("ok", result)


class SaveLoadReviewReportTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_and_load_roundtrip(self):
        report = {"project_id": "004", "overall_score": 4, "items": []}
        saved = save_review_report("004", report, outputs_dir=self.outputs_dir)
        self.assertTrue(saved["ok"])
        self.assertTrue(saved["path"].endswith("review_report.json"))

        loaded = load_review_report("004", outputs_dir=self.outputs_dir)
        self.assertEqual(loaded, report)

    def test_load_returns_none_when_not_saved(self):
        self.assertIsNone(load_review_report("does_not_exist", outputs_dir=self.outputs_dir))


class ReviewApiValidationTest(unittest.TestCase):
    """Flask APIレベルのバリデーション、およびDashboard APIがreview reportを返せることを確認する。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_review_images_rejects_invalid_project_id(self):
        resp = self.client.post("/api/projects/review-images", json={"id": "../../etc"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_review_images_returns_error_when_no_generated_images(self):
        resp = self.client.post("/api/projects/review-images", json={"id": "definitely_no_images_project"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_review_report_endpoint_returns_exists_false_for_missing_project(self):
        resp = self.client.get("/api/projects/definitely_does_not_exist/review-report")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()["exists"])

    def test_review_report_endpoint_rejects_invalid_project_id(self):
        resp = self.client.get("/api/projects/../../etc/review-report")
        self.assertIn(resp.status_code, (400, 404))


if __name__ == "__main__":
    unittest.main()
