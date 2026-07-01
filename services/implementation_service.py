"""
DAF OS v2.0 Phase1 — 実装キュー生成サービス
GitHub Open Issues から高優先度を上位3件選び、
Claude Code へ渡す推奨プロンプト付きの実装キューを生成する。
GitHub 未設定時は安全にスキップする。
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


# ──────────────────────────────────────────
# GitHub API
# ──────────────────────────────────────────

def _fetch_open_issues(token: str, owner: str, repo: str) -> list[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=open&per_page=100"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            issues = json.loads(resp.read())
            # Pull Request は除外
            return [i for i in issues if isinstance(i, dict) and "pull_request" not in i]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API エラー {e.code}: {e.read().decode()}") from e
    except Exception as e:
        raise RuntimeError(f"GitHub 接続失敗: {e}") from e


def _priority_rank(issue: dict) -> int:
    """ラベルに基づいて優先度スコアを返す（低いほど高優先）。"""
    labels = [lb["name"] for lb in issue.get("labels", [])]
    if "priority: high" in labels:
        return 0
    if "priority: medium" in labels:
        return 1
    return 2


def _label_names(issue: dict) -> list[str]:
    return [lb["name"] for lb in issue.get("labels", [])]


# ──────────────────────────────────────────
# プロンプト生成
# ──────────────────────────────────────────

def _build_prompt(issue: dict, owner: str, repo: str) -> str:
    number = issue["number"]
    title  = issue["title"]
    body   = (issue.get("body") or "").strip()
    url    = issue["html_url"]
    labels = _label_names(issue)

    # body から背景・要件・完了条件を抽出（DAF OS フォーマットに対応）
    import re

    def _section(text: str, heading: str) -> str:
        m = re.search(rf"## {re.escape(heading)}\s*\n([\s\S]*?)(?=\n## |\Z)", text)
        return m.group(1).strip() if m else ""

    background  = _section(body, "背景") or ""
    requirement = _section(body, "要件") or ""
    completion  = _section(body, "完了条件") or ""

    lines = [f"GitHub Issue #{number}（{url}）を実装してください。"]
    lines.append(f"\nタイトル：{title}\n")

    if background:
        lines.append(f"背景：\n{background}\n")
    if requirement:
        lines.append(f"要件：\n{requirement}\n")
    if completion:
        lines.append(f"完了条件：\n{completion}\n")

    lines.append(
        "実装完了後、変更したファイルの一覧と動作確認方法を教えてください。"
    )

    return "\n".join(lines)


# ──────────────────────────────────────────
# キュー Markdown 生成
# ──────────────────────────────────────────

def _build_queue_md(
    top_issues: list[dict],
    owner: str,
    repo: str,
    generated_at: str,
) -> str:
    lines = [
        "# DAF OS 実装キュー",
        "",
        f"> 生成日時: {generated_at}　リポジトリ: {owner}/{repo}",
        "",
        "---",
        "",
    ]

    for issue in top_issues:
        number  = issue["number"]
        title   = issue["title"]
        url     = issue["html_url"]
        labels  = _label_names(issue)
        prompt  = _build_prompt(issue, owner, repo)

        priority_label = next(
            (lb for lb in labels if lb.startswith("priority:")), "未設定"
        )
        agent_label = next(
            (lb.replace("agent: ", "").capitalize() for lb in labels if lb.startswith("agent:")),
            "—",
        )

        lines += [
            f"## Issue #{number}",
            "",
            f"**タイトル：** {title}",
            f"**URL：** {url}",
            f"**優先度：** {priority_label}　**担当エージェント：** {agent_label}",
            "",
            "### 実装目的",
            "",
            (issue.get("body") or "")[:300].split("\n")[0] or "（説明なし）",
            "",
            "### Claude Code への推奨プロンプト",
            "",
            "```",
            prompt,
            "```",
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


# ──────────────────────────────────────────
# 公開関数
# ──────────────────────────────────────────

def generate_implementation_queue(
    outputs: Path,
    token: str | None,
    owner: str | None,
    repo: str | None,
    limit: int = 3,
) -> list[dict]:
    """
    GitHub Open Issues から高優先度 Issue を選び、
    outputs/implementation_queue.md を生成する。
    未設定時は空リストを返してスキップ。
    """
    if not (token and owner and repo):
        print("[実装キュー] GITHUB_TOKEN / REPO 未設定 → スキップ")
        return []

    print(f"[実装キュー] {owner}/{repo} から Open Issues を取得中...")
    try:
        issues = _fetch_open_issues(token, owner, repo)
    except RuntimeError as e:
        print(f"  [警告] {e} → スキップ")
        return []

    # 優先度順でソートして上位 limit 件
    issues.sort(key=_priority_rank)
    top = issues[:limit]

    if not top:
        print("  [実装キュー] Open Issue がありません → スキップ")
        return []

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    md = _build_queue_md(top, owner, repo, generated_at)

    queue_path = outputs / "implementation_queue.md"
    queue_path.write_text(md, encoding="utf-8")
    print(f"  ✓ {queue_path}（{len(top)}件）")

    return top
