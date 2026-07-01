"""
outputs/ の状態を読み取り、CEOダッシュボード（dashboard.md）を生成する。
LLM不使用。ファイルシステムとGitHub APIのみ使用。
"""

import re
import urllib.request
import urllib.error
import json
from datetime import datetime
from pathlib import Path


# ---------- ファイル読み取りヘルパー ----------

def _read(path: Path, default: str = "") -> str:
    return path.read_text(encoding="utf-8") if path.exists() else default


def _count_files(directory: Path, pattern: str = "*.md") -> int:
    if not directory.exists():
        return 0
    return len(list(directory.glob(pattern)))


# ---------- report.md から要点を抽出 ----------

def _extract_final_proposal(report_text: str) -> str:
    """CEOへの最終提言セクションを抽出する。"""
    m = re.search(r"## CEOへの最終提言\s*\n([\s\S]*?)(?=\n## |\Z)", report_text)
    if m:
        text = m.group(1).strip()
        # 長すぎる場合は3文に制限
        sentences = re.split(r"(?<=。)", text)
        return "".join(sentences[:3]).strip() or text[:300]
    # フォールバック：最後の ## セクションを返す
    sections = re.findall(r"## .+?\n([\s\S]*?)(?=\n## |\Z)", report_text)
    return sections[-1].strip()[:300] if sections else "（report.md が見つかりません）"


def _extract_action_plan(report_text: str) -> list[str]:
    """フェーズ1のアクション項目を抽出する。"""
    m = re.search(r"### フェーズ1[^\n]*\n([\s\S]*?)(?=### フェーズ2|## |\Z)", report_text)
    if not m:
        return []
    items = re.findall(r"[-*]\s+(.+)", m.group(1))
    return items[:5]


# ---------- Issue ファイルから次のアクションを取得 ----------

