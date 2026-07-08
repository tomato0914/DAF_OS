"""
DAF OS Quest107 — Creative Style Engine

設計思想（全体の流れ）：
  Reference → Reference Analysis（Quest103）→ IP Memory（Quest104）→
  IP DNA → IP Bible（Quest105）→ Creative Style（本Quest）→
  Prompt Builder（将来）→ Asset Generation（将来）

IP DNA・IP Bibleはまだ「設計書」であり、実際に画像を生成する際にAIへ渡す
具体的な描画ルール（配色・線・形・表情・構図・文字組・NG事項）と、
Prompt Builder（将来）が機械的に使えるルール（always/prefer/avoid/never）
までは落とし込まれていなかった。Quest107でこの最後の変換層を実装する。

成果物：
  outputs/ip_memory/<ip_name>/style_guide.md    （人が読むMarkdown）
  outputs/ip_memory/<ip_name>/prompt_rules.json （AI/Prompt Builderが読むJSON）
  （ip_bible.mdと同じフォルダ。ip_memory.json本体・Reference Library・
  Asset Generator・Quality Control Engineのいずれにも書き込まない）

Vega（Chief IP Designer）視点でAI生成する（OPENROUTER_API_KEY設定時、
IP DNA・IP Bibleを入力とする）。未設定・AI失敗時は、IP DNAの値をそのまま
差し込む決定的なテンプレートへフォールバックする（例外を投げない）。
画像生成AI（Image Generation）・AI Reviewは行わない。

必要な関数：
- generate_style_guide(ip_name):  Style Guide（Markdown）の"提案"を生成する
                                   （保存はしない）
- generate_prompt_rules(ip_name): Prompt Rules（JSON）の"提案"を生成する
                                   （保存はしない）
- save_style_guide(ip_name, markdown): style_guide.mdへ保存する
- load_style_guide(ip_name):      保存済みstyle_guide.mdを読み込む
- save_prompt_rules(ip_name, rules): prompt_rules.jsonへ保存する
- load_prompt_rules(ip_name):     保存済みprompt_rules.jsonを読み込む

CLI:
  python services/creative_style_service.py <ip_name>

IP未存在・DNA未設定・AI呼び出し失敗・書き込み失敗のいずれでも例外を
投げず、DAF OS全体を止めない。
"""

import json
import os
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_STYLE_GUIDE_FILENAME = "style_guide.md"
_PROMPT_RULES_FILENAME = "prompt_rules.json"

_STYLE_GUIDE_SECTIONS = (
    "Color Rules", "Line Rules", "Shape Rules", "Expression Rules",
    "Composition Rules", "Typography Rules", "Negative Rules",
)
_PROMPT_RULE_KEYS = ("always", "prefer", "avoid", "never")

_VEGA_STYLE_GUIDE_PROMPT = """あなたはVega、DAF OSのChief IP Designerです。
Sol（Visual Designer）・Astra（Brand Guardian）・Luna（Story Designer）の
視点も取り入れながら、IP「{ip_name}」のIP DNAとIP Bibleをもとに、実制作
（イラスト・画像生成AI・LINEスタンプ等）で使う具体的な描画ルール
「Style Guide」をMarkdownで作成してください。

IP DNA:
{dna_text}

IP Bible（抜粋）:
{bible_text}

出力は必ずMarkdownで、次の見出しをこの順番・この英語表記のまま
「## 見出し名」として含めてください（本文は日本語で構いません）：
Color Rules, Line Rules, Shape Rules, Expression Rules, Composition Rules,
Typography Rules, Negative Rules

注意：
- IP DNA・IP Bibleと矛盾しないルールにすること
- 各セクションは実制作者・画像生成AIがそのまま従える具体的な指示にする
  （例：「パステルカラーを基調とする」ではなく「主色は#F5D5C8、差し色は
  #A8D8D0を上限2色まで」のように、可能な範囲で具体化する）
- Negative RulesにはIP DNAのmust_notを必ず反映する
- 説明文やコードブロック記法（```）で全体を囲まず、Markdown本文のみを返すこと
"""

