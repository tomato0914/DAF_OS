"""
Quest105 — IP Bible Generatorの動作確認用ミニテスト。
services/ip_bible_service.py（生成・保存・読込・AI未設定時フォールバック）
と、dashboard_web/app.py の /api/ip-memory/bible系APIの入力バリデーション
を対象とする。

実際のOpenRouter APIへは接続しない（ネットワーク非依存・再現性を優先）。
Flask側のテストはoutputs/ip_memoryを汚さないよう、検証（400/exists:false）
のみに限定する。

実行:
  python -m unittest tests/test_quest105_ip_bible.py -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ip_memory_service import create_ip, update_dna
from services.ip_bible_service import generate_ip_bible, save_ip_bible, load_ip_bible


class GenerateIpBibleTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)
        self._had_key = os.environ.pop("OPENROUTER_API_KEY", None)

    def tearDown(self):
        self._tmp.cleanup()
        if self._had_key is not None:
            os.environ["OPENROUTER_API_KEY"] = self._had_key

    def test_generate_uses_template_fallback_without_api_key(self):
        create_ip("mofu", outputs_dir=self.outputs_dir)
        update_dna("mofu", {
            "identity": {"name": "もふ", "species": "dog", "type": "mascot"},
            "visual": {"color_palette": "pastel brown"},
            "rules": {"must_have": "round silhouette", "must_not": "sharp lines"},
            "keywords": ["cute", "warm"],
        }, outputs_dir=self.outputs_dir)

        result = generate_ip_bible("mofu", outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["source"], "template")
        self.assertIsNone(result["error"])

        markdown = result["markdown"]
        for heading in ("Identity", "Story", "Core Personality", "Visual Identity",
                         "Color Palette", "World", "Brand Position", "Style Rules",
                         "Forbidden Rules", "Prompt Examples", "Future Evolution"):
            self.assertIn(f"## {heading}", markdown)
        # DNAの値がそのまま反映されている（複製ではなく差し込み）
        self.assertIn("もふ", markdown)
        self.assertIn("pastel brown", markdown)
        self.assertIn("round silhouette", markdown)

    def test_generate_returns_error_for_missing_ip(self):
        result = generate_ip_bible("does_not_exist", outputs_dir=self.outputs_dir)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["markdown"])
        self.assertIsNotNone(result["error"])

    def test_generate_works_with_empty_dna(self):
        create_ip("empty_ip", outputs_dir=self.outputs_dir)
        result = generate_ip_bible("empty_ip", outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["source"], "template")
        self.assertIn("## Identity", result["markdown"])


class SaveLoadIpBibleTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_and_load_roundtrip(self):
        create_ip("mofu", outputs_dir=self.outputs_dir)
        markdown = "## Identity\n- Name: もふ\n"

        saved = save_ip_bible("mofu", markdown, outputs_dir=self.outputs_dir)
        self.assertTrue(saved["ok"])
        self.assertTrue(Path(saved["path"]).exists())
        self.assertTrue(saved["path"].endswith("ip_bible.md"))

        loaded = load_ip_bible("mofu", outputs_dir=self.outputs_dir)
        self.assertEqual(loaded, markdown)

        # ip_memory.jsonと同じフォルダに保存され、Reference Libraryとは分離
        self.assertEqual(Path(saved["path"]).parent.name, "mofu")
        self.assertTrue((Path(saved["path"]).parent / "ip_memory.json").exists())

    def test_load_returns_none_when_not_saved(self):
        create_ip("mofu", outputs_dir=self.outputs_dir)
        self.assertIsNone(load_ip_bible("mofu", outputs_dir=self.outputs_dir))

    def test_save_rejects_missing_ip(self):
        result = save_ip_bible("does_not_exist", "## Identity\n", outputs_dir=self.outputs_dir)
        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["error"])


class IpBibleApiValidationTest(unittest.TestCase):
    """
    Flask APIレベルのバリデーションのみを確認する（実データを書き換えない
    ケースに限定）。
    """

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_generate_rejects_empty_ip_name(self):
        resp = self.client.post("/api/ip-memory/bible/generate", json={"ip_name": ""})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_generate_returns_400_for_missing_ip(self):
        resp = self.client.post("/api/ip-memory/bible/generate", json={"ip_name": "definitely_does_not_exist_ip"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_save_rejects_empty_markdown(self):
        resp = self.client.post("/api/ip-memory/bible/save", json={"ip_name": "mofu", "markdown": ""})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_get_bible_returns_exists_false_for_missing_ip(self):
        resp = self.client.get("/api/ip-memory/definitely_does_not_exist_ip/bible")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()["exists"])

    def test_get_bible_rejects_invalid_ip_name(self):
        resp = self.client.get("/api/ip-memory/../../etc/bible")
        self.assertIn(resp.status_code, (400, 404))


if __name__ == "__main__":
    unittest.main()
