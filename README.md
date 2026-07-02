# DAF OS v2.6 / v1.7

Digital Asset Factory の最小プロトタイプ。  
CrewAI を使って5人のAI社員が経営会議を行い、成果物・Issue・Claude Task指示書・GitHub Issues登録を自動化する。  
v0.2 から **Notion連携**、v0.3 から **5人体制**、v0.4 から **成果物自動生成**、v0.5a から **Issue自動生成**、v0.5b から **Claude Task生成**、v0.6 から **GitHub Issues自動登録**、v0.6.1 から **クリーンアップ**、v0.7 から **ダッシュボード**、v0.8 から **ワンコマンド起動**、v0.9 から **launchd自動スケジュール**、v1.0 から **Webダッシュボード**、v1.1 から **Notion議事録自動保存**、v1.2 から **Mac通知**、v1.3 から **会社メモリ（価値観・CEO好み・学び）**、v1.4 から **メモリ見直し提案**、v1.5 から **CEO承認センター（CLI）**、v1.6 から **Web承認センター**、v1.7 から **PR作成準備の自動生成**、v2.0 から **Claude Code 実装キュー自動生成 / 半自律実装フロー**、v2.1 から **マルチプロダクト対応**、v2.2 から **プロダクト別Issue管理**、v2.3 から **ワンクリック実装準備**、v2.4 から **CEOデイリーブリーフ**、v2.5 から **AI承認アドバイザー**、v2.6 から **ダッシュボード自動リフレッシュ**に対応。

## クイックスタート

```bash
# 1. 経営会議を実行してダッシュボードを生成
./run_daf.sh

# 2. ブラウザでダッシュボードを開く（起動していなければ自動起動する）
./open_dashboard.sh
```

---

## ダッシュボードをワンコマンドで開く（open_dashboard.sh）

CEOが1コマンドでWebダッシュボードを開けるようにするスクリプトです。DAF Dashboard.app からもこのスクリプトが呼ばれます。

```bash
./open_dashboard.sh
```

### 動作

1. **自動リフレッシュ判定**（v2.6 Quest46。詳細は次項）— 必要であれば `./run_daf.sh` を自動実行してダッシュボードを最新化する
2. ポート8000で `dashboard_web/app.py` が既に起動しているか確認する
3. 起動中ならそのままブラウザで `http://localhost:8000` を開く
4. 起動していなければ `.venv` を有効化し、`dashboard_web/app.py` をバックグラウンドで起動する
5. バックグラウンド起動時のログは `logs/dashboard_stdout.log` / `logs/dashboard_stderr.log` に保存される
6. サーバー起動後、ブラウザで `http://localhost:8000` を開く

`.venv` が無い場合はエラーメッセージとセットアップ手順を表示して終了します（`run_daf.sh` と同様の挙動）。既にサーバーが起動している場合は、二重起動せずそのままブラウザを開きます。

---

## 自動リフレッシュ（v2.6 Quest46）

`DAF Dashboard.app` や `open_dashboard.sh` を開いたとき、`outputs/dashboard.md` が古ければ自動で `./run_daf.sh` を実行し、最新の状態でダッシュボードを表示します。

### コマンド例

```bash
# 通常起動（30分以上古ければ自動で再実行、そうでなければそのまま開く）
./open_dashboard.sh

# 強制的に最新化してから開く
./open_dashboard.sh --refresh

# 再実行せず、既存のダッシュボードのまま開く
./open_dashboard.sh --no-refresh
```

### 自動実行される条件

- `outputs/dashboard.md` が存在しない
- `outputs/dashboard.md` が30分以上前に生成されたものである
- `--refresh` が指定された

### 自動実行されない条件

- 既に `run_daf.sh` が実行中（二重実行防止）
- `outputs/dashboard.md` が30分以内に更新済み
- `--no-refresh` が指定された

`--refresh` と `--no-refresh` を両方指定した場合は `--no-refresh` が優先されます。

### ログ

自動リフレッシュの判定結果と `run_daf.sh` の実行ログは `logs/auto_refresh.log` に記録されます。

### 安全設計

- 二重実行しません（`run_daf.sh` が実行中であれば自動実行をスキップします）
- `run_daf.sh` の実行に失敗しても、既存の `outputs/dashboard.md` のままWebダッシュボードは必ず開きます
- `.env` の内容は一切表示・ログ出力しません
- `git commit` / `git push` は行いません

---

## DAF Dashboard.app（Dockから1クリックで開く）

MacのDockから1クリックでWebダッシュボードを開けるように、`DAF Dashboard.app` を作成できます。中身は `open_dashboard.sh` を呼び出すだけの薄いAppleScriptアプリです。