_VEGA_PROMPT_RULES_PROMPT = """あなたはVega、DAF OSのChief IP Designerです。
IP「{ip_name}」のIP DNAとIP Bibleをもとに、画像生成AIへ渡すプロンプトの
機械的なルール（Prompt Rules）をJSONで作成してください。

IP DNA:
{dna_text}

IP Bible（抜粋）:
{bible_text}

必ず次のキーだけを持つJSONオブジェクトで返してください（説明文やコード
ブロック記法は不要）。各キーの値は英語の短いプロンプト断片（3〜8個程度）
の配列にしてください：
{{
  "always": ["どの画像にも必ず含めるべき要素"],
  "prefer": ["できるだけ含めたい要素"],
  "avoid": ["できるだけ避けたい要素"],
  "never": ["絶対に含めてはいけない要素（IP DNAのmust_notを反映）"]
}}
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


def _template_style_guide(ip_name: str, dna: dict) -> str:
    """
    OPENROUTER_API_KEY未設定・AI呼び出し失敗時のフォールバック。
    IP DNAの値をそのまま差し込んだ決定的なMarkdownテンプレートを返す
    （AIによる創作は行わない）。
    """
    identity_name = _get(dna, "identity", "name", ip_name)
    color_palette = _get(dna, "visual", "color_palette")
    line_style = _get(dna, "visual", "line_style")
    eye_style = _get(dna, "visual", "eye_style")
    body_style = _get(dna, "visual", "body_style")
    target_emotion = _get(dna, "personality", "target_emotion")
    must_have = _get(dna, "rules", "must_have")
    must_not = _get(dna, "rules", "must_not")
    keywords = dna.get("keywords") or []
    keywords_text = "、".join(keywords) if keywords else "（未設定）"

    lines = [
        f"# {identity_name} — Style Guide",
        "",
        f"> IP名: {ip_name}",
        "",
        "## Color Rules",
        "",
        f"- Color Palette: {color_palette}",
        "",
        "## Line Rules",
        "",
        f"- Line Style: {line_style}",
        "",
        "## Shape Rules",
        "",
        f"- Body Style: {body_style}",
        "",
        "## Expression Rules",
        "",
        f"- Eye Style: {eye_style}",
        f"- Target Emotion: {target_emotion}",
        "",
        "## Composition Rules",
        "",
        "（IP DNAには構図に関する情報がまだありません。IP Bible・Reference"
        "を参考に手動で追記してください。）",
        "",
        "## Typography Rules",
        "",
        "（IP DNAには文字組に関する情報がまだありません。LINEスタンプ等で"
        "文字を使う場合は、Color Rules・Line Rulesと一貫させてください。）",
        "",
        "## Negative Rules",
        "",
        f"- Must Not: {must_not}",
        "",
        "---",
        "",
        f"Must Have: {must_have}",
        f"Keywords: {keywords_text}",
        "",
        "_このStyle GuideはテンプレートからIP DNAの値を差し込んで自動生成"
        "されました（OPENROUTER_API_KEY未設定、またはAI生成に失敗したため）。_",
    ]
    return "\n".join(lines) + "\n"


def _template_prompt_rules(dna: dict) -> dict:
    """OPENROUTER_API_KEY未設定・AI失敗時のフォールバック（IP DNAの値をそのまま分類する）。"""
    always = []
    prefer = list(dna.get("keywords") or [])
    avoid: list[str] = []
    never = []

    color_palette = _get(dna, "visual", "color_palette", "")
    if color_palette and color_palette != "（未設定）":
        always.append(color_palette)
    line_style = _get(dna, "visual", "line_style", "")
    if line_style and line_style != "（未設定）":
        always.append(line_style)
    must_have = _get(dna, "rules", "must_have", "")
    if must_have and must_have != "（未設定）":
        always.append(must_have)
    must_not = _get(dna, "rules", "must_not", "")
    if must_not and must_not != "（未設定）":
        never.append(must_not)

    return {"always": always, "prefer": prefer, "avoid": avoid, "never": never}


def _bible_excerpt(bible_markdown: str | None, max_chars: int = 2000) -> str:
    if not bible_markdown:
        return "（IP Bibleはまだ生成・保存されていません）"
    text = bible_markdown.strip()
    return text if len(text) <= max_chars else text[:max_chars] + "\n...(以下省略)"


def generate_style_guide(ip_name: str, outputs_dir: Path | None = None) -> dict:
    """
    Quest107：指定IPのIP DNA・IP Bibleから、Style Guide（Markdown）の
    "提案"を生成する。style_guide.mdへの保存は行わない
    （save_style_guide()を明示的に呼んだ時のみ反映）。

    OPENROUTER_API_KEY設定時はVega視点のプロンプトでAI生成する。未設定・
    IP未存在・AI呼び出し失敗のいずれでも例外を投げず、DNAの値をそのまま
    差し込んだ決定的なテンプレートへフォールバックする。

    戻り値: {"ok": bool, "markdown": str | None, "source": str,
             "error": str | None}
    """
    try:
        from services.ip_memory_service import load_ip
        from services.ip_bible_service import load_ip_bible

        ip = load_ip(ip_name, outputs_dir=outputs_dir)
        if ip is None:
            return {"ok": False, "markdown": None, "source": None,
                     "error": "指定されたIPが見つかりません（先にIPを作成してください）"}

        dna = ip.get("dna") or {}
        bible_text = _bible_excerpt(load_ip_bible(ip_name, outputs_dir=outputs_dir))

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return {"ok": True, "markdown": _template_style_guide(ip_name, dna),
                     "source": "template", "error": None}

        try:
            import litellm

            prompt = _VEGA_STYLE_GUIDE_PROMPT.format(
                ip_name=ip_name, dna_text=_dna_to_text(dna), bible_text=bible_text,
            )
            response = litellm.completion(
                model="openrouter/openai/gpt-4o-mini",
                api_key=api_key,
                api_base="https://openrouter.ai/api/v1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                timeout=90,
            )
            content = (response["choices"][0]["message"]["content"] or "").strip()
            if not content or "## Color Rules" not in content:
                raise ValueError("AI応答が期待するMarkdown構造ではありません")
            return {"ok": True, "markdown": content, "source": "ai", "error": None}
        except Exception as e:
            print(f"[警告] Style GuideのAI生成に失敗しました（{ip_name}）：{e}")
            return {"ok": True, "markdown": _template_style_guide(ip_name, dna),
                     "source": "template", "error": f"AI生成に失敗したためテンプレートを使用：{e}"}
    except Exception as e:
        print(f"[警告] Style Guideの生成に失敗しました（{ip_name}）：{e}")
        return {"ok": False, "markdown": None, "source": None, "error": str(e)}


def _parse_prompt_rules_json(raw_text: str) -> dict:
    text = (raw_text or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("AI応答からJSONを抽出できませんでした")
    data = json.loads(text[start:end + 1])

    rules = {}
    for key in _PROMPT_RULE_KEYS:
        value = data.get(key)
        if not isinstance(value, list):
            value = [v.strip() for v in str(value or "").split(",") if v.strip()]
        rules[key] = [str(v).strip() for v in value if str(v).strip()]
    return rules


def generate_prompt_rules(ip_name: str, outputs_dir: Path | None = None) -> dict:
    """
    Quest107：指定IPのIP DNA・IP Bibleから、Prompt Rules（JSON:
    always/prefer/avoid/never）の"提案"を生成する。prompt_rules.jsonへの
    保存は行わない（save_prompt_rules()を明示的に呼んだ時のみ反映）。

    OPENROUTER_API_KEY設定時はVega視点のプロンプトでAI生成する。未設定・
    IP未存在・AI呼び出し失敗のいずれでも例外を投げず、DNAの値をそのまま
    分類した決定的なフォールバックを返す。

    戻り値: {"ok": bool, "rules": dict | None, "source": str, "error": str | None}
    """
    try:
        from services.ip_memory_service import load_ip
        from services.ip_bible_service import load_ip_bible

        ip = load_ip(ip_name, outputs_dir=outputs_dir)
        if ip is None:
            return {"ok": False, "rules": None, "source": None,
                     "error": "指定されたIPが見つかりません（先にIPを作成してください）"}

        dna = ip.get("dna") or {}
        bible_text = _bible_excerpt(load_ip_bible(ip_name, outputs_dir=outputs_dir))

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return {"ok": True, "rules": _template_prompt_rules(dna), "source": "template", "error": None}

        try:
            import litellm

            prompt = _VEGA_PROMPT_RULES_PROMPT.format(
                ip_name=ip_name, dna_text=_dna_to_text(dna), bible_text=bible_text,
            )
            response = litellm.completion(
                model="openrouter/openai/gpt-4o-mini",
                api_key=api_key,
                api_base="https://openrouter.ai/api/v1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                timeout=90,
            )
            content = response["choices"][0]["message"]["content"]
            rules = _parse_prompt_rules_json(content)
            return {"ok": True, "rules": rules, "source": "ai", "error": None}
        except Exception as e:
            print(f"[警告] Prompt RulesのAI生成に失敗しました（{ip_name}）：{e}")
            return {"ok": True, "rules": _template_prompt_rules(dna), "source": "template",
                     "error": f"AI生成に失敗したためテンプレートを使用：{e}"}
    except Exception as e:
        print(f"[警告] Prompt Rulesの生成に失敗しました（{ip_name}）：{e}")
        return {"ok": False, "rules": None, "source": None, "error": str(e)}


def save_style_guide(ip_name: str, markdown: str, outputs_dir: Path | None = None) -> dict:
    """
    生成済みStyle Guide（Markdown）をoutputs/ip_memory/<ip_name>/
    style_guide.md へ保存する。IPが存在しない場合はエラーを返す。

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
        path = ip_dir / _STYLE_GUIDE_FILENAME
        path.write_text(markdown or "", encoding="utf-8")
        return {"ok": True, "path": str(path), "error": None}
    except Exception as e:
        print(f"[警告] Style Guideの保存に失敗しました（{ip_name}）：{e}")
        return {"ok": False, "path": None, "error": str(e)}


