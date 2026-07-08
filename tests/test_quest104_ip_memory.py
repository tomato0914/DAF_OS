"""
Quest104 — IP Memory Engineの動作確認用ミニテスト。
services/ip_memory_service.py（IP作成・DNA保存・読込・更新・一覧・
Referenceからの生成）と、dashboard_web/app.py の /api/ip-memory系APIの
入力バリデーションを対象とする。

DNA生成AI呼び出しは、OPENROUTER_API_KEY未設定時のフォールバック集計経路の
みテストする（実際のOpenRouter APIへは接続しない。ネットワーク非依存・
再現性を優先するため）。Flask側のテストはoutputs/ip_memory・
outputs/reference_libraryを汚さないよう、検証（400）のみに限定する。

実行:
  python -m unittest tests/test_quest104_ip_memory.py -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ip_memory_service import (
    create_ip,
    load_ip,
    save_ip,
    update_dna,
    list_ips,
    generate_dna_from_reference,
)
from services.reference_analysis_service import save_reference_image


class CreateIpTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_create_ip_creates_empty_dna_structure(self):
        result = create_ip("mofu", outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertFalse(result["already_exists"])
        self.assertTrue(Path(result["path"]).exists())

        dna = result["ip"]["dna"]
        self.assertEqual(set(dna.keys()), {"identity", "personality", "visual", "brand", "rules", "keywords"})
        self.assertEqual(dna["identity"], {"name": "", "species": "", "type": ""})
        self.assertEqual(dna["keywords"], [])

        # 将来追加しやすいよう、DNA以外のセクションもキーだけ確保されている
        for section in ("character_bible", "world_bible", "style_guide"):
            self.assertIn(section, result["ip"])
        for history in ("prompt_history", "review_history", "evolution_history"):
            self.assertEqual(result["ip"][history], [])

    def test_create_ip_does_not_overwrite_existing(self):
        first = create_ip("mofu", outputs_dir=self.outputs_dir)
        update_dna("mofu", {"identity": {"name": "もふ"}}, outputs_dir=self.outputs_dir)

        second = create_ip("mofu", outputs_dir=self.outputs_dir)
        self.assertTrue(second["ok"])
        self.assertTrue(second["already_exists"])
        self.assertEqual(second["ip"]["dna"]["identity"]["name"], "もふ")

    def test_create_ip_rejects_empty_name(self):
        result = create_ip("", outputs_dir=self.outputs_dir)
        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["error"])


class DnaPersistenceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_and_load_ip_roundtrip(self):
        created = create_ip("mofu", outputs_dir=self.outputs_dir)
        ip_data = created["ip"]
        ip_data["dna"]["identity"]["name"] = "もふ"

        saved = save_ip("mofu", ip_data, outputs_dir=self.outputs_dir)
        self.assertTrue(saved["ok"])
        self.assertEqual(saved["ip"]["metadata"]["version"], 2)  # create=1, save=2

        loaded = load_ip("mofu", outputs_dir=self.outputs_dir)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["dna"]["identity"]["name"], "もふ")

    def test_load_ip_returns_none_for_missing(self):
        self.assertIsNone(load_ip("does_not_exist", outputs_dir=self.outputs_dir))

    def test_update_dna_merges_and_preserves_other_fields(self):
        create_ip("mofu", outputs_dir=self.outputs_dir)
        update_dna("mofu", {
            "identity": {"name": "もふ", "species": "dog"},
            "keywords": ["cute", "warm"],
        }, outputs_dir=self.outputs_dir)

        result = update_dna("mofu", {
            "visual": {"color_palette": "pastel brown"},
        }, outputs_dir=self.outputs_dir)

        dna = result["ip"]["dna"]
        # 新しく更新したフィールド
        self.assertEqual(dna["visual"]["color_palette"], "pastel brown")
        # 前回更新したフィールドは保持される
        self.assertEqual(dna["identity"]["name"], "もふ")
        self.assertEqual(dna["identity"]["species"], "dog")
        self.assertEqual(dna["keywords"], ["cute", "warm"])
        # 未指定フィールドは空のまま保持される
        self.assertEqual(dna["identity"]["type"], "")

    def test_update_dna_creates_ip_if_missing(self):
        result = update_dna("brand_new", {"identity": {"name": "x"}}, outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["ip"]["dna"]["identity"]["name"], "x")

    def test_list_ips_returns_registered_ips(self):
        create_ip("mofu", outputs_dir=self.outputs_dir)
        create_ip("nyan", outputs_dir=self.outputs_dir)
        update_dna("mofu", {"identity": {"name": "もふ"}}, outputs_dir=self.outputs_dir)

        ips = list_ips(outputs_dir=self.outputs_dir)
        names = sorted(ip["ip_name"] for ip in ips)
        self.assertEqual(names, ["mofu", "nyan"])
        mofu = next(ip for ip in ips if ip["ip_name"] == "mofu")
        self.assertEqual(mofu["dna_name"], "もふ")


class GenerateDnaFromReferenceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.outputs_dir = Path(self._tmp.name)
        self._had_key = os.environ.pop("OPENROUTER_API_KEY", None)

    def tearDown(self):
        self._tmp.cleanup()
        if self._had_key is not None:
            os.environ["OPENROUTER_API_KEY"] = self._had_key

    def test_generate_dna_uses_fallback_aggregation_without_api_key(self):
        save_reference_image(
            file_bytes=b"a", original_filename="a.png", category="cute",
            project_id="001", tags=["dog", "cute", "pastel"],
            outputs_dir=self.outputs_dir,
        )
        save_reference_image(
            file_bytes=b"b", original_filename="b.png", category="cute",
            project_id="001", tags=["dog", "cute", "simple"],
            outputs_dir=self.outputs_dir,
        )

        result = generate_dna_from_reference("mofu", project_id="001", outputs_dir=self.outputs_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["reference_count"], 2)
        self.assertEqual(result["source"], "fallback_aggregation")
        # 2件に共通するタグが優先的に上位へ来る
        self.assertIn("dog", result["dna"]["keywords"])
        self.assertIn("cute", result["dna"]["keywords"])

    def test_generate_dna_returns_error_when_no_references(self):
        result = generate_dna_from_reference("mofu", project_id="does_not_exist", outputs_dir=self.outputs_dir)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reference_count"], 0)
        self.assertIsNotNone(result["error"])


class IpMemoryApiValidationTest(unittest.TestCase):
    """
    Flask APIレベルのバリデーションのみを確認する（実データを書き換えない
    ケースに限定：不正なip_name・存在しないIPへの400/exists:false）。
    """

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard_web"))
        from dashboard_web.app import app
        cls.client = app.test_client()

    def test_list_ips_endpoint_returns_200(self):
        resp = self.client.get("/api/ip-memory")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ips", resp.get_json())

    def test_detail_rejects_invalid_ip_name(self):
        resp = self.client.get("/api/ip-memory/../../etc")
        self.assertIn(resp.status_code, (400, 404))

    def test_detail_returns_exists_false_for_missing_ip(self):
        resp = self.client.get("/api/ip-memory/definitely_does_not_exist_ip")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()["exists"])

    def test_create_rejects_empty_name(self):
        resp = self.client.post("/api/ip-memory/create", json={"ip_name": ""})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_dna_update_rejects_empty_name(self):
        resp = self.client.post("/api/ip-memory/dna/update", json={"ip_name": "", "dna": {}})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])

    def test_dna_generate_rejects_empty_name(self):
        resp = self.client.post("/api/ip-memory/dna/generate", json={"ip_name": ""})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["ok"])


if __name__ == "__main__":
    unittest.main()
