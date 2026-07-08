"""
DAF OS Quest112 — CEO Production Dashboard（Production Status Service）

Quest108〜111で、
  Prompt生成 → 画像生成 → AIレビュー → Export
までのProduction Pipelineが完成した。しかしDashboard上ではまだ開発者向けの
個別ボタンが並ぶだけで、CEOが「今どこまで進んでいて、次に何をすればいいか」
を一目で把握できなかった。本Questでは、既存のService（Quest104〜111）を
そのまま再利用し、Projectごとの進捗を1つのステータスとして組み立てる
Production Status Serviceを追加する。

このServiceは新しい状態を保存しない（read-only）。既存の保存済みデータ
（IP Memory・IP Bible・Style Guide・Prompt・生成画像・AI Review・Export）を
毎回読み直して判定するだけで、DAF OS全体の他の部分には一切影響しない。

7ステップ（CEO向け日本語ラベル）：
  ① ip_dna            キャラクターの特徴を作る（Quest104 IP Memory）
  ② ip_bible          設定資料を作る（Quest105 IP Bible）
  ③ style_guide       描き方を作る（Quest107 Creative Style）
  ④ prompt            プロンプト生成（Quest108 Prompt Builder v2）
  ⑤ image_generation  画像生成（Quest109 Image Generation Pipeline）
  ⑥ ai_review         AIレビュー（Quest110 AI Review Engine）
  ⑦ export            提出用ZIP作成（Quest111 Export Engine）

各ステップの状態は以下の4種類：
  pending       未実行
  done          完了
  needs_review  要確認（AIレビューでneeds_fixあり、Exportでエラー/警告あり等）
  error         エラー（状態確認自体が失敗した場合）

ip_dna・ip_bible・style_guideの3ステップは、ProjectとIPを紐づける仕組みが
まだ無いため（Quest108〜111と同じ制約）、呼び出し側がip_nameを明示的に
渡した場合のみ判定する。ip_name未指定の場合はpending扱いとする（IPが
無くてもプロンプト生成以降は動作を継続できる設計のため、ブロックはしない）。

必要な関数：
- get_production_status(project_id, ip_name=None): 7ステップの状態・
  現在の状態サマリー・次のおすすめAction・提出準備完了フラグを返す

CLI:
  python services/production_status_service.py <project_id> [ip_name]

各ステップの判定は個別にtry/exceptで守られ、1つのステップの確認に失敗
しても他のステップ・DAF OS全体には影響しない（失敗したステップは
status="error"として記録する）。
"""

import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BASE_DIR = Path(__file__).parent.parent
_OUTPUTS_DIR = _BASE_DIR / "outputs"

STATUS_PENDING = "pending"
STATUS_DONE = "done"
STATUS_NEEDS_REVIEW = "needs_review"
STATUS_ERROR = "error"

DEFAULT_ASSET_TYPE = "line_sticker"

# ステップ定義（順序が進捗判定・Next Actionの基準になる）。
_STEP_DEFS = (
    {"id": "ip_dna", "label": "キャラクターの特徴を作る"},
    {"id": "ip_bible", "label": "設定資料を作る"},
    {"id": "style_guide", "label": "描き方を作る"},
    {"id": "prompt", "label": "プロンプト生成"},
    {"id": "image_generation", "label": "画像生成"},
    {"id": "ai_review", "label": "AIレビュー"},
    {"id": "export", "label": "提出用ZIP作成"},
)


def _step(step_id: str, label: str, status: str, detail: str = "") -> dict:
    return {"id": step_id, "label": label, "status": status, "detail": detail}


def _check_ip_dna(ip_name: str | None, outputs_dir: Path | None) -> dict:
    if not ip_name:
        return _step("ip_dna", "キャラクターの特徴を作る", STATUS_PENDING, "IPが未紐づけです")
    try:
        from services.ip_memory_service import load_ip
        ip = load_ip(ip_name, outputs_dir=outputs_dir)
        if ip is None:
            return _step("ip_dna", "キャラクターの特徴を作る", STATUS_PENDING, "IPが未作成です")
        dna = ip.get("dna") or {}
        has_content = any(
            (dna.get(group) or {}).get(key)
            for group, keys in (("identity", ("name", "species", "type")),
                                 ("personality", ("personality", "values", "target_emotion")),
                                 ("visual", ("color_palette", "line_style", "eye_style", "body_style")))
            for key in keys
        ) or bool(dna.get("keywords"))
        status = STATUS_DONE if has_content else STATUS_PENDING
        return _step("ip_dna", "キャラクターの特徴を作る", status)
    except Exception as e:
        return _step("ip_dna", "キャラクターの特徴を作る", STATUS_ERROR, str(e))


def _check_ip_bible(ip_name: str | None, outputs_dir: Path | None) -> dict:
    if not ip_name:
        return _step("ip_bible", "設定資料を作る", STATUS_PENDING, "IPが未紐づけです")
    try:
        from services.ip_bible_service import load_ip_bible
        bible = load_ip_bible(ip_name, outputs_dir=outputs_dir)
        status = STATUS_DONE if bible else STATUS_PENDING
        return _step("ip_bible", "設定資料を作る", status)
    except Exception as e:
        return _step("ip_bible", "設定資料を作る", STATUS_ERROR, str(e))


def _check_style_guide(ip_name: str | None, outputs_dir: Path | None) -> dict:
    if not ip_name:
        return _step("style_guide", "描き方を作る", STATUS_PENDING, "IPが未紐づけです")
    try:
        from services.creative_style_service import load_style_guide
        guide = load_style_guide(ip_name, outputs_dir=outputs_dir)
        status = STATUS_DONE if guide else STATUS_PENDING
        return _step("style_guide", "描き方を作る", status)
    except Exception as e:
        return _step("style_guide", "描き方を作る", STATUS_ERROR, str(e))


