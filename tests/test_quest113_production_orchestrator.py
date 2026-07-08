"""
Quest113 — Production Orchestrator（One-Click Production Flow）の動作確認用
ミニテスト。services/production_orchestrator.py（既存Service、Quest108〜111
を順番に呼び出すだけのオーケストレーション）と、dashboard_web/app.py の
/api/projects/run-production・/api/projects/<id>/production-report の応答を
対象とする。

実際のAI呼び出しへは接続しない（OPENAI_API_KEY/OPENROUTER_API_KEY未設定の
まま、Pillowフォールバック・fallback_rule_review経路のみで検証する）。

実行:
  python -m unittest tests/test_quest113_production_orchestrator.py -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.production_orchestrator import (
    run_production,
    load_production_report,
    STATUS_SUCCESS,
    STATUS_FAILED,
)


class ProductionOrchestratorTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_orchestrator_runs_successfully(self):
        result = run_production("004", count=2, outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], STATUS_SUCCESS)

    def test_prompt_step_completes(self):
        result = run_production("004", count=2, outputs_dir=self.outputs_dir)
        self.assertIn("prompt", result["completed_steps"])

    def test_image_generation_step_completes(self):
        result = run_production("004", count=2, outputs_dir=self.outputs_dir)
        self.assertIn("image_generation", result["completed_steps"])
        self.assertEqual(result["image_count"], 2)

    def test_ai_review_step_completes(self):
        result = run_production("004", count=2, outputs_dir=self.outputs_dir)
        self.assertIn("ai_review", result["completed_steps"])
        self.assertIsNotNone(result["review_mode"])

    def test_export_step_completes(self):
        result = run_production("004", count=2, outputs_dir=self.outputs_dir)
        self.assertIn("export", result["completed_steps"])
        self.assertIsNotNone(result["zip_filename"])

    def test_production_report_is_saved(self):
        run_production("004", count=2, outputs_dir=self.outputs_dir)
        report = load_production_report("004", outputs_dir=self.outputs_dir)
        self.assertIsNotNone(report)
        self.assertEqual(report["status"], STATUS_SUCCESS)
        self.assertEqual(
            report["completed_steps"],
            ["prompt", "image_generation", "ai_review", "export"],
        )

    def test_next_action_on_success(self):
        result = run_production("004", count=2, outputs_dir=self.outputs_dir)
        self.assertEqual(result["next_action"], "LINE Creators Marketへ提出してください")

    def test_stops_at_failed_step_and_does_not_continue(self):
        with patch(
            "services.image_generation_pipeline.generate_images",
            return_value={"ok": False, "error": "強制的な失敗（テスト用）"},
        ):
            result = run_production("004", count=2, outputs_dir=self.outputs_dir)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], STATUS_FAILED)
        self.assertEqual(result["failed_step"], "image_generation")
        self.assertEqual(result["completed_steps"], ["prompt"])
        self.assertNotIn("ai_review", result["completed_steps"])
        self.assertNotIn("export", result["completed_steps"])
        self.assertIn("強制的な失敗", result["error"])

    def test_failed_report_is_still_saved(self):
        with patch(
            "services.ai_review_engine.review_images",
            return_value={"ok": False, "report": None, "path": None, "error": "強制的な失敗（テスト用）"},
        ):
            run_production("004", count=2, outputs_dir=self.outputs_dir)

        report = load_production_report("004", outputs_dir=self.outputs_dir)
        self.assertIsNotNone(report)
        self.assertEqual(report["status"], STATUS_FAILED)
        self.assertEqual(report["failed_step"], "ai_review")

    def test_load_production_report_returns_none_when_missing(self):
        self.assertIsNone(load_production_report("no_such_project_yet", outputs_dir=self.outputs_dir))


class ProductionOrchestratorApiTest(unittest.TestCase):
    """Flask APIレベルのバリデーションのみを確認する（実データを書き換えない）。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_run_production_rejects_invalid_project_id(self):
        resp = self.client.post("/api/projects/run-production", json={"id": "../../etc"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_production_report_endpoint_returns_exists_false_for_missing_project(self):
        resp = self.client.get("/api/projects/definitely_does_not_exist_yet/production-report")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["exists"])

    def test_production_report_endpoint_rejects_invalid_project_id(self):
        resp = self.client.get("/api/projects/../../etc/production-report")
        self.assertIn(resp.status_code, (400, 404))


if __name__ == "__main__":
    unittest.main()
