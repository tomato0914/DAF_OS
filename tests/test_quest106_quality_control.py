"""
Quest106 — Quality Control Engineの動作確認用ミニテスト。
services/quality_control_service.py（画像判定・メタデータ判定・
IP/Reference判定・Quality Report生成）と、dashboard_web/app.py の
/api/quality/check の入力バリデーションを対象とする。

AI・OpenRouterは一切呼ばない（Pythonの決定的なルールのみ）ため、
すべてネットワーク非依存で毎回同じ結果になる。

実行:
  python -m unittest tests/test_quest106_quality_control.py -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image

from services.quality_control_service import (
    validate_image,
    validate_metadata,
    validate_ip,
    validate_reference,
    validate_asset,
    generate_quality_report,
    PASS, WARNING, FAIL,
)
from services.ip_memory_service import create_ip
from services.ip_bible_service import save_ip_bible
from services.reference_analysis_service import save_reference_image


def _status_of(checks, name):
    for c in checks:
        if c["name"] == name:
            return c["status"]
    return None


class ValidateImageTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_valid_transparent_png_passes(self):
        path = self.dir / "good.png"
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 0))
        img.putpixel((50, 50), (255, 0, 0, 255))
        img.save(path, format="PNG")

        checks = validate_image(path)
        self.assertEqual(_status_of(checks, "PNG"), PASS)
        self.assertEqual(_status_of(checks, "Transparency"), PASS)
        self.assertEqual(_status_of(checks, "Size"), PASS)
        self.assertEqual(_status_of(checks, "Aspect Ratio"), PASS)
        self.assertEqual(_status_of(checks, "File Size"), PASS)

    def test_opaque_png_gets_transparency_warning(self):
        path = self.dir / "opaque.png"
        Image.new("RGBA", (100, 100), (255, 0, 0, 255)).save(path, format="PNG")

        checks = validate_image(path)
        self.assertEqual(_status_of(checks, "PNG"), PASS)
        self.assertEqual(_status_of(checks, "Transparency"), WARNING)

    def test_rgb_png_without_alpha_fails_transparency(self):
        path = self.dir / "rgb.png"
        Image.new("RGB", (100, 100), (255, 0, 0)).save(path, format="PNG")

        checks = validate_image(path)
        self.assertEqual(_status_of(checks, "PNG"), PASS)
        self.assertEqual(_status_of(checks, "Transparency"), FAIL)

    def test_non_png_extension_fails(self):
        path = self.dir / "image.jpg"
        Image.new("RGB", (10, 10)).save(path, format="JPEG")

        checks = validate_image(path)
        self.assertEqual(_status_of(checks, "PNG"), FAIL)

    def test_missing_file_fails_all_checks(self):
        checks = validate_image(self.dir / "does_not_exist.png")
        for name in ("PNG", "Transparency", "Size", "Resolution", "Aspect Ratio", "File Size"):
            self.assertEqual(_status_of(checks, name), FAIL)


class ValidateMetadataTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_valid_json_with_required_keys_passes(self):
        path = self.dir / "metadata.json"
        path.write_text(json.dumps({"version": 1, "timestamp": "2026-07-08"}), encoding="utf-8")

        checks = validate_metadata(path)
        self.assertEqual(_status_of(checks, "Metadata"), PASS)

    def test_json_missing_required_keys_warns(self):
        path = self.dir / "metadata.json"
        path.write_text(json.dumps({"title": "no version or timestamp"}), encoding="utf-8")

        checks = validate_metadata(path)
        self.assertEqual(_status_of(checks, "Metadata"), WARNING)

    def test_ip_memory_style_json_is_recognized(self):
        # ip_memory.jsonのようにversion/updated_atがmetadata配下にネストされていても検出できる
        path = self.dir / "metadata.json"
        path.write_text(json.dumps({"metadata": {"version": 2, "updated_at": "2026-07-08 12:00"}}), encoding="utf-8")

        checks = validate_metadata(path)
        self.assertEqual(_status_of(checks, "Metadata"), PASS)

    def test_invalid_json_fails(self):
        path = self.dir / "metadata.json"
        path.write_text("{not valid json", encoding="utf-8")

        checks = validate_metadata(path)
        self.assertEqual(_status_of(checks, "Metadata"), FAIL)

    def test_legacy_markdown_metadata_warns(self):
        path = self.dir / "metadata.md"
        path.write_text("# LINE Sticker Metadata\n", encoding="utf-8")

        checks = validate_metadata(path)
        self.assertEqual(_status_of(checks, "Metadata"), WARNING)

    def test_missing_metadata_fails(self):
        checks = validate_metadata(self.dir / "does_not_exist.json")
        self.assertEqual(_status_of(checks, "Metadata"), FAIL)

    def test_none_path_fails(self):
        checks = validate_metadata(None)
        self.assertEqual(_status_of(checks, "Metadata"), FAIL)


class ValidateIpAndReferenceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_ip_memory_and_bible_pass_when_present(self):
        create_ip("mofu", outputs_dir=self.dir)
        save_ip_bible("mofu", "## Identity\n", outputs_dir=self.dir)

        checks = validate_ip("mofu", outputs_dir=self.dir)
        self.assertEqual(_status_of(checks, "IP Memory"), PASS)
        self.assertEqual(_status_of(checks, "IP Bible"), PASS)

    def test_ip_memory_missing_fails_bible_warns(self):
        checks = validate_ip("does_not_exist", outputs_dir=self.dir)
        self.assertEqual(_status_of(checks, "IP Memory"), FAIL)
        self.assertEqual(_status_of(checks, "IP Bible"), WARNING)

    def test_ip_none_warns_without_error(self):
        checks = validate_ip(None, outputs_dir=self.dir)
        self.assertEqual(_status_of(checks, "IP Memory"), WARNING)
        self.assertEqual(_status_of(checks, "IP Bible"), WARNING)

    def test_reference_present_passes(self):
        save_reference_image(
            file_bytes=b"a", original_filename="a.png", category="cute",
            project_id="001", outputs_dir=self.dir,
        )
        checks = validate_reference("001", outputs_dir=self.dir)
        self.assertEqual(_status_of(checks, "Reference"), PASS)

    def test_reference_absent_warns(self):
        checks = validate_reference("no_such_project", outputs_dir=self.dir)
        self.assertEqual(_status_of(checks, "Reference"), WARNING)

    def test_reference_none_warns_without_error(self):
        checks = validate_reference(None, outputs_dir=self.dir)
        self.assertEqual(_status_of(checks, "Reference"), WARNING)


class GenerateQualityReportTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)
        self.asset_dir = self.outputs_dir / "generated_assets" / "line_sticker"
        self.asset_dir.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _make_good_asset(self):
        img = Image.new("RGBA", (240, 240), (255, 200, 200, 0))
        img.putpixel((120, 120), (255, 200, 200, 255))
        img.save(self.asset_dir / "main.png", format="PNG")
        (self.asset_dir / "metadata.json").write_text(
            json.dumps({"version": 1, "timestamp": "2026-07-08"}), encoding="utf-8",
        )

    def test_report_passes_for_well_formed_asset(self):
        self._make_good_asset()
        report = generate_quality_report(self.asset_dir, outputs_dir=self.outputs_dir)
        self.assertTrue(report["passed"])
        self.assertGreaterEqual(report["score"], 70)
        self.assertIsInstance(report["checks"], list)
        names = {c["name"] for c in report["checks"]}
        self.assertEqual(
            names,
            {"PNG", "Transparency", "Size", "Resolution", "Aspect Ratio",
             "File Size", "Metadata", "IP Memory", "IP Bible", "Reference"},
        )

    def test_report_fails_for_empty_asset_dir(self):
        report = generate_quality_report(self.asset_dir, outputs_dir=self.outputs_dir)
        self.assertFalse(report["passed"])
        self.assertEqual(_status_of(report["checks"], "PNG"), FAIL)

    def test_report_never_raises_for_missing_directory(self):
        report = generate_quality_report(self.outputs_dir / "does_not_exist", outputs_dir=self.outputs_dir)
        self.assertFalse(report["passed"])
        self.assertIsInstance(report["score"], int)

    def test_report_does_not_write_to_ip_memory_or_reference_library(self):
        create_ip("mofu", outputs_dir=self.outputs_dir)
        save_reference_image(
            file_bytes=b"a", original_filename="a.png", category="cute",
            project_id="001", outputs_dir=self.outputs_dir,
        )
        self._make_good_asset()

        ip_json = self.outputs_dir / "ip_memory" / "mofu" / "ip_memory.json"
        before = ip_json.read_bytes()

        generate_quality_report(self.asset_dir, ip_name="mofu", project_id="001", outputs_dir=self.outputs_dir)

        after = ip_json.read_bytes()
        self.assertEqual(before, after)


class ValidateAssetTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_prefers_main_png_and_json_metadata(self):
        Image.new("RGBA", (50, 50), (0, 0, 0, 0)).save(self.dir / "main.png", format="PNG")
        Image.new("RGBA", (50, 50), (0, 0, 0, 0)).save(self.dir / "stamp_01.png", format="PNG")
        (self.dir / "metadata.json").write_text(json.dumps({"version": 1, "timestamp": "x"}), encoding="utf-8")
        (self.dir / "metadata.md").write_text("# legacy", encoding="utf-8")

        checks = validate_asset(self.dir)
        self.assertEqual(_status_of(checks, "PNG"), PASS)
        self.assertEqual(_status_of(checks, "Metadata"), PASS)  # JSONを優先


class QualityCheckApiValidationTest(unittest.TestCase):
    """Flask APIレベルのバリデーションのみを確認する（実データを書き換えない）。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_rejects_unsupported_asset_type(self):
        resp = self.client.post("/api/quality/check", json={"asset_type": "youtube_short"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_rejects_invalid_project_id(self):
        resp = self.client.post("/api/quality/check", json={
            "asset_type": "line_sticker", "project_id": "../../etc",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_returns_404_for_missing_asset_dir(self):
        resp = self.client.post("/api/quality/check", json={
            "asset_type": "line_sticker", "project_id": "definitely_does_not_exist",
        })
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
