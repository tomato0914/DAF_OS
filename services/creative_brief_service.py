"""
DAF OS Quest99 — Creative Brief Service（Vega / Creative Director）

Vega（Creative Director / CDO、docs/organization.md参照）が担当する
「デザイン設計」の最初の一歩として、ProjectごとにCreative Brief
（Character Direction / Style Direction / Prompt Direction）を生成する。

Quest98で作った Character Bible（services/prompt_builder_service.py が読み込む
outputs/character_bibles/<bible_id>/）を土台にする。Quest99時点では
Projectごとに新しいCharacter Bibleを作るのではなく、既定の"dog_default"を
参照しつつ、Project固有の情報（Vision・Asset Type）を組み合わせた
Creative Briefを作るところまでとする。

画像生成APIは呼ばない（Quest99は設計レイヤーのみ）。

出力先：outputs/creative_briefs/<project_id>/creative_brief.md
（project_idはservices/project_service.pyが発番するProject ID、
例："001"）。

必要な関数：
- generate_creative_brief(project_id, project_name, vision, asset_type):
    Creative Briefを生成し、creative_brief.mdへ保存する
- get_creative_brief(project_id): 生成済みCreative Briefを読み込み、
    Dashboard・Prompt Builder向けの構造化データで返す
- list_creative_briefs(): 生成済みの全Creative Briefを一覧で返す

CLI:
  python services/creative_brief_service.py <project_id> <project_name> [vision]

Character Bible未存在・書き込み失敗のいずれでも例外を投げず、
DAF OS全体を止めない。
"""

import re
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"
_CREATIVE_BRIEFS_DIR_NAME = "creative_briefs"
_DEFAULT_BIBLE_ID = "dog_default"
_SAMPLE_PHRASE = "おはよう"


def _briefs_root(outputs_dir: Path | None = None) -> Path:
    return (outputs_dir or _OUTPUTS_DIR) / _CREATIVE_BRIEFS_DIR_NAME


def _brief_dir(project_id: str, outputs_dir: Path | None = None) -> Path:
    return _briefs_root(outputs_dir) / project_id


def _first_meaningful_line(text: str) -> str:
    """
    character.md/style.mdはMarkdown（見出し・複数行）のことが多いため、
    見出し・表・空行を読み飛ばして最初の本文行を返す
    （services/prompt_builder_service._first_meaningful_line()と同じ方針）。
    """
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("|"):
            continue
        return stripped.lstrip("- ").strip()
    return ""


def generate_creative_brief(
    project_id: str,
    project_name: str,
    vision: str = "",
    asset_type: str = "line_sticker",
    outputs_dir: Path | None = None,
    bible_id: str = _DEFAULT_BIBLE_ID,
) -> dict:
    """
    Project情報（project_id/project_name/vision/asset_type）とQuest98の
    Character Bible（既定"dog_default"）から、Creative Brief
    （Character Direction / Style Direction / Prompt Direction）を組み立て、
    outputs/creative_briefs/<project_id>/creative_brief.md へ保存する。

    戻り値: {"ok": bool, "project_id": str, "project": str,
             "path": str | None, "error": str | None}
    Character Bible読み込み失敗・書き込み失敗のいずれでも例外を投げない
    （Character Bibleが読めなくても、デフォルト文言でCreative Brief自体は
    生成する）。
    """
    try:
        from services.prompt_builder_service import load_character_bible, build_image_prompt

        bible = load_character_bible(bible_id)
        character_direction = _first_meaningful_line(bible.get("character")) or "（Character Bible未設定。デフォルトのキャラクター方針を使用）"
        style_direction = _first_meaningful_line(bible.get("style")) or "（Style Guide未設定。デフォルトの絵柄方針を使用）"
        prompt_direction = build_image_prompt(
            _SAMPLE_PHRASE,
            character_bible=bible,
            execution_context=f"Project: {project_name}",
        )

        # Quest101：参考画像メタデータ（reference.json群）からReference
        # Summaryを組み立てる。参考画像が無くても例外を投げず、その旨の
        # 固定文言を返す（services/reference_analysis_service.py）。
        reference_summary = "参考画像はまだ登録されていません。"
        try:
            from services.reference_analysis_service import (
                generate_vega_reference_report, get_reference_summary_for_brief,
            )
            generate_vega_reference_report(project_id, outputs_dir=outputs_dir)
            reference_summary = get_reference_summary_for_brief(project_id, outputs_dir=outputs_dir)
        except Exception as e:
            print(f"[警告] Reference Summaryの取得に失敗しました（{project_id}）：{e}")

        base_dir = _brief_dir(project_id, outputs_dir)
        base_dir.mkdir(parents=True, exist_ok=True)

        lines = [
            "# Creative Brief",
            "",
            "Project:",
            project_name,
            "",
            "Project ID:",
            project_id,
            "",
            "Asset Type:",
            asset_type,
            "",
            "Character Bible:",
            bible_id,
            "",
            "Vision:",
            vision or "（未設定）",
            "",
            "---",
            "",
            "## Character Direction",
            "",
            character_direction,
            "",
            "## Style Direction",
            "",
            style_direction,
            "",
            "## Prompt Direction",
            "",
            prompt_direction,
            "",
            "## Reference Summary",
            "",
            reference_summary,
            "",
            "## Notes",
            "Quest99時点ではCreative Brief（設計レイヤー）のみ。画像生成APIはまだ呼ばない。",
            "Vega（Creative Director）がCharacter Bible・Style Guide・Promptの土台をここに集約する。",
            "Quest101：Reference SummaryはCEOが登録した参考画像のメタデータ（タグ・雰囲気）を",
            "集計したものであり、画像そのものの解析・複製は行わない。",
        ]
        path = base_dir / "creative_brief.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return {"ok": True, "project_id": project_id, "project": project_name, "path": str(path), "error": None}
    except Exception as e:
        print(f"[警告] Creative Briefの生成に失敗しました（{project_id}）：{e}")
        return {"ok": False, "project_id": project_id, "project": project_name, "path": None, "error": str(e)}


