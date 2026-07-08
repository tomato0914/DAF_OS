"""
DAF OS Quest108 — Prompt Builder v2（Production Phaseの開始）

Quest101〜107（Reference Intelligence Engine → IP Memory → IP Bible →
Creative Style Engine）で積み上げてきた「IPの知識」を、実際に画像生成AIへ
渡すプロンプト文字列へ変換する最終層。

設計思想（全体の流れ）：
  Reference → Reference Analysis（Quest103）→ IP Memory（Quest104）→
  IP DNA → IP Bible（Quest105）→ Creative Style（Quest107）→
  Prompt Builder v2（本Quest）→ Image Generation（将来）

Lean AI Firstを維持し、画像生成AI（OpenAI / Google / Stability AI等）
そのものへは依存しない。役割は「高品質なプロンプト文字列を組み立てる」
ことに限定し、既存のservices/prompt_builder_service.py（Quest98、
Character Bible = outputs/character_bibles/ベース）とは独立した別モジュール
とする（v1はCharacter Bibleベース、v2はIP Memory/IP Bible/Creative Style
ベース。既存のPrompt Builder v1・Asset Generator・Image Generation
Serviceには一切手を加えない）。

Projectに紐づくIP（ip_name）は現時点でProject側に保存する仕組みが無いため、
build_prompt()の引数として明示的に渡す（省略時はIP関連コンテキストを
「未設定」として扱い、Reference Summary・Project Visionのみで組み立てる。
IPが無くてもPrompt Builder自体は動作を継続できるようにするため）。

必要な関数：
- build_character_prompt(context):  Character（Identity・Visual・Personality）
                                     のプロンプト断片を組み立てる
- build_style_prompt(context):      配色・線・形（Style Guide）のプロンプト
                                     断片を組み立てる
- build_expression_prompt(context): 表情・雰囲気のプロンプト断片を組み立てる
- build_output_prompt(context):     出力形式（Asset Type）のプロンプト断片を
                                     組み立てる
- merge_prompt(character, style, expression, output, prompt_rules=None):
                                     4断片とPrompt Rules（Quest107）を
                                     1つのプロンプト文字列に統合する
- build_prompt(project_id, ip_name=None, save=True):
                                     IP Bible・Creative Style・Reference
                                     Summary・Project情報を統合し、プロンプト
                                     を生成する（save=Trueなら保存まで行う）
- save_prompt(project_id, prompt_text): outputs/prompts/<project_id>/へ
                                     連番ファイルとして保存する
- list_prompts(project_id) / load_prompt(project_id, filename=None):
                                     保存済みプロンプトの一覧・読み込み

保存先：
  outputs/prompts/<project_id>/prompt_001.txt, prompt_002.txt, ...
  （実行のたびに連番で追記保存。既存ファイルは上書きしない）

CLI:
  python services/prompt_builder_v2.py <project_id> [ip_name]

Project未存在・IP未設定・IP Bible/Style Guide未生成のいずれでも例外を
投げず、可能な範囲の情報だけでプロンプトを組み立てる。
"""

import re
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"
_PROMPTS_DIR_NAME = "prompts"

_ASSET_TYPE_OUTPUT_HINTS = {
    "line_sticker": (
        "LINE sticker illustration, transparent PNG background, "
        "centered composition with small margin, no watermark, no text overlay"
    ),
    "youtube_short": "vertical 9:16 thumbnail illustration, bold readable composition, no watermark",
    "ios_app": "app icon / in-app illustration, clean flat design, no watermark",
    "generic": "digital illustration, transparent or simple background, no watermark",
}
_DEFAULT_OUTPUT_HINT = _ASSET_TYPE_OUTPUT_HINTS["generic"]


def _extract_section(markdown: str | None, heading: str) -> str:
    """
    Markdown（ip_bible.md / style_guide.md）から"## heading"配下の本文を
    抜き出す。プロンプト文字列としてそのまま使えるよう、箇条書きの
    "- "マーカー・改行を取り除き、カンマ区切りの1行に正規化する。
    """
    if not markdown:
        return ""
    m = re.search(rf"##\s*{re.escape(heading)}\s*\n([\s\S]*?)(?=\n##\s|\Z)", markdown)
    if not m:
        return ""
    lines = [re.sub(r"^[-*]\s*", "", line).strip() for line in m.group(1).splitlines()]
    return ", ".join(line for line in lines if line)


def _dna_get(dna: dict, group: str, key: str) -> str:
    return ((dna or {}).get(group) or {}).get(key) or ""


