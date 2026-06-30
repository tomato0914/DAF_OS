import re
from pathlib import Path


_SLUG_MAP = {
    "リマインダー": "reminder",
    "通知": "notification",
    "ケアガイド": "care_guide",
    "犬種": "breed_guide",
    "App Store": "appstore",
    "アプリストア": "appstore",
    "説明文": "description",
    "SNS": "sns",
    "マーケティング": "marketing",
    "セキュリティ": "security",
    "プライバシーポリシー": "privacy_policy",
    "プライバシー": "privacy",
    "データ暗号化": "data_encryption",
    "データ": "data",
    "KPI": "kpi",
    "インフラ": "infrastructure",
    "チェックリスト": "checklist",
    "UGC": "ugc",
    "コミュニティ": "community",
    "ダッシュボード": "dashboard",
    "健康": "health",
    "写真": "photo",
    "体重": "weight",
    "脆弱性テスト": "vulnerability_test",
    "脆弱性": "vulnerability",
    "暗号化": "encryption",
    "同意取得": "consent",
    "フロー": "flow",
    "設計": "design",
    "整備": "setup",
    "実施": "execution",
    "実装": "implementation",
    "定義": "definition",
    "計測": "measurement",
    "ユーザー": "user",
    "ポリシー": "policy",
    "確認": "check",
    "の": "_",
    "と": "_",
}


def _title_to_slug(title: str) -> str:
    slug = title.strip()
    for jp, en in _SLUG_MAP.items():
        slug = slug.replace(jp, en)
    # 残った非ASCII文字を除去してからクリーンアップ
    slug = re.sub(r"[^\x00-\x7F]", "", slug)
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "_", slug).strip("_").lower()
    return slug[:40] if slug else "issue"


def parse_and_save_issues(raw: str, output_dir: Path) -> list[Path]:
    """
    Issue一括テキストを個別ファイルに分割して保存する。
    戻り値: 保存したファイルのパスリスト
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # "# Issue #NNN" を区切りとして分割
    blocks = re.split(r"(?=^# Issue #\d+)", raw, flags=re.MULTILINE)
    blocks = [b.strip() for b in blocks if re.match(r"^# Issue #\d+", b.strip())]

    if not blocks:
        # フォールバック：--- 区切りで分割を試みる
        blocks = [b.strip() for b in raw.split("---") if b.strip()]
        blocks = [b for b in blocks if "Issue" in b or "タイトル" in b]

    saved: list[Path] = []
    for i, block in enumerate(blocks, start=1):
        # Issue番号をブロックから抽出（なければ連番）
        num_match = re.search(r"#\s*(\d+)", block.split("\n")[0])
        num = int(num_match.group(1)) if num_match else i

        # タイトルを抽出してスラッグ化
        title_match = re.search(r"## タイトル\s*\n+(.+)", block)
        if title_match:
            slug = _title_to_slug(title_match.group(1))
        else:
            slug = "issue"

        filename = f"{num:03d}_{slug}.md"
        path = output_dir / filename
        path.write_text(block, encoding="utf-8")
        saved.append(path)

    return saved
