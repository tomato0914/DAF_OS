"""
DAF OS Quest105 — IP Bible Generator

Quest104のIP Memory（DNA）から、人とAIが共通認識として使える「IP Bible」
（IP全体の設計書）をMarkdownで生成する。

設計思想（全体の流れ）：
  Reference → Reference Analysis（Quest103）→ IP Memory（Quest104）→
  IP DNA → IP Bible（本Quest）→ Prompt Builder（将来）→ Asset Generation（将来）

IP BibleはCharacter設定だけではなく、Identity・Story・Core Personality・
Visual Identity・Color Palette・World・Brand Position・Style Rules・
Forbidden Rules・Prompt Examples・Future Evolutionを含むIP全体の設計書と
する。Vega（Chief IP Designer、docs/organization.md参照）視点でAI生成する
（OPENROUTER_API_KEY設定時）。未設定・AI失敗時は、IP DNAの値をそのまま
差し込むテンプレートへフォールバックする（例外を投げない）。

保存先：
  outputs/ip_memory/<ip_name>/ip_bible.md
  （ip_memory.jsonと同じフォルダ。Reference Libraryとは分離済み＝Quest104を踏襲）

必要な関数：
- generate_ip_bible(ip_name):  IP DNAからIP Bible（Markdown）の"提案"を生成する
                                （保存はしない）
- save_ip_bible(ip_name, markdown): ip_bible.mdへ保存する
- load_ip_bible(ip_name):      保存済みip_bible.mdを読み込む

CLI:
  python services/ip_bible_service.py <ip_name>

IP未存在・DNA未設定・AI呼び出し失敗・書き込み失敗のいずれでも例外を
投げず、DAF OS全体を止めない。
"""

import os
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_IP_BIBLE_FILENAME = "ip_bible.md"

_BIBLE_SECTIONS = (
    "Identity", "Story", "Core Personality", "Visual Identity",
    "Color Palette", "World", "Brand Position", "Style Rules",
    "Forbidden Rules", "Prompt Examples", "Future Evolution",
)

_VEGA_BIBLE_PROMPT = """あなたはVega、DAF OSのChief IP Designerです。
以下はIP「{ip_name}」のDNA（IP Memoryから抽出された本質的な特徴）です。
これを土台に、人とAIが共通認識として使える「IP Bible」（IP全体の設計書）を
Markdownで作成してください。単なるCharacter設定ではなく、IPの世界観・
ブランド方針まで含めた設計書にしてください。

IP DNA:
{dna_text}

出力は必ずMarkdownで、次の見出しをこの順番・この英語表記のまま
「## 見出し名」として含めてください（本文は日本語で構いません）：
Identity, Story, Core Personality, Visual Identity, Color Palette, World,
Brand Position, Style Rules, Forbidden Rules, Prompt Examples, Future Evolution

注意：
- DNAに存在しない設定を断定的に創作しすぎないこと（Storyのみ、DNAと矛盾
  しない範囲で短い物語的説明を補ってよい）
- Prompt Examplesは画像生成AIへ渡す想定の英語プロンプト例を2〜3個、
  箇条書きで示す（画像生成自体は行わない）
- Forbidden Rulesにはmust_notの内容を反映する
- Future EvolutionにはこのIPが将来どう成長しうるかの方向性を簡潔に書く
- 説明文やコードブロック記法（```）で全体を囲まず、Markdown本文のみを返すこと
"""


def _dna_to_text(dna: dict) -> str:
    lines = []
    for group in ("identity", "personality", "visual", "brand", "rules"):
        values = dna.get(group) or {}
        for key, value in values.items():
            if value:
                lines.append(f"- {group}.{key}: {value}")
    if dna.get("keywords"):
        lines.append(f"- keywords: {', '.join(dna['keywords'])}")
    return "\n".join(lines) if lines else "（DNAはまだ空です）"


def _get(dna: dict, group: str, key: str, default: str = "（未設定）") -> str:
    value = (dna.get(group) or {}).get(key)
    return value if value else default