def _project_dir_for_id(project_id: str, projects_dir: Path | None = None) -> Path | None:
    base = projects_dir or (_BASE_DIR / "projects")
    if not base.exists():
        return None
    for entry in sorted(base.iterdir()):
        if entry.is_dir() and entry.name.startswith(f"{project_id}_"):
            return entry
        if entry.is_dir() and entry.name == project_id:
            return entry
    return None


def _load_project(project_id: str, projects_dir: Path | None = None) -> dict:
    """
    Project情報（name/asset_type/status/vision）を読み込む。
    services/project_service.pyのlist_projects()を再利用し、visionは
    project.mdの"## Vision"セクションから直接読み取る（list_projects()の
    戻り値にはvisionが含まれないため）。読み込み失敗時も例外を投げず、
    空のdictを返す。
    """
    try:
        from services.project_service import list_projects

        projects = list_projects(projects_dir=projects_dir)
        project = next((p for p in projects if p.get("id") == project_id), None)
        if project is None:
            return {}

        vision = ""
        project_dir = Path(project["path"]) if project.get("path") else _project_dir_for_id(project_id, projects_dir)
        if project_dir:
            project_md = project_dir / "project.md"
            if project_md.exists():
                text = project_md.read_text(encoding="utf-8")
                m = re.search(r"## Vision\s*\n(.+?)(?=\n##\s|\Z)", text, re.DOTALL)
                if m:
                    vision = m.group(1).strip()

        return {
            "id": project.get("id"),
            "name": project.get("name"),
            "asset_type": project.get("asset_type") or "generic",
            "status": project.get("status"),
            "vision": vision,
        }
    except Exception as e:
        print(f"[警告] Project情報の読み込みに失敗しました（{project_id}）：{e}")
        return {}


def _gather_context(
    project_id: str,
    ip_name: str | None = None,
    outputs_dir: Path | None = None,
    memory_dir: Path | None = None,
    projects_dir: Path | None = None,
) -> dict:
    """
    build_prompt()が使うコンテキスト一式を集める。各情報源は個別に
    try/exceptで守り、1つが欠けていても他の情報だけでプロンプトを
    組み立てられるようにする（例外を投げない）。
    """
    context = {
        "project_id": project_id,
        "project": {},
        "ip_name": ip_name,
        "dna": {},
        "ip_bible": "",
        "style_guide": "",
        "prompt_rules": None,
        "reference_summary": "",
    }

    context["project"] = _load_project(project_id, projects_dir=projects_dir)

    try:
        from services.reference_analysis_service import get_reference_summary_for_brief
        context["reference_summary"] = get_reference_summary_for_brief(project_id, outputs_dir=outputs_dir)
    except Exception as e:
        print(f"[警告] Reference Summaryの取得に失敗しました（{project_id}）：{e}")

    if ip_name:
        try:
            from services.ip_memory_service import load_ip
            ip = load_ip(ip_name, outputs_dir=outputs_dir)
            if ip:
                context["dna"] = ip.get("dna") or {}
        except Exception as e:
            print(f"[警告] IP DNAの読み込みに失敗しました（{ip_name}）：{e}")

        try:
            from services.ip_bible_service import load_ip_bible
            context["ip_bible"] = load_ip_bible(ip_name, outputs_dir=outputs_dir) or ""
        except Exception as e:
            print(f"[警告] IP Bibleの読み込みに失敗しました（{ip_name}）：{e}")

        try:
            from services.creative_style_service import load_style_guide, load_prompt_rules
            context["style_guide"] = load_style_guide(ip_name, outputs_dir=outputs_dir) or ""
            context["prompt_rules"] = load_prompt_rules(ip_name, outputs_dir=outputs_dir)
        except Exception as e:
            print(f"[警告] Creative Styleの読み込みに失敗しました（{ip_name}）：{e}")

    return context


def build_character_prompt(context: dict) -> str:
    """
    Character（Identity・Visual・Personality）のプロンプト断片を組み立てる。
    IP DNAを優先し、無ければIP Bibleの"## Identity"セクションを使う。
    どちらも無い場合は汎用的なフォールバック文言を返す。
    """
    dna = context.get("dna") or {}
    parts = [p for p in (
        _dna_get(dna, "identity", "name"),
        _dna_get(dna, "identity", "species"),
        _dna_get(dna, "identity", "type"),
        _dna_get(dna, "visual", "body_style"),
        _dna_get(dna, "visual", "eye_style"),
        _dna_get(dna, "personality", "personality"),
    ) if p]
    if parts:
        return ", ".join(parts)

    identity_section = _extract_section(context.get("ip_bible"), "Identity")
    if identity_section:
        return identity_section

    return "a friendly original character (no IP Memory linked yet — using generic fallback)"


