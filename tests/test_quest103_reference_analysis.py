"""
Quest103 — Reference Image Analysis AIの動作確認用ミニテスト。
services/reference_analysis_service.py に追加した
analyze_reference_image() / update_reference_metadata() と、
dashboard_web/app.py の /api/references/analyze・/api/references/update の
入力バリデーションを対象とする。

AI解析（analyze_reference_image）はOPENROUTER_API_KEY未設定時のStub経路のみ
テストする（実際のOpenRouter APIへは接続しない。ネットワーク非依存・
再現性を優先するため）。Flask側のテストは実際のoutputs/reference_libraryを
汚さないよう、更新が成功するケースのみService層のテストで確認し、
Flask側は検証（400/404）のみ確認する。

実行:
  python -m unittest tests/test_quest103_reference_analysis.py -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.reference_analysis_service import (
    analyze_reference_image,
    save_reference_image,
    update_reference_metadata,
)


class AnalyzeReferenceImageTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)
        self._had_key = os.environ.pop("OPENROUTER_API_KEY", None)

    def tearDown(self):
        self._tmp.cleanup()
        if self._had_key is not None:
            os.environ["OPENROUTER_API_KEY"] = self._had_key

    def test_returns_safe_stub_when_api_key_missing(self):
        result = save_reference_image(
            file_bytes=b"fake-image-bytes", original_filename="dog.png",
            category="cute", outputs_dir=self.outputs_dir,
        )
        image_path = Path(result["path"]).parent / result["metadata"]["filename"]

        analysis = analyze_reference_image(str(image_path))
        self.assertFalse(analysis["ok"])
        self.assertIsNotNone(analysis["error"])
        self.assertEqual(analysis["tags"], [])
        self.assertEqual(analysis["animal"], "")
        self.assertIn("OPENROUTER_API_KEY", analysis["memo"])

    def test_returns_error_when_image_missing(self):
        analysis = analyze_reference_image(str(self.outputs_dir / "does_not_exist.png"))
        self.assertFalse(analysis["ok"])
        self.assertEqual(analysis["error"], "image file not found")


class UpdateReferenceMetadataTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_update_merges_fields_and_preserves_existing(self):
        saved = save_reference_image(
            file_bytes=b"a", original_filename="dog.png", category="cute",
            project_id="004", tags=["犬"], description="元のメモ",
            outputs_dir=self.outputs_dir,
        )
        filename = saved["metadata"]["filename"]

        result = update_reference_metadata(
            category="cute", filename=filename,
            tags=["犬", "かわいい", "パステル"], animal="dog",
            color="soft brown, cream", mood="warm, gentle",
            outputs_dir=self.outputs_dir,
        )
        self.assertTrue(result["ok"])
        metadata = result["metadata"]

        # 更新対象フィールド
        self.assertEqual(metadata["tags"], ["犬", "かわいい", "パステル"])
        self.assertEqual(metadata["animal"], "dog")
        self.assertEqual(metadata["color"], "soft brown, cream")
        self.assertEqual(metadata["mood"], "warm, gentle")
        # memoは更新していないので元の値を保持
        self.assertEqual(metadata["memo"], "元のメモ")
        # 既存フィールド（project_id/category/filename）は保持される
        self.assertEqual(metadata["project_id"], "004")
        self.assertEqual(metadata["category"], "cute")
        self.assertEqual(metadata["filename"], filename)

    def test_update_missing_reference_returns_not_found(self):
        result = update_reference_metadata(
            category="cute", filename="ref_does_not_exist.png",
            tags=["x"], outputs_dir=self.outputs_dir,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "not_found")

    def test_update_rejects_path_traversal(self):
        result = update_reference_metadata(
            category="../../etc", filename="passwd",
            tags=["x"], outputs_dir=self.outputs_dir,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "invalid_category_or_filename")

        result2 = update_reference_metadata(
            category="cute", filename="../../etc/passwd",
            tags=["x"], outputs_dir=self.outputs_dir,
        )
        self.assertFalse(result2["ok"])
        self.assertEqual(result2["error"], "invalid_category_or_filename")


class ReferenceApiValidationTest(unittest.TestCase):
    """
    Flask APIレベルのバリデーションのみを確認する（実データを書き換えない
    ケースに限定：不正なcategory/filename・存在しないReferenceへの400/404）。
    """

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_analyze_rejects_path_traversal(self):
        resp = self.client.post("/api/references/analyze", json={
            "category": "../../etc", "filename": "passwd",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["success"])

    def test_analyze_returns_404_for_missing_image(self):
        resp = self.client.post("/api/references/analyze", json={
            "category": "cute", "filename": "definitely_does_not_exist.png",
        })
        self.assertEqual(resp.status_code, 404)

    def test_update_rejects_path_traversal(self):
        resp = self.client.post("/api/references/update", json={
            "category": "cute", "filename": "../../../etc/passwd", "tags": "x",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_update_returns_404_for_missing_reference(self):
        resp = self.client.post("/api/references/update", json={
            "category": "cute", "filename": "definitely_does_not_exist.png", "tags": "x",
        })
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