def _get_top_issues(issues_dir: Path, limit: int = 3) -> list[dict]:
    """優先度「高」のIssueを最大limit件返す。"""
    results = []
    for f in sorted(issues_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        num_m = re.search(r"# Issue #(\d+)", text)
        title_m = re.search(r"## タイトル\s*\n(.+)", text)
        priority_m = re.search(r"## 優先度\s*\n(.+)", text)
        assignee_m = re.search(r"## 想定担当\s*\n(.+)", text)
        if not (num_m and title_m):
            continue
        results.append({
            "number": num_m.group(1),
            "title": title_m.group(1).strip(),
            "priority": priority_m.group(1).strip() if priority_m else "—",
            "assignee": assignee_m.group(1).strip() if assignee_m else "—",
        })

    # 優先度「高」を先頭に
    high = [r for r in results if r["priority"] == "高"]
    others = [r for r in results if r["priority"] != "高"]
    return (high + others)[:limit]


# ---------- GitHub Open Issues を取得 ----------

def _fetch_github_issues(token: str, owner: str, repo: str) -> list[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=open&per_page=10"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            issues = json.loads(resp.read())
            return [
                {"number": i["number"], "title": i["title"], "url": i["html_url"]}
                for i in issues
                if isinstance(i, dict) and "pull_request" not in i
            ]
    except Exception:
        return []


# ---------- 進捗バー ----------

def _progress_bar(done: int, total: int, width: int = 20) -> str:
    if total == 0:
        return f"{'░' * width} 0%"
    ratio = min(done / total, 1.0)
    filled = int(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {int(ratio * 100)}%"


def _launch_progress(outputs: Path) -> tuple[int, int]:
    """公開準備の完了数 / 総数を返す。"""
    checklist_text = _read(outputs / "launch_checklist.md")
    if not checklist_text:
        return 0, 0
    total = len(re.findall(r"- \[[ x]\]", checklist_text))
    done = len(re.findall(r"- \[x\]", checklist_text, re.IGNORECASE))
    return done, total


def _agent_status(outputs: Path) -> dict[str, bool]:
    """各AI社員の成果物が存在するか確認。"""
    return {
        "Orion（COO）": (outputs / "report.md").exists(),
        "Atlas（CTO）": (outputs / "report.md").exists(),
        "Sirius（CPO）": (outputs / "appstore_description.md").exists(),
        "Nova（CMO）": (outputs / "social_posts.md").exists(),
        "Cosmos（CIO）": (outputs / "launch_checklist.md").exists(),
    }


# ---------- ダッシュボード生成 ----------

def _get_approval_counts(outputs: Path) -> tuple[int, int, int]:
    """(pending件数, approved件数, rejected件数) を返す。"""
    pending  = len(list((outputs / "approvals" / "pending").glob("*.md")))  \
               if (outputs / "approvals" / "pending").exists() else 0
    approved = len(list((outputs / "approvals" / "approved").glob("*.md"))) \
               if (outputs / "approvals" / "approved").exists() else 0
    rejected = len(list((outputs / "approvals" / "rejected").glob("*.md"))) \
               if (outputs / "approvals" / "rejected").exists() else 0
    return pending, approved, rejected


def _get_impl_queue(outputs: Path) -> list[dict]:
    """implementation_queue.md から実装待ち Issue リストを取得する。"""
    path = outputs / "implementation_queue.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    items = []
    for m in re.finditer(
        r"## Issue #(\d+)\s*\n\s*\*\*タイトル：\*\* (.+)\n\s*\*\*URL：\*\* (\S+)",
        text,
    ):
        items.append({"number": m.group(1), "title": m.group(2).strip(), "url": m.group(3).strip()})
    return items


def generate_dashboard(
    outputs: Path,
    github_token: str | None = None,
    github_owner: str | None = None,
    github_repo: str | None = None,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    report_text = _read(outputs / "report.md")
    issues_dir = outputs / "issues"
    tasks_dir = outputs / "claude_tasks"

    issue_count = _count_files(issues_dir)
    task_count = _count_files(tasks_dir)
    impl_queue = _get_impl_queue(outputs)
    pending_count, approved_count, rejected_count = _get_approval_counts(outputs)
    artifact_files = [
        "appstore_description.md", "social_posts.md",
        "launch_checklist.md", "report.md",
    ]
    artifact_count = sum(1 for f in artifact_files if (outputs / f).exists())

    top_issues = _get_top_issues(issues_dir)
    final_proposal = _extract_final_proposal(report_text) if report_text else "（まだ会議が実行されていません）"
    action_items = _extract_action_plan(report_text)

    launch_done, launch_total = _launch_progress(outputs)
    agents = _agent_status(outputs)
    agent_done = sum(1 for v in agents.values() if v)

    # GitHub
    gh_issues: list[dict] = []
    gh_section = ""
    if github_token and github_owner and github_repo:
        gh_issues = _fetch_github_issues(github_token, github_owner, github_repo)
        if gh_issues:
            rows = "\n".join(
                f"| [#{i['number']}]({i['url']}) | {i['title']} |"
                for i in gh_issues
            )
            gh_section = f"""
## 5. GitHub Open Issues（{github_owner}/{github_repo}）

| # | タイトル |
|---|---------|
{rows}

> 🔗 [すべてのIssueを見る](https://github.com/{github_owner}/{github_repo}/issues)
"""
        else:
            gh_section = f"\n## 5. GitHub Open Issues\n\n現在 Open Issue はありません。\n"
    else:
        gh_section = "\n## 5. GitHub連携\n\nGITHUB_TOKEN 未設定 — `.env` に追加するとここにOpen Issueが表示されます。\n"

    # 次のアクション
    if top_issues:
        next_actions = "\n".join(
            f"{i+1}. **Issue #{r['number']}**：{r['title']}（担当: {r['assignee']}）"
            for i, r in enumerate(top_issues)
        )
    elif action_items:
        next_actions = "\n".join(f"{i+1}. {a}" for i, a in enumerate(action_items))
    else:
        next_actions = "1. `python main.py` を実行して会議を開始してください"

    lines = [
        f"# DAF OS ダッシュボード",
        f"",
        f"> 最終更新: {now}",
        f"",
        f"---",
        f"",
        f"## 1. 今日の状況",
        f"",
        f"| 項目 | 数 | 状態 |",
        f"|------|----|----|",
        f"| 成果物 | {artifact_count} / 4 | {'✅ 完了' if artifact_count == 4 else '⏳ 生成中'} |",
        f"| Issue | {issue_count} | {'✅ あり' if issue_count else '— なし'} |",
        f"| Claude Task指示書 | {task_count} | {'✅ あり' if task_count else '— なし'} |",
        f"| GitHub Open Issues | {len(gh_issues) if gh_issues else '—'} | {'🔴 対応待ち' if gh_issues else '—'} |",
        f"| 実装キュー | {len(impl_queue) if impl_queue else '—'} | {'⚡ 実装待ち' if impl_queue else '—'} |",
        f"| 承認待ち | {pending_count if pending_count else '—'} | {'🔔 要確認' if pending_count else '✅ なし'} |",
        f"",
        f"---",
        f"",
        f"## 2. 最新のAI提案",
        f"",
        final_proposal,
        f"",
        f"---",
        f"",
        f"## 3. 次にCEOがやること",
        f"",
        next_actions,
        f"",
        f"---",
        f"",
        f"## 4. 進捗バー",
        f"",
        f"**公開準備チェックリスト**",
        f"```",
        f"{_progress_bar(launch_done, launch_total)}  {launch_done}/{launch_total} 完了",
        f"```",
        f"",
        f"**AI社員稼働状況**",
        f"```",
        f"{_progress_bar(agent_done, len(agents))}  {agent_done}/{len(agents)} 稼働中",
        f"```",
        f"",
    ]
    for agent, active in agents.items():
        lines.append(f"- {'✅' if active else '⬜'} {agent}")

    lines.append(f"")
    lines.append(f"---")
    lines.append(gh_section)

    # 実装待ちタスク（implementation_queue.md が存在する場合のみ）
    if impl_queue:
        impl_rows = "\n".join(
            f"| [#{i['number']}]({i['url']}) | {i['title']} |"
            for i in impl_queue
        )
        impl_section = (
            f"\n## 6. 実装待ちタスク（Claude Code キュー）\n\n"
            f"| # | タイトル |\n"
            f"|---|----------|\n"
            f"{impl_rows}\n\n"
            f"> 📄 [実装キューを開く](implementation_queue.md)\n"
        )
    else:
        impl_section = (
            "\n## 6. 実装待ちタスク\n\n"
            "実装キューなし — `python main.py` 実行後に自動生成されます。\n"
        )
    lines.append(impl_section)

    # 承認センター
    if pending_count:
        approval_section = (
            f"\n## 7. 承認センター\n\n"
            f"🔔 **{pending_count}件の承認待ちアイテムがあります。**\n\n"
            f"| 操作 | コマンド |\n"
            f"|------|----------|\n"
            f"| 一覧を見る | `python services/approval_service.py list` |\n"
            f"| すべて承認 | `python services/approval_service.py approve-all` |\n"
            f"| 個別承認 | `python services/approval_service.py approve <id>` |\n\n"
            f"> 📁 `outputs/approvals/pending/` — 承認待ちファイル  \n"
            f"> 📁 `outputs/approvals/approved/` — 承認済み（{approved_count}件）  \n"
            f"> 📁 `outputs/approvals/rejected/` — 却下済み（{rejected_count}件）\n"
        )
    else:
        approval_section = (
            f"\n## 7. 承認センター\n\n"
            f"✅ 承認待ちなし（承認済み: {approved_count}件 / 却下済み: {rejected_count}件）\n"
        )
    lines.append(approval_section)

    # メモリ見直し提案
    suggestions_path = outputs / "memory_update_suggestions.md"
    if suggestions_path.exists():
        memory_section = (
            "\n## 8. メモリ見直し提案\n\n"
            "💡 **AIからの提案があります。** 会社メモリの見直し候補が生成されました。\n\n"
            "> 📄 [memory_update_suggestions.md を開いて確認する](memory_update_suggestions.md)  \n"
            "> ✏️ 確認後、`memory/` フォルダのファイルを手動で更新してください。\n"
        )
    else:
        memory_section = (
            "\n## 8. メモリ見直し提案\n\n"
            "提案なし — `python main.py` 実行後に自動生成されます。\n"
        )
    lines.append(memory_section)

    # PR作成準備（v1.7）
    pr_draft_path = outputs / "pr_draft.md"
    if pr_draft_path.exists():
        pr_section = (
            "\n## 9. PR作成準備\n\n"
            "🔀 **PR作成準備あり。** コード変更差分からブランチ名・コミットメッセージ・PR本文案が生成されました。\n\n"
            "> 📄 [pr_draft.md を開いて確認する](pr_draft.md)  \n"
            "> ⚠️ commit / push / PR作成は自動実行されません。内容を確認の上、手動で行ってください。\n"
        )
    else:
        pr_section = (
            "\n## 9. PR作成準備\n\n"
            "PR作成準備なし — 変更差分がある状態で `python main.py` を実行すると生成されます。\n"
        )
    lines.append(pr_section)

    return "\n".join(lines)


def save_dashboard(
    outputs: Path,
    github_token: str | None = None,
    github_owner: str | None = None,
    github_repo: str | None = None,
) -> Path:
    content = generate_dashboard(outputs, github_token, github_owner, github_repo)
    path = outputs / "dashboard.md"
    path.write_text(content, encoding="utf-8")
    return path
