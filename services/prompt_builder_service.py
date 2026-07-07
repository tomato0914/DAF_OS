"""
DAF OS Quest98 — Prompt Builder Service

将来の画像生成AI導入に向けて、

  Character Bible → Style Guide → Execution Plan → Image Prompt

の流れでプロンプト文字列を組み立てるモジュール。Quest98では画像生成API は
まだ呼ばない（プロンプト文字列を作るところまで）。

Character Bibleは outputs/character_bibles/<bible_id>/ 配下の
character.md / style.md / palette.md を読み込む（Quest97までの
services/asset_generator_service.pyが持っていた「A cute shiba inu LINE
sticker saying "..."」というprompts.md用の即席プロンプト生成を、Character
Bibleベースの組み立てに置き換える）。

必要な関数：
- load_character_bible(bible_id): Character Bibleを読み込み、dictで返す
- build_image_prompt(phrase, character_bible, execution_context):
    1件のフレーズに対する画像生成プロンプト文字列を組み立てる
- build_prompts_for_phrases(phrases, character_bible, execution_context):
    複数フレーズ分をまとめて組み立てる（services/asset_generator_service.py
    が prompts.md の生成に使う）

CLI:
  python services/prompt_builder_service.py [bible_id]
    → 指定（省略時は既定の"dog_default"）Character Bibleでサンプルプロンプトを表示する

Character Bible未存在・読み込み失敗のいずれでも例外を投げず、決定的な
デフォルト文言にフォールバックする。
"""

import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_CHARACTER_BIBLES_DIR = _BASE_DIR / "outputs" / "character_bibles"
_DEFAULT_BIBLE_ID = "dog_default"

_DEFAULT_CHARACTER_DESC = "A cute shiba inu character"
_DEFAULT_STYLE_DESC = "simple flat illustration, transparent background"


def _read_text_or_empty(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def load_character_bible(bible_id: str = _DEFAULT_BIBLE_ID, base_dir: Path | None = None) -> dict:
    """
    outputs/character_bibles/<bible_id>/ から character.md / style.md /
    palette.md を読み込み、構造化データで返す。

    戻り値: {"bible_id": str, "exists": bool, "character": str,
             "style": str, "palette": str}
    ディレクトリ・各ファイルが存在しない場合も空文字列で埋めて返す
    （Character Bibleが無くてもPrompt Builder自体は動作を継続できるように
    するため）。例外を投げない。
    """
    try:
        base = (base_dir or _CHARACTER_BIBLES_DIR) / bible_id
        return {
            "bible_id": bible_id,
            "exists": base.exists(),
            "character": _read_text_or_empty(base / "character.md"),
            "style": _read_text_or_empty(base / "style.md"),
            "palette": _read_text_or_empty(base / "palette.md"),
        }
    except Exception as e:
        print(f"[警告] Character Bibleの読み込みに失敗しました（{bible_id}）：{e}")
        return {"bible_id": bible_id, "exists": False, "character": "", "style": "", "palette": ""}


def _first_meaningful_line(text: str) -> str:
    """
    character.md/style.mdはMarkdown（見出し・複数行）のことが多いため、
    プロンプトに使いやすい1行を取り出す。見出し行（"#"）・表の行（"|"）・
    空行は読み飛ばし、最初の本文行を返す（見つからなければ空文字列）。
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("|"):
            continue
        return stripped.lstrip("- ").strip()
    return ""


def build_image_prompt(
    phrase: str,
    character_bible: dict | None = None,
    execution_context: str | None = None,
) -> str:
    """
    Character Bible（character.md/style.md）とフレーズから、将来の画像生成API
    向けのプロンプト文字列を1件組み立てる。Quest98ではプロンプト文字列を作る
    ところまでで、実際の画像生成APIは呼ばない。

    Character Bibleが無い・読み込めない場合は、Quest90〜97までのデフォルト
    文言（"A cute shiba inu character" / "simple flat illustration,
    transparent background"）にフォールバックする。
    """
    bible = character_bible or load_character_bible()
    character_line = _first_meaningful_line(bible.get("character") or "") or _DEFAULT_CHARACTER_DESC
    style_line = _first_meaningful_line(bible.get("style") or "") or _DEFAULT_STYLE_DESC

    prompt = f'{character_line} saying "{phrase}", {style_line}'
    if execution_context:
        prompt += f" ({execution_context})"
    return prompt


def build_prompts_for_phrases(
    phrases: list[str],
    character_bible: dict | None = None,
    execution_context: str | None = None,
) -> list[str]:
    """複数フレーズ分のプロンプトをまとめて組み立てる（順序はphrasesと対応）。"""
    bible = character_bible or load_character_bible()
    return [
        build_image_prompt(phrase, character_bible=bible, execution_context=execution_context)
        for phrase in phrases
    ]


if __name__ == "__main__":
    # Quest98: 動作確認用のCLI導線。
    #   python services/prompt_builder_service.py [bible_id]
    bible_id = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_BIBLE_ID
    bible = load_character_bible(bible_id)
    print(f"[Prompt Builder] Character Bible: {bible_id}（exists={bible['exists']}）")
    sample_prompt = build_image_prompt("おはよう", character_bible=bible)
    print(f"サンプルプロンプト: {sample_prompt}")
