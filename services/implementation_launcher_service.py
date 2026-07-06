"""
DAF OS v2.3 Quest42 — ワンクリック実装準備サービス
DAF OS Quest48 — 選択したIssueだけを対象にする実装準備

承認済みIssueからClaude Codeへ渡すまでの準備を1操作にまとめる。
- outputs/autonomous_flow.md を再生成（常に承認済み全件を対象。一覧としての完全性を保つ）
- outputs/claude_code_prompt.md を生成（複数プロダクトに対応、そのままコピペ可能な形式）
  - approval_ids を指定した場合は、そのIssueだけを claude_code_prompt.md に含める（Quest48）
  - 指定しない場合は従来どおり承認済み全件を対象にする（既存フローとの後方互換）
- 生成したファイルをローカルのデフォルトアプリで開く（Mac想定・失敗しても無視）

安全設計：
- git commit / git push は一切行わない
- Claude Code を自動起動しない（生成したMarkdownファイルを開くのみ）
- 途中でエラーが発生した場合、既存の outputs/claude_code_prompt.md / autonomous_flow.md は削除・破壊しない
  （新しい内容が完全に組み立てられるまで書き込みを行わないため、失敗時は旧ファイルがそのまま残る）
- completed/ に移動済みのIssueは get_approved_implementation_items() が approved/ のみを走査するため、
  常に対象外になる
"""

import platform
import subprocess
from datetime import datetime
from pathlib import Path

from services.autonomous_flow_service import (
    generate_autonomous_flow,
    get_approved_implementation_items,
)