def get_creative_brief(project_id: str, outputs_dir: Path | None = None) -> dict:
    """
    指定ProjectのCreative Brief（creative_brief.md）を読み込み、Dashboard・
    Prompt Builder向けの構造化データで返す。

    戻り値: {"exists": bool, "project_id": str, "project_name": str | None,
             "asset_type": str | None, "character_bible": str | None,
             "vision": str | None, "character_direction": str,
             "style_direction": str, "prompt_direction": str,
             "reference_summary": str, "raw_text": str}
    未生成・読み込み失敗のいずれでも例外を投げず、{"exists": False}を返す。
    """
    try:
        path = _brief_dir(project_id, outputs_dir) / "creative_brief.md"
        if not path.exists():
            return {"exists": False, "project_id": project_id}

        text = path.read_text(encoding="utf-8")

        def _field(label: str) -> str | None:
            m = re.search(rf"^{re.escape(label)}:\s*\n(.+)$", text, re.MULTILINE)
            return m.group(1).strip() if m else None

        def _section(heading: str) -> str:
            m = re.search(rf"## {re.escape(heading)}\s*\n([\s\S]*?)(?=\n## |\Z)", text)
            return m.group(1).strip() if m else ""

        return {
            "exists": True,
            "project_id": project_id,
            "project_name": _field("Project"),
            "asset_type": _field("Asset Type"),
            "character_bible": _field("Character Bible"),
            "vision": _field("Vision"),
            "character_direction": _section("Character Direction"),
            "style_direction": _section("Style Direction"),
            "prompt_direction": _section("Prompt Direction"),
            "reference_summary": _section("Reference Summary"),
            "raw_text": text,
        }
    except Exception as e:
        print(f"[警告] Creative Briefの取得に失敗しました（{project_id}）：{e}")
        return {"exists": False, "project_id": project_id, "error": str(e)}


def list_creative_briefs(outputs_dir: Path | None = None) -> list[dict]:
    """
    outputs/creative_briefs/ 配下に生成済みの全Creative Briefを一覧で返す
    （project_id昇順）。ディレクトリ未存在・読み込み失敗のいずれでも
    例外を投げず、空リストを返す。
    """
    try:
        root = _briefs_root(outputs_dir)
        if not root.exists():
            return []
        results = []
        for sub in sorted(root.iterdir()):
            if not sub.is_dir():
                continue
            brief = get_creative_brief(sub.name, outputs_dir=outputs_dir)
            if brief.get("exists"):
                results.append(brief)
        return results
    except Exception as e:
        print(f"[警告] Creative Brief一覧の取得に失敗しました：{e}")
        return []


if __name__ == "__main__":
    # Quest99: 動作確認用のCLI導線。
    #   python services/creative_brief_service.py <project_id> <project_name> [vision]
    argv = sys.argv[1:]
    if len(argv) < 2:
        print("使い方: python services/creative_brief_service.py <project_id> <project_name> [vision]")
    else:
        pid, name = argv[0], argv[1]
        vision = argv[2] if len(argv) > 2 else ""
        result = generate_creative_brief(pid, name, vision=vision)
        print(f"[Creative Brief] {result}")
