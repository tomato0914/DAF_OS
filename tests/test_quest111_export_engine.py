"""
Quest111 — Export Engineの動作確認用ミニテスト。
services/export_engine.py（Export前チェック・package作成・ZIP作成・
export_report.json保存・読込）と、dashboard_web/app.py の
/api/projects/export・/export-report・/download-export の入力
バリデーションを対象とする。

外部サービス（LINE Creators Market等）へは一切接続しない
（Export Engineはローカルにパッケージ・ZIP・レポートを作るだけで、
申請自体は行わない設計のため）。

実行:
  python -m unittest tests/test_quest111_export_engine.py -v
"""

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.prompt_builder_v2 import build_prompt
from services.image_generation_pipeline import generate_images
from services.export_engine import (
    check_export_readiness,
    build_export_package,
    create_export_zip,
    export_project,
    load_export_report,
    LineExportAdapter,
)


class ExportProjectIntegrationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)
        build_prompt("004", save=True, outputs_dir=self.outputs_dir)
        generate_images("004", count=2, outputs_dir=self.outputs_dir)

    def tearDown(self):
        self._tmp.cleanup()

    def test_zip_is_generated(self):
        result = export_project("004", outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["zip_path"])
        self.assertTrue(Path(result["zip_path"]).exists())

        with zipfile.ZipFile(result["zip_path"]) as zf:
            names = zf.namelist()
        self.assertIn("main.png", names)
        self.assertIn("tab.png", names)
        self.assertIn("metadata.json", names)
        self.assertIn("stickers/sticker_001.png", names)
        self.assertIn("stickers/sticker_002.png", names)

    def test_metadata_is_generated(self):
        result = export_project("004", outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])

        metadata_path = Path(result["package_dir"]) / "metadata.json"
        self.assertTrue(metadata_path.exists())
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        for key in ("project_id", "asset_type", "image_count", "main_image", "tab_image", "created_at", "status"):
            self.assertIn(key, metadata)
        self.assertEqual(metadata["project_id"], "004")
        self.assertEqual(metadata["image_count"], 2)

    def test_export_report_is_generated(self):
        result = export_project("004", outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])

        report = result["report"]
        for key in ("ready", "warnings", "errors", "exported_at", "zip_file"):
            self.assertIn(key, report)
        self.assertEqual(report["zip_file"], "line_stickers.zip")

        loaded = load_export_report("004", outputs_dir=self.outputs_dir)
        self.assertEqual(loaded, report)

    def test_ready_is_true_for_valid_pngs(self):
        result = export_project("004", outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertTrue(result["report"]["ready"])
        self.assertEqual(result["report"]["errors"], [])

    def test_returns_error_for_missing_generated_images(self):
        result = export_project("no_images_project", outputs_dir=self.outputs_dir)
        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["error"])
        self.assertFalse(result["report"]["ready"])
        self.assertTrue(result["report"]["errors"])

    def test_never_raises_for_unexpected_project_id(self):
        result = export_project("../../etc", outputs_dir=self.outputs_dir)
        self.assertIsInstance(result, dict)
        self.assertIn("ok", result)


class CheckExportReadinessTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_ready_false_when_no_images(self):
        readiness = check_export_readiness("no_images_project", outputs_dir=self.outputs_dir)
        self.assertFalse(readiness["ready"])
        self.assertTrue(readiness["errors"])
        self.assertEqual(readiness["image_count"], 0)

    def test_ready_true_when_images_are_valid_png(self):
        build_prompt("004", save=True, outputs_dir=self.outputs_dir)
        generate_images("004", count=1, outputs_dir=self.outputs_dir)

        readiness = check_export_readiness("004", outputs_dir=self.outputs_dir)
        self.assertTrue(readiness["ready"])
        self.assertEqual(readiness["image_count"], 1)
        # 8枚未満は警告のみ（エラーではない）
        self.assertTrue(any("画像枚数" in w for w in readiness["warnings"]))


class BuildPackageAndZipTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)
        build_prompt("004", save=True, outputs_dir=self.outputs_dir)
        generate_images("004", count=2, outputs_dir=self.outputs_dir)

    def tearDown(self):
        self._tmp.cleanup()

    def test_build_package_creates_expected_structure(self):
        result = build_export_package("004", outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])

        package_dir = Path(result["package_dir"])
        self.assertTrue((package_dir / "stickers" / "sticker_001.png").exists())
        self.assertTrue((package_dir / "stickers" / "sticker_002.png").exists())
        self.assertTrue((package_dir / "main.png").exists())
        self.assertTrue((package_dir / "tab.png").exists())
        self.assertTrue((package_dir / "metadata.json").exists())

    def test_create_zip_requires_package_first(self):
        result = create_export_zip("no_package_project", outputs_dir=self.outputs_dir)
        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["error"])

    def test_create_zip_after_package_succeeds(self):
        build_export_package("004", outputs_dir=self.outputs_dir)
        result = create_export_zip("004", outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertTrue(Path(result["zip_path"]).exists())
        self.assertEqual(result["zip_filename"], "line_stickers.zip")


class LineExportAdapterTest(unittest.TestCase):
    def test_adapter_platform_and_zip_filename(self):
        adapter = LineExportAdapter()
        self.assertEqual(adapter.platform, "line")
        self.assertEqual(adapter.zip_filename, "line_stickers.zip")

    def test_validate_reports_error_for_empty_image_list(self):
        adapter = LineExportAdapter()
        result = adapter.validate(Path("/tmp/does-not-matter"), [])
        self.assertTrue(result["errors"])


class ExportApiValidationTest(unittest.TestCase):
    """Flask APIレベルのバリデーション・ダウンロード動作を確認する。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_export_rejects_invalid_project_id(self):
        resp = self.client.post("/api/projects/export", json={"id": "../../etc"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_export_returns_error_when_no_generated_images(self):
        resp = self.client.post("/api/projects/export", json={"id": "definitely_no_images_project"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_export_report_endpoint_returns_exists_false_for_missing_project(self):
        resp = self.client.get("/api/projects/definitely_does_not_exist/export-report")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()["exists"])

    def test_download_export_returns_404_when_not_exported(self):
        resp = self.client.get("/api/projects/definitely_does_not_exist/download-export")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
