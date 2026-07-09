"""
Quest117 — CEO Modeの動作確認用ミニテスト。
Production Pipeline本体・AI Review・Export等の中核ロジックは変更して
いないため、本Questで新たに追加するのはDashboard（フロントエンド）と
Review Packageテンプレートの構成確認のみ。

対象：
- dashboard_web/templates/index.html：CEO Home優先順位（①〜⑤）・
  Projectsタブの簡素化（📊等がDeveloper Modeへ移動していること）
- services/dashboard_review_package_service.py：テンプレート文言の
  CEO Mode反映（レビュー→確認、Export→提出データ等）

実行:
  python -m unittest tests/test_quest117_ceo_mode.py -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.dashboard_review_package_service import (
    build_dashboard_structure_markdown,
    build_api_summary_markdown,
    build_ux_notes_markdown,
)


class CeoHomePriorityOrderTest(unittest.TestCase):
    """dashboard_web/templates/index.htmlのCEO Home優先順位（①〜⑤）を確認する。"""

    @classmethod
    def setUpClass(cls):
        template_path = Path(__file__).parent.parent / "dashboard_web" / "templates" / "index.html"
        cls.template_text = template_path.read_text(encoding="utf-8")

    def test_five_priority_sections_are_present(self):
        for marker in ("① 今日やること", "② AI社員からの重要報告", "③ 進行中Project",
                        "④ 要承認事項", "⑤ 最近完了した制作"):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.template_text)

    def test_five_priority_sections_appear_in_order(self):
        markers = ("① 今日やること", "② AI社員からの重要報告", "③ 進行中Project",
                   "④ 要承認事項", "⑤ 最近完了した制作")
        positions = [self.template_text.index(m) for m in markers]
        self.assertEqual(positions, sorted(positions), "①〜⑤の出現順が優先順位と一致していません")

    def test_review_package_button_uses_executive_board_wording(self):
        self.assertIn("📦 Executive Boardレビュー資料を作成", self.template_text)

    def test_ceo_inbox_link_and_approval_link_are_present(self):
        self.assertIn("Inboxを見る", self.template_text)
        self.assertIn("承認センターへ", self.template_text)

    def test_details_section_wraps_legacy_dashboard_cards(self):
        self.assertIn('id="dashboardDetailsSection"', self.template_text)
        self.assertIn("🔧 詳細情報を見る（開発者・AI社員レポート）", self.template_text)


class ProjectsTabSimplificationTest(unittest.TestCase):
    """Quest121（External Image Workflow）でProjectsタブの主導線は、
    内部AI一括制作の🚀ボタンから①〜⑤の外部画像ワークフロー
    （プロンプト生成→Geminiで画像生成→画像アップロード→品質チェック→
    提出データ作成）へ変わった。①〜⑤は常時表示のまま、内部AI一括制作は
    将来のAPI接続用としてDeveloper Mode内へ移動していることを確認する。"""

    @classmethod
    def setUpClass(cls):
        template_path = Path(__file__).parent.parent / "dashboard_web" / "templates" / "index.html"
        text = template_path.read_text(encoding="utf-8")
        start = text.index("function renderProjects(")
        end = text.index("function fetchProjects(")
        cls.render_projects_body = text[start:end]

    def test_external_workflow_steps_appear_before_developer_mode_toggle(self):
        body = self.render_projects_body
        dev_mode_idx = body.index("🔧 詳細操作を表示（開発者向け）")
        for label in ("① プロンプト生成", "② Geminiで画像生成（CEO手動）", "③ 画像アップロード",
                      "④ 品質チェック（AIレビュー）", "⑤ 提出データ作成"):
            with self.subTest(label=label):
                self.assertLess(body.index(label), dev_mode_idx)

    def test_production_status_button_is_visible_for_ceo(self):
        # Quest121：CEOが常時5ステップの進行状況を一目で確認できるよう、
        # 「📊 進行状況を見る」はDeveloper Modeより前（常時表示）に配置している。
        body = self.render_projects_body
        dev_mode_idx = body.index("🔧 詳細操作を表示（開発者向け）")
        status_idx = body.index("📊 進行状況を見る")
        self.assertLess(status_idx, dev_mode_idx, "📊 進行状況を見るがDeveloper Mode内（常時非表示）になっています")

    def test_internal_ai_bulk_production_is_inside_developer_mode(self):
        body = self.render_projects_body
        dev_mode_idx = body.index("🔧 詳細操作を表示（開発者向け）")
        bulk_idx = body.index("🤖 内部AIで一括制作")
        self.assertLess(dev_mode_idx, bulk_idx)


class ReviewPackageTemplateCeoModeWordingTest(unittest.TestCase):
    """Review Packageテンプレートに、CEO Mode（Quest117）の用語簡素化が反映されていることを確認する。"""

    def test_dashboard_structure_mentions_ceo_priority_order(self):
        text = build_dashboard_structure_markdown()
        self.assertIn("今日やること", text)
        self.assertIn("提出データ作成", text)

    def test_api_summary_mentions_review_package_button(self):
        text = build_api_summary_markdown()
        self.assertIn("Executive Boardレビュー資料を作成", text)

    def test_ux_notes_mentions_quest117(self):
        text = build_ux_notes_markdown()
        self.assertIn("Quest117", text)


if __name__ == "__main__":
    unittest.main()
