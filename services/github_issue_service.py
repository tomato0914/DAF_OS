"""
outputs/issues/*.md を読み込み、GitHub Issues へ登録するサービス。
- タイトル重複チェック（Open状態のIssueと照合）
- 優先度 → ラベル変換
- 登録結果を outputs/github_issue_results.md に保存
"""

import re
import urllib.request
import urllib.error
import json
from datetime import datetime
from pathlib import Path

from services.product_registry_service import DEFAULT_PRODUCT, get_product_by_name


# 優先度 → GitHubラベル
_PRIORITY_LABELS: dict[str, str] = {
    "高": "priority: high",
    "中": "priority: medium",
    "低": "priority: low",
}

# 想定担当 → GitHubラベル
_ASSIGNEE_LABELS: dict[str, str] = {
    "Orion": "agent: orion",
    "Atlas": "agent: atlas",
    "Sirius": "agent: sirius",
    "Nova": "agent: nova",
    "Cosmos": "agent: cosmos",
}


# ---------- Issueパーサー ----------

def _extract_section(text: str, heading: str) -> str:
    pattern = rf"## {re.escape(heading)}\s*\n([\s\S]*?)(?=\n## |\n---|\Z)"
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""


def parse_issue_file(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    num_m = re.search(r"# Issue #(\d+)", text)
    product = _extract_section(text, "対象プロダクト") or DEFAULT_PRODUCT
    return {
        "number": num_m.group(1) if num_m else "",
        "title": _extract_section(text, "タイトル"),
        "background": _extract_section(text, "背景"),
        "requirements": _extract_section(text, "要件"),
        "priority": _extract_section(text, "優先度"),
        "assignee": _extract_section(text, "想定担当"),
        "completion": _extract_section(text, "完了条件"),
        "artifacts": _extract_section(text, "関連成果物"),
        "product": product,
        "raw": text,
    }


def _build_body(issue: dict[str, str], source_path: Path) -> str:
    return (
        f"> 自動生成 by DAF OS — ソース: `{source_path}`\n\n"
        f"## 背景\n\n{issue['background']}\n\n"
        f"## 要件\n\n{issue['requirements']}\n\n"
        f"## 完了条件\n\n{issue['completion']}\n\n"
        f"## 関連成果物\n\n{issue['artifacts']}\n\n"
        f"---\n**優先度**: {issue['priority']}　**想定担当**: {issue['assignee']}"
        f"　**対象プロダクト**: {issue['product']}"
    )


def _prefixed_title(title: str, product: str) -> str:
    """タイトル先頭に [product] を付与する。"""
    return f"[{product}] {title}"


# ---------- GitHub API クライアント ----------

class GitHubClient:
    def __init__(self, token: str, owner: str, repo: str):
        self._base = f"https://api.github.com/repos/{owner}/{repo}"
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, body: dict | None = None) -> dict | list:
        url = f"{self._base}{path}"
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, headers=self._headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode()
            raise RuntimeError(f"GitHub API {method} {url} → {e.code}: {msg}") from e

    def list_open_issues(self) -> list[dict]:
        """Open状態のIssue一覧を取得（最大100件）。"""
        return self._request("GET", "/issues?state=open&per_page=100")  # type: ignore

    def ensure_label(self, name: str, color: str = "ededed") -> None:
        """ラベルが存在しなければ作成する。"""
        try:
            self._request("GET", f"/labels/{urllib.parse.quote(name)}")
        except RuntimeError:
            try:
                self._request("POST", "/labels", {"name": name, "color": color})
            except RuntimeError:
                pass  # 競合などは無視

    def create_issue(self, title: str, body: str, labels: list[str]) -> dict:
        return self._request("POST", "/issues", {  # type: ignore
            "title": title,
            "body": body,
            "labels": labels,
        })


# urllib.parse は標準ライブラリなのでインポート追加
import urllib.parse


# ---------- ラベル色定義 ----------

_LABEL_COLORS: dict[str, str] = {
    "priority: high": "d73a4a",
    "priority: medium": "e4e669",
    "priority: low": "0075ca",
    "agent: orion": "7057ff",
    "agent: atlas": "008672",
    "agent: sirius": "e4e669",
    "agent: nova": "d4edda",
    "agent: cosmos": "cfd3d7",
}