def load_style_guide(ip_name: str, outputs_dir: Path | None = None) -> str | None:
    """保存済みstyle_guide.mdを読み込む。未存在・失敗時はNoneを返す（例外を投げない）。"""
    try:
        from services.ip_memory_service import ip_dir_path

        ip_dir = ip_dir_path(ip_name, outputs_dir=outputs_dir)
        if ip_dir is None:
            return None
        path = ip_dir / _STYLE_GUIDE_FILENAME
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[警告] Style Guideの読み込みに失敗しました（{ip_name}）：{e}")
        return None


def save_prompt_rules(ip_name: str, rules: dict, outputs_dir: Path | None = None) -> dict:
    """
    生成済みPrompt Rules（dict）をoutputs/ip_memory/<ip_name>/
    prompt_rules.json へ保存する。always/prefer/avoid/never以外のキーは
    無視し、欠けているキーは空配列で補う。IPが存在しない場合はエラーを返す。

    戻り値: {"ok": bool, "path": str | None, "rules": dict | None, "error": str | None}
    例外を投げない。
    """
    try:
        from services.ip_memory_service import ip_dir_path, load_ip

        if load_ip(ip_name, outputs_dir=outputs_dir) is None:
            return {"ok": False, "path": None, "rules": None, "error": "指定されたIPが見つかりません"}

        ip_dir = ip_dir_path(ip_name, outputs_dir=outputs_dir)
        if ip_dir is None:
            return {"ok": False, "path": None, "rules": None, "error": "無効なIP名です"}

        normalized = {}
        for key in _PROMPT_RULE_KEYS:
            value = (rules or {}).get(key) or []
            if isinstance(value, str):
                value = [v.strip() for v in value.split(",") if v.strip()]
            normalized[key] = [str(v).strip() for v in value if str(v).strip()]

        ip_dir.mkdir(parents=True, exist_ok=True)
        path = ip_dir / _PROMPT_RULES_FILENAME
        path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "path": str(path), "rules": normalized, "error": None}
    except Exception as e:
        print(f"[警告] Prompt Rulesの保存に失敗しました（{ip_name}）：{e}")
        return {"ok": False, "path": None, "rules": None, "error": str(e)}


