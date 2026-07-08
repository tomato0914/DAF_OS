"""
Quest107 — Creative Style Engineの動作確認用ミニテスト。
services/creative_style_service.py（Style Guide生成・Prompt Rules生成・
保存・読込・AI未設定時フォールバック）と、dashboard_web/app.py の
/api/ip-memory/style系APIの入力バリデーションを対象とする。

実際のOpenRouter APIへは接続しない（ネットワーク非依存・再現性を優先）。
Flask側のテストはoutputs/ip_memoryを汚さないよう、検証（400/exists:false）
のみに限定する。

実行:
  python -m unittest tests/test_quest107_creative_style.py -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ip_memory_service import create_ip, update_dna
from services.creative_style_service import (
    generate_style_guide,
    generate_prompt_rules,
    save_style_guide,
    load_style_guide,
    save_prompt_rules,
    load_prompt_rules,
)


class GenerateStyleGuideTest(unittest.TestCase):
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
            "identity": {"name": "もふ", "species": "dog"},
            "visual": {"color_palette": "pastel brown", "line_style": "thin lines"},
            "rules": {"must_have": "round silhouette", "must_not": "sharp edges"},
            "keywords": ["cute", "warm"],
        }, outputs_dir=self.outputs_dir)

        result = generate_style_guide("mofu", outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["source"], "template")
        self.assertIsNone(result["error"])

        markdown = result["markdown"]
        for heading in ("Color Rules", "Line Rules", "Shape Rules", "Expression Rules",
                         "Composition Rules", "Typography Rules", "Negative Rules"):
            self.assertIn(f"## {heading}", markdown)
        self.assertIn("pastel brown", markdown)
        self.assertIn("sharp edges", markdown)

    def test_generate_style_guide_returns_error_for_missing_ip(self):
        result = generate_style_guide("does_not_exist", outputs_dir=self.outputs_dir)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["markdown"])
        self.assertIsNotNone(result["error"])

    def test_generate_prompt_rules_uses_template_fallback(self):
        create_ip("mofu", outputs_dir=self.outputs_dir)
        update_dna("mofu", {
            "visual": {"color_palette": "pastel brown"},
            "rules": {"must_have": "round silhouette", "must_not": "sharp edges"},
            "keywords": ["cute", "warm"],
        }, outputs_dir=self.outputs_dir)

        result = generate_prompt_rules("mofu", outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["source"], "template")

        rules = result["rules"]
        self.assertEqual(set(rules.keys()), {"always", "prefer", "avoid", "never"})
        self.assertIn("pastel brown", rules["always"])
        self.assertIn("round silhouette", rules["always"])
        self.assertIn("sharp edges", rules["never"])
        self.assertIn("cute", rules["prefer"])

    def test_generate_prompt_rules_returns_error_for_missing_ip(self):
        result = generate_prompt_rules("does_not_exist", outputs_dir=self.outputs_dir)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["rules"])

    def test_generate_works_with_empty_dna(self):
        create_ip("empty_ip", outputs_dir=self.outputs_dir)
        style = generate_style_guide("empty_ip", outputs_dir=self.outputs_dir)
        self.assertTrue(style["ok"])
        self.assertIn("## Color Rules", style["markdown"])

        rules = generate_prompt_rules("empty_ip", outputs_dir=self.outputs_dir)
        self.assertTrue(rules["ok"])
        self.assertEqual(rules["rules"], {"always": [], "prefer": [], "avoid": [], "never": []})


class SaveLoadCreativeStyleTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_and_load_style_guide_roundtrip(self):
        create_ip("mofu", outputs_dir=self.outputs_dir)
        markdown = "## Color Rules\n- pastel\n"

        saved = save_style_guide("mofu", markdown, outputs_dir=self.outputs_dir)
        self.assertTrue(saved["ok"])
        self.assertTrue(saved["path"].endswith("style_guide.md"))
        self.assertTrue(Path(saved["path"]).exists())

        loaded = load_style_guide("mofu", outputs_dir=self.outputs_dir)
        self.assertEqual(loaded, markdown)

        # ip_memory.jsonと同じフォルダに保存される（IP Bibleと同じパターン）
        self.assertEqual(Path(saved["path"]).parent.name, "mofu")
        self.assertTrue((Path(saved["path"]).parent / "ip_memory.json").exists())

    def test_save_and_load_prompt_rules_roundtrip(self):
        create_ip("mofu", outputs_dir=self.outputs_dir)
        rules = {"always": ["a"], "prefer": ["b"], "avoid": [], "never": ["c"]}

        saved = save_prompt_rules("mofu", rules, outputs_dir=self.outputs_dir)
        self.assertTrue(saved["ok"])
        self.assertTrue(saved["path"].endswith("prompt_rules.json"))

        loaded = load_prompt_rules("mofu", outputs_dir=self.outputs_dir)
        self.assertEqual(loaded, rules)

    def test_save_prompt_rules_fills_missing_keys(self):
        create_ip("mofu", outputs_dir=self.outputs_dir)
        saved = save_prompt_rules("mofu", {"always": ["a"]}, outputs_dir=self.outputs_dir)
        self.assertTrue(saved["ok"])
        self.assertEqual(saved["rules"], {"always": ["a"], "prefer": [], "avoid": [], "never": []})

    def test_load_returns_none_when_not_saved(self):
        create_ip("mofu", outputs_dir=self.outputs_dir)
        self.assertIsNone(load_style_guide("mofu", outputs_dir=self.outputs_dir))
        self.assertIsNone(load_prompt_rules("mofu", outputs_dir=self.outputs_dir))

    def test_save_rejects_missing_ip(self):
        style_result = save_style_guide("does_not_exist", "## Color Rules\n", outputs_dir=self.outputs_dir)
        self.assertFalse(style_result["ok"])
        rules_result = save_prompt_rules("does_not_exist", {"always": []}, outputs_dir=self.outputs_dir)
        self.assertFalse(rules_result["ok"])

    def test_saving_style_does_not_mutate_ip_memory_json(self):
        create_ip("mofu", outputs_dir=self.outputs_dir)
        ip_json = self.outputs_dir / "ip_memory" / "mofu" / "ip_memory.json"
        before = ip_json.read_bytes()

        save_style_guide("mofu", "## Color Rules\n- x\n", outputs_dir=self.outputs_dir)
        save_prompt_rules("mofu", {"always": ["x"]}, outputs_dir=self.outputs_dir)

        after = ip_json.read_bytes()
        self.assertEqual(before, after)


class CreativeStyleApiValidationTest(unittest.TestCase):
    """
    Flask APIレベルのバリデーションのみを確認する（実データを書き換えない
    ケースに限定：不正な入力・存在しないIPへの400/exists:false）。
    """

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_generate_rejects_empty_ip_name(self):
        resp = self.client.post("/api/ip-memory/style/generate", json={"ip_name": ""})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_generate_returns_400_for_missing_ip(self):
        resp = self.client.post("/api/ip-memory/style/generate", json={"ip_name": "definitely_does_not_exist_ip"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_save_rejects_missing_markdown(self):
        resp = self.client.post("/api/ip-memory/style/save", json={
            "ip_name": "mofu", "markdown": "", "rules": {"always": []},
        })
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_save_rejects_missing_rules(self):
        resp = self.client.post("/api/ip-memory/style/save", json={
            "ip_name": "mofu", "markdown": "## Color Rules\n",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_get_style_returns_exists_false_for_missing_ip(self):
        resp = self.client.get("/api/ip-memory/definitely_does_not_exist_ip/style")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()["exists"])

    def test_get_style_rejects_invalid_ip_name(self):
        resp = self.client.get("/api/ip-memory/../../etc/style")
        self.assertIn(resp.status_code, (400, 404))


if __name__ == "__main__":
    unittest.main()