# ---------- メイン処理 ----------

class IssueRegistrationResult:
    def __init__(self, issue_num: str, title: str):
        self.issue_num = issue_num
        self.title = title
        self.status: str = ""      # "created" | "skipped" | "error"
        self.github_url: str = ""
        self.github_num: int = 0
        self.reason: str = ""


def register_issues(
    issues_dir: Path,
    token: str,
    owner: str,
    repo: str,
) -> list[IssueRegistrationResult]:
    client = GitHubClient(token, owner, repo)

    # 既存Openタイトルを取得（重複チェック用）
    print("  [GitHub] 既存IssueのOpenリストを取得中...")
    try:
        open_issues = client.list_open_issues()
        existing_titles = {i["title"].strip() for i in open_issues if isinstance(i, dict)}
    except RuntimeError as e:
        raise RuntimeError(f"GitHub接続に失敗しました: {e}") from e

    # ラベルを事前作成
    all_labels = list(_LABEL_COLORS.keys())
    for label in all_labels:
        client.ensure_label(label, _LABEL_COLORS[label])

    issue_files = sorted(issues_dir.glob("*.md"))
    results: list[IssueRegistrationResult] = []

    for path in issue_files:
        issue = parse_issue_file(path)
        if not issue["title"]:
            continue

        # product 検証（存在しないproductは警告のみ・登録自体は止めない）
        product = issue["product"]
        if get_product_by_name(product) is None:
            print(f"  [警告] #{issue['number']} 未登録のプロダクトです: {product}"
                  f"（products/*.md に登録するとダッシュボードに反映されます）")

        title = _prefixed_title(issue["title"], product)
        result = IssueRegistrationResult(issue["number"], title)

        # 重複チェック（[product] タイトルで比較）
        if title in existing_titles:
            result.status = "skipped"
            result.reason = "同タイトルのOpen Issueが既に存在します"
            results.append(result)
            print(f"  [スキップ] #{issue['number']} {title}")
            continue

        # ラベル構築
        labels: list[str] = []
        priority_label = _PRIORITY_LABELS.get(issue["priority"])
        if priority_label:
            labels.append(priority_label)
        assignee_label = _ASSIGNEE_LABELS.get(issue["assignee"])
        if assignee_label:
            labels.append(assignee_label)

        # Issue作成
        body = _build_body(issue, path)
        try:
            created = client.create_issue(title, body, labels)
            result.status = "created"
            result.github_num = created["number"]
            result.github_url = created["html_url"]
            existing_titles.add(title)  # 連続重複を防ぐ
            print(f"  [作成] #{issue['number']} {title} → {result.github_url}")
        except RuntimeError as e:
            result.status = "error"
            result.reason = str(e)
            print(f"  [エラー] #{issue['number']} {issue['title']}: {e}")

        results.append(result)

    return results


def save_results(results: list[IssueRegistrationResult], owner: str, repo: str, output_path: Path) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# GitHub Issue 登録結果",
        "",
        f"**実行日時**: {now}  ",
        f"**リポジトリ**: [{owner}/{repo}](https://github.com/{owner}/{repo})",
        "",
        "---",
        "",
        "| # | タイトル | 結果 | GitHub Issue | 備考 |",
        "|---|---------|------|-------------|------|",
    ]

    for r in results:
        if r.status == "created":
            gh_link = f"[#{r.github_num}]({r.github_url})"
            lines.append(f"| {r.issue_num} | {r.title} | ✅ 作成 | {gh_link} | |")
        elif r.status == "skipped":
            lines.append(f"| {r.issue_num} | {r.title} | ⏭ スキップ | — | {r.reason} |")
        else:
            lines.append(f"| {r.issue_num} | {r.title} | ❌ エラー | — | {r.reason} |")

    created = sum(1 for r in results if r.status == "created")
    skipped = sum(1 for r in results if r.status == "skipped")
    errors  = sum(1 for r in results if r.status == "error")

    lines += [
        "",
        "---",
        "",
        "## サマリー",
        "",
        f"- 作成: **{created}件**",
        f"- スキップ（重複）: **{skipped}件**",
        f"- エラー: **{errors}件**",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
