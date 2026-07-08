"""
Quest112 — CEO Production Dashboardの動作確認用ミニテスト。
services/production_status_service.py（7ステップ進捗判定・現在の状態・
次のおすすめAction・提出準備完了フラグ）と、dashboard_web/app.py の
/api/projects/<id>/production-status の応答を対象とする。

このServiceは新しい状態を一切保存しないため、既存Service（Quest104〜111）
の保存済みデータを都度読み直すだけ。実際のAI呼び出しへは接続しない
（OPENROUTER_API_KEY未設定のままPillowフォールバック経路のみで検証する）。

実行:
  python -m unittest tests/test_quest112_ceo_production_dashboard.py -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.prompt_builder_v2 import build_prompt
from services.image_generation_pipeline import generate_images
from services.export_engine import export_project
from services.production_status_service import (
    get_production_status,
    STATUS_PENDING,
    STATUS_DONE,
)


def _step(steps, step_id):
    return next(s for s in steps if s["id"] == step_id)


class ProductionStatusServiceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_returns_all_seven_steps(self):
        result = get_production_status("004", outputs_dir=self.outputs_dir)
        self.assertEqual(len(result["steps"]), 7)
        ids = [s["id"] for s in result["steps"]]
        self.assertEqual(ids, [
            "ip_dna", "ip_bible", "style_guide", "prompt",
            "image_generation", "ai_review", "export",
        ])

    def test_next_action_is_returned(self):
        result = get_production_status("004", outputs_dir=self.outputs_dir)
        self.assertIsInstance(result["next_action"], str)
        self.assertTrue(result["next_action"])

    def test_fresh_project_does_not_crash(self):
        result = get_production_status("no_such_project_yet", outputs_dir=self.outputs_dir)
        self.assertEqual(result["project_id"], "no_such_project_yet")
        for step in result["steps"]:
            self.assertEqual(step["status"], STATUS_PENDING)
        self.assertFalse(result["ready_for_submission"])
        self.assertEqual(result["current_status"], "まだ何も実行されていません")
        self.assertIn("プロンプト生成", result["next_action"])

    def test_prompt_step_done_after_prompt_generated(self):
        build_prompt("004", save=True, outputs_dir=self.outputs_dir)
        result = get_production_status("004", outputs_dir=self.outputs_dir)
        self.assertEqual(_step(result["steps"], "prompt")["status"], STATUS_DONE)
        self.assertEqual(_step(result["steps"], "image_generation")["status"], STATUS_PENDING)
        self.assertIn("画像生成", result["next_action"])

    def test_image_generation_step_done_after_images_generated(self):
        build_prompt("004", save=True, outputs_dir=self.outputs_dir)
        generate_images("004", count=2, outputs_dir=self.outputs_dir)

        result = get_production_status("004", outputs_dir=self.outputs_dir)
        self.assertEqual(_step(result["steps"], "image_generation")["status"], STATUS_DONE)
        self.assertEqual(result["current_status"], "画像生成まで完了")
        self.assertIn("AIレビュー", result["next_action"])

    def test_ready_for_submission_true_after_export(self):
        build_prompt("004", save=True, outputs_dir=self.outputs_dir)
        generate_images("004", count=2, outputs_dir=self.outputs_dir)
        export_project("004", outputs_dir=self.outputs_dir)

        result = get_production_status("004", outputs_dir=self.outputs_dir)
        self.assertEqual(_step(result["steps"], "export")["status"], STATUS_DONE)
        self.assertTrue(result["ready_for_submission"])

    def test_ready_for_submission_false_without_export(self):
        build_prompt("004", save=True, outputs_dir=self.outputs_dir)
        generate_images("004", count=2, outputs_dir=self.outputs_dir)

        result = get_production_status("004", outputs_dir=self.outputs_dir)
        self.assertFalse(result["ready_for_submission"])

    def test_ip_steps_are_done_when_ip_name_provided_and_populated(self):
        from services.ip_memory_service import create_ip, update_dna
        from services.ip_bible_service import save_ip_bible
        from services.creative_style_service import save_style_guide

        create_ip("mofu", outputs_dir=self.outputs_dir)
        update_dna("mofu", {"identity": {"name": "もふ"}}, outputs_dir=self.outputs_dir)
        save_ip_bible("mofu", "## Identity\n- Name: もふ\n", outputs_dir=self.outputs_dir)
        save_style_guide("mofu", "## Color Rules\n- pastel\n", outputs_dir=self.outputs_dir)

        result = get_production_status("004", ip_name="mofu", outputs_dir=self.outputs_dir)
        self.assertEqual(_step(result["steps"], "ip_dna")["status"], STATUS_DONE)
        self.assertEqual(_step(result["steps"], "ip_bible")["status"], STATUS_DONE)
        self.assertEqual(_step(result["steps"], "style_guide")["status"], STATUS_DONE)

    def test_ip_steps_pending_without_ip_name_do_not_block_next_action(self):
        # IPが紐づいていない場合、ip_dna等はpendingのままだが、
        # Next Actionはprompt以降のステップから提案される（Quest108の
        # 「IPが無くてもPrompt Builderは動作継続する」設計を尊重するため）。
        result = get_production_status("004", ip_name=None, outputs_dir=self.outputs_dir)
        self.assertEqual(_step(result["steps"], "ip_dna")["status"], STATUS_PENDING)
        self.assertIn("プロンプト生成", result["next_action"])


class ProductionStatusApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_production_status_endpoint_returns_data(self):
        resp = self.client.get("/api/projects/definitely_does_not_exist_yet/production-status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("steps", data)
        self.assertIn("current_status", data)
        self.assertIn("next_action", data)
        self.assertIn("ready_for_submission", data)
        self.assertEqual(len(data["steps"]), 7)

    def test_production_status_endpoint_rejects_invalid_project_id(self):
        resp = self.client.get("/api/projects/../../etc/production-status")
        self.assertIn(resp.status_code, (400, 404))


if __name__ == "__main__":
    unittest.main()