def _template_ip_bible(ip_name: str, dna: dict) -> str:
    """
    OPENROUTER_API_KEY未設定・AI呼び出し失敗時のフォールバック。
    IP DNAの値をそのまま差し込んだ決定的なMarkdownテンプレートを返す
    （AIによる創作は行わない）。
    """
    identity_name = _get(dna, "identity", "name", ip_name)
    species = _get(dna, "identity", "species")
    ip_type = _get(dna, "identity", "type")
    personality = _get(dna, "personality", "personality")
    values = _get(dna, "personality", "values")
    target_emotion = _get(dna, "personality", "target_emotion")
    color_palette = _get(dna, "visual", "color_palette")
    line_style = _get(dna, "visual", "line_style")
    eye_style = _get(dna, "visual", "eye_style")
    body_style = _get(dna, "visual", "body_style")
    positioning = _get(dna, "brand", "positioning")
    audience = _get(dna, "brand", "audience")
    must_have = _get(dna, "rules", "must_have")
    must_not = _get(dna, "rules", "must_not")
    keywords = dna.get("keywords") or []
    keywords_text = "、".join(keywords) if keywords else "（未設定）"

    prompt_example_parts = [p for p in (identity_name, species, line_style, color_palette, body_style) if p and p != "（未設定）"]
    prompt_example = ", ".join(prompt_example_parts) if prompt_example_parts else "（DNAを充実させるとここにプロンプト例が生成されます）"

    lines = [
        f"# {identity_name} — IP Bible",
        "",
        f"> IP名: {ip_name}",
        "",
        "## Identity",
        "",
        f"- Name: {identity_name}",
        f"- Species: {species}",
        f"- Type: {ip_type}",
        "",
        "## Story",
        "",
        "（IP Memoryにはまだストーリー情報が登録されていません。"
        "Character Bible・World Bibleの実装時に拡張予定です。）",
        "",
        "## Core Personality",
        "",
        f"- Personality: {personality}",
        f"- Values: {values}",
        f"- Target Emotion: {target_emotion}",
        "",
        "## Visual Identity",
        "",
        f"- Line Style: {line_style}",
        f"- Eye Style: {eye_style}",
        f"- Body Style: {body_style}",
        "",
        "## Color Palette",
        "",
        f"- {color_palette}",
        "",
        "## World",
        "",
        "（World Bibleはまだ実装されていません。Quest104のIP Memory構造に"
        "領域のみ確保済みです。）",
        "",
        "## Brand Position",
        "",
        f"- Positioning: {positioning}",
        f"- Audience: {audience}",
        "",
        "## Style Rules",
        "",
        f"- Must Have: {must_have}",
        "",
        "## Forbidden Rules",
        "",
        f"- Must Not: {must_not}",
        "",
        "## Prompt Examples",
        "",
        f"- {prompt_example}",
        "",
        "## Future Evolution",
        "",
        "（Evolution Historyはまだ記録されていません。DNAが更新されるたびに"
        "このセクションを充実させていく想定です。）",
        "",
        "---",
        "",
        f"Keywords: {keywords_text}",
        "",
        "_このIP Bibleはテンプレートから自動生成されました"
        "（OPENROUTER_API_KEY未設定、またはAI生成に失敗したため）。_",
    ]
    return "\n".join(lines) + "\n"