def build_style_prompt(context: dict) -> str:
    """
    配色・線・形（Style Guide）のプロンプト断片を組み立てる。Style Guide
    （Quest107）のColor/Line/Shape Rulesを優先し、無ければIP DNAのvisual群、
    どちらも無ければ汎用フォールバックを返す。
    """
    style_guide = context.get("style_guide")
    sections = [
        _extract_section(style_guide, "Color Rules"),
        _extract_section(style_guide, "Line Rules"),
        _extract_section(style_guide, "Shape Rules"),
    ]
    sections = [s for s in sections if s]
    if sections:
        return " / ".join(sections)

    dna = context.get("dna") or {}
    parts = [p for p in (
        _dna_get(dna, "visual", "color_palette"),
        _dna_get(dna, "visual", "line_style"),
    ) if p]
    if parts:
        return ", ".join(parts)

    return "simple flat illustration, soft pastel color palette, clean outline (no Style Guide generated yet)"


def build_expression_prompt(context: dict) -> str:
    """
    表情・雰囲気のプロンプト断片を組み立てる。Style GuideのExpression Rules
    を優先し、無ければIP DNAのtarget_emotion、それも無ければReference
    Summaryのキーワードにフォールバックする。
    """
    expression_section = _extract_section(context.get("style_guide"), "Expression Rules")
    if expression_section:
        return expression_section

    dna = context.get("dna") or {}
    target_emotion = _dna_get(dna, "personality", "target_emotion")
    if target_emotion:
        return f"expression conveying {target_emotion}"

    reference_summary = context.get("reference_summary") or ""
    if reference_summary and "登録されていません" not in reference_summary:
        return f"expression inspired by: {reference_summary}"

    return "warm, friendly expression (no Expression Rules available yet)"


def build_output_prompt(context: dict) -> str:
    """出力形式（Asset Type）のプロンプト断片を組み立てる（決定的、AI不使用）。"""
    asset_type = (context.get("project") or {}).get("asset_type") or "generic"
    return _ASSET_TYPE_OUTPUT_HINTS.get(asset_type, _DEFAULT_OUTPUT_HINT)


def merge_prompt(character: str, style: str, expression: str, output: str, prompt_rules: dict | None = None) -> str:
    """
    Character・Style・Expression・Outputの4断片と、Creative Style Engine
    （Quest107）のPrompt Rules（always/prefer/avoid/never）を1つのプロンプト
    文字列に統合する。画像生成AIへそのまま渡せる形式（カンマ区切りの
    メインプロンプト＋ルール別セクション）にする。
    """
    main_line = ", ".join(p.strip() for p in (character, style, expression, output) if p and p.strip())

    lines = [main_line, ""]

    rules = prompt_rules or {}
    always = rules.get("always") or []
    prefer = rules.get("prefer") or []
    avoid = rules.get("avoid") or []
    never = rules.get("never") or []

    if always:
        lines.append("Always include: " + ", ".join(always))
    if prefer:
        lines.append("Prefer: " + ", ".join(prefer))
    if avoid:
        lines.append("Avoid: " + ", ".join(avoid))
    if never:
        lines.append("Never include: " + ", ".join(never))

    return "\n".join(lines).strip() + "\n"


def _prompts_dir(project_id: str, outputs_dir: Path | None = None) -> Path:
    return (outputs_dir or _OUTPUTS_DIR) / _PROMPTS_DIR_NAME / project_id


def _next_prompt_path(project_id: str, outputs_dir: Path | None = None) -> Path:
    directory = _prompts_dir(project_id, outputs_dir)
    directory.mkdir(parents=True, exist_ok=True)
    existing = sorted(directory.glob("prompt_*.txt"))
    max_index = 0
    for path in existing:
        m = re.match(r"prompt_(\d+)\.txt$", path.name)
        if m:
            max_index = max(max_index, int(m.group(1)))
    return directory / f"prompt_{max_index + 1:03d}.txt"