def load_prompt_rules(ip_name: str, outputs_dir: Path | None = None) -> dict | None:
    """保存済みprompt_rules.jsonを読み込む。未存在・破損時はNoneを返す（例外を投げない）。"""
    try:
        from services.ip_memory_service import ip_dir_path

        ip_dir = ip_dir_path(ip_name, outputs_dir=outputs_dir)
        if ip_dir is None:
            return None
        path = ip_dir / _PROMPT_RULES_FILENAME
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[警告] Prompt Rulesの読み込みに失敗しました（{ip_name}）：{e}")
        return None


if __name__ == "__main__":
    # Quest107: 動作確認用のCLI導線。
    #   python services/creative_style_service.py <ip_name>
    if len(sys.argv) > 1:
        ip_name = sys.argv[1]
        style = generate_style_guide(ip_name)
        print(f"[Style Guide] source={style.get('source')} ok={style.get('ok')}")
        if style.get("markdown"):
            print(style["markdown"])
        rules = generate_prompt_rules(ip_name)
        print(f"[Prompt Rules] source={rules.get('source')} ok={rules.get('ok')}")
        if rules.get("rules"):
            print(json.dumps(rules["rules"], ensure_ascii=False, indent=2))
    else:
        print("使い方: python services/creative_style_service.py <ip_name>")
