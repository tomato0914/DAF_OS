"""
DAF OS Quest110 — AI Review Engine

Quest109で生成したLINEスタンプ画像を、必要な時だけAIレビューできる
仕組みを追加する。DAFのLean AI First方針において、判定の優先順位は：

  1. Python Quality Check（services/quality_control_service.py、Quest106）
  2. Rule Engine（本Engineのfallback_rule_review）
  3. AI Review（本Engine、必要な時だけ）
  4. CEO承認

AIは「最後の専門家」として扱う：常時実行はせず、CEOがDashboardから
明示的にレビューを依頼した場合（manual_request=True）、またはPython
Quality CheckでWARNING/FAILが出た場合のみ実行する候補にする（本Quest時点の
初期実装ではDashboardボタンからの手動レビューのみ配線する）。

パイプライン：
  生成画像一覧取得（services/image_generation_pipeline.py） →
  metadata取得 → Creative Style / IP Bible / Prompt情報を参照
  （services/creative_style_service.py・services/ip_bible_service.py・
  services/prompt_builder_v2.py） → Python Quality Check
  （services/quality_control_service.py）→ レビュー対象を判定 →
  必要な画像だけAIレビュー → review_report.json保存

レビュー観点（6項目、各{"score": 1-5, "comment": str, "needs_fix": bool}）：
  character_consistency / style_consistency / line_sticker_usability /
  text_readability / emotional_clarity / commercial_quality

AI呼び出しはOPENROUTER_API_KEY経由（Quest103のAI画像解析・Quest105の
IP Bible生成・Quest107のCreative Style生成と同じ、gpt-4o-mini・
OpenRouter経由の方針を踏襲）。未設定・呼び出し失敗のいずれの場合も例外を
投げず、ルールベースの簡易レビュー（review_mode="fallback_rule_review"）
へフォールバックする。

このEngineは「合否判定」ではなく、CEOの判断を助けるレポートを作るのが
目的。画像修正・再生成・ZIP化は行わない（Quest110の対象外）。
Image Generation Pipeline（Quest109）・Prompt Builder v2（Quest108）には
読み取り専用でのみアクセスし、変更を加えない。

保存先：
  outputs/reviews/<project_id>/review_report.json

必要な関数：
- get_generated_images(project_id):     生成済み画像一覧・metadataを取得する
                                         （image_generation_pipeline.pyへ委譲）
- should_run_ai_review(manual_request, quality_report): AIレビューを実行
                                         すべきか判定する
- review_images(project_id, ip_name=None, manual_request=True):
                                         レビュー全体を実行し、
                                         review_report.jsonまで保存する
- save_review_report(project_id, report): review_report.jsonを保存する
- load_review_report(project_id):       保存済みreview_report.jsonを読み込む

CLI:
  python services/ai_review_engine.py <project_id> [ip_name]

生成画像未存在・AI呼び出し失敗・書き込み失敗のいずれでも例外を投げず、
DAF OS全体を止めない。
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"
_REVIEWS_DIR_NAME = "reviews"
_REPORT_FILENAME = "review_report.json"

REVIEW_MODE_AI = "ai"
REVIEW_MODE_FALLBACK = "fallback_rule_review"

REVIEW_ITEM_NAMES = (
    "character_consistency", "style_consistency", "line_sticker_usability",
    "text_readability", "emotional_clarity", "commercial_quality",
)

_MAX_REVIEW_IMAGES = 3  # Quest109のMAX_GENERATION_COUNTと同じ上限（コスト・安全のため）

_VEGA_REVIEW_PROMPT = """あなたはVega、DAF OSのChief IP Designerです。
以下の生成済みLINEスタンプ画像を、Creative Direction（IP DNA・IP Bible・
Style Guide・生成に使ったPrompt）と照らし合わせてレビューしてください。

Prompt:
{prompt_text}

Creative Style（Style Guide抜粋）:
{style_guide_excerpt}

IP Bible（抜粋）:
{ip_bible_excerpt}