### 作成方法（スクリプトを使う・推奨）

```bash
./scripts/create_dashboard_app.sh
```

- `/Applications` に書き込み権限があれば `/Applications/DAF Dashboard.app` を作成します
- 書き込めない場合は `DAF_OS` フォルダ内に作成します
- 既に同名の `.app` がある場合は作り直します（置き換え）

### 作成方法（Automator を手動で使う場合）

1. 「Automator」を開き、「新規書類」→「アプリケーション」を選択
2. アクション検索で「シェルスクリプトを実行」を追加
3. 「シェル」を `/bin/bash` に設定し、以下を入力する（パスは実際のDAF_OSの場所に置き換える）：
   ```bash
   cd /Users/tomato/DAF/DAF_OS
   ./open_dashboard.sh
   ```
4. 「ファイル」→「保存」で名前を `DAF Dashboard`、場所を `アプリケーション` にして保存する

### 作成方法（AppleScriptエディタを手動で使う場合）

1. 「スクリプトエディタ」を開き、新規スクリプトに以下を入力する（パスは実際のDAF_OSの場所に置き換える）：
   ```applescript
   do shell script "cd " & quoted form of "/Users/tomato/DAF/DAF_OS" & " && ./open_dashboard.sh > /dev/null 2>&1 &"
   ```
2. 「ファイル」→「書き出す」→ ファイル形式を「アプリケーション」にして `DAF Dashboard.app` として保存する

### 使い方

1. 作成した `DAF Dashboard.app` をダブルクリックする、またはDockにドラッグ＆ドロップして常駐させる
2. クリックすると `open_dashboard.sh` が実行され、`http://localhost:8000` がブラウザで開く
3. 既にダッシュボードサーバーが起動中の場合は、`open_dashboard.sh` のポート確認ロジックにより二重起動されない

### 完了条件

- `DAF Dashboard.app` をダブルクリックすると `http://localhost:8000` が開く
- 既にサーバー起動中なら二重起動しない（`open_dashboard.sh` のポートチェックに準拠）
- Dockに追加できる（通常の `.app` と同様にドラッグ＆ドロップ可能）

---

## Webダッシュボード（v1.0）

`outputs/dashboard.md` をブラウザで閲覧できます。5秒ごとに自動更新されます。

```bash
python dashboard_web/app.py
```

または `./open_dashboard.sh` を使うと、サーバー起動とブラウザを開く操作を1コマンドにまとめられます。

ブラウザで `http://localhost:8000` を開いてください。

| 機能 | 内容 |
|------|------|
| 今日の状況 | 成果物・Issue・Claude Task・GitHub Issue数 |
| 次のアクション | 高優先度Issueの一覧 |
| 最新のAI提案 | report.md からCEOへの提言を抽出 |
| 進捗バー | 公開準備チェックリスト・AI社員稼働率 |
| GitHub Issues | Open Issue一覧（GITHUB_TOKEN未設定でも動作） |

- スマートフォンでもそのまま閲覧可能（レスポンシブ対応）
- `dashboard.md` が更新されると5秒以内に自動反映

---

## CEOデイリーブリーフ（v2.4 Quest43）

CEOが毎朝5分で状況を把握し、「今日やること」に迷わないための要約レポートです。

### 生成ファイル

`outputs/ceo_brief.md`

以下の情報源から自動生成されます（LLM不使用・外部API不使用）：

- `outputs/dashboard.md`（フォールバック用）
- `outputs/implementation_queue.md`
- `outputs/approvals/`（pending / approved / rejected）
- `products/*.md`

### 出力内容

| セクション | 内容 |
|-----------|------|
| ☀️ CEO Daily Brief | タイトル・生成日時 |
| 📦 プロダクト状況 | 登録プロダクトごとのステータス・パス確認結果 |
| ⚡ 最優先事項 TOP3 | 実装キュー→ローカルIssue→dashboard.mdの順にフォールバックして選出 |
| 🚀 実装準備状況 | 承認済み実装アイテム数、`claude_code_prompt.md`/`pr_draft.md`の有無 |
| 📋 今日やること（3つまで） | 承認待ち・最優先Issue・実装準備・PR確認の中から最大3件に絞り込み |
| 🌱 CEOへの一言 | 状況に応じた一言メッセージ |

### 確認できる場所

- `python main.py` 実行後、`outputs/ceo_brief.md` を直接開く
- `outputs/dashboard.md` の「☀️ CEO Daily Brief」セクション
- Webダッシュボード（`http://localhost:8000`）の最上部カード
- Mac通知（`python main.py` 実行完了時）— 「今日やることTOP3」として表示