def generate_ip_bible(ip_name: str, outputs_dir: Path | None = None) -> dict:
    """
    Quest105：指定IPのIP Memory（DNA）からIP Bible（Markdown）の"提案"を
    生成する。ip_bible.mdへの保存は行わない（save_ip_bible()を明示的に
    呼んだ時のみ反映。Quest103/104と同じ「AIは提案、CEOが確認・保存」方針）。

    OPENROUTER_API_KEY設定時はVega視点のプロンプトでAI生成する。未設定・
    IP未存在・AI呼び出し失敗のいずれでも例外を投げず、DNAの値をそのまま
    差し込んだ決定的なテンプレートへフォールバックする。

    戻り値: {"ok": bool, "markdown": str | None, "source": str,
             "error": str | None}
    """
    try:
        from services.ip_memory_service import load_ip

        ip = load_ip(ip_name, outputs_dir=outputs_dir)
        if ip is None:
            return {"ok": False, "markdown": None, "source": None,
                     "error": "指定されたIPが見つかりません（先にIPを作成してください）"}

        dna = ip.get("dna") or {}

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            markdown = _template_ip_bible(ip_name, dna)
            return {"ok": True, "markdown": markdown, "source": "template", "error": None}

        try:
            import litellm

            prompt = _VEGA_BIBLE_PROMPT.format(ip_name=ip_name, dna_text=_dna_to_text(dna))
            response = litellm.completion(
                model="openrouter/openai/gpt-4o-mini",
                api_key=api_key,
                api_base="https://openrouter.ai/api/v1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                timeout=90,
            )
            content = (response["choices"][0]["message"]["content"] or "").strip()
            if not content or "## Identity" not in content:
                # AIが指定フォーマットを守らなかった場合もテンプレートへ
                # フォールバックする（壊れたBibleを提案しないため）。
                raise ValueError("AI応答が期待するMarkdown構造ではありません")
            return {"ok": True, "markdown": content, "source": "ai", "error": None}
        except Exception as e:
            print(f"[警告] IP BibleのAI生成に失敗しました（{ip_name}）：{e}")
            markdown = _template_ip_bible(ip_name, dna)
            return {"ok": True, "markdown": markdown, "source": "template",
                     "error": f"AI生成に失敗したためテンプレートを使用：{e}"}
    except Exception as e:
        print(f"[警告] IP Bibleの生成に失敗しました（{ip_name}）：{e}")
        return {"ok": False, "markdown": None, "source": None, "error": str(e)}


def save_ip_bible(ip_name: str, markdown: str, outputs_dir: Path | None = None) -> dict:
    """
    生成済みIP Bible（Markdown）をoutputs/ip_memory/<ip_name>/ip_bible.md
    へ保存する。IPフォルダが存在しない場合はエラーを返す（先にIP作成が必要）。

    戻り値: {"ok": bool, "path": str | None, "error": str | None}
    例外を投げない。
    """
    try:
        from services.ip_memory_service import ip_dir_path, load_ip

        if load_ip(ip_name, outputs_dir=outputs_dir) is None:
            return {"ok": False, "path": None, "error": "指定されたIPが見つかりません"}

        ip_dir = ip_dir_path(ip_name, outputs_dir=outputs_dir)
        if ip_dir is None:
            return {"ok": False, "path": None, "error": "無効なIP名です"}

        ip_dir.mkdir(parents=True, exist_ok=True)
        path = ip_dir / _IP_BIBLE_FILENAME
        path.write_text(markdown or "", encoding="utf-8")
        return {"ok": True, "path": str(path), "error": None}
    except Exception as e:
        print(f"[警告] IP Bibleの保存に失敗しました（{ip_name}）：{e}")
        return {"ok": False, "path": None, "error": str(e)}


def load_ip_bible(ip_name: str, outputs_dir: Path | None = None) -> str | None:
    """
    保存済みip_bible.mdを読み込む。未存在・読み込み失敗の場合はNoneを返す
    （例外を投げない）。
    """
    try:
        from services.ip_memory_service import ip_dir_path

        ip_dir = ip_dir_path(ip_name, outputs_dir=outputs_dir)
        if ip_dir is None:
            return None
        path = ip_dir / _IP_BIBLE_FILENAME
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[警告] IP Bibleの読み込みに失敗しました（{ip_name}）：{e}")
        return None


if __name__ == "__main__":
    # Quest105: 動作確認用のCLI導線。
    #   python services/ip_bible_service.py <ip_name>
    if len(sys.argv) > 1:
        result = generate_ip_bible(sys.argv[1])
        print(f"[IP Bible] source={result.get('source')} ok={result.get('ok')}")
        if result.get("markdown"):
            print(result["markdown"])
    else:
        print("使い方: python services/ip_bible_service.py <ip_name>")
