"""
Quest116 — Dashboard Review Packageの動作確認用ミニテスト。
services/dashboard_review_package_service.py（Dashboard構造・API一覧・
Project一覧・Production Status・CEO Home集計・UX Notesの収集とZIP化）と、
dashboard_web/app.pyの
  POST /api/dashboard/review-package/create
  GET  /api/dashboard/review-package/latest
  GET  /api/dashboard/review-package/download/<package_id>
の応答を対象とする。

実際のAI呼び出しへは接続しない（OPENAI_API_KEY/OPENROUTER_API_KEY未設定の
まま、Pillowフォールバック経路のみで検証する）。

実行:
  python -m unittest tests/test_quest116_dashboard_review_package.py -v
"""

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.dashboard_review_package_service import (
    create_review_package,
    list_review_packages,
    get_latest_review_package,
    get_review_package_zip_path,
    collect_project_summary,
    collect_production_status,
    collect_ceo_home_summary,
    _REQUIRED_FILES,
)


class DashboardReviewPackageServiceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name) / "outputs"
        self.projects_dir = Path(self._tmp.name) / "projects"

        from services.project_service import create_project
        create_project(
            "犬のLINEスタンプ", asset_type="line_sticker", vision="テスト用",
            projects_dir=self.projects_dir, auto_launch=False,
        )
        create_project(
            "壁紙プロジェクト", asset_type="wallpaper", vision="テスト用",
            projects_dir=self.projects_dir, auto_launch=False,
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_review_package_directory_is_created(self):
        result = create_review_package(outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertTrue(result["ok"])
        self.assertTrue(Path(result["path"]).is_dir())

    def test_required_files_are_generated(self):
        result = create_review_package(outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        directory = Path(result["path"])
        for filename in _REQUIRED_FILES:
            with self.subTest(filename=filename):
                self.assertTrue((directory / filename).exists(), f"{filename} が生成されていません")

    def test_project_summary_json_contains_created_projects(self):
        result = create_review_package(outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        import json
        data = json.loads((Path(result["path"]) / "project_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(data["count"], 2)
        asset_types = {p["asset_type"] for p in data["projects"]}
        self.assertEqual(asset_types, {"line_sticker", "wallpaper"})
        line_sticker_row = next(p for p in data["projects"] if p["asset_type"] == "line_sticker")
        self.assertEqual(line_sticker_row["asset_type_label"], "LINEスタンプ")

    def test_production_status_json_has_one_entry_per_project(self):
        result = create_review_package(outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        import json
        data = json.loads((Path(result["path"]) / "production_status.json").read_text(encoding="utf-8"))
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["projects"]), 2)
        self.assertIn("current_status", data["projects"][0])

    def test_review_package_summary_md_is_generated(self):
        result = create_review_package(outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        summary_text = (Path(result["path"]) / "review_package_summary.md").read_text(encoding="utf-8")
        self.assertIn("Project数", summary_text)
        self.assertIn("2", summary_text)

    def test_zip_is_generated_and_contains_required_files(self):
        result = create_review_package(outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        zip_path = Path(result["zip_path"])
        self.assertTrue(zip_path.exists())
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
        for filename in _REQUIRED_FILES:
            self.assertIn(filename, names)

    def test_list_and_get_latest_review_package(self):
        first = create_review_package(outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        packages = list_review_packages(outputs_dir=self.outputs_dir)
        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0]["package_id"], first["package_id"])

        latest = get_latest_review_package(outputs_dir=self.outputs_dir)
        self.assertEqual(latest["package_id"], first["package_id"])
        self.assertIn("review_package.zip", latest["files"])

    def test_get_review_package_zip_path_returns_none_for_missing_package(self):
        self.assertIsNone(get_review_package_zip_path("no_such_package", outputs_dir=self.outputs_dir))

    def test_collect_helpers_do_not_raise_on_empty_state(self):
        empty_outputs = Path(self._tmp.name) / "empty_outputs"
        empty_projects = Path(self._tmp.name) / "empty_projects"
        project_summary = collect_project_summary(projects_dir=empty_projects, outputs_dir=empty_outputs)
        self.assertEqual(project_summary["count"], 0)

        production_status = collect_production_status([], outputs_dir=empty_outputs)
        self.assertEqual(production_status["count"], 0)

        ceo_home_summary = collect_ceo_home_summary(projects_dir=empty_projects, outputs_dir=empty_outputs)
        self.assertIn("active_projects", ceo_home_summary)
        self.assertIn("next_action", ceo_home_summary)


class ReviewPackageApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_create_review_package_endpoint_succeeds(self):
        resp = self.client.post("/api/dashboard/review-package/create")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("package_id", data)
        self.assertIn("review_package.zip", data["files"])

    def test_download_endpoint_returns_zip_for_created_package(self):
        create_resp = self.client.post("/api/dashboard/review-package/create")
        package_id = create_resp.get_json()["package_id"]

        download_resp = self.client.get(f"/api/dashboard/review-package/download/{package_id}")
        self.assertEqual(download_resp.status_code, 200)
        self.assertIn("zip", download_resp.headers.get("Content-Type", ""))

    def test_latest_endpoint_reflects_created_package(self):
        create_resp = self.client.post("/api/dashboard/review-package/create")
        package_id = create_resp.get_json()["package_id"]

        latest_resp = self.client.get("/api/dashboard/review-package/latest")
        self.assertEqual(latest_resp.status_code, 200)
        data = latest_resp.get_json()
        self.assertTrue(data["exists"])
        self.assertEqual(data["package_id"], package_id)

    def test_download_endpoint_rejects_invalid_package_id(self):
        resp = self.client.get("/api/dashboard/review-package/download/../../etc")
        self.assertIn(resp.status_code, (400, 404))

    def test_download_endpoint_404_for_missing_package(self):
        resp = self.client.get("/api/dashboard/review-package/download/definitely_no_such_package")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
