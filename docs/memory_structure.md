---
layout: page
title: Company Memory 構成
permalink: /memory_structure
---

# Company Memory 構成（Phase3）

DAF OSが持つ「会社としての記憶」の現状構成と運用ルールをまとめたものです。
ChatGPTの会話履歴だけに依存せず、DAF自体が会社の価値観・CEOの好み・過去の学びを保持することを目的としています。

---

## 1. 現在のmemory構成

```
DAF_OS/memory/
├── company_memory.md      会社の価値観（製品方針・経営方針・禁止事項）
├── ceo_preferences.md      CEOの意思決定スタイル・提案の好み
├── lessons_learned.md      過去の学び・教訓（うまくいったこと／失敗／今後のルール）
├── atlas.md                CTO 社員手帳（技術リスク・実装難易度の評価軸）
├── cosmos.md                CIO 社員手帳（データ管理・セキュリティ・KPI評価軸）
├── nova.md                  CMO 社員手帳（ブランド・集客・SNS戦略評価軸）
├── orion.md                  COO 社員手帳（優先順位付け・仕組み化評価軸）
└── sirius.md                CPO 社員手帳（UX・プロダクトロードマップ評価軸）
```

`company_memory.md` / `ceo_preferences.md` / `lessons_learned.md` の3ファイルが「会社全体の記憶」、
`atlas.md` 〜 `sirius.md` の5ファイルが「AI役員個別の判断基準（社員手帳）」という位置づけです。

---

## 2. 読み込み対象

`services/memory_service.py` が起動時に以下3ファイルを読み込み、AI社員のタスク description に注入します。

- `company_memory.md`
- `ceo_preferences.md`
- `lessons_learned.md`

存在しないファイルはスキップされ、読み込んだ内容は `load_company_memory()` が1つの文字列にまとめて返します。
（`atlas.md` 〜 `sirius.md` の社員手帳は各AI役員のエージェント定義側で個別に参照される想定で、`memory_service.py` の読み込み対象には含まれていません。）

---

## 3. 更新提案フロー

memoryは自動では更新されません。以下のレビューループを経てCEOが手動で反映します。

```
経営会議ログ
    ↓
services/memory_review_service.py が分析
    ↓
outputs/memory_update_suggestions.md に提案を出力
  （維持する項目 / 見直し候補 / 新しく追加した方がよい項目）
    ↓
CEOが承認・保留・却下を判断
    ↓
承認分のみ、CEOまたは指示を受けたAI社員が
memory/*.md を手動で編集して反映
```

---

## 4. 運用ルール

- `outputs/memory_update_suggestions.md` はあくまでAIによる提案であり、ファイル自体を書き換えても memory には反映されない。
- **CEOが確認・承認するまで `memory/*.md` は変更しない。**
- 承認候補は原則 `lessons_learned.md`（学び・教訓）へ追記する。すでに実装・検証済みの事実の記録はここに置く。
- `company_memory.md`（会社の価値観）は法的・経営方針レベルの強い記述になりやすいため、CEOの明示的な承認がない限り新規追記しない。
- プライバシーポリシーの文言変更やKPI数値の確定など、法的・数値的なコミットメントを伴う項目は、CEOが文言・数値を確定させるまで保留とする。
