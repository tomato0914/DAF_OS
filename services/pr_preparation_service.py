"""
DAF OS v1.7 — PR作成準備サービス
git diff の内容から Pull Request 作成に必要な情報（ブランチ名・コミットメッセージ・
PRタイトル・PR本文など）を自動生成する。LLM不使用（安全性重視）。

このサービスは GitHub へ何も書き込まない。
- git commit しない
- git push しない
- Pull Request を作成しない
- .env は一切読み取らない・表示しない
- GitHub Token を表示しない

生成物は outputs/pr_draft.md に保存され、CEOが内容を確認した上で
手動で commit / push / PR作成を行うことを想定している。
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# 差分に含めない・機密になりうるファイル
EXCLUDE_PATTERNS = [
    ".env",
    ".env.local",
    ".env.production",
]


def _run_git(args: list[str]) -> str:
    """git コマンドを実行して標準出力を返す。失敗時は空文字。"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return ""
        return result.stdout
    except Exception:
        return ""


def _is_git_repo() -> bool:
    return bool(_run_git(["rev-parse", "--is-inside-work-tree"]).strip())


def _is_excluded(path: str) -> bool:
    name = path.split("/")[-1]
    return any(name == p or name.startswith(p) for p in EXCLUDE_PATTERNS)


def get_changed_files() -> list[dict]:
    """
    git status --porcelain から変更ファイル一覧を取得する。
    .env 系ファイルは除外する。
    """
    raw = _run_git(["status", "--porcelain"])
    files = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        status = line[:2].strip()
        path = line[3:].strip()
        # rename の場合 "old -> new" 形式
        if " -> " in path:
            path = path.split(" -> ")[-1].strip()
        if _is_excluded(path):
            continue
        files.append({"status": status, "path": path})
    return files


def get_diff_stat() -> str:
    """git diff --stat（未ステージ＋ステージ済み）を取得する。.env は除外。"""
    exclude_args = [f":(exclude){p}" for p in EXCLUDE_PATTERNS]
    raw = _run_git(["diff", "HEAD", "--stat", "--"] + exclude_args)
    return raw.strip()


def get_diff_text(max_chars: int = 6000) -> str:
    """
    git diff HEAD の本文を取得する（.env 除外・文字数制限あり）。
    プレビュー表示用。
    """
    exclude_args = [f":(exclude){p}" for p in EXCLUDE_PATTERNS]
    raw = _run_git(["diff", "HEAD", "--"] + exclude_args)
    if len(raw) > max_chars:
        return raw[:max_chars] + "\n\n... （以下省略、全文は `git diff` で確認してください）"
    return raw


# ──────────────────────────────────────────
# 推測ロジック（LLM不使用）
# ──────────────────────────────────────────

def _guess_category(files: list[dict]) -> str:
    """変更ファイルの傾向から種別（feat/fix/docs/chore）を推測する。"""
    paths = [f["path"] for f in files]
    if all(p.startswith("docs/") or p.endswith(".md") for p in paths):
        return "docs"
    if any("test" in p for p in paths):
        return "test"
    if any(p.startswith("services/") or p.startswith("agents/") or p.startswith("crews/") for p in paths):
        return "feat"
    return "chore"


def _guess_scope(files: list[dict]) -> str:
    """最も多く変更されたトップレベルディレクトリを返す。"""
    dirs = [f["path"].split("/")[0] for f in files if "/" in f["path"]]
    if not dirs:
        return "root"
    counts: dict[str, int] = {}
    for d in dirs:
        counts[d] = counts.get(d, 0) + 1
    return max(counts, key=counts.get)


def _slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\-]+", "-", text.strip().lower())
    return re.sub(r"-+", "-", text).strip("-") or "update"


def generate_branch_name(files: list[dict]) -> str:
    category = _guess_category(files)
    scope = _slugify(_guess_scope(files))
    date_tag = datetime.now().strftime("%Y%m%d")
    prefix = {"docs": "docs", "test": "test", "feat": "feature", "chore": "chore"}.get(category, "chore")
    return f"{prefix}/{date_tag}-{scope}"


def generate_commit_message(files: list[dict]) -> str:
    category = _guess_category(files)
    scope = _guess_scope(files)
    tag = {"docs": "docs", "test": "test", "feat": "feat", "chore": "chore"}.get(category, "chore")
    count = len(files)
    return f"{tag}({scope}): {count}件のファイルを更新"


def generate_pr_title(files: list[dict]) -> str:
    category = _guess_category(files)
    scope = _guess_scope(files)
    labels = {"docs": "ドキュメント更新", "test": "テスト更新", "feat": "機能追加/更新", "chore": "メンテナンス"}
    return f"[{labels.get(category, 'メンテナンス')}] {scope} 関連の変更"


def _file_list_md(files: list[dict]) -> str:
    status_labels = {
        "M": "変更", "A": "追加", "D": "削除", "R": "リネーム",
        "??": "新規（未追跡）", "AM": "追加/変更",
    }
    lines = []
    for f in files:
        label = status_labels.get(f["status"], f["status"] or "変更")
        lines.append(f"- `{f['path']}`（{label}）")
    return "\n".join(lines) if lines else "（変更ファイルなし）"


