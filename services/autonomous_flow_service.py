"""
DAF OS v2.0 Phase2 — 半自律実装フローサービス

GitHub Issue → 実装キュー → CEO承認 → Claude Code実装 → PRドラフト生成
の流れを1つにまとめる。LLM不使用（テンプレートベース）。

このサービスは **CEOが承認済み（outputs/approvals/approved/）のアイテムのみ**を対象にする。
未承認・却下済みのアイテムは一切含まれない。

安全設計：
- git commit しない
- git push しない
- Pull Request を作成しない
- .env は一切読み取らない
- GitHub Token を表示しない
"""

import re
from datetime import datetime
from pathlib import Path

from services.product_registry_service import DEFAULT_PRODUCT, get_product_by_name

# 担当者ごとの編集可能ファイル・禁止ファイル（claude_task_generator.py と同等の方針）
_ASSIGNEE_RULES: dict[str, dict[str, list[str]]] = {
    "Sirius": {
        "may_edit": ["docs/", "outputs/appstore_description.md", "memory/sirius.md"],
        "must_not_touch": [".env", "crews/", "agents/", "services/", "main.py"],
    },
    "Nova": {
        "may_edit": ["docs/", "outputs/social_posts.md", "memory/nova.md"],
        "must_not_touch": [".env", "crews/", "agents/", "services/", "main.py"],
    },
    "Cosmos": {
        "may_edit": ["docs/", "outputs/launch_checklist.md", "memory/cosmos.md"],
        "must_not_touch": [".env", "crews/", "agents/", "services/", "main.py"],
    },
    "Atlas": {
        "may_edit": ["docs/", "memory/atlas.md", "requirements.txt"],
        "must_not_touch": [".env", "outputs/", "main.py"],
    },
    "Orion": {
        "may_edit": ["docs/", "outputs/report.md", "memory/orion.md", "README.md"],
        "must_not_touch": [".env", "crews/", "agents/", "services/", "main.py"],
    },
}

_DEFAULT_RULES = {
    "may_edit": ["docs/", "outputs/"],
    "must_not_touch": [".env", "main.py", "crews/", "agents/", "services/"],
}


# ──────────────────────────────────────────
# パーサー
# ──────────────────────────────────────────

def _extract_source_issue_meta(outputs: Path, purpose_text: str) -> dict[str, str]:
    """
    '自動生成 by DAF OS — ソース: `outputs/issues/xxx.md`' から
    元Issueファイルを読み込み、想定担当・関連成果物を取得する。
    """
    m = re.search(r"ソース: `([^`]+)`", purpose_text)
    if not m:
        return {}
    source_path = outputs.parent / m.group(1)
    if not source_path.exists():
        return {}
    text = source_path.read_text(encoding="utf-8")
    assignee_m = re.search(r"## 想定担当\s*\n(.+)", text)
    artifact_m = re.search(r"## 関連成果物\s*\n(.+)", text)
    return {
        "assignee": assignee_m.group(1).strip() if assignee_m else "",
        "artifact": artifact_m.group(1).strip() if artifact_m else "",
    }


def _build_file_rules(assignee: str, artifact: str) -> tuple[list[str], list[str]]:
    rules = _ASSIGNEE_RULES.get(assignee, _DEFAULT_RULES)
    may_edit = list(rules["may_edit"])
    artifact_path_map = {
        "report.md": "outputs/report.md",
        "appstore_description.md": "outputs/appstore_description.md",
        "social_posts.md": "outputs/social_posts.md",
        "launch_checklist.md": "outputs/launch_checklist.md",
    }
    artifact_path = artifact_path_map.get(artifact, artifact)
    if artifact_path and artifact_path not in may_edit:
        may_edit.insert(0, artifact_path)
    return may_edit, list(rules["must_not_touch"])