def save_prompt(project_id: str, prompt_text: str, outputs_dir: Path | None = None) -> dict:
    """
    生成済みプロンプトをoutputs/prompts/<project_id>/prompt_NNN.txtへ
    連番で保存する（既存ファイルは上書きしない、常に新規追加）。

    戻り値: {"ok": bool, "path": str | None, "error": str | None}
    例外を投げない。
    """
    try:
        if not project_id:
            return {"ok": False, "path": None, "error": "project_idを指定してください"}
        if not prompt_text or not prompt_text.strip():
            return {"ok": False, "path": None, "error": "保存するプロンプトが空です"}

        path = _next_prompt_path(project_id, outputs_dir)
        path.write_text(prompt_text, encoding="utf-8")
        return {"ok": True, "path": str(path), "error": None}
    except Exception as e:
        print(f"[警告] プロンプトの保存に失敗しました（{project_id}）：{e}")
        return {"ok": False, "path": None, "error": str(e)}


def list_prompts(project_id: str, outputs_dir: Path | None = None) -> list[dict]:
    """
    保存済みプロンプト一覧を返す（ファイル名昇順＝生成順）。
    戻り値: [{"filename": str, "path": str}, ...]
    ディレクトリ未存在・読み込み失敗時は空リストを返す。例外を投げない。
    """
    try:
        directory = _prompts_dir(project_id, outputs_dir)
        if not directory.exists():
            return []
        return [
            {"filename": p.name, "path": str(p)}
            for p in sorted(directory.glob("prompt_*.txt"))
        ]
    except Exception as e:
        print(f"[警告] プロンプト一覧の取得に失敗しました（{project_id}）：{e}")
        return []


def load_prompt(project_id: str, filename: str | None = None, outputs_dir: Path | None = None) -> str | None:
    """
    保存済みプロンプトを読み込む。filename未指定の場合は最新
    （番号が最大のファイル）を返す。未存在・読み込み失敗時はNoneを返す
    （例外を投げない）。
    """
    try:
        prompts = list_prompts(project_id, outputs_dir=outputs_dir)
        if not prompts:
            return None
        target = next((p for p in prompts if p["filename"] == filename), None) if filename else prompts[-1]
        if target is None:
            return None
        return Path(target["path"]).read_text(encoding="utf-8")
    except Exception as e:
        print(f"[警告] プロンプトの読み込みに失敗しました（{project_id}）：{e}")
        return None


def build_prompt(
    project_id: str,
    ip_name: str | None = None,
    save: bool = True,
    outputs_dir: Path | None = None,
    memory_dir: Path | None = None,
    projects_dir: Path | None = None,
) -> dict:
    """
    Quest108：IP Bible・Creative Style・Reference Summary・Project情報を
    統合し、画像生成AI向けのプロンプトを生成する。save=True（既定）の
    場合はoutputs/prompts/<project_id>/へ連番保存まで行う
    （Dashboardの「④ プロンプト生成」ボタンが生成・保存・表示を1回の
    実行でまとめて行えるようにするため）。

    Prompt Builder自体は画像生成AI（OpenAI / Google / Stability AI等）へは
    一切依存しない。IP未紐づけ・IP Bible/Style Guide未生成でも例外を
    投げず、取得できた情報だけでプロンプトを組み立てる。

    戻り値: {"ok": bool, "prompt": str | None, "path": str | None,
             "context": dict, "error": str | None}
    """
    try:
        context = _gather_context(
            project_id, ip_name=ip_name, outputs_dir=outputs_dir,
            memory_dir=memory_dir, projects_dir=projects_dir,
        )

        character = build_character_prompt(context)
        style = build_style_prompt(context)
        expression = build_expression_prompt(context)
        output = build_output_prompt(context)
        prompt_text = merge_prompt(character, style, expression, output, context.get("prompt_rules"))

        result = {"ok": True, "prompt": prompt_text, "path": None, "context": context, "error": None}

        if save:
            saved = save_prompt(project_id, prompt_text, outputs_dir=outputs_dir)
            result["path"] = saved.get("path")
            if not saved.get("ok"):
                result["error"] = saved.get("error")

        return result
    except Exception as e:
        print(f"[警告] プロンプトの生成に失敗しました（{project_id}）：{e}")
        return {"ok": False, "prompt": None, "path": None, "context": {}, "error": str(e)}


if __name__ == "__main__":
    # Quest108: 動作確認用のCLI導線。
    #   python services/prompt_builder_v2.py <project_id> [ip_name]
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
        ip_name = sys.argv[2] if len(sys.argv) > 2 else None
        result = build_prompt(project_id, ip_name=ip_name)
        print(f"[Prompt Builder v2] ok={result['ok']} path={result.get('path')}")
        if result.get("prompt"):
            print(result["prompt"])
    else:
        print("使い方: python services/prompt_builder_v2.py <project_id> [ip_name]")
