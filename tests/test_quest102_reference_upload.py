"""
Quest102 — Reference Upload UIの動作確認用ミニテスト。
services/reference_analysis_service.py に追加した
save_reference_image() / refresh_all_reference_summaries() を対象とする
（Flask経由のAPIではなく、Service関数を直接呼ぶユニットテスト）。

実行:
  python -m unittest tests/test_quest102_reference_upload.py -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.reference_analysis_service import (
    save_reference_image,
    list_reference_images,
    refresh_all_reference_summaries,
    get_default_categories,
)


class ReferenceUploadTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_reference_image_registers_metadata(self):
        result = save_reference_image(
            file_bytes=b"fake-image-bytes",
            original_filename="my dog.png",
            category="cute",
            project_id="004",
            tags=["犬", "かわいい"],
            description="丸い目、やさしい色",
            outputs_dir=self.outputs_dir,
        )
        self.assertTrue(result["ok"])
        self.assertTrue(Path(result["path"]).exists())

        saved_image = Path(result["path"]).with_suffix("").with_suffix(".png")
        self.assertTrue(saved_image.exists())
        self.assertEqual(saved_image.read_bytes(), b"fake-image-bytes")

        images = list_reference_images(project_id="004", outputs_dir=self.outputs_dir)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["tags"], ["犬", "かわいい"])
        self.assertEqual(images[0]["memo"], "丸い目、やさしい色")

    def test_rejects_unsupported_extension(self):
        result = save_reference_image(
            file_bytes=b"not-an-image",
            original_filename="notes.txt",
            category="cute",
            outputs_dir=self.outputs_dir,
        )
        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["error"])

    def test_refresh_all_reference_summaries_covers_registered_projects(self):
        save_reference_image(
            file_bytes=b"a", original_filename="a.png", category="cute",
            project_id="001", outputs_dir=self.outputs_dir,
        )
        save_reference_image(
            file_bytes=b"b", original_filename="b.jpg", category="pastel",
            project_id="002", outputs_dir=self.outputs_dir,
        )
        # project_id未紐づけの画像はレポート対象に含まれない
        save_reference_image(
            file_bytes=b"c", original_filename="c.webp", category="simple",
            outputs_dir=self.outputs_dir,
        )

        results = refresh_all_reference_summaries(outputs_dir=self.outputs_dir)
        project_ids = sorted(r["project_id"] for r in results)
        self.assertEqual(project_ids, ["001", "002"])
        for r in results:
            self.assertTrue(r["ok"])
            self.assertTrue(Path(r["path"]).exists())

    def test_get_default_categories_returns_copy(self):
        categories = get_default_categories()
        categories.append("mutated")
        self.assertNotIn("mutated", get_default_categories())


if __name__ == "__main__":
    unittest.main()
