"""
IssueファイルをClaude Code用実装指示書に変換するジェネレーター。
LLM不要。テンプレートベースで構造的に変換する。
"""

import re
from pathlib import Path


# 担当者ごとの編集可能ファイル・禁止ファイルの定義
_ASSIGNEE_RULES: dict[str, dict[str, list[str]]] = {
    "Sirius": {
        "may_edit": [
            "docs/",
            "outputs/appstore_description.md",
            "memory/sirius.md",
        ],
        "must_not_touch": [
            ".env",
            "crews/",
            "agents/",
            "services/",
            "main.py",
        ],
    },
    "Nova": {
        "may_edit": [
            "docs/",
            "outputs/social_posts.md",
            "memory/nova.md",
        ],
        "must_not_touch": [
            ".env",
            "crews/",
            "agents/",
            "services/",
            "main.py",
        ],
    },
    "Cosmos": {
        "may_edit": [
            "docs/",
            "outputs/launch_checklist.md",
            "memory/cosmos.md",
        ],
        "must_not_touch": [
            ".env",
            "crews/",
            "agents/",
            "services/",
            "main.py",
        ],
    },
    "Atlas": {
        "may_edit": [
            "docs/",
            "memory/atlas.md",
            "requirements.txt",
        ],
        "must_not_touch": [
            ".env",
            "outputs/",
            "main.py",
        ],
    },
    "Orion": {
        "may_edit": [
            "docs/",
            "outputs/report.md",
            "memory/orion.md",
            "README.md",
        ],
        "must_not_touch": [
            ".env",
            "crews/",
            "agents/",
            "services/",
            "main.py",
        ],
    },
}

# 関連成果物と実ファイルパスのマッピング
_ARTIFACT_PATHS: dict[str, str] = {
    "report.md": "outputs/report.md",
    "appstore_description.md": "outputs/appstore_description.md",
    "social_posts.md": "outputs/social_posts.md",
    "launch_checklist.md": "outputs/launch_checklist.md",
}


def _parse_issue(text: str) -> dict[str, str]:
    """Issueテキストを辞書にパースする。"""

    def _extract(heading: str) -> str:
        pattern = rf"## {re.escape(heading)}\s*\n([\s\S]*?)(?=\n## |\n---|\Z)"
        m = re.search(pattern, text)
        return m.group(1).strip() if m else ""

    issue_num = ""
    m = re.search(r"# Issue #(\d+)", text)
    if m:
        issue_num = m.group(1)

    return {
        "number": issue_num,
        "title": _extract("タイトル"),
        "background": _extract("背景"),
        "requirements": _extract("要件"),
        "priority": _extract("優先度"),
        "assignee": _extract("想定担当"),
        "completion": _extract("完了条件"),
        "artifacts": _extract("関連成果物"),
    }


def _build_todo_steps(issue: dict[str, str]) -> str:
    """要件・完了条件からやってほしいことのリストを生成する。"""
    lines: list[str] = []

    # 完了条件のチェックボックスを読み取り、未完了のものを抽出
    pending = []
    completed = []
    for line in issue["completion"].splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- [x]") or line.startswith("- [X]"):
            completed.append(line[6:].strip())
        elif line.startswith("- [ ]"):
            pending.append(line[6:].strip())

    if completed:
        lines.append("### 実施済み（確認のみ）")
        for item in completed:
            lines.append(f"- ✅ {item}")
        lines.append("")

    if pending:
        lines.append("### 未完了（実装・作成が必要）")
        for i, item in enumerate(pending, 1):
            lines.append(f"{i}. {item}")
        lines.append("")

    if not pending and not completed:
        # 完了条件が解析できなかった場合は要件から生成
        lines.append("### 実装・作成が必要な作業")
        for line in issue["requirements"].splitlines():
            line = line.strip()
            if line.startswith("-"):
                lines.append(f"1. {line[1:].strip()}")

    return "\n".join(lines)


def _build_file_rules(issue: dict[str, str]) -> tuple[str, str]:
    """担当者と関連成果物から編集可否ルールを生成する。"""
    assignee = issue["assignee"].strip()
    artifact = issue["artifacts"].strip()
    artifact_path = _ARTIFACT_PATHS.get(artifact, artifact)

    rules = _ASSIGNEE_RULES.get(assignee, {
        "may_edit": ["docs/", "outputs/"],
        "must_not_touch": [".env", "main.py", "crews/", "agents/", "services/"],
    })

    may_edit = list(rules["may_edit"])
    if artifact_path and artifact_path not in may_edit:
        may_edit.insert(0, artifact_path)

    may_str = "\n".join(f"- `{f}`" for f in may_edit)
    must_not_str = "\n".join(f"- `{f}`" for f in rules["must_not_touch"])
    return may_str, must_not_str


def _build_prompt(issue: dict[str, str], source_path: Path) -> str:
    """1つのIssueからClaude Code用指示書Markdownを生成する。"""
    todo = _build_todo_steps(issue)
    may_edit, must_not_touch = _build_file_rules(issue)

    artifact = issue["artifacts"].strip()
    artifact_path = _ARTIFACT_PATHS.get(artifact, artifact)

    return f"""# Claude Code 実装指示書 — Issue #{issue['number']}

> **対象Issue**：`{source_path}`
> **優先度**：{issue['priority']}　**想定担当**：{issue['assignee']}

---

## 目的

{issue['title']} を完了させる。

## 背景

{issue['background']}

## やってほしいこと

{todo}

## 編集してよいファイル

{may_edit}

## 触らないでほしいファイル

{must_not_touch}

## 完了条件

{issue['completion']}

## 関連成果物

- `{artifact_path}` を参照して作業してください

## CEOへの報告形式

作業完了後、以下の形式で報告してください。

```
## 完了報告 — Issue #{issue['number']}：{issue['title']}

### 作成・変更したファイル
| ファイル | 変更内容 |
|---------|---------|
| （ファイルパス） | （変更内容） |

### 完了条件チェック
（Issue の完了条件を1つずつ確認）

### CEOが次に確認・判断すべきこと
（残タスクや意思決定が必要な事項）
```
"""


def generate_claude_tasks(issues_dir: Path, output_dir: Path) -> list[Path]:
    """
    issues_dir 内の全Issueファイルを読み込み、
    output_dir にClaude Code用指示書を生成する。
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    issue_files = sorted(issues_dir.glob("*.md"))
    if not issue_files:
        return []

    saved: list[Path] = []
    for issue_path in issue_files:
        text = issue_path.read_text(encoding="utf-8")
        issue = _parse_issue(text)

        if not issue["number"]:
            continue

        # 出力ファイル名：001_xxx_prompt.md
        stem = issue_path.stem  # 例: 001_privacyポリシーの整備と明示
        output_name = f"{stem}_prompt.md"
        output_path = output_dir / output_name

        prompt = _build_prompt(issue, issue_path)
        output_path.write_text(prompt, encoding="utf-8")
        saved.append(output_path)

    return saved