def _build_claude_code_prompt(items: list[dict], selected_only: bool = False) -> str:
    """承認済みアイテムから、そのままコピペ可能な実装プロンプト集を組み立てる。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    scope_label = "CEOが選択した実装アイテム" if selected_only else "CEO承認済みの実装アイテム"
    guidance = (
        "以下の指示書をClaude Codeに貼り付けて実装してください。"
        if selected_only else
        "作業したいプロダクトのセクションを1つ選び、"
        "「事前準備」のコマンドを実行してから「貼り付けるプロンプト」をClaude Codeに貼り付けてください。"
    )

    header = (
        f"# Claude Code 実装プロンプト\n\n"
        f"> 生成日時: {now}\n"
        f"> 対象: {scope_label}（{len(items)}件）\n\n"
        f"{guidance}\n\n"
        f"⚠️ DAF OSはこのファイルを生成するだけで、Claude Codeの自動起動・"
        f"git commit・git push・PR作成は一切行いません。\n\n"
        f"---\n\n"
    )

    blocks = []
    for item in items:
        warning = f"\n> {item['product_warning']}\n" if item.get("product_warning") else ""
        blocks.append(
            f"## 📦 {item['product']} — Issue #{item['issue_number']} — {item['title']}\n"
            f"{warning}\n"
            f"**作業ディレクトリ:** `{item['work_dir']}`\n\n"
            f"### 事前準備\n\n"
            f"```bash\n"
            f"cd {item['work_dir']}\n"
            f"```\n\n"
            f"### 貼り付けるプロンプト\n\n"
            f"```\n{item['raw_prompt'] or '（プロンプトが見つかりません。autonomous_flow.md を確認してください）'}\n```\n\n"
            f"---\n"
        )

    return header + "\n".join(blocks)


def _try_open_with_app(path: Path, app_name: str) -> tuple[bool, str]:
    """指定アプリでファイルを開く。(成功したか, エラーメッセージ) を返す。"""
    try:
        result = subprocess.run(
            ["open", "-a", app_name, str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, ""
        return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)


def _try_open_file(path: Path) -> bool:
    """
    生成したファイルをローカルのアプリで開く。
    Macでは Visual Studio Code → TextEdit → 通常の open の順にフォールバックする。
    Claude Code自体は起動しない（エディタ／ビューアが開くだけ）。
    Mac以外・全て失敗時は静かにスキップする。
    """
    if platform.system() != "Darwin":
        print("[実装準備] Mac以外の環境のため自動オープンをスキップします")
        return False

    ok, err = _try_open_with_app(path, "Visual Studio Code")
    if ok:
        print(f"[実装準備] VS Codeでファイルを開きました: {path}")
        return True
    print(f"[実装準備] VS Codeで開けませんでした（{err}）→ TextEditにフォールバック")

    ok, err = _try_open_with_app(path, "TextEdit")
    if ok:
        print(f"[実装準備] TextEditでファイルを開きました: {path}")
        return True
    print(f"[実装準備] TextEditで開けませんでした（{err}）→ 通常のopenにフォールバック")

    try:
        result = subprocess.run(
            ["open", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print(f"[実装準備] ファイルを開きました: {path}")
            return True
        print(f"[実装準備] ファイルを開けませんでした: {result.stderr.strip()}")
        return False
    except Exception as e:
        print(f"[実装準備] ファイルオープンに失敗しました: {e} → スキップ")
        return False


def start_implementation(
    outputs: Path,
    auto_open: bool = True,
    approval_ids: list[str] | None = None,
) -> dict:
    """
    ワンクリック実装準備のメイン処理。
    例外を投げず、常に結果を dict で返す（Web APIからそのまま使える）。

    Args:
        approval_ids: 指定した場合、その承認IDのIssueだけを claude_code_prompt.md に
            含める（Quest48）。None または空リストの場合は承認済み全件が対象（従来どおり）。

    戻り値:
        {
            "ok": bool,
            "message": str,
            "items": int,
            "prompt_path": str | None,
            "flow_path": str | None,
            "opened": bool,
        }
    """
    try:
        items = get_approved_implementation_items(outputs)
        if not items:
            return {
                "ok": False,
                "message": "承認済みの実装アイテムがありません。承認センターで承認してください。",
                "items": 0,
                "prompt_path": None,
                "flow_path": None,
                "opened": False,
            }

        selected_only = bool(approval_ids)
        if selected_only:
            target_items = [i for i in items if i["approval_id"] in approval_ids]
            if not target_items:
                return {
                    "ok": False,
                    "message": "指定されたIssueが承認済みアイテムの中に見つかりません"
                               "（既に実装完了済み、または却下済みの可能性があります）。",
                    "items": 0,
                    "prompt_path": None,
                    "flow_path": None,
                    "opened": False,
                }
        else:
            target_items = items

        # 1. autonomous_flow.md を最新化（常に承認済み全件が対象。一覧としての完全性を保つ）
        flow_path = generate_autonomous_flow(outputs)

        # 2. claude_code_prompt.md を生成（内容を完全に組み立ててから書き込む＝失敗時は旧ファイル温存）
        prompt_content = _build_claude_code_prompt(target_items, selected_only=selected_only)
        prompt_path = outputs / "claude_code_prompt.md"
        prompt_path.write_text(prompt_content, encoding="utf-8")
        print(f"[実装準備] ✓ {prompt_path}（{len(target_items)}件{'・選択のみ' if selected_only else ''}）")

        # 3. ファイルを自動で開く（失敗しても処理全体は成功扱い）
        opened = _try_open_file(prompt_path) if auto_open else False

        message = (
            f"選択した{len(target_items)}件のIssueから実装プロンプトを生成しました。"
            if selected_only else
            f"{len(target_items)}件の承認済み実装アイテムから実装プロンプトを生成しました。"
        )
        return {
            "ok": True,
            "message": message,
            "items": len(target_items),
            "prompt_path": str(prompt_path),
            "flow_path": str(flow_path) if flow_path else None,
            "opened": opened,
        }
    except Exception as e:
        # 例外時は何も書き込んでいない状態、または直前の正常な内容のままなので
        # 既存ファイルを削除・破壊することはない
        return {
            "ok": False,
            "message": f"実装準備中にエラーが発生しました: {e}",
            "items": 0,
            "prompt_path": None,
            "flow_path": None,
            "opened": False,
        }


if __name__ == "__main__":
    result = start_implementation(Path(__file__).parent.parent / "outputs")
    print(result)