def generate_pr_body(files: list[dict], diff_stat: str) -> str:
    file_list = _file_list_md(files)
    return (
        f"## 概要\n\n"
        f"このPRは、DAF OS が自動生成した変更内容の要約です。\n"
        f"内容を確認の上、必要に応じて修正してから commit / push / PR作成してください。\n\n"
        f"## 変更ファイル（{len(files)}件）\n\n"
        f"{file_list}\n\n"
        f"## diff 概要\n\n"
        f"```\n{diff_stat or '（統計情報を取得できませんでした）'}\n```\n"
    )


def generate_checkpoints(files: list[dict]) -> list[str]:
    points = [
        "生成されたコミットメッセージ・PRタイトルが内容と合っているか確認する",
        "意図しないファイルが変更されていないか確認する",
    ]
    paths = [f["path"] for f in files]
    if any(p.startswith("services/") for p in paths):
        points.append("services/ の変更がテスト・既存動作に影響しないか確認する")
    if any(p.startswith("docs/") for p in paths):
        points.append("docs/ の公開ページ（GitHub Pages）に反映して問題ないか確認する")
    if any(".env" in p for p in paths):
        points.append(".env に関連する変更が含まれていないか再確認する（本サービスは自動除外済み）")
    return points


def generate_risks(files: list[dict]) -> list[str]:
    risks = []
    count = len(files)
    if count > 15:
        risks.append(f"変更ファイル数が多いため（{count}件）、レビューが困難になる可能性があります")
    paths = [f["path"] for f in files]
    if any(p.startswith("crews/") or p == "main.py" for p in paths):
        risks.append("コアロジック（main.py / crews/）の変更が含まれており、動作確認が必須です")
    if not risks:
        risks.append("大きなリスクは検出されませんでしたが、必ず内容を目視確認してください")
    return risks


# ──────────────────────────────────────────
# メイン生成関数
# ──────────────────────────────────────────

def generate_pr_draft(outputs: Path) -> Path | None:
    """
    git diff から pr_draft.md を生成する。
    差分がない・git未初期化の場合は None を返し安全にスキップする。
    """
    if not _is_git_repo():
        print("[PR準備] git リポジトリではないためスキップします")
        return None

    files = get_changed_files()
    if not files:
        print("[PR準備] 変更差分がないためスキップします")
        return None

    diff_stat = get_diff_stat()
    branch_name = generate_branch_name(files)
    commit_message = generate_commit_message(files)
    pr_title = generate_pr_title(files)
    pr_body = generate_pr_body(files, diff_stat)
    checkpoints = generate_checkpoints(files)
    risks = generate_risks(files)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    content = (
        f"# PR作成準備\n\n"
        f"> 生成日時: {now}\n"
        f"> ⚠️ このファイルはCEOが内容を確認するための下書きです。\n"
        f"> DAF OS は自動で commit / push / PR作成を行いません。\n\n"
        f"---\n\n"
        f"## 推奨ブランチ名\n\n"
        f"```\n{branch_name}\n```\n\n"
        f"## コミットメッセージ案\n\n"
        f"```\n{commit_message}\n```\n\n"
        f"## PRタイトル案\n\n"
        f"```\n{pr_title}\n```\n\n"
        f"## PR本文案\n\n"
        f"{pr_body}\n"
        f"## 確認すべきポイント\n\n"
        + "\n".join(f"- {p}" for p in checkpoints) + "\n\n"
        f"## リスク\n\n"
        + "\n".join(f"- {r}" for r in risks) + "\n\n"
        f"## CEOへの次アクション\n\n"
        f"1. 上記の内容と実際の `git diff` を見比べて確認する\n"
        f"2. 問題なければ以下を手動で実行する：\n\n"
        f"```bash\n"
        f"git checkout -b {branch_name}\n"
        f'git add <確認したファイル>\n'
        f'git commit -m "{commit_message}"\n'
        f"git push -u origin {branch_name}\n"
        f"```\n\n"
        f"3. GitHub上で Pull Request を作成し、上記PRタイトル・PR本文案を貼り付ける\n\n"
        f"> 🔒 本ファイルは `.env` の内容や GitHub Token を含みません。\n"
    )

    path = outputs / "pr_draft.md"
    path.write_text(content, encoding="utf-8")
    print(f"[PR準備] ✓ {path}")
    return path


def has_pr_draft(outputs: Path) -> bool:
    return (outputs / "pr_draft.md").exists()


def get_pr_draft_summary(outputs: Path) -> dict | None:
    """Web UI 向けに pr_draft.md の要約を返す。"""
    path = outputs / "pr_draft.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")

    def _extract_block(heading: str) -> str:
        m = re.search(rf"## {re.escape(heading)}\s*\n```\s*\n([\s\S]*?)```", text)
        return m.group(1).strip() if m else ""

    generated_m = re.search(r"> 生成日時: (.+)", text)
    files_m = re.search(r"## 変更ファイル（(\d+)件）", text)

    return {
        "generated_at": generated_m.group(1).strip() if generated_m else "—",
        "branch_name": _extract_block("推奨ブランチ名"),
        "commit_message": _extract_block("コミットメッセージ案"),
        "pr_title": _extract_block("PRタイトル案"),
        "file_count": int(files_m.group(1)) if files_m else 0,
    }