def _check_prompt(project_id: str, outputs_dir: Path | None) -> dict:
    try:
        from services.prompt_builder_v2 import list_prompts
        prompts = list_prompts(project_id, outputs_dir=outputs_dir)
        status = STATUS_DONE if prompts else STATUS_PENDING
        return _step("prompt", "プロンプト生成", status)
    except Exception as e:
        return _step("prompt", "プロンプト生成", STATUS_ERROR, str(e))


def _check_image_generation(project_id: str, asset_type: str, outputs_dir: Path | None) -> dict:
    try:
        from services.image_generation_pipeline import list_generated_images
        result = list_generated_images(project_id, asset_type=asset_type, outputs_dir=outputs_dir)
        status = STATUS_DONE if result.get("exists") and result.get("image_files") else STATUS_PENDING
        return _step("image_generation", "画像生成", status)
    except Exception as e:
        return _step("image_generation", "画像生成", STATUS_ERROR, str(e))


def _check_ai_review(project_id: str, outputs_dir: Path | None) -> dict:
    try:
        from services.ai_review_engine import load_review_report
        report = load_review_report(project_id, outputs_dir=outputs_dir)
        if report is None:
            return _step("ai_review", "AIレビュー", STATUS_PENDING)
        items = report.get("items") or []
        needs_fix = any(i.get("needs_fix") for i in items)
        status = STATUS_NEEDS_REVIEW if needs_fix else STATUS_DONE
        return _step("ai_review", "AIレビュー", status,
                      f"overall_score={report.get('overall_score')}")
    except Exception as e:
        return _step("ai_review", "AIレビュー", STATUS_ERROR, str(e))


def _check_export(project_id: str, outputs_dir: Path | None) -> dict:
    try:
        from services.export_engine import load_export_report
        report = load_export_report(project_id, outputs_dir=outputs_dir)
        if report is None:
            return _step("export", "提出用ZIP作成", STATUS_PENDING)
        if report.get("errors"):
            return _step("export", "提出用ZIP作成", STATUS_NEEDS_REVIEW, "エラーが記録されています")
        status = STATUS_DONE if report.get("ready") else STATUS_NEEDS_REVIEW
        return _step("export", "提出用ZIP作成", status)
    except Exception as e:
        return _step("export", "提出用ZIP作成", STATUS_ERROR, str(e))


def get_production_status(
    project_id: str,
    ip_name: str | None = None,
    asset_type: str = DEFAULT_ASSET_TYPE,
    outputs_dir: Path | None = None,
) -> dict:
    """
    Quest112：Projectの7ステップ進捗（IP DNA〜Export）をまとめて返す。
    既存Service（Quest104〜111）をread-onlyで呼ぶだけで、新しい状態は
    一切保存しない。

    戻り値: {"project_id": str, "steps": list[dict], "current_status": str,
             "next_action": str, "ready_for_submission": bool}
    各ステップの確認に失敗しても例外を投げない（該当ステップのみ
    status="error"として記録する）。
    """
    steps = [
        _check_ip_dna(ip_name, outputs_dir),
        _check_ip_bible(ip_name, outputs_dir),
        _check_style_guide(ip_name, outputs_dir),
        _check_prompt(project_id, outputs_dir),
        _check_image_generation(project_id, asset_type, outputs_dir),
        _check_ai_review(project_id, outputs_dir),
        _check_export(project_id, outputs_dir),
    ]

    export_step = steps[-1]
    ready_for_submission = export_step["status"] == STATUS_DONE

    # ip_dna/ip_bible/style_guideはProjectとIPを紐づける仕組みがまだ無いため
    # （Quest108〜111と同じ制約）、ip_name未指定の場合はCurrent Status /
    # Next Actionの判定対象から外す（Prompt Builder v2はIP無しでも動作
    # できる設計のため、CEOに「まずIPを作ってください」と誤誘導しない）。
    relevant_steps = steps if ip_name else steps[3:]

    if all(s["status"] == STATUS_DONE for s in relevant_steps):
        current_status = "すべての工程が完了しています"
        next_action = "Exportしたファイルを確認し、LINE Creators Marketへ提出してください"
    else:
        first_blocking = next(s for s in relevant_steps if s["status"] != STATUS_DONE)
        done_labels = [s["label"] for s in relevant_steps if s["status"] == STATUS_DONE]

        if first_blocking["status"] == STATUS_PENDING:
            current_status = f"{done_labels[-1]}まで完了" if done_labels else "まだ何も実行されていません"
            next_action = f"{first_blocking['label']}を実行してください"
        elif first_blocking["status"] == STATUS_NEEDS_REVIEW:
            current_status = f"{first_blocking['label']}で要確認があります"
            next_action = f"{first_blocking['label']}の結果を確認してください"
        else:  # error
            current_status = f"{first_blocking['label']}の確認中にエラーが発生しました"
            next_action = f"{first_blocking['label']}を再実行するか、内容を確認してください"

    return {
        "project_id": project_id,
        "steps": steps,
        "current_status": current_status,
        "next_action": next_action,
        "ready_for_submission": ready_for_submission,
    }


if __name__ == "__main__":
    # Quest112: 動作確認用のCLI導線。
    #   python services/production_status_service.py <project_id> [ip_name]
    import json
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
        ip_name = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(get_production_status(project_id, ip_name=ip_name), ensure_ascii=False, indent=2))
    else:
        print("使い方: python services/production_status_service.py <project_id> [ip_name]")