def _parse_approved_item(path: Path, outputs: Path) -> dict | None:
    """承認済みファイル（type: implementation）を構造化データに変換する。"""
    text = path.read_text(encoding="utf-8")

    type_m = re.search(r"^type: (.+)$", text, re.MULTILINE)
    if not type_m or type_m.group(1).strip() != "implementation":
        return None

    # ディレクトリだけでなく status フロントマターも確認する（過去の不整合データ対策）
    status_m = re.search(r"^status: (.+)$", text, re.MULTILINE)
    if not status_m or status_m.group(1).strip() != "approved":
        return None

    id_m = re.search(r"^id: (.+)$", text, re.MULTILINE)
    approval_id = id_m.group(1).strip() if id_m else path.stem

    num_m = re.search(r"impl_issue_(\d+)", approval_id)
    issue_number = num_m.group(1) if num_m else "?"

    title_m = re.search(r"^title: (.+)$", text, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else approval_id
    # "実装: Issue #NN — " のような接頭辞を除去して素のタイトルにする
    title = re.sub(r"^実装:\s*Issue\s*#\d+\s*[—\-]\s*", "", title)

    url_m = re.search(r"\*\*GitHub Issue:\*\*\s*\[([^\]]+)\]", text)
    github_url = url_m.group(1).strip() if url_m else ""

    purpose_m = re.search(r"## 実装目的\s*\n\n(.+)", text)
    purpose_text = purpose_m.group(1).strip() if purpose_m else ""

    prompt_m = re.search(r"```\n(GitHub Issue[\s\S]*?)\n```", text)
    prompt_text = prompt_m.group(1).strip() if prompt_m else ""

    background_m = re.search(r"背景：\n([\s\S]*?)\n\n要件：", prompt_text)
    requirements_m = re.search(r"要件：\n([\s\S]*?)\n\n完了条件：", prompt_text)
    completion_m = re.search(r"完了条件：\n([\s\S]*?)(?=\n\n実装完了後|\Z)", prompt_text)

    background = background_m.group(1).strip() if background_m else ""
    requirements = requirements_m.group(1).strip() if requirements_m else ""
    completion = completion_m.group(1).strip() if completion_m else ""

    approved_at_m = re.search(r"^approved_at: (.+)$", text, re.MULTILINE)
    approved_at = approved_at_m.group(1).strip() if approved_at_m else ""

    meta = _extract_source_issue_meta(outputs, purpose_text)
    assignee = meta.get("assignee", "")
    artifact = meta.get("artifact", "")
    may_edit, must_not_touch = _build_file_rules(assignee, artifact)

    # 対象プロダクト / 作業ディレクトリ（implementation_queue.md 経由で埋め込まれる）
    # 旧フォーマットの承認済みファイル（product情報なし）は DEFAULT_PRODUCT にフォールバック
    product_m = re.search(r"\*\*対象プロダクト:\*\*\s*(\S+)　\*\*作業ディレクトリ:\*\*\s*(\S+)", text)
    if product_m:
        product = product_m.group(1).strip()
        work_dir = product_m.group(2).strip()
    else:
        product = DEFAULT_PRODUCT
        work_dir = "."

    product_entry = get_product_by_name(product)
    product_warning = ""
    if product_entry is None:
        product_warning = f"⚠️ プロダクト「{product}」が products/*.md に登録されていません。"
    elif not product_entry["path_exists"]:
        product_warning = f"⚠️ プロダクト「{product}」のパスが見つかりません（{product_entry['path']}）。"

    return {
        "approval_id": approval_id,
        "issue_number": issue_number,
        "title": title,
        "github_url": github_url,
        "background": background,
        "requirements": requirements,
        "completion": completion,
        "assignee": assignee or "未指定",
        "may_edit": may_edit,
        "must_not_touch": must_not_touch,
        "approved_at": approved_at,
        "product": product,
        "work_dir": work_dir,
        "product_warning": product_warning,
        "raw_prompt": prompt_text,
    }


def get_approved_implementation_items(outputs: Path) -> list[dict]:
    """
    outputs/approvals/approved/ から type: implementation のアイテムのみを抽出する。
    承認済み（approved/ 配下）以外は絶対に含めない。
    """
    approved_dir = outputs / "approvals" / "approved"
    if not approved_dir.exists():
        return []
    items = []
    for f in sorted(approved_dir.glob("*.md")):
        item = _parse_approved_item(f, outputs)
        if item:
            items.append(item)
    return items


def get_approved_implementation_count(outputs: Path) -> int:
    """Web UI 向け：承認済み実装アイテム件数のみを軽量に返す。"""
    return len(get_approved_implementation_items(outputs))


# ──────────────────────────────────────────
# ドキュメント生成
# ──────────────────────────────────────────

def _render_item(item: dict) -> str:
    may_edit_md = "\n".join(f"- `{p}`" for p in item["may_edit"])
    must_not_md = "\n".join(f"- `{p}`" for p in item["must_not_touch"])

    warning_line = f"\n> {item['product_warning']}\n" if item.get("product_warning") else ""

    return f"""## Issue #{item['issue_number']} — {item['title']}

> ✅ 承認済み（{item['approved_at'] or '承認日時不明'}） / 想定担当: {item['assignee']}
{warning_line}
### 対象Issue

Issue #{item['issue_number']}

### GitHub URL

{item['github_url'] or '（URL不明）'}

### 対象プロダクト

{item['product']}

### 作業ディレクトリ

`{item['work_dir']}`

### 実装目的

{item['background'] or '（背景情報なし）'}

### やってほしいこと

{item['requirements'] or '（要件情報なし）'}

### 触ってよいファイル

{may_edit_md}

### 触らないファイル

{must_not_md}

### 完了条件

{item['completion'] or '（完了条件情報なし）'}

### 実装後に確認すべきこと

- 変更したファイルの一覧を確認する
- 完了条件をすべて満たしているか確認する
- 「触らないファイル」に挙げたファイルを変更していないか確認する
- 動作確認方法をCEOへの報告としてまとめる

### 実装後にPRドラフトを生成する手順

実装が完了すると `git diff` に変更が現れます。以下のいずれかの方法でPRドラフトを生成してください。

```bash
# 方法1: 次回の経営会議実行時に自動生成される
python main.py

# 方法2: 経営会議を待たずにすぐ生成したい場合
python services/pr_preparation_service.py
```

生成された `outputs/pr_draft.md` を確認し、内容が問題なければCEOが手動で
`git commit` / `git push` / Pull Request作成 を行ってください。
**DAF OSはこれらを自動実行しません。**

---
"""


def generate_autonomous_flow(outputs: Path) -> Path | None:
    """
    承認済みの実装アイテムから outputs/autonomous_flow.md を生成する。
    承認済みアイテムが1件もない場合は安全にスキップする。
    """
    items = get_approved_implementation_items(outputs)
    if not items:
        print("[半自律フロー] 承認済みの実装アイテムがないためスキップします")
        return None

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = (
        f"# 半自律実装フロー\n\n"
        f"> 生成日時: {now}\n"
        f"> 対象: CEO承認済みの実装アイテムのみ（{len(items)}件）\n\n"
        f"このファイルは以下の流れをつなぐための実装指示書です：\n\n"
        f"```\n"
        f"GitHub Issue → 実装キュー → CEO承認 → Claude Code実装 → PRドラフト生成\n"
        f"```\n\n"
        f"⚠️ **DAF OSは git commit / git push / Pull Request作成を自動実行しません。**\n"
        f"以下の指示書をClaude Codeに貼り付けて実装を進め、完了後は必ずCEOが内容を確認してください。\n\n"
        f"---\n\n"
    )

    body = "\n".join(_render_item(item) for item in items)
    content = header + body

    path = outputs / "autonomous_flow.md"
    path.write_text(content, encoding="utf-8")
    print(f"[半自律フロー] ✓ {path}（{len(items)}件）")
    return path


def get_autonomous_flow_summary(outputs: Path) -> dict | None:
    """Web UI 向けの要約を返す。"""
    items = get_approved_implementation_items(outputs)
    path = outputs / "autonomous_flow.md"
    if not items or not path.exists():
        return None
    return {
        "count": len(items),
        "issues": [
            {
                "number": i["issue_number"],
                "title": i["title"],
                "assignee": i["assignee"],
                "product": i["product"],
                "work_dir": i["work_dir"],
                "product_warning": i.get("product_warning", ""),
            }
            for i in items
        ],
    }


def run_autonomous_flow_generation(outputs: Path) -> Path | None:
    """main.py のパイプラインから呼び出す。"""
    print("[半自律フロー] 承認済み実装アイテムを確認中...")
    return generate_autonomous_flow(outputs)


if __name__ == "__main__":
    generate_autonomous_flow(Path(__file__).parent.parent / "outputs")
