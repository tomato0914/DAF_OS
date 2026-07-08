"""
Quest108 — Prompt Builder v2の動作確認用ミニテスト。
services/prompt_builder_v2.py（プロンプト生成・保存・読込・IP未紐づけ時の
フォールバック）と、dashboard_web/app.py の /api/projects/build-prompt の
入力バリデーションを対象とする。

画像生成AI（OpenAI / Google / Stability AI等）へは一切接続しない
（Prompt Builder v2自体がAIを呼ばない決定的な文字列組み立てのため、
ネットワーク非依存・毎回同じ結果になる）。

実行:
  python -m unittest tests/test_quest108_prompt_builder.py -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.prompt_builder_v2 import (
    build_character_prompt,
    build_style_prompt,
    build_expression_prompt,
    build_output_prompt,
    merge_prompt,
    build_prompt,
    save_prompt,
    list_prompts,
    load_prompt,
)
from services.ip_memory_service import create_ip, update_dna
from services.ip_bible_service import save_ip_bible
from services.creative_style_service import save_style_guide, save_prompt_rules
from services.project_service import create_project


class SubBuilderTest(unittest.TestCase):
    def test_build_character_prompt_uses_dna_when_available(self):
        context = {"dna": {
            "identity": {"name": "Mofu", "species": "dog", "type": "mascot"},
            "visual": {"body_style": "round silhouette", "eye_style": "round eyes"},
            "personality": {"personality": "friendly"},
        }, "ip_bible": ""}
        result = build_character_prompt(context)
        self.assertIn("Mofu", result)
        self.assertIn("dog", result)
        self.assertIn("round silhouette", result)

    def test_build_character_prompt_falls_back_without_dna_or_bible(self):
        result = build_character_prompt({"dna": {}, "ip_bible": ""})
        self.assertTrue(result)
        self.assertIn("no IP Memory linked", result)

    def test_build_style_prompt_prefers_style_guide_sections(self):
        style_guide = "## Color Rules\n- pastel brown\n\n## Line Rules\n- thin lines\n"
        result = build_style_prompt({"style_guide": style_guide, "dna": {}})
        self.assertIn("pastel brown", result)
        self.assertIn("thin lines", result)

    def test_build_style_prompt_falls_back_to_dna_visual(self):
        context = {"style_guide": "", "dna": {"visual": {"color_palette": "warm cream"}}}
        result = build_style_prompt(context)
        self.assertIn("warm cream", result)

    def test_build_expression_prompt_uses_reference_summary_as_last_resort(self):
        context = {"style_guide": "", "dna": {}, "reference_summary": "犬、可愛い"}
        result = build_expression_prompt(context)
        self.assertIn("犬、可愛い", result)

    def test_build_output_prompt_maps_asset_type(self):
        result = build_output_prompt({"project": {"asset_type": "line_sticker"}})
        self.assertIn("transparent", result.lower())
        self.assertIn("LINE sticker", result)

    def test_build_output_prompt_falls_back_for_unknown_asset_type(self):
        result = build_output_prompt({"project": {"asset_type": "unknown_type"}})
        self.assertTrue(result)

    def test_merge_prompt_combines_fragments_and_rules(self):
        merged = merge_prompt(
            "a dog character", "pastel colors", "gentle smile", "transparent PNG",
            prompt_rules={"always": ["round shapes"], "prefer": [], "avoid": ["dark colors"], "never": ["violence"]},
        )
        self.assertIn("a dog character, pastel colors, gentle smile, transparent PNG", merged)
        self.assertIn("Always include: round shapes", merged)
        self.assertIn("Avoid: dark colors", merged)
        self.assertIn("Never include: violence", merged)

    def test_merge_prompt_without_rules_still_returns_main_line(self):
        merged = merge_prompt("a", "b", "c", "d")
        self.assertTrue(merged.strip())
        self.assertIn("a, b, c, d", merged)


class BuildPromptIntegrationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)
        self._projects_tmp = tempfile.TemporaryDirectory()
        self.projects_dir = Path(self._projects_tmp.name)

    def tearDown(self):
        self._tmp.cleanup()
        self._projects_tmp.cleanup()

    def _make_project(self):
        result = create_project(
            name="Test Dog Stickers", asset_type="line_sticker",
            vision="A cheerful dog sticker series", projects_dir=self.projects_dir,
            auto_launch_meeting=False,
        )
        self.assertTrue(result["ok"])
        return result["id"]

    def test_build_prompt_without_ip_still_produces_nonempty_prompt(self):
        project_id = self._make_project()
        result = build_prompt(project_id, ip_name=None, save=False,
                               outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["prompt"])
        self.assertTrue(result["prompt"].strip())

    def test_build_prompt_with_full_ip_context(self):
        project_id = self._make_project()
        create_ip("mofu", outputs_dir=self.outputs_dir)
        update_dna("mofu", {
            "identity": {"name": "Mofu", "species": "dog"},
            "visual": {"color_palette": "pastel brown", "line_style": "thin lines"},
        }, outputs_dir=self.outputs_dir)
        save_ip_bible("mofu", "## Identity\n- Name: Mofu\n", outputs_dir=self.outputs_dir)
        save_style_guide("mofu", "## Color Rules\n- pastel brown\n\n## Expression Rules\n- gentle smile\n",
                          outputs_dir=self.outputs_dir)
        save_prompt_rules("mofu", {"always": ["round shapes"], "prefer": [], "avoid": [], "never": ["scary face"]},
                           outputs_dir=self.outputs_dir)

        result = build_prompt(project_id, ip_name="mofu", save=False,
                               outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertTrue(result["ok"])
        self.assertIn("Mofu", result["prompt"])
        self.assertIn("pastel brown", result["prompt"])
        self.assertIn("gentle smile", result["prompt"])
        self.assertIn("Always include: round shapes", result["prompt"])
        self.assertIn("Never include: scary face", result["prompt"])

    def test_build_prompt_saves_when_requested(self):
        project_id = self._make_project()
        result = build_prompt(project_id, save=True,
                               outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["path"])
        self.assertTrue(Path(result["path"]).exists())
        self.assertEqual(Path(result["path"]).read_text(encoding="utf-8"), result["prompt"])

    def test_build_prompt_never_raises_for_missing_project(self):
        result = build_prompt("does_not_exist", save=False,
                               outputs_dir=self.outputs_dir, projects_dir=self.projects_dir)
        self.assertTrue(result["ok"])  # Project情報が空でも、フォールバックで生成は続行する
        self.assertTrue(result["prompt"].strip())


class SavePromptTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_prompt_creates_sequential_files(self):
        first = save_prompt("004", "prompt one\n", outputs_dir=self.outputs_dir)
        second = save_prompt("004", "prompt two\n", outputs_dir=self.outputs_dir)

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertTrue(first["path"].endswith("prompt_001.txt"))
        self.assertTrue(second["path"].endswith("prompt_002.txt"))
        self.assertNotEqual(first["path"], second["path"])

    def test_save_prompt_rejects_empty_text(self):
        result = save_prompt("004", "   ", outputs_dir=self.outputs_dir)
        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["error"])

    def test_list_and_load_prompts(self):
        save_prompt("004", "prompt one\n", outputs_dir=self.outputs_dir)
        save_prompt("004", "prompt two\n", outputs_dir=self.outputs_dir)

        prompts = list_prompts("004", outputs_dir=self.outputs_dir)
        self.assertEqual(len(prompts), 2)
        self.assertEqual(prompts[0]["filename"], "prompt_001.txt")
        self.assertEqual(prompts[1]["filename"], "prompt_002.txt")

        latest = load_prompt("004", outputs_dir=self.outputs_dir)
        self.assertEqual(latest, "prompt two\n")

        specific = load_prompt("004", filename="prompt_001.txt", outputs_dir=self.outputs_dir)
        self.assertEqual(specific, "prompt one\n")

    def test_load_prompt_returns_none_when_nothing_saved(self):
        self.assertIsNone(load_prompt("does_not_exist", outputs_dir=self.outputs_dir))

    def test_list_prompts_returns_empty_for_missing_project(self):
        self.assertEqual(list_prompts("does_not_exist", outputs_dir=self.outputs_dir), [])


class BuildPromptApiValidationTest(unittest.TestCase):
    """Flask APIレベルのバリデーションのみを確認する（実データを書き換えない）。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_build_prompt_rejects_invalid_project_id(self):
        resp = self.client.post("/api/projects/build-prompt", json={"id": "../../etc"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_list_prompts_rejects_invalid_project_id(self):
        resp = self.client.get("/api/projects/../../etc/prompts")
        self.assertIn(resp.status_code, (400, 404))


if __name__ == "__main__":
    unittest.main()
