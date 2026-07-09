"""
Quest115 — Universal Production / 汎用Production Factory化の動作確認用
ミニテスト。services/production_orchestrator.py（asset_type対応・
未対応Asset Typeの安全な失敗）と、dashboard_web/app.pyの
/api/projects/run-production、dashboard_web/templates/index.htmlの
主ボタン文言を対象とする。

実際のAI呼び出しへは接続しない（OPENAI_API_KEY/OPENROUTER_API_KEY未設定の
まま、Pillowフォールバック・fallback_rule_review経路のみで検証する）。

実行:
  python -m unittest tests/test_quest115_universal_production.py -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.production_orchestrator import (
    run_production,
    load_production_report,
    get_asset_type_label,
    is_supported_production_asset_type,
    STATUS_SUCCESS,
    STATUS_UNSUPPORTED_ASSET_TYPE,
    SUPPORTED_PRODUCTION_ASSET_TYPES,
)


class AssetTypeHelpersTest(unittest.TestCase):
    def test_line_sticker_is_supported(self):
        self.assertTrue(is_supported_production_asset_type("line_sticker"))

    def test_wallpaper_is_not_supported(self):
        self.assertFalse(is_supported_production_asset_type("wallpaper"))

    def test_supported_types_contains_only_line_sticker(self):
        self.assertEqual(set(SUPPORTED_PRODUCTION_ASSET_TYPES.keys()), {"line_sticker"})

    def test_get_asset_type_label_known(self):
        self.assertEqual(get_asset_type_label("line_sticker"), "LINEスタンプ")

    def test_get_asset_type_label_unknown_falls_back_to_raw_value(self):
        self.assertEqual(get_asset_type_label("wallpaper"), "wallpaper")


class UniversalProductionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name) / "outputs"
        self.projects_dir = Path(self._tmp.name) / "projects"

    def tearDown(self):
        self._tmp.cleanup()

    def test_line_sticker_project_still_succeeds(self):
        result = run_production("004", count=2, outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], STATUS_SUCCESS)

    def test_report_records_asset_type_fields(self):
        run_production("004", count=2, outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        report = load_production_report("004", outputs_dir=self.outputs_dir)
        self.assertEqual(report["asset_type"], "line_sticker")
        self.assertEqual(report["asset_type_label"], "LINEスタンプ")

    def test_explicit_unsupported_asset_type_fails_safely(self):
        result = run_production("004", asset_type="wallpaper", outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], STATUS_UNSUPPORTED_ASSET_TYPE)
        self.assertEqual(result["asset_type"], "wallpaper")
        self.assertIn("準備中", result["message"])

    def test_unsupported_asset_type_does_not_save_report(self):
        run_production("004", asset_type="wallpaper", outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertIsNone(load_production_report("004", outputs_dir=self.outputs_dir))

    def test_asset_type_is_resolved_from_project_when_unspecified(self):
        from services.project_service import create_project
        created = create_project(
            "壁紙プロジェクト", asset_type="youtube_short", vision="テスト用",
            projects_dir=self.projects_dir, auto_launch=False,
        )
        project_id = created["id"]

        result = run_production(project_id, outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], STATUS_UNSUPPORTED_ASSET_TYPE)
        self.assertEqual(result["asset_type"], "youtube_short")

    def test_line_sticker_project_resolved_from_project_still_succeeds(self):
        from services.project_service import create_project
        created = create_project(
            "犬のLINEスタンプ", asset_type="line_sticker", vision="テスト用",
            projects_dir=self.projects_dir, auto_launch=False,
        )
        project_id = created["id"]

        result = run_production(project_id, count=1, outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["asset_type"], "line_sticker")


class RunProductionApiTest(unittest.TestCase):
    """Flask APIレベルの検証。実データを書き換えない範囲のみ確認する。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_run_production_with_explicit_unsupported_asset_type(self):
        resp = self.client.post(
            "/api/projects/run-production",
            json={"id": "definitely_no_such_project", "asset_type": "wallpaper"},
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["status"], "unsupported_asset_type")
        self.assertEqual(data["asset_type"], "wallpaper")

    def test_run_production_rejects_invalid_project_id(self):
        resp = self.client.post("/api/projects/run-production", json={"id": "../../etc"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])


class DashboardMainButtonLabelTest(unittest.TestCase):
    """Projectsタブの主ボタンが汎用文言に変わっていることを確認する（文字列検証のみ）。"""

    @classmethod
    def setUpClass(cls):
        template_path = Path(__file__).parent.parent / "dashboard_web" / "templates" / "index.html"
        cls.template_text = template_path.read_text(encoding="utf-8")

    def test_main_button_uses_generic_wording(self):
        self.assertIn("🚀 このProjectを制作する", self.template_text)

    def test_main_button_no_longer_says_line_sticker_specific_wording(self):
        self.assertNotIn("🚀 LINEスタンプを作る", self.template_text)


if __name__ == "__main__":
    unittest.main()