必ず次のキーだけを持つJSONオブジェクトで返してください（説明文やコード
ブロック記法は不要）：
{{
  "summary": "全体講評（日本語2〜3文）",
  "items": {{
    "character_consistency": {{"score": 1-5, "comment": "...", "needs_fix": true/false}},
    "style_consistency": {{"score": 1-5, "comment": "...", "needs_fix": true/false}},
    "line_sticker_usability": {{"score": 1-5, "comment": "...", "needs_fix": true/false}},
    "text_readability": {{"score": 1-5, "comment": "...", "needs_fix": true/false}},
    "emotional_clarity": {{"score": 1-5, "comment": "...", "needs_fix": true/false}},
    "commercial_quality": {{"score": 1-5, "comment": "...", "needs_fix": true/false}}
  }},
  "images": [
    {{"filename": "画像のファイル名", "comment": "その画像に対する短いコメント"}}
  ]
}}
"""


def get_generated_images(
    project_id: str,
    asset_type: str = "line_sticker",
    outputs_dir: Path | None = None,
) -> dict:
    """
    Quest109の生成済み画像一覧・metadataを取得する（読み取り専用、
    services/image_generation_pipeline.pyへそのまま委譲）。
    """
    try:
        from services.image_generation_pipeline import list_generated_images
        return list_generated_images(project_id, asset_type=asset_type, outputs_dir=outputs_dir)
    except Exception as e:
        print(f"[警告] 生成済み画像一覧の取得に失敗しました（{project_id}）：{e}")
        return {"exists": False, "project_id": project_id, "asset_type": asset_type,
                 "image_files": [], "metadata": None}


def should_run_ai_review(manual_request: bool, quality_report: dict | None) -> bool:
    """
    AIレビューを実行すべきか判定する。DAFのLean AI First方針：AIレビューは
    「必要な時だけ」実行し、常時実行はしない。

    True になる条件：
      - manual_request=True（CEOがDashboardから明示的に依頼した場合）
      - または quality_report（Quest106）にWARNING/FAILが1件でも含まれる場合
        （Python Quality Checkが「要確認」と判定した場合の補助判断として）
    """
    if manual_request:
        return True
    if not quality_report:
        return False
    checks = quality_report.get("checks") or []
    return any(c.get("status") in ("WARNING", "FAIL") for c in checks)


def _gather_review_context(
    project_id: str,
    ip_name: str | None,
    outputs_dir: Path | None,
) -> dict:
    """AIレビュー・フォールバックレビュー双方が使うコンテキストを集める（例外を投げない）。"""
    context = {"prompt_text": "", "style_guide": "", "ip_bible": ""}

    try:
        from services.prompt_builder_v2 import load_prompt
        context["prompt_text"] = load_prompt(project_id, outputs_dir=outputs_dir) or ""
    except Exception as e:
        print(f"[警告] Promptの読み込みに失敗しました（{project_id}）：{e}")

    if ip_name:
        try:
            from services.creative_style_service import load_style_guide
            context["style_guide"] = load_style_guide(ip_name, outputs_dir=outputs_dir) or ""
        except Exception as e:
            print(f"[警告] Style Guideの読み込みに失敗しました（{ip_name}）：{e}")
        try:
            from services.ip_bible_service import load_ip_bible
            context["ip_bible"] = load_ip_bible(ip_name, outputs_dir=outputs_dir) or ""
        except Exception as e:
            print(f"[警告] IP Bibleの読み込みに失敗しました（{ip_name}）：{e}")

    return context


def _excerpt(text: str, max_chars: int = 1500) -> str:
    if not text:
        return "（未生成）"
    text = text.strip()
    return text if len(text) <= max_chars else text[:max_chars] + "\n...(以下省略)"


def _fallback_rule_review(image_files: list[str], metadata: dict | None, context: dict) -> dict:
    """
    OPENROUTER_API_KEY未設定・AI呼び出し失敗時のフォールバック。Python
    Quality Check（Quest106）・生成metadataの内容から、決定的なルールで
    簡易スコアを組み立てる（AIによる画像そのものの評価は行わない）。
    """
    generation_mode = (metadata or {}).get("generation_mode")

    items = {}
    for name in REVIEW_ITEM_NAMES:
        items[name] = {"score": 3, "comment": "Python Quality Checkに基づく簡易評価です（AIレビュー未実行）。", "needs_fix": False}

    if generation_mode == "fallback_pillow":
        items["commercial_quality"] = {
            "score": 2,
            "comment": "画像生成AIではなくPillowのダミー画像のため、商用品質としては要確認です。",
            "needs_fix": True,
        }
    if not context.get("style_guide"):
        items["style_consistency"] = {
            "score": 2,
            "comment": "Style Guideが未生成のため、配色・線のルール一貫性を確認できません。",
            "needs_fix": True,
        }
    if not context.get("ip_bible"):
        items["character_consistency"] = {
            "score": 2,
            "comment": "IP Bibleが未生成のため、キャラクター設定との一致を確認できません。",
            "needs_fix": True,
        }

    overall_score = round(sum(i["score"] for i in items.values()) / len(items))
    needs_fix_any = any(i["needs_fix"] for i in items.values())
    summary = (
        "AIレビューは未実行のため、Python Quality Checkとmetadataに基づく簡易評価です。"
        + ("要確認の項目があります。" if needs_fix_any else "大きな問題は検出されていません。")
    )

    images = [{"filename": f, "comment": "簡易評価のみ（AIレビュー未実行）。"} for f in image_files]

    return {
        "review_mode": REVIEW_MODE_FALLBACK,
        "summary": summary,
        "overall_score": overall_score,
        "items": [{"name": name, **items[name]} for name in REVIEW_ITEM_NAMES],
        "images": images,
    }


def _ai_review(image_paths: list[Path], context: dict) -> dict:
    """
    OpenRouter経由gpt-4o-mini（画像入力対応）で実際にAIレビューを行う。
    呼び出し失敗時は例外をそのまま呼び出し元に伝える（フォールバックへの
    切替判断は呼び出し側で行う）。
    """
    import base64
    import litellm

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    review_targets = image_paths[:_MAX_REVIEW_IMAGES]
    filenames_line = ", ".join(p.name for p in review_targets)

    content = [{"type": "text", "text": _VEGA_REVIEW_PROMPT.format(
        prompt_text=_excerpt(context.get("prompt_text")),
        style_guide_excerpt=_excerpt(context.get("style_guide")),
        ip_bible_excerpt=_excerpt(context.get("ip_bible")),
    ) + f"\n添付画像は次の順番・ファイル名です: {filenames_line}\n"
      "images配列のfilenameには、必ずこの実際のファイル名を使ってください。"}]

    for path in review_targets:
        ext = path.suffix.lstrip(".").lower()
        mime = "image/png" if ext == "png" else f"image/{ext}"
        data_url = f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
        content.append({"type": "image_url", "image_url": {"url": data_url}})

    response = litellm.completion(
        model="openrouter/openai/gpt-4o-mini",
        api_key=api_key,
        api_base="https://openrouter.ai/api/v1",
        messages=[{"role": "user", "content": content}],
        temperature=0.4,
        timeout=90,
    )
    raw = (response["choices"][0]["message"]["content"] or "").strip()

    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("AI応答からJSONを抽出できませんでした")
    data = json.loads(raw[start:end + 1])

    raw_items = data.get("items") or {}
    items = []
    scores = []
    for name in REVIEW_ITEM_NAMES:
        entry = raw_items.get(name) or {}
        score = entry.get("score")
        try:
            score = int(score)
        except (TypeError, ValueError):
            score = 3
        score = max(1, min(5, score))
        scores.append(score)
        items.append({
            "name": name,
            "score": score,
            "comment": str(entry.get("comment") or ""),
            "needs_fix": bool(entry.get("needs_fix", score <= 2)),
        })

    overall_score = round(sum(scores) / len(scores)) if scores else 3
    images = [
        {"filename": str(img.get("filename") or ""), "comment": str(img.get("comment") or "")}
        for img in (data.get("images") or [])
        if img.get("filename")
    ]

    return {
        "review_mode": REVIEW_MODE_AI,
        "summary": str(data.get("summary") or ""),
        "overall_score": overall_score,
        "items": items,
        "images": images,
    }


def review_images(
    project_id: str,
    ip_name: str | None = None,
    manual_request: bool = True,
    asset_type: str = "line_sticker",
    outputs_dir: Path | None = None,
) -> dict:
    """
    Quest110：生成画像一覧取得 → metadata取得 → Creative Style/IP Bible/
    Prompt参照 → Python Quality Check → レビュー対象判定 → 必要な画像だけ
    AIレビュー → review_report.json保存、までを1回で行う。

    生成画像が無い場合はエラーを返す（先に「⑤ 画像生成」の実行が必要）。
    AIレビューを実行しない/できない場合は、Rule Engineによる簡易レビュー
    （review_mode="fallback_rule_review"）を返す。

    戻り値: {"ok": bool, "report": dict | None, "path": str | None, "error": str | None}
    例外を投げない。
    """
    try:
        images_info = get_generated_images(project_id, asset_type=asset_type, outputs_dir=outputs_dir)
        if not images_info.get("exists") or not images_info.get("image_files"):
            return {"ok": False, "report": None, "path": None,
                     "error": "生成済み画像が見つかりません（先に「⑤ 画像生成」を実行してください）"}

        image_files = images_info["image_files"]
        metadata = images_info.get("metadata")

        image_dir = ((outputs_dir or _OUTPUTS_DIR) / "generated_assets" / asset_type / project_id)

        # 1. Python Quality Check（Quest106）を先に実行する（Lean AI Firstの優先順位）。
        quality_report = None
        try:
            from services.quality_control_service import generate_quality_report
            quality_report = generate_quality_report(
                image_dir, ip_name=ip_name, project_id=project_id, outputs_dir=outputs_dir,
            )
        except Exception as e:
            print(f"[警告] Python Quality Checkの実行に失敗しました（{project_id}）：{e}")

        context = _gather_review_context(project_id, ip_name, outputs_dir)

        review_data = None
        if should_run_ai_review(manual_request, quality_report):
            try:
                image_paths = [image_dir / f for f in image_files]
                review_data = _ai_review(image_paths, context)
            except Exception as e:
                print(f"[情報] AIレビューを利用できないため、Rule Engineによる簡易レビューを行います（{project_id}）：{e}")

        if review_data is None:
            review_data = _fallback_rule_review(image_files, metadata, context)

        report = {
            "project_id": project_id,
            "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "review_mode": review_data["review_mode"],
            "summary": review_data["summary"],
            "overall_score": review_data["overall_score"],
            "items": review_data["items"],
            "images": review_data["images"],
        }

        saved = save_review_report(project_id, report, outputs_dir=outputs_dir)
        return {"ok": True, "report": report, "path": saved.get("path"), "error": None}
    except Exception as e:
        print(f"[警告] AIレビューの実行に失敗しました（{project_id}）：{e}")
        return {"ok": False, "report": None, "path": None, "error": str(e)}


def save_review_report(project_id: str, report: dict, outputs_dir: Path | None = None) -> dict:
    """
    review_report.jsonをoutputs/reviews/<project_id>/へ保存する。

    戻り値: {"ok": bool, "path": str | None, "error": str | None}
    例外を投げない。
    """
    try:
        directory = (outputs_dir or _OUTPUTS_DIR) / _REVIEWS_DIR_NAME / project_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / _REPORT_FILENAME
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "path": str(path), "error": None}
    except Exception as e:
        print(f"[警告] review_report.jsonの保存に失敗しました（{project_id}）：{e}")
        return {"ok": False, "path": None, "error": str(e)}


def load_review_report(project_id: str, outputs_dir: Path | None = None) -> dict | None:
    """保存済みreview_report.jsonを読み込む。未存在・破損時はNoneを返す（例外を投げない）。"""
    try:
        path = (outputs_dir or _OUTPUTS_DIR) / _REVIEWS_DIR_NAME / project_id / _REPORT_FILENAME
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[警告] review_report.jsonの読み込みに失敗しました（{project_id}）：{e}")
        return None


if __name__ == "__main__":
    # Quest110: 動作確認用のCLI導線。
    #   python services/ai_review_engine.py <project_id> [ip_name]
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
        ip_name = sys.argv[2] if len(sys.argv) > 2 else None
        result = review_images(project_id, ip_name=ip_name, manual_request=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("使い方: python services/ai_review_engine.py <project_id> [ip_name]")