### 動作仕様

| 状況 | 動作 |
|------|------|
| 情報源（dashboard.md・implementation_queue.md・products/*.mdなど）が一部欠けている | 該当セクションを空欄・デフォルト表示にして生成を継続する |
| 承認待ち・優先Issue・実装準備のいずれも無い | 「緊急のアクションはありません」と表示 |
| 生成中に例外が発生 | ログに警告を出して安全にスキップ（既存の `ceo_brief.md` は変更されない） |

### 安全設計

- **外部APIを呼びません。** すべてローカルファイルの読み取りのみで完結します。
- 既存ファイルを削除することはありません。
- 情報が不足していても例外を出さず、空欄・デフォルト値で生成を継続します。

---

## ワンクリック実装準備（v2.3 Quest42）

承認済みIssueからClaude Codeへ渡すまでの準備を、Webダッシュボードのボタン1つで完結させる機能です。

### 使い方

1. [承認センター（v1.6）](#web-承認センターv16)で実装アイテムを承認する
2. Webダッシュボード（`http://localhost:8000`）の「🚀 ワンクリック実装準備」カードにある **🚀 実装開始** ボタンを押す
3. 以下が自動で行われる：
   - `outputs/autonomous_flow.md` の再生成（最新の承認状態を反映）
   - `outputs/claude_code_prompt.md` の生成（複数プロダクトのIssueがあってもプロダクトごとにセクション分けされ、`cd 作業ディレクトリ` → プロンプト貼り付け、の手順がそのままコピペできる形式）
   - 生成した `claude_code_prompt.md` をMac標準の `open` コマンドでデフォルトアプリにより自動表示（Claude Code自体は起動しません）
4. 開かれたファイルから、作業したいプロダクトのセクションをコピーしてClaude Codeに貼り付ければ実装を開始できる

### API

| メソッド | パス | 内容 |
|---------|------|------|
| POST | `/api/start_implementation` | 承認済み実装アイテムから `autonomous_flow.md` / `claude_code_prompt.md` を生成する |

レスポンス例：

```json
{
  "ok": true,
  "message": "2件の承認済み実装アイテムから実装プロンプトを生成しました。",
  "items": 2,
  "prompt_path": "outputs/claude_code_prompt.md",
  "flow_path": "outputs/autonomous_flow.md",
  "opened": true
}
```

承認済みアイテムが0件の場合は `"ok": false` とメッセージのみ返り、既存ファイルには一切手を加えません。

### 動作仕様

| 状況 | 動作 |
|------|------|
| 承認済みの実装アイテムが0件 | ボタンは無効化表示。押下してもエラーメッセージのみで、既存ファイルは変更されない |
| 生成途中でエラー発生 | 例外を捕捉し `"ok": false` を返す。ファイルへの書き込みは内容を完全に組み立てた後にのみ行うため、既存の `claude_code_prompt.md` / `autonomous_flow.md` は破壊されない |
| Mac以外の環境 | ファイル生成は行われるが、自動オープンのみスキップされる |

### 安全設計

- **git commit / git push は一切行いません。**
- **Claude Code を自動起動しません。** 生成したMarkdownファイルをOS標準のビューアで開くだけです。
- エラー発生時に既存ファイルを削除・上書きすることはありません（新しい内容を完全に構築できた場合のみ書き込みます）。
- 複数プロダクトの承認済みIssueが混在していても、プロダクトごとにセクション分けされるため、どのプロダクトを操作するか迷いません。

---

## プロダクト別Issue管理（v2.2 Quest41）

各Issueがどのプロダクト向けかを明示し、GitHub登録・実装キュー・半自律実装フローの全段階で追跡できるようにする機能です。

### Issueへのproduct指定

`outputs/issues/*.md` に `## 対象プロダクト` セクションを追加すると、そのIssueの対象プロダクトを指定できます。

```markdown
## 対象プロダクト
mofulog
```

指定がない場合は自動的に `DAF_OS`（デフォルト）として扱われます。CrewAIが生成する新規Issueにも、この項目が自動的に含まれるようになりました。

### GitHub登録時のタイトル

GitHub Issue登録時、タイトルの先頭に `[product]` が自動で付与されます。

```
[mofulog] ユーザー同意の取得メカニズム実装
[DAF_OS] ダッシュボードの表示崩れ修正
```

`products/*.md` に未登録のproductが指定された場合は、登録は継続しつつ起動ログに警告を表示します。

### 実装キュー・半自律実装フローへの反映

- `outputs/implementation_queue.md` の各Issueに `product` / `path` が出力されます。
- `outputs/autonomous_flow.md` の各Issueに「対象プロダクト」「作業ディレクトリ」が追加され、Claude Codeがどのリポジトリを編集すべきか判断できます。

### ダッシュボードでの確認

- `outputs/dashboard.md` の「📦 プロダクト別Issue状況」セクション
- Webダッシュボードの「📦 プロダクト別Issue状況」カード（プロダクトごとのIssue数・実装キュー内件数・登録状態）

### 安全設計

- **存在しないproduct**（`products/*.md` に未登録）は警告表示のみで処理は止めません。
- **pathが存在しないproduct**のIssueは実装キューへ追加しません（`⚠️ プロダクト「X」のpathが存在しません → 実装キューから除外`とログ表示）。
- GitHub Token は表示しません。

### 完了条件

- Issueファイル・GitHub Issueタイトル・実装キュー・半自律実装フローのすべてで対象プロダクトが分かる
- Claude Codeは `autonomous_flow.md` の「作業ディレクトリ」を見るだけで編集すべきリポジトリを判断できる
- `products/*.md` を追加するだけで3つ以上のプロダクトに拡張可能（コード変更不要）

---

## マルチプロダクト対応（v2.1 Quest40）

DAFが複数のプロダクト（アプリ・サービス）を横断的に管理できるようにする機能です。`products/*.md` を1ファイル追加するだけで、新しいプロダクトをDAFの管理対象に加えられます。

### プロダクトの追加方法

`products/` フォルダに Markdown ファイルを1つ作成するだけです。

```markdown
---
name: プロダクト名
path: 相対パス（DAF_OSディレクトリからの相対パス、または絶対パス）
type: mobile-app / web-app / internal-tool など自由記述
description: プロダクトの概要
repository: GitHubリポジトリURL
status: active / planning / paused / archived など自由記述
---
```

例：[products/daf_os.md](products/daf_os.md)（DAF_OS自身も1プロダクトとして登録済み）、[products/mofulog.md](products/mofulog.md)

### 動作仕様

| 状況 | 動作 |
|------|------|
| `products/` が空・存在しない | スキップ（エラーなし） |
| `path` に指定したパスが存在しない | ⚠️ 警告表示（起動ログ・ダッシュボード両方） |
| `products/*.md` を追加 | 次回 `python main.py` 実行時に自動反映 |

### 確認できる場所

- 起動ログ：`python main.py` 実行時に `[Products]` として一覧・警告が出力される
- `outputs/dashboard.md` の「🏢 管理中プロダクト」セクション
- Webダッシュボード（`http://localhost:8000`）の「🏢 管理中プロダクト」カード

### 今後の連携予定

[半自律実装フロー（v2.0 Phase2）](#半自律実装フローv20-phase2)がプロダクトごとに実装対象を切り替えられるよう、`services/product_registry_service.py` の `load_products()` が返す構造（`name` / `path` / `type` / `status` など）をそのまま利用できる設計にしています。

### 安全設計

- `.env` は読み取りません。
- GitHub Token は表示しません（`repository` はURL文字列としてのみ保持・表示します）。
- DAF_OS自身も他プロダクトと同じ形式（`products/daf_os.md`）で管理されます。

---

## 半自律実装フロー（v2.0 Phase2）

GitHub Issue → 実装キュー → CEO承認 → Claude Code実装 → PRドラフト生成、という一連の流れを1つにつなぐ機能です。
**対象は承認センター（[Web 承認センター（v1.6）](#web-承認センターv16)）で承認済みの実装アイテムのみ**です。未承認・却下済みのものは一切含まれません。

### 生成ファイル

`outputs/autonomous_flow.md`

承認済みの実装アイテムごとに、以下を含む指示書が生成されます：

| 項目 | 内容 |
|------|------|
| 対象Issue | Issue番号・タイトル |
| GitHub URL | 対象のGitHub Issueリンク |
| 実装目的 | 背景・課題 |
| やってほしいこと | 要件 |
| 触ってよいファイル | 想定担当エージェントごとの編集可能パス |
| 触らないファイル | `.env`・`main.py`・`crews/` など |
| 完了条件 | Issueの完了条件 |
| 実装後に確認すべきこと | 変更ファイル確認・完了条件チェックなど |
| 実装後にPRドラフトを生成する手順 | `python main.py` または `python services/pr_preparation_service.py` の実行方法 |

### ワークフロー

```
python main.py
  ↓
implementation_queue.md 生成（GitHub Open Issuesから）
  ↓
承認センター（Web/CLI）で実装アイテムを承認
  ↓
次回 python main.py 実行時、承認済みアイテムのみ autonomous_flow.md に反映
  ↓
outputs/autonomous_flow.md の指示書を Claude Code に貼り付けて実装
  ↓
実装完了後 python main.py（または pr_preparation_service.py 単体実行）で pr_draft.md を生成
  ↓
CEOが pr_draft.md を確認し、手動で commit / push / PR作成
```

### Webダッシュボードでの確認

`http://localhost:8000` の「📊 ダッシュボード」タブに **🤖 実装準備完了** カードが表示され、対象Issue一覧が確認できます。`outputs/dashboard.md` の「10. 半自律実装フロー」セクションにも表示されます。

### 動作仕様

| 状況 | 動作 |
|------|------|
| 承認済みの実装アイテムがない | スキップ（エラーなし） |
| 承認済みの実装アイテムがある | `outputs/autonomous_flow.md` を生成 |

### 安全設計

- **CEO承認済み（`outputs/approvals/approved/`）のアイテムのみを対象にします。** pending・rejected は含まれません。
- **git commit / git push / Pull Request作成は一切自動実行しません。**
- `.env` は読み取りません。
- GitHub Token は表示しません（本サービスはローカルファイルのみを読み取ります）。

---

## PR作成準備（v1.7）

`python main.py` 実行後、コードの変更差分（`git diff`）から Pull Request 作成に必要な情報を自動生成します。**LLMは使用せず、`git`コマンドの出力のみから生成します。**

### 生成ファイル

`outputs/pr_draft.md`

```markdown
# PR作成準備

> 生成日時: 2026-07-01 16:40

## 推奨ブランチ名
feature/20260701-services

## コミットメッセージ案
feat(services): 3件のファイルを更新

## PRタイトル案
[機能追加/更新] services 関連の変更

## PR本文案
（変更ファイル一覧・diff概要）

## 確認すべきポイント
## リスク
## CEOへの次アクション
```

### 動作仕様

| 状況 | 動作 |
|------|------|
| git リポジトリでない | スキップ（エラーなし） |
| 変更差分がない | スキップ（エラーなし） |
| 変更差分がある | `outputs/pr_draft.md` を生成 |

### Webダッシュボードでの確認

`http://localhost:8000` の「📊 ダッシュボード」タブに **🔀 PR作成準備あり** カードが表示され、推奨ブランチ名・PRタイトル案・コミットメッセージ案を確認できます。`outputs/dashboard.md` の「9. PR作成準備」セクションにも表示されます。

### 安全設計

- **git commit / git push / Pull Request 作成は一切自動実行しません。** すべてCEOが手動で行います。
- `.env`・`.env.local` などの機密ファイルは diff の取得・表示対象から常に除外されます。
- GitHub Token は読み取り・表示されません（本サービスは `git` コマンドのみ使用し、GitHub APIには一切アクセスしません）。
- 生成物はあくまで「下書き」であり、内容は必ず目視確認した上で使用してください。

---

## Web 承認センター（v1.6）

`python main.py` 実行後、ブラウザ上で AIが生成した提案を承認・却下できます。

```bash
python dashboard_web/app.py
# → http://localhost:8000 を開き「✅ 承認センター」タブをクリック
```

### 画面構成

| 要素 | 内容 |
|------|------|
| 承認センタータブ | 承認待ち件数をバッジで表示。クリックで切り替え |
| サマリー | 承認待ち / 承認済み / 却下済みの件数を一覧表示 |
| 承認カード | タイプ・タイトル・内容プレビューを表示 |
| 承認ボタン | クリックで即時承認。画面を自動更新 |
| 却下ボタン | 却下理由入力モーダルを開く。理由を入力して「却下する」 |

### API エンドポイント

| メソッド | パス | 内容 |
|---------|------|------|
| GET | `/api/approvals` | 承認待ち一覧 + 承認済み/却下済み件数 |
| POST | `/api/approvals/approve` | `{"id": "..."}` で承認 |
| POST | `/api/approvals/reject` | `{"id": "...", "reason": "..."}` で却下 |

### ディレクトリ構造

```
outputs/approvals/
├── pending/     承認待ちファイル（実行ごとに再生成）
├── approved/    承認済み履歴（累積保存）
└── rejected/    却下済み履歴（理由付き・累積保存）
```

## CEO 承認センター CLI（v1.5）

CLIからも引き続き操作できます。

### 承認対象

| 種類 | 絵文字 | 内容 |
|------|--------|------|
| メモリ見直し提案 | 🧠 | `memory_update_suggestions.md` から生成 |
| 実装キュー | ⚡ | `implementation_queue.md` の各 Issue |

### 操作コマンド

```bash
# 一覧を確認
python services/approval_service.py list

# 個別承認
python services/approval_service.py approve 2026-07-01_impl_issue_75

# すべて承認
python services/approval_service.py approve-all

# 却下（理由付き）
python services/approval_service.py reject 2026-07-01_memory_review "今回は変更不要"
```

### ワークフロー

```
python main.py
  ↓
outputs/approvals/pending/ に承認待ちファイル生成
  ↓
dashboard.md セクション7「承認センター」で件数を確認
  ↓
python services/approval_service.py list  で内容を確認
  ↓
approve / reject で判断
  ↓
outputs/approvals/approved/ に履歴として保存
```

- **AIは自動承認しません**。すべての判断は CEO が行います。
- `approved/` は実行をまたいで永続保存されます（`pending/` は毎回再生成）。
- GitHub 未設定でも動作します。

---

## メモリ見直し提案（v1.4）

`python main.py` 実行後、AIが `memory/` の3ファイルと最新の `report.md` を比較して見直し提案を生成します。

### 生成ファイル

`outputs/memory_update_suggestions.md`

```markdown
# メモリ見直し提案

> 分析日時: 2026-07-01 12:00
> ステータス: 要確認 / CEO未承認

## 維持する項目
（会議レポートでも引き続き有効と確認できた価値観）

## 見直し候補
（現在の記述・気になる点・修正案）

## 新しく追加した方がよい項目
（会議から浮かんだ新しい学び）

## CEOへのメモ
（全体所感と特に判断が必要な点）
```

### ワークフロー

```
python main.py
  ↓
memory_update_suggestions.md を確認
  ↓
同意する項目のみ memory/*.md を手動編集
  ↓（次回 main.py 実行時に反映）
```

**AIはメモリを自動書き換えしません。** すべての変更はCEOが承認・手動適用します。

### ダッシュボードでの表示

提案がある場合、`outputs/dashboard.md`（セクション7）および Webダッシュボード（`http://localhost:8000`）に通知バナーが表示されます。

---

## 会社メモリ（v1.3）

`python main.py` 起動時に `memory/` フォルダの3ファイルを自動読み込みし、5人のAI社員全員のタスクにコンテキストとして注入します。これにより、AI提案が会社の価値観・CEOの好み・過去の学びを反映したものになります。

### メモリファイル

| ファイル | 内容 | 編集者 |
|---------|------|--------|
| [`memory/company_memory.md`](memory/company_memory.md) | 会社の価値観・製品方針・禁止事項 | CEO |
| [`memory/ceo_preferences.md`](memory/ceo_preferences.md) | CEOの判断基準・提案スタイルの好み | CEO |
| [`memory/lessons_learned.md`](memory/lessons_learned.md) | うまくいったこと・失敗・今後のルール | CEO |

### カスタマイズ方法

MarkdownファイルをそのままテキストエディタやClaude Codeで編集するだけです。次回 `python main.py` 実行時に自動で反映されます。

```bash
# 例：学びを追記する
open memory/lessons_learned.md
```

Git管理されるため、価値観の変化をバージョン履歴で追跡できます。

### 動作ログ

```
[Memory] 会社メモリを読み込みました（127行）
```

---

## Claude Code 実装キュー（v2.0）

`python main.py` 実行後、GitHub Open Issues から高優先度を上位3件選び、Claude Code にそのまま貼れる推奨プロンプト付きの実装キューを自動生成します。

### 生成ファイル

`outputs/implementation_queue.md`

```markdown
# DAF OS 実装キュー

## Issue #43
**タイトル：** ユーザー同意取得フローの設計と実装
**URL：** https://github.com/owner/repo/issues/43
**優先度：** priority: high　**担当エージェント：** Sirius

### Claude Code への推奨プロンプト

\`\`\`
GitHub Issue #43 を実装してください。

タイトル：ユーザー同意取得フローの設計と実装
背景：...
要件：...
完了条件：...

実装完了後、変更したファイルの一覧と動作確認方法を教えてください。
\`\`\`
```

### 使い方

1. `python main.py` を実行
2. `outputs/implementation_queue.md` を開く
3. 実装したい Issue のプロンプトを Claude Code に貼り付ける

ダッシュボード（`outputs/dashboard.md`）の「6. 実装待ちタスク」にも Issue 一覧が表示されます。

### 未設定時の動作

`GITHUB_TOKEN` が未設定の場合、エラーなくスキップされます：

```
[実装キュー] GITHUB_TOKEN / REPO 未設定 → スキップ
```

---

## Mac 通知（v1.2）

`python main.py` または `./run_daf.sh` の実行完了後、Mac の通知センターに結果が表示されます。

**通知内容：**

```
DAF OS 実行完了
Issue 5件を生成しました。
次のアクション:
• Issue #001：ユーザーデータの暗号化確認
• Issue #002：プライバシーポリシーの最新化
📋 /path/to/outputs/dashboard.md
```

- 設定不要（Mac 標準の `osascript` を使用）
- launchd での自動実行時も `logs/daf_stdout.log` に通知結果が記録される
- Mac 以外の環境では自動スキップ（エラー停止しない）

> 通知が表示されない場合は、システム設定 → 通知 → ターミナル（または実行環境）の通知を「オン」にしてください。

---

## Notion 議事録自動保存（v1.1）

`python main.py` 実行後、会議結果を Notion データベースに1件のページとして自動保存します。

### 設定手順

#### 1. Notion Integration を作成（未作成の場合）

1. [Notion Developers](https://www.notion.so/my-integrations) にアクセス
2. 「New integration」→ 名前（例：`DAF OS`）を入力して作成
3. **Internal Integration Token** をコピー → `.env` の `NOTION_API_KEY` に設定

#### 2. 議事録を保存する Notion データベースを作成

Notion で新しいデータベース（テーブルビュー）を作成し、以下のプロパティを追加します：

| プロパティ名 | タイプ |
|-------------|--------|
| タイトル | タイトル（デフォルト） |
| 日付 | 日付 |
| GitHub Issue数 | 数値 |

#### 3. Integration をデータベースに接続

データベースページ右上「…」→「Connections」→ 作成した Integration を追加

#### 4. データベース ID を取得

データベースのURL：  
`https://notion.so/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...`

`?v=` の前の32文字が **Database ID** です。

#### 5. `.env` に追加

```
NOTION_API_KEY=secret_xxxxx
NOTION_LOG_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 保存される内容

| 項目 | 内容 |
|------|------|
| タイトル | `DAF OS 経営会議 YYYY-MM-DD` |
| 日付 | 実行日 |
| GitHub Issue数 | Open Issue 件数 |
| 今日の要約 | report.md の「CEOへの最終提言」 |
| 次にCEOがやること | 高優先度 Issue 最大5件 |
| GitHub 登録結果 | github_issue_results.md の内容 |
| report.md 全文 | 会議レポート本文（先頭10,000文字） |

### 未設定時の動作

`NOTION_API_KEY` または `NOTION_LOG_DATABASE_ID` が未設定の場合、エラーなくスキップされます：

```
[Notion Log] NOTION_LOG_DATABASE_ID 未設定 → スキップ
```

---

## 自動スケジュール（v0.9 / launchd）

Macのlaunchdを使って、DAF OSを自動実行できます。

### フェーズ1：5分後テスト実行

```bash
./scripts/install_scheduler.sh test
```

5分後に `run_daf.sh` が自動起動します。  
成功すると `outputs/dashboard.md` が更新され、`logs/` に実行ログが残ります。

**確認コマンド：**

```bash
launchctl list | grep com.daf
tail -f logs/daf_stdout.log
```

### フェーズ2：毎朝8:00 本番スケジュール

テスト成功後、以下で本番設定に切り替えます：

```bash
./scripts/install_scheduler.sh daily
```

`com.daf.test` は自動的にアンロードされ、`com.daf.daily`（毎朝8:00）に切り替わります。

### スケジューラ削除

```bash
./scripts/install_scheduler.sh uninstall
```

### ログファイル

| ファイル | 内容 |
|---------|------|
| `logs/daf_stdout.log` | 実行ログ（通常出力） |
| `logs/daf_stderr.log` | エラーログ |

### launchd設定ファイル

| ファイル | 用途 |
|---------|------|
| `launchd/com.daf.test.plist` | 5分間隔テスト用（`StartInterval: 300`） |
| `launchd/com.daf.daily.plist` | 毎朝8:00本番用（`StartCalendarInterval`） |

> **注意：** plist内のパスはインストール時に自動解決されます。直接 `~/Library/LaunchAgents/` に配置しないでください。

---

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
| `claude_tasks/001_*_prompt.md` | Claude Code実装指示書（Issue連動） | 自動生成 |
| `github_issue_results.md` | GitHub Issue登録結果（トークン設定時のみ） | 自動生成 |
| `dashboard.md` | CEOダッシュボード（状況・提案・次のアクション） | 自動生成 |

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

### Claude Task指示書の使い方

`outputs/claude_tasks/` に各Issueに対応した実装指示書が生成されます。

```
outputs/claude_tasks/
├── 001_privacy_policy_setup_prompt.md
├── 002_data_encryption_check_prompt.md
└── ...
```

**使い方：**

1. `outputs/claude_tasks/001_*_prompt.md` を開く
2. ファイルの内容を **Claude Codeにそのまま貼り付ける**
3. Claude Codeが指示に従ってファイルを作成・編集する
4. 完了後、報告形式に沿ってCEOへ報告される

各指示書には以下が含まれます：

| 項目 | 内容 |
|------|------|
| 目的 | Issueのタイトルと目標 |
| 背景 | なぜこのタスクが必要か |
| やってほしいこと | 実施済み／未完了を分けて列挙 |
| 編集してよいファイル | 担当者ごとに安全なパスを定義 |
| 触らないでほしいファイル | `.env`・`main.py`・`crews/`など |
| 完了条件 | Issueの完了条件をそのまま転記 |
| CEOへの報告形式 | 作業後の報告テンプレート |

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

## CEOダッシュボード（v0.7）

`python main.py` 実行後に `outputs/dashboard.md` が生成されます。

```markdown
# DAF OS ダッシュボード
> 最終更新: 2026-06-30 12:31

## 1. 今日の状況
| 成果物 | Issue | Claude Task | GitHub Open Issues |

## 2. 最新のAI提案
（report.md から CEOへの最終提言を自動抽出）

## 3. 次にCEOがやること
1. Issue #001：ユーザーデータの暗号化確認（担当: Atlas）
2. Issue #002：プライバシーポリシーの最新化（担当: Cosmos）
...

## 4. 進捗バー
公開準備チェックリスト ░░░░░░░░░░░░░░░░░░░░ 0%
AI社員稼働状況         ████████████████████ 100%

## 5. GitHub Open Issues（GITHUB_TOKEN設定時のみ）
```

**GitHub未設定でも動作します。** トークンがない場合は「5. GitHub連携」セクションに設定方法のヒントが表示されます。

---

## 実行前クリーンアップ（v0.6.1）

`python main.py` を実行するたびに、前回の生成物を自動削除してからクリーンな状態で生成します。

```
[Clean]
  ✓ outputs/issues を初期化（5件削除）
  ✓ outputs/claude_tasks を初期化（5件削除）
  ✓ outputs/ の成果物を初期化（5件削除）
```

**削除されるファイル：**

| 対象 | 内容 |
|------|------|
| `outputs/issues/*.md` | 前回生成のIssueファイル |
| `outputs/claude_tasks/*.md` | 前回生成のClaude Task指示書 |
| `outputs/appstore_description.md` など成果物4ファイル | 前回の会議結果 |
| `outputs/github_issue_results.md` | 前回のGitHub登録結果 |

**削除されないもの：**
- `outputs/issues/`・`outputs/claude_tasks/` フォルダ自体
- `docs/` 以下（プライバシーポリシーなど手動作成ファイル）
- `.env`・`memory/`・`agents/`・`crews/` などコード・設定ファイル

---

## GitHub Issues 自動登録

`python main.py` 実行時に `.env` に3つのキーが設定されていると、生成したIssueをGitHub Issuesへ自動登録します。

### 設定方法

**.env に以下を追加：**

```
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_REPO_OWNER=yourname
GITHUB_REPO_NAME=DAF_OS
```

**GITHUB_TOKEN の取得手順：**

1. GitHub → Settings → Developer settings → Personal access tokens → **Tokens (classic)**
2. **Generate new token** をクリック
3. スコープ `repo`（または `public_repo`）にチェック
4. 生成されたトークンを `.env` の `GITHUB_TOKEN` に貼り付け

### 動作仕様

| 状況 | 動作 |
|------|------|
| GITHUB_TOKEN 未設定 | スキップ（エラーなし）。Issueファイル生成までで完了 |
| 同タイトルのOpen Issueが存在する | 作成せずスキップ（重複防止） |
| 正常登録 | GitHub Issue が作成され、ラベルが付与される |

### 自動付与されるラベル

登録時に以下のラベルが自動作成・付与されます：

| ラベル | 内容 |
|--------|------|
| `priority: high` | 優先度：高 |
| `priority: medium` | 優先度：中 |
| `priority: low` | 優先度：低 |
| `agent: orion` 〜 `agent: cosmos` | 想定担当AI社員 |

### 登録結果

`outputs/github_issue_results.md` に作成・スキップ・エラーの一覧が保存されます。

---

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
