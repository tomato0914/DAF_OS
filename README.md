# DAF OS v0.5a

Digital Asset Factory の最小プロトタイプ。  
CrewAI を使って5人のAI社員が経営会議を行い、成果物と実装Issueを自動生成する。  
v0.2 から **Notion連携**、v0.3 から **5人体制**、v0.4 から **成果物自動生成**、v0.5a から **Issue自動生成**に対応。

## AI社員

| 名前 | 役職 | 担当成果物 |
|------|------|-----------|
| Orion | COO | `report.md`（最終提案書）＋ Issue生成 |
| Atlas | CTO | 技術リスク確認（report.mdに統合） |
| Sirius | CPO | `appstore_description.md` |
| Nova | CMO | `social_posts.md` |
| Cosmos | CIO | `launch_checklist.md` |

## 生成される成果物

`python main.py` を実行すると `outputs/` に以下が生成されます。

| ファイル | 内容 | 担当 |
|---------|------|------|
| `report.md` | 最終提案書（全員の意見＋アクションプラン） | Orion |
| `appstore_description.md` | App Store掲載用説明文 | Sirius |
| `social_posts.md` | SNS投稿文5本 | Nova |
| `launch_checklist.md` | 公開前チェックリスト | Cosmos |
| `issues/001_*.md` | 実装Issue（3〜5件） | Orion |

### Issueの形式

`outputs/issues/` フォルダに番号付きファイルとして保存されます：

```
outputs/issues/
├── 001_privacy_policy_setup.md
├── 002_data_encryption_check.md
├── 003_vulnerability_test_execution.md
├── 004_user_consent_flow_design.md
└── 005_kpi_definition_measurement_implementation.md
```

各Issueには **タイトル・背景・要件・優先度・想定担当・完了条件・関連成果物** が含まれます。

---

## セットアップ

### 1. 依存パッケージをインストール

```bash
cd DAF_OS
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install "setuptools<70"   # pkg_resources の互換性対応
```

### 2. `.env` を作成

```bash
cp .env.example .env
```

`.env` の内容：

```
# 必須
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxx

# 任意（Notion連携を使う場合）
NOTION_API_KEY=secret_xxxxx
ORION_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ATLAS_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. 実行

```bash
python main.py
```

---

## Notion連携の設定方法

### ステップ1：Notion Integration を作成

1. [Notion Developers](https://www.notion.so/my-integrations) にアクセス
2. 「New integration」をクリック
3. 名前（例：`DAF OS`）を入力して作成
4. 表示された **Internal Integration Token** をコピー → `.env` の `NOTION_API_KEY` に貼り付け

### ステップ2：Notionページを作成して連携

1. Notionで Orion と Atlas の社員手帳ページを作成（[memory/orion.md](memory/orion.md) の内容を参考に）
2. 各ページの右上メニュー「…」→「Connections」→ 作成した Integration を追加
3. ページURLまたは「Share」から **Page ID** をコピー
   - URL例：`https://notion.so/My-Page-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` の部分が Page ID
4. `.env` に設定：
   ```
   ORION_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ATLAS_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

### フォールバック動作

Notion が未設定・接続失敗の場合は、自動的にローカルの `memory/*.md` を使用する。

| 状態 | 使用する手帳 |
|------|------------|
| Notion設定あり・接続成功 | Notionページの内容 |
| Notion未設定 | `memory/orion.md` / `memory/atlas.md` |
| Notion接続失敗（APIエラー等） | `memory/orion.md` / `memory/atlas.md` |

---

## 使用モデル

デフォルトは `openai/gpt-4o-mini`（OpenRouter経由）。  
[crews/mofulog_crew.py](crews/mofulog_crew.py) の `build_llm()` 内の `model=` を変更すれば他のモデルも使える。

| モデル名 | 特徴 |
|----------|------|
| `openrouter/openai/gpt-4o-mini` | 安価・高速（デフォルト） |
| `openrouter/openai/gpt-4o` | 高品質・高コスト |
| `openrouter/anthropic/claude-3-5-haiku` | 安価・高品質 |
| `openrouter/google/gemini-flash-1.5` | 安価・多用途 |

---

## 出力

`outputs/report.md` に以下の形式でレポートが生成される：

```
# もふログ Version2 改善提案書

## 1. Orionの経営判断
## 2. Atlasの技術レビュー
## 3. 優先すべき改善案
## 4. 実装難易度
## 5. CEOへの提案
```

## フォルダ構成

```
DAF_OS/
├── main.py                  # エントリーポイント
├── agents/
│   ├── orion.py             # COO Orion（Notion/ローカル両対応）
│   └── atlas.py             # CTO Atlas（Notion/ローカル両対応）
├── crews/
│   └── mofulog_crew.py      # クルー編成・LLM設定・タスク定義
├── services/
│   └── notion_service.py    # Notionページ取得・フォールバック処理
├── memory/
│   ├── orion.md             # Orion のローカル社員手帳
│   └── atlas.md             # Atlas のローカル社員手帳
├── outputs/
│   └── report.md            # 生成されるレポート
├── .env.example
├── requirements.txt
└── README.md
```

## プライバシーポリシーの公開（GitHub Pages）

App Store Connect に登録するプライバシーポリシーURLを、GitHub Pages で公開する手順です。

### 1. GitHubリポジトリを作成してプッシュ

```bash
cd DAF_OS
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/yourname/DAF_OS.git
git push -u origin main
```

### 2. `docs/_config.yml` を自分のリポジトリ情報に書き換える

[docs/_config.yml](docs/_config.yml) を開いて2箇所を修正：

```yaml
baseurl: "/DAF_OS"               # ← リポジトリ名に変更
url: "https://yourname.github.io"  # ← GitHubユーザー名に変更
```

変更後にコミット＆プッシュ：

```bash
git add docs/_config.yml
git commit -m "set github pages url"
git push
```

### 3. GitHub Pages を有効化

1. GitHubのリポジトリページを開く
2. **Settings → Pages**
3. Source：`Deploy from a branch`
4. Branch：`main` ／ Folder：`/docs`
5. **Save** をクリック

### 4. 公開URL

設定後、数分で以下のURLでアクセスできます。

| ページ | URL |
|--------|-----|
| トップ | `https://yourname.github.io/DAF_OS/` |
| **プライバシーポリシー** | `https://yourname.github.io/DAF_OS/privacy_policy` |

> App Store Connect の「プライバシーポリシーURL」欄には  
> `https://yourname.github.io/DAF_OS/privacy_policy` を入力してください。

### 関連ファイル

| ファイル | 役割 |
|---------|------|
| `docs/privacy_policy.md` | ポリシー本文（公開ページ） |
| `docs/index.md` | サイトのトップページ |
| `docs/_config.yml` | Jekyll設定（URLの baseurl を要編集） |
| `docs/privacy_policy_display_guide.md` | アプリ内表示設計書（非公開・社内用） |

---

## トラブルシューティング

- **OPENROUTER_API_KEY エラー**：`.env` にキーが正しく設定されているか確認
- **Notion接続エラー**：Integration がページに追加されているか確認（ページ右上「Connections」）
- **pkg_resources エラー**：`pip install "setuptools<70"` を実行
- **GitHub Pagesが表示されない**：Settings → Pages でブランチ・フォルダの設定を確認。反映まで最大5分かかる
- **実行エラー**：`python main.py` は `DAF_OS/` ディレクトリ内から実行する
