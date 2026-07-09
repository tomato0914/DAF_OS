---
layout: page
title: DAF OS Session Handover
permalink: /session_handover
---

# DAF OS Session Handover

このファイルは、新しいClaude Codeセッションへ引き継ぐための資料です。
まず内容を理解し、現在のDAF OSの状態・思想・未完了タスクを把握してください。

Date: 2026-07-05

## 現在のフェーズ
Phase5 - Strategic Company（Goal → Initiative → Issue → KPI の接続完了）

---

# DAFの目的

Issueを消化することではない。
プロダクトを成長させること。

CEOが意思決定し、
AI社員が実務を行う。

最終的には、
「自分専用のAI会社のOS」を目指す。

---

# 現在のプロダクト

## mofulog
状況：
- 犬の記録アプリ
- App Store審査待ち

ターゲット：
- 初めて犬を飼った人

提供価値：
- 犬との思い出を残す
- 健康管理を簡単にする

---

# 完了済みQuest

- Quest40：マルチプロダクト対応
- Quest41：プロダクト別Issue管理
- Quest42：ワンクリック実装準備
- Quest43：CEO Daily Brief
- Quest44：AIアドバイス付き承認
- Quest46：Dashboard自動リフレッシュ
- Quest47：実装完了フロー
- Quest48：選択したIssueだけ実装
- Quest49：Dashboard CEO View改善
- Quest50：Company Memory基盤の整理・運用ルール化（本セッションで実施）

---

# Company Memory の現状（Quest50）

Company Memory基盤は**新規構築ではなく、既にv1.3〜v1.4で実装済み**。
Quest50は「作る」のではなく「整理して運用に乗せる」タスクとして実施した。

現在のmemory構成（詳細は [docs/memory_structure.md](./memory_structure.md)）：

```
DAF_OS/memory/
├── company_memory.md      会社の価値観
├── ceo_preferences.md      CEOの意思決定スタイル
├── lessons_learned.md      過去の学び・教訓
├── atlas.md / cosmos.md / nova.md / orion.md / sirius.md
                            AI役員（CTO/CIO/CMO/COO/CPO）の社員手帳
```

- 読み込み：`services/memory_service.py` が company_memory / ceo_preferences / lessons_learned の3ファイルをAI社員タスクへ注入
- 更新提案：`services/memory_review_service.py` が会議ログを分析し `outputs/memory_update_suggestions.md` に提案を出力
- 反映ルール：**CEOが承認するまで `memory/*.md` は変更しない**。承認分のみ手動で反映する

2026-07-04時点の更新提案の扱い：
- 承認 → 暗号化・セキュリティ対策への言及を `lessons_learned.md` に追記済み
- 保留（CEO判断待ち） → プライバシーポリシーの記述、ユーザーエンゲージメントKPIの設定

---

# 最近の学び

## OpenRouter
残高不足で自動化が停止した。

学び：
AI会社にも運転資金管理が必要。

今後：
- 残高監視機能を検討する。

---

# 現在の運用フロー

CEO Daily Brief
↓
承認待ち確認
↓
承認
↓
🚀 このIssueを実装
↓
Claude Code
↓
レビュー
↓
✅ 実装完了

---

# Issue状況

- **#90** プライバシーポリシーの公開準備 — 承認済み（2026-07-01）
- **#122** プライバシーポリシーの作成 — 承認済み（2026-07-02）
- **#123** セキュリティテストの実施 — 承認済み（2026-07-02）

上記3件は「未完了」ではなく`outputs/approvals/approved/`に承認済みとして記録されている（`outputs/approvals/completed/`への実装完了記録はまだない状態＝承認済み・実装待ち）。

> ⚠️ **過去の誤記についての注記（2026-07-05訂正）**
> 本ドキュメントは以前この3件を「未完了Issue」「gh CLI未導入のため未確認」と記載していたが、これは誤りだった。
> `gh` CLIに頼らず、`outputs/approvals/{pending,approved,rejected,completed}/` を確認すれば実際の承認・却下・実装状況はリポジトリ内で常に確認できる。
> **今後Issueのステータスをこのドキュメントに書く際は、必ず`outputs/approvals/`配下の実ファイルを確認してから記載すること。**（`gh` CLI導入の要否とは無関係に、まずローカルの承認記録を確認する）

---

# 次の目標

Company Memoryのレビューループ（AI提案 → CEO承認 → 反映）を定着させ、
毎回の会議後にCEOが `outputs/memory_update_suggestions.md` を確認する習慣を作る。

---

# CEOメモ

- Dashboardは毎日使いたくなることを重視する。
- シンプルさを優先する。
- コーディングはAI社員に任せ、
  CEOは意思決定に集中する。

---

# 最新状況（2026-07-05）

## 完了
- Quest55：Dedicated Meeting Crew
- Quest56：Executive Summary
- Quest57：CEO Decision History

## DAFの現在地
- AI経営会議は約8点レベルまで向上
- 完了済みIssueの再提案は大幅に減少
- 経営サマリーを用いた推論が可能になった
- CEOの過去の意思決定を参照できるようになった

## 次の目標
- 9点レベルを目指す
- Quest58：KPI Memory
- Quest59：Reflection Loop

## CEO所感
- 「かなり信用できる相談相手」まで到達。
- 次は「かなり信用して任せられる」レベルを目指す。

---

# 最新状況（2026-07-05）

## 完了
- Quest73：Failed Decision Memory
- Quest74：Confidence History
- Quest75：Meeting Quality Score
- Quest76：Strategic Goal Memory

## 現在地
- Phase5：Strategic Company 開始
- Strategic Goal Memory 実装済み
- strategic_goals.md 設定済み

## Strategic Goals
North Star Metric：
週1回以上、犬の記録を続けているアクティブ飼い主数

Annual Goals：
- mofulogをApp Storeで公開する
- 初期ユーザー100人を獲得する
- App Store評価4.5以上を目指す

Quarterly Goals：
- App Store審査を通過する
- 初回ユーザー10人に使ってもらう
- 初回記録完了率を確認する

Monthly Goals：
- App Store公開準備を完了する
- プライバシー・セキュリティ確認を完了する
- SNS告知文を準備する

Current Priorities：
- App Store公開
- 初回ユーザー獲得
- 初回体験の改善

## 次候補
- Quest77：Initiative Tracking
- Quest78：KPI Alert System
- Quest79：Autonomous Issue Generation
- Quest80：CEO Inbox

## DAFの状態
- AI経営会議：8.5〜9.0点
- 学習ループ完成
- 経営目標を参照可能
- 次フェーズは「Goal → Initiative → Issue → KPI」を繋ぐ戦略レイヤー

---

# 最新状況（2026-07-05・続き）

## 完了
- Quest77：Initiative Tracking

## Quest77の内容
Strategic Goals（Quest76）は「会社が目指す目標」を保持するだけで、
その目標を実現するために「今どの施策が動いていて、どのIssueにつながり、
どのKPIで成功を測るか」をAI経営会議が参照できなかった。Quest77でその間を埋める層を追加した。

- `memory/initiatives.md`：施策の一覧（CEOが直接編集する読み込み専用ファイル）。
  「## Initiative Template」のテンプレート見出しに続けて、各施策を
  「## 施策名」の見出し＋ Goal: / Description: / Related Issues: / Success KPI: の
  ラベル付き本文で記載する。Related IssuesはIssue番号ではなくタイトル文字列で記載する
  （find_related_initiatives()がタイトルの一致・部分一致で照合するため）。
- `services/initiative_service.py`：
  - `load_initiatives()` — initiatives.mdをパースし、Initiative Templateを除外した
    構造化データ（name / goal / description / related_issues / success_kpi）を返す
  - `generate_initiative_summary()` — AI会議への注入用Markdown要約を生成する
  - `find_related_initiatives(issue_title)` — Issueタイトルからrelated_issuesと
    一致・部分一致するInitiative名の一覧を返す
  strategic_goal_service.pyと同じ方針（LLM不使用・読み込み専用・例外を投げない）。
- `services/memory_service.py`：Strategic Goal Summaryの直後（KPI Summaryより前）に
  Initiative Summaryを注入するよう更新済み（前回セッションで配線済みのものを流用）。

現状 `memory/initiatives.md` には「App Store公開準備」施策のみ登録済み
（Goal：mofulogをApp Storeで公開する／Related Issues：プライバシーポリシーの公開準備・
プライバシーポリシーの作成・セキュリティテストの実施／Success KPI：App Store審査通過・初回ユーザー10人）。

## 次候補
- Quest78：KPI Alert System
- Quest79：Autonomous Issue Generation
- Quest80：CEO Inbox

## DAFの状態
- Goal → Initiative → Issue の繋がりをAI経営会議が参照可能になった
- 次は「KPIの異常検知」または「Issueの自動生成」で戦略レイヤーをさらに強化する予定

---

# 最新状況（2026-07-05）

## 完了
- Quest73：Failed Decision Memory
- Quest74：Confidence History
- Quest75：Meeting Quality Score
- Quest76：Strategic Goal Memory
- Quest77：Initiative Tracking

## 現在地
- Phase5：Strategic Company
- Goal → Initiative → Issue → KPI の接続が完了

## Strategic Goals
North Star Metric：
週1回以上、犬の記録を続けているアクティブ飼い主数

Annual Goals：
- mofulogをApp Storeで公開する
- 初期ユーザー100人を獲得する
- App Store評価4.5以上を目指す

Quarterly Goals：
- App Store審査を通過する
- 初回ユーザー10人に使ってもらう
- 初回記録完了率を確認する

Monthly Goals：
- App Store公開準備を完了する
- プライバシー・セキュリティ確認を完了する
- SNS告知文を準備する

Current Priorities：
- App Store公開
- 初回ユーザー獲得
- 初回体験の改善

## Initiatives
- App Store公開準備（実装済み）
- User Acquisition（追加候補）
- Onboarding Improvement（追加候補）

## 次候補
- Quest78：KPI Alert System
- Quest79：Autonomous Issue Generation
- Quest80：CEO Inbox

## DAFの状態
- AI経営会議：8.5〜9.0点
- Learning Company 完了
- Strategic Company 開始
- Goal → Initiative → Issue → KPI の戦略レイヤー完成
- 次は「目標から外れ始めたことを検知する仕組み（KPI Alert）」を実装する

---

# 最新状況（2026-07-05・Quest78）

## 完了
- Quest78：KPI Alert System

## Quest78の内容
KPI Memory（Quest58）はスナップショットを記録するだけで、悪化の検知・通知はしていなかった。
Quest78で「悪化を検知してCEOに知らせる」層を追加した。

- `services/kpi_alert_service.py`：
  - `detect_kpi_alerts()` — `memory/kpi/kpi_snapshots/`の直近2件を
    `kpi_memory_service.compare_snapshot()`で比較し、悪化KPIを検知する。
    下がると悪いKPI（Downloads / New Users / DAU / Retention / D1 Retention /
    Record Completion Rate / App Store Review Success / User Trust /
    Crash Free Rate / Review Rating）と、上がると悪いKPI（Crash Rate /
    Error Rate / Churn Rate）を区別して判定する。10%以上悪化でWARNING、
    20%以上悪化でCRITICAL。変化なし・改善はアラートなし。
    `initiative_service.load_initiatives()`のSuccess KPIと突き合わせ、
    一致すればそのInitiative名とGoal（Initiativeの`Goal:`欄）を関連情報として付与する。
  - `generate_kpi_alert_report()` — `outputs/kpi_alerts.md`にCRITICAL/WARNING別の
    レポートを生成する（`outputs/`はgitignore対象の生成物）。
  - `get_kpi_alert_summary()` — AI会議注入用の短いMarkdown要約を返す。
- `memory/initiatives.md`：KPI Alertとの紐付けを実演できるよう、
  「User Acquisition」「Onboarding Improvement」の2施策を追加登録した
  （Quest77完了時点では「追加候補」だったもの）。Goalの文言は
  `strategic_goals.md`の該当目標とそのまま一致させ、`related_goal`の
  引き当てが素通しで正しく機能するようにしている。
- `services/memory_service.py`：KPI Summaryの直後（Reflection Summaryより前）に
  KPI Alert Summaryを注入するよう更新。
- `main.py`：Meeting Quality更新の後（Notion議事録保存の前）にKPI Alert Report生成を追加。
  失敗してもDaily Brief/AI会議全体を止めないよう、警告ログのみで続行する設計。

現状 `memory/kpi/kpi_snapshots/` は0件のため、`outputs/kpi_alerts.md`・
KPI Alert Summaryとも「現在、重大なKPI悪化は検出されていません。」を返す
（テスト用の一時ディレクトリでD1 Retention 0.50→0.38・DAU 100→88のケースを
検証済み。CRITICAL/WARNING判定・Goal/Initiativeの紐付けとも仕様通りに動作した）。

## 次候補
- Quest79：Autonomous Issue Generation
- Quest80：CEO Inbox

## DAFの状態
- KPIの悪化をAI経営会議・CEOが早期に検知できるようになった
- Goal → Initiative → Issue → KPI → Alert の戦略レイヤーが一巡した
- 次はKPI/Initiative/Alertを踏まえてIssueを自動生成する仕組み、またはCEO Inbox（承認・アラート・提案の一元化）を検討

---

# 最新状況（2026-07-05・Quest79）

## 完了
- Quest79：Autonomous Issue Generation

## Quest79の内容
KPI Alert System（Quest78）は悪化を検知するだけで、「では何をすればいいか」を
AI社員が提案していなかった。Quest79でKPI Alertから改善Issue案を自動生成する層を追加した。

- `services/kpi_alert_service.py`：`get_active_kpi_alerts()`を追加
  （既存の`detect_kpi_alerts()`の公開エイリアス。Quest79側の呼び出し名に合わせた）
- `services/autonomous_issue_service.py`：新規。
  - `generate_autonomous_issues()` — `get_active_kpi_alerts()`でWARNING/CRITICALの
    KPI Alertを取得し、アラートごとに改善Issue案（タイトル・Why・Proposed Action・
    Acceptance Criteria）を生成し、`outputs/autonomous_issues.md`に
    `Status: pending_ceo_approval`のMarkdownとして保存する。生成したIssue案の
    リストも返す。KPI Alertが1件も無い場合はIssueを生成しない（空リストを返し、
    ファイルには「提案するIssueはありません」の旨のみ書き込む）。
  - v1方針としてLLMは使わず、KPIの性質（獲得／継続・オンボーディング／品質・信頼／
    安定性／解約）ごとの決定的なテンプレートで文章を組み立てる設計にした。
    外部API呼び出しに依存せず、ネットワーク障害やAPIコストの影響を受けないため。
  - GitHub Issue化や承認センター（`outputs/approvals/`）への投入は行わない。
    あくまでCEOが確認・判断するためのMarkdown案にとどめる。
- `main.py`：KPI Alert Report生成の直後（Notion議事録保存の前）に
  Autonomous Issue Suggestions生成を追加。失敗してもDaily Brief/AI会議全体を
  止めないよう、警告ログのみで続行する設計。

現状 `memory/kpi/kpi_snapshots/` は0件のため、`outputs/autonomous_issues.md`は
「現在、KPI Alertが無いため、提案するIssueはありません。」を出力する。
テスト用の一時ディレクトリでRecord Completion Rate 0.70→0.60・DAU 100→88の
2件のスナップショットを用意して検証し、指示書の出力例と一致する
「初回記録完了率の低下原因を分析する」Issue案（Related Goal/Initiativeの
紐付け含む）が正しく生成されることを確認した。

## 次候補
- Quest80：CEO Inbox
- Autonomous Issue Suggestionsの承認センター（`outputs/approvals/`）への統合

## DAFの状態
- KPI Alert → 改善Issue案 の自動生成までがつながった
- CEOは「KPIが悪化している」だけでなく「何をすべきか」の一次案も確認できるようになった
- 次はこの提案をCEOがワンクリックで承認・却下できる導線（CEO Inbox）を検討

---

# 最新状況（2026-07-05・Quest79追加修正）

## 完了
- Quest79追加修正：Autonomous Issue SummaryのMemory Context注入／重複生成防止

## 追加修正の内容
Quest79本体はほぼ完了していたが、以下2点を追加した。

1. **Memory Contextへの注入**：`services/memory_service.py`にKPI Alert Summaryの
   直後（Reflection Summaryより前）にAutonomous Issue Summaryを注入するよう追加。
   実体は`services/autonomous_issue_service.py`の`generate_autonomous_issue_summary()`
   （新規）で、`outputs/autonomous_issues.md`を読み込みそのまま要約として返す。
   ファイル未存在・空・パース失敗時は「現在、Autonomous Issue Suggestionsは
   ありません。」を返し、例外を投げない。
2. **重複生成防止**：`generate_autonomous_issues()`に、既存の
   `outputs/autonomous_issues.md`をパースし直す`_parse_existing_issues()`を追加。
   実行のたびに全アラートを新規生成するのではなく、既に同じ(Source KPI, Severity)の
   Issue案がファイル内に存在する場合はスキップし、新しく検知されたアラート分のみ
   追記するようにした（v1のため日付判定はしない）。戻り値は「既存分＋新規分」を
   合わせた現在有効なIssue案一覧。

経営サマリー領域内の注入順序（最終形）：
Executive Summary → Strategic Goal Summary → Initiative Summary → KPI Summary →
KPI Alert Summary → Autonomous Issue Summary → Reflection Summary →
Failed Decision Summary → Confidence History Summary → Meeting Quality Summary

## 動作確認結果
- `load_company_memory()`の出力に`## Autonomous Issue Summary`セクションが
  含まれることを確認（実データはアラート0件のため「ありません」文言）
- テスト用一時ディレクトリでRecord Completion Rate / DAUのWARNINGアラートを用意し、
  `generate_autonomous_issues()`を2回連続実行 → 1回目・2回目とも同じ2件のみで、
  重複エントリが増えないことを確認
- `services/autonomous_issue_service.py` / `services/memory_service.py`とも
  astによる構文チェックOK

## 次候補
- Quest80：CEO Inbox
- Autonomous Issue Suggestionsの承認センター（`outputs/approvals/`）への統合

## DAFの状態
- KPI Alert → 改善Issue案 → Memory Context注入まで一巡し、AI経営会議が
  「悪化しているKPI」「対応すべき理由」「関連Goal/Initiative」を毎回参照できる
- 重複生成防止により、同じ悪化KPIに対してIssue案が積み上がる心配がなくなった

---

# 最新状況（2026-07-05・Quest80）

## 完了
- Quest80：CEO Inbox

## Quest80の内容
KPI Alert・Autonomous Issue Suggestions・Memory Update Suggestions・承認待ちが
それぞれ別ファイルに散らばっており、CEOが毎回探しに行く必要があった。
Quest80でそれらを1つの`outputs/ceo_inbox.md`に集約した。

- `services/ceo_inbox_service.py`：新規。`generate_ceo_inbox()`が以下4つの
  情報源を読み込み、危険度が高い順（Priority 1〜4）にまとめる：
  1. KPI Alert Summary（`outputs/kpi_alerts.md`）
  2. Autonomous Issue Suggestions（`outputs/autonomous_issues.md`）
  3. Pending Approvals（`outputs/approvals/pending/*.md`のfrontmatterから
     title・advisor_priority・advisor_riskを抽出して一覧化）
  4. Memory Update Suggestions（`outputs/memory_update_suggestions.md`）
  末尾に固定の「CEO Recommended Actions」（4項目）を付与する。
  各セクションは個別にtry/exceptで守られており、1つの情報源の読み込みに
  失敗しても他のセクション・DAF OS全体には影響しない
  （失敗したセクションは「〜はありません」にフォールバックする）。
  v1方針としてLLMは使わず、単純な読み込み・整形のみの決定的な処理。
  GitHub Issue作成・承認処理はここでは行わない。
- `main.py`：Autonomous Issue Suggestions生成の直後（Notion議事録保存の前）に
  CEO Inbox生成を追加。失敗してもDaily Brief/AI会議全体を止めない設計。

現状、実データでは KPI Alert・Autonomous Issue Suggestionsは0件（「ありません」表示）、
Pending Approvalsは4件（Issue #161・#163・#165の実装承認＋会社メモリ見直し提案）、
Memory Update Suggestionsは1件（2026-07-05分析の見直し提案）が正しく表示されることを確認。
テスト用ディレクトリでCRITICAL KPI AlertとAutonomous Issueが実際にある場合の
レンダリングも別途検証済み。

## 次候補
- Autonomous Issue SuggestionsやMemory Update Suggestionsの承認センターへの統合
- CEO InboxのDashboard UIへの表示（現状はMarkdownファイルのみ）
- Pending Approvalsの表示順を危険度（advisor_risk）でソートする改善

## DAFの状態
- CEOが「まずCEO Inboxを見ればよい」状態になった
- KPI Alert・Autonomous Issue・Pending Approval・Memory Update Suggestionsの
  全体像を1ファイルで俯瞰できるようになった

---

# 最新状況（2026-07-05・Quest80追加修正）

## 完了
- Quest80追加修正：CEO Inbox SummaryのMemory Context注入

## 追加修正の内容
1. **`generate_ceo_inbox_summary()`を追加**（`services/ceo_inbox_service.py`）：
   `outputs/ceo_inbox.md`を読み込み、`## CEO Inbox Summary`として返す。
   ファイル未存在・空・読み込み失敗時は「現在、CEO Inboxは空です。」を返し、
   例外を投げない。
2. **`services/memory_service.py`にCEO Inbox Summaryを注入**：
   `_safe_ceo_inbox_summary()`を追加し、Memory Contextの最上部
   （Executive Summaryより前）に注入するようにした。CEO Inboxは
   KPI Alert・Autonomous Issue・Pending Approval・Memory Update Suggestionsを
   集約したものなので、AI経営会議も真っ先に参照できるようにするため。

Memory Context全体の注入順序（最終形）：
CEO Inbox Summary → Executive Summary → Strategic Goal Summary →
Initiative Summary → KPI Summary → KPI Alert Summary → Autonomous Issue Summary →
Reflection Summary → Failed Decision Summary → Confidence History Summary →
Meeting Quality Summary

## 動作確認結果
- `load_company_memory()`の出力の先頭（`=== DAF 会社メモリ ===`ヘッダーの直後、
  `【経営サマリー】`より前）に`## CEO Inbox Summary`が含まれることを確認
- `outputs/ceo_inbox.md`が存在しない一時ディレクトリで
  `generate_ceo_inbox_summary()`を実行 →「現在、CEO Inboxは空です。」を返し、
  例外を投げないことを確認
- `services/ceo_inbox_service.py` / `services/memory_service.py`とも
  astによる構文チェックOK

## 次候補
- Autonomous Issue SuggestionsやMemory Update Suggestionsの承認センターへの統合
- CEO InboxのDashboard UIへの表示（現状はMarkdownファイルのみ）

## DAFの状態
- AI経営会議もCEOと同じ「まず見るべき優先順位」でMemory Contextを参照できるようになった
- Company Memory全体の先頭がCEO Inbox Summaryになり、経営サマリーより先に
  「今すぐ対応すべきこと」が目に入る構造になった

---

# 最新状況（2026-07-05・Quest81）

## 完了
- Quest81：CEO Decision Center

## Quest81の内容
CEO Inbox（Quest80）はAI会社からの提案を1箇所に集約するところまでだった。
Quest81で、CEOがそれぞれの提案に approve / hold / reject を記録できる
決裁ログの仕組みを追加した。

- ディレクトリ：`outputs/decisions/{approved,on_hold,rejected}/`を作成
- `services/decision_center_service.py`：新規。
  - `record_decision(source_type, item_id, title, decision, reason=None)` —
    1件の判断をMarkdownファイルとして該当フォルダに記録する。
    `source_type`は`autonomous_issue` / `pending_approval` / `memory_update` /
    `kpi_alert` / `other`の5種類、`decision`は`approve` / `hold` / `reject`
    （`approved` / `on_hold` / `rejected`も可）。不正な値の場合は書き込まず
    `None`を返す（例外は投げない）。
  - `get_decision_history(source_type=None)` — 記録済みの判断をdecided_atの
    新しい順で一覧にして返す。ディレクトリ未存在・パース失敗でも空リストを返す。
  - `generate_decision_log_summary()` — AI会議・CEO Inboxへ注入できる短い
    Markdown要約（直近10件）を返す。記録が無ければ「現在、記録されたCEOの
    判断はありません。」を返す。
  - CLI：`python services/decision_center_service.py record <source_type>
    <item_id> <decision> [理由]` で記録、引数無しで直近の判断ログ要約を表示。

v1のスコープとして、GitHub Issue化・Memoryへの自動反映・既存の承認センター
（`outputs/approvals/`）との自動連携は行っていない（「AI会社が提案 → CEOが
判断 → 判断履歴を保存」までを完成させる、という指示範囲を厳守）。
main.py・memory_service.pyへの組み込みも今回はスコープ外として実施していない
（必要であれば別途指示を受けて追加する）。

## 動作確認結果
- テスト用一時ディレクトリで`autonomous_issue`（approve）・`kpi_alert`（hold）・
  `pending_approval`（reject）の3件を記録 → それぞれ正しいフォルダ
  （approved/on_hold/rejected）にファイルが作成され、`get_decision_history()`で
  新しい順に正しく取得できることを確認
- 不正な`source_type`・不正な`decision`を渡した場合 → 警告ログのみで`None`を
  返し、例外を投げないことを確認
- 実データ（記録0件）でCLI実行 →「現在、記録されたCEOの判断はありません。」を表示
- `services/decision_center_service.py`のastによる構文チェックOK

## 次候補
- main.py・memory_service.pyへのDecision Log Summary組み込み（次の追加修正候補）
- CEO Inbox上に既に判断済みの項目を表示・除外する連携
- Decision（特にapprove）を実際のGitHub Issue化・Memory反映・既存承認センターへ
  つなげる自動化（v2以降）

## DAFの状態
- CEOの意思決定（approve/hold/reject）が初めて構造化データとして残るようになった
- 「AI会社が提案 → CEOが判断 → 判断履歴を保存」の最小ループが完成した

---

# 最新状況（2026-07-05・Quest81追加修正）

## 完了
- Quest81追加修正：CEO Decision SummaryのMemory Context注入

## 追加修正の内容
1. **`generate_ceo_decision_summary()`を追加**（`services/decision_center_service.py`）：
   `generate_decision_log_summary()`の薄いラッパーとして追加。既存の
   `generate_decision_log_summary()`・CLIはそのまま残し、影響を与えない。
   Memory Context側の見出しは「## CEO Decision Summary」に統一する必要が
   あったため、ラッパー内で`generate_decision_log_summary()`が返す
   「## Decision Log Summary」見出しだけを置き換えている
   （最初は単純なパススルーを検討したが、それだと見出しが
   `## Decision Log Summary`のままでMemory Context側の要件を満たせなかったため、
   見出し差し替えに修正した）。
2. **`services/memory_service.py`にCEO Decision Summaryを注入**：
   `_safe_ceo_decision_summary()`を追加し、CEO Inbox Summaryの直後
   （Executive Summaryより前）に注入するようにした。

Memory Context全体の注入順序（最終形）：
CEO Inbox Summary → CEO Decision Summary → Executive Summary →
Strategic Goal Summary → Initiative Summary → KPI Summary → KPI Alert Summary →
Autonomous Issue Summary → Reflection Summary → Failed Decision Summary →
Confidence History Summary → Meeting Quality Summary

## 動作確認結果
- `load_company_memory()`の出力に`## CEO Decision Summary`が含まれ、
  `## CEO Inbox Summary`の直後・`【経営サマリー】`より前に位置することを確認
- 判断履歴0件（実データ・一時ディレクトリとも）でも例外を投げず
  「現在、記録されたCEOの判断はありません。」を返すことを確認
- `services/decision_center_service.py` / `services/memory_service.py` /
  `main.py`とも astによる構文チェックOK

## 次候補
- Quest82候補：CEO Inbox上に既に判断済みの項目を表示・除外する連携
- approve判断を実際のGitHub Issue化・Memory反映・既存承認センターへ
  つなげる自動化（v2以降）

## DAFの状態
- CEOの判断（approve/hold/reject）がAI経営会議のMemory Contextにも
  反映されるようになり、「CEOが何を承認・保留・却下したか」を踏まえた
  提案ができる土台が整った

---

# 最新状況（2026-07-05・Quest82）

## 完了
- Quest82：Weekly Board Meeting

## Quest82の内容
Strategic Goals → Initiatives → KPI Alerts → Autonomous Issues → CEO Inbox →
CEO Decisionまでの戦略レイヤーが完成した（Quest76〜81）が、CEOは毎日
これらを個別に確認する必要があった。Quest82でそれらを週次で1つの経営会議
資料にまとめ、「今週何が起きたか／最大のリスク／来週の優先事項」をCEOが
5分で把握できるようにした。

- `services/weekly_board_meeting_service.py`：新規。
  - `generate_weekly_board_meeting()` — Strategic Goals・Initiatives・
    KPI Alerts・Autonomous Issues・CEO Decisions・Meeting Quality・
    Reflection Report・CEO Inboxを集約し、`outputs/weekly_board_meeting.md`に
    以下8セクションで保存する：
    1. Executive Summary（今週のCritical/Warning件数・Autonomous Issue件数・
       CEO判断件数・会議品質スコアの箇条書き）
    2. Goal Review（strategic_goal_service）
    3. Initiative Review（initiative_service）
    4. KPI Review（kpi_alert_service.get_active_kpi_alerts()）
    5. CEO Decisions This Week（decision_center_service.get_decision_history()を
       直近7日でフィルタ）
    6. Biggest Risks（Critical KPI → Warning KPI → 未着手Initiative →
       Autonomous Issue → 承認待ちIssueの優先順位でルールベース抽出）
    7. Recommended Priorities Next Week（Critical KPI → Annual Goal直結の
       Initiative → CEOがApproveしたIssue → User Acquisition →
       Onboarding Improvementの優先順位でルールベース抽出）
    8. Board Recommendation（Critical/Warning有無に応じた定型コメント）
    各情報源は個別にtry/exceptで守られており、1つが欠けても他セクション・
    DAF OS全体には影響しない。
  - `generate_weekly_board_meeting_summary()` — 生成済みの
    `outputs/weekly_board_meeting.md`を読み込み、`## Weekly Board Meeting
    Summary`としてMemory Contextへ注入できる形で返す。未生成・空・失敗時は
    「現在、Weekly Board Meetingはまだ生成されていません。」を返す。
  - v1方針としてLLMは使わず、他サービスのサマリー関数・構造化データを
    組み合わせた決定的な処理にした（autonomous_issue_serviceと同じ理由で、
    外部API依存を避けて堅牢性を優先）。
  - 「Autonomous Issueの増加」「承認待ちIssueの増加」は、週次スナップショットを
    まだ持たないため、v1では「現時点の件数」で代替している（履歴比較はv2以降）。
- `services/autonomous_issue_service.py`：`load_autonomous_issues()`を追加
  （`outputs/autonomous_issues.md`を読み込み専用でパースする公開関数。
  Weekly Board Meetingが書き込みを伴わずに現在のIssue案一覧を参照するため）。
- `services/memory_service.py`：CEO Decision Summaryの直後（Executive Summaryより前）に
  Weekly Board Meeting Summaryを注入するよう更新。
- `main.py`：CEO Inbox生成の直後（Notion議事録保存の前）にWeekly Board Meeting
  生成を追加。失敗してもDaily Brief/AI会議全体を止めない設計。

Memory Context全体の注入順序（最終形）：
CEO Inbox Summary → CEO Decision Summary → Weekly Board Meeting Summary →
Executive Summary → Strategic Goal Summary → Initiative Summary → KPI Summary →
KPI Alert Summary → Autonomous Issue Summary → Reflection Summary →
Failed Decision Summary → Confidence History Summary → Meeting Quality Summary

## 動作確認結果
- 実データ実行 → `outputs/weekly_board_meeting.md`が正しく生成され、8セクション
  すべてが実データ（Strategic Goals・3件のInitiative・0件のKPI Alert・
  4件のPending Approvals等）を反映することを確認
- テスト用一時ディレクトリでCritical/Warning KPI Alert・未着手Initiative
  （関連Issue未登録）・今週のCEO承認判断を用意して検証 → Biggest Risksに
  Critical→Warning→未着手Initiativeの順で正しく表示され、Recommended
  Prioritiesも指定の優先順位（Critical KPI→Annual Goal直結Initiative→
  CEO承認Issue→User Acquisition/Onboarding Improvement）で正しく生成される
  ことを確認
- `load_company_memory()`の出力に`## Weekly Board Meeting Summary`が、
  `## CEO Decision Summary`の直後・`【経営サマリー】`より前に含まれることを確認
- `services/weekly_board_meeting_service.py` / `services/autonomous_issue_service.py` /
  `services/memory_service.py` / `main.py`ともastによる構文チェックOK

## 次候補
- Autonomous Issue・承認待ちIssueの「増加」を実際に週次スナップショットと
  比較する仕組み（v2）
- Weekly Board MeetingのExecutive Summary・Board RecommendationをLLMで
  自然文化する（v1は決定的なテンプレートのまま）
- Weekly Board MeetingとCEO Decision Centerを連携させ、レポート内の推奨
  優先事項に直接approve/hold/rejectできる導線

## DAFの状態
- 「AI役員が毎週、会社の状態をレビューする」仕組みが完成した
- CEOはCEO Inbox（日次）に加え、Weekly Board Meeting（週次）で会社全体を
  俯瞰できるようになった

---

# 最新状況（2026-07-05・Quest83）

## 完了
- Quest83：Scenario Planning

## Quest83の内容
Quest76〜82まではすべて「実際に起きたこと」を検知・記録・レビューする仕組み
だった。Quest83で初めて「まだ起きていないが起こり得るリスク」を先回りして
シミュレーションする仕組みを追加した。

- `services/scenario_planning_service.py`：新規。
  - 4つの主要シナリオを固定定義（`_SCENARIOS`）：
    1. DAUが30%減少した場合（Severity: High）
    2. App Store審査に落ちた場合（Severity: High）
    3. 初回ユーザーが10人未満の場合（Severity: Medium）
    4. Crash Rateが20%以上上昇した場合（Severity: Critical）
    各シナリオにImpact（影響）・Recommended Actions（発生時の対応）・
    Preparation（発生前に準備しておくこと）を持たせている。
  - `generate_scenario_planning()` — 上記4シナリオを`outputs/scenario_planning.md`に
    「## Scenario N」「### Impact」「### Recommended Actions」（番号付き）
    「### Severity」の形式で保存する。シナリオ定義はKPI実測値に依存しない
    固定データのため、常に生成できる。
  - `generate_scenario_planning_summary()` — 固定シナリオ定義から直接、
    「High Risk Scenarios」（severity=High）と「Recommended Preparation」
    （severity=Critical/High）をMarkdown要約として返す。ファイルの生成有無に
    依存しないため、`outputs/scenario_planning.md`が無くても例外を投げず
    常に同じ内容を返す。
  - v1方針としてLLMは使わず（利用可の指示だったが、堅牢性・再現性を優先し
    決定的なテンプレートを選択）、GitHub連携やIssue自動生成も行わない。
- `services/memory_service.py`：Weekly Board Meeting Summaryの直後
  （Executive Summaryより前）にScenario Planning Summaryを注入するよう更新。
- `main.py`：Weekly Board Meeting生成の直後（Notion議事録保存の前）に
  Scenario Planning生成を追加。失敗してもDaily Brief/AI会議全体を止めない設計。

Memory Context全体の注入順序（最終形）：
CEO Inbox Summary → CEO Decision Summary → Weekly Board Meeting Summary →
Scenario Planning Summary → Executive Summary → Strategic Goal Summary →
Initiative Summary → KPI Summary → KPI Alert Summary → Autonomous Issue Summary →
Reflection Summary → Failed Decision Summary → Confidence History Summary →
Meeting Quality Summary

## 動作確認結果
- `outputs/scenario_planning.md`が正しく生成され、4シナリオすべてが
  指定フォーマット（Impact/Recommended Actions/Severity）で出力されることを確認
- `generate_scenario_planning_summary()`の出力が指示書の出力例
  （High Risk Scenarios: DAUが30%減少・App Store審査落ち／Recommended
  Preparation: KPI分析手順の準備・App Store再申請手順の整備・
  緊急修正フローの確認）と完全に一致することを確認
- `outputs/scenario_planning.md`が存在しない状態で`generate_scenario_planning_summary()`
  を実行 → 例外を投げず、固定定義から同じ内容を返すことを確認（シナリオ定義が
  KPI実測値・ファイルの有無に依存しない設計のため）
- `load_company_memory()`の出力に`## Scenario Planning Summary`が、
  `## Weekly Board Meeting Summary`の直後・`【経営サマリー】`より前に
  含まれることを確認
- `services/scenario_planning_service.py` / `services/memory_service.py` /
  `main.py`ともastによる構文チェックOK

## 次候補
- シナリオの発生確率・現在のKPIとの近さを評価し、シナリオごとに
  「現在の警戒レベル」を動的に算出する（v1は固定シナリオ・固定Severityのみ）
- Scenario PlanningとKPI Alert／Autonomous Issueを連携させ、実際にシナリオの
  兆候が出た時点で自動的にアラートを出す
- シナリオ数を増やす・LLMで新規シナリオ候補を提案させる（v2以降）

## DAFの状態
- 「問題が起きてから考える」から「起きる前に準備しておく」への転換が
  経営会議資料として形になった
- Strategic Goals〜Weekly Board Meetingの「実績レビュー」系と、Scenario
  Planningの「将来リスク準備」系の両輪がAI経営会議のMemory Contextに揃った

---

# 最新状況（2026-07-05・Quest84）

## 完了
- Quest84：Capital Allocation Engine

## Quest84の内容
Strategic Goals〜Scenario Planning（Quest76〜83）で「状況把握・リスク事前準備」
までは揃ったが、「CEOの限られた時間を今週どこへ向けるべきか」は提案していな
かった。Quest84でKPI Alert・Initiative・Weekly Board Meeting・Scenario Planning
をルールベースで集約し、施策（Initiative）単位の推奨配分比率（合計100%）を
算出する仕組みを追加した。

- `services/capital_allocation_service.py`：新規。
  - 配分対象（v1固定）：App Store公開準備 / User Acquisition /
    Onboarding Improvement / その他
  - v1配分ルール（加点方式）：Critical KPI Alert +30 / Warning KPI Alert +15 /
    Annual Goal直結Initiative +20 / Autonomous Issue存在 +10 /
    Weekly Board MeetingでPriority指定 +10 / Scenario PlanningでHigh Risk +15。
    各シグナルの対象施策は、KPI Alert・Autonomous IssueのRelated Initiative、
    InitiativeのGoal（Annual Goalとの一致）、Weekly Board Meetingの
    「Recommended Priorities Next Week」本文にInitiative名が含まれるか、
    Scenario Planningの高リスクシナリオのタイトルにInitiative名（英字部分）
    またはSuccess KPIが含まれるかで判定する。
  - シグナルが1つも無い場合は、3つの実施策に均等な基礎スコアを与え
    フォールバックする（「その他」に100%割り振られる無意味な結果を避けるため）。
  - `generate_capital_allocation()` — 上記ルールを適用し、正規化して合計100%に
    なるよう丸め、`outputs/capital_allocation.md`に「## Recommended Allocation」
    （各施策の%・Reason）と「## CEO Recommendation」として保存する。
  - `generate_capital_allocation_summary()` — 現在のシグナルから都度再計算し、
    AI会議への短いMarkdown要約を返す（ファイルの生成有無に依存しない）。
  - v1方針としてLLMは使わず、決定的なルールベース処理にした。
- `services/scenario_planning_service.py`：`get_high_risk_scenarios()`を追加
  （severity="High"のシナリオ一覧を返す公開関数。capital_allocation_serviceが
  内部の`_SCENARIOS`定義に直接依存しないようにするため）。
- `services/memory_service.py`：Scenario Planning Summaryの直後
  （Executive Summaryより前）にCapital Allocation Summaryを注入するよう更新。
- `main.py`：Scenario Planning生成の直後（Notion議事録保存の前）に
  Capital Allocation生成を追加。失敗してもDaily Brief/AI会議全体を止めない設計。

途中、Scenario2「App Store審査に落ちた場合」というタイトルに対し、Initiative名
「App Store公開準備」全体が部分文字列として含まれず正しく紐付かないバグを検証中に
発見・修正した（Initiative名の英字部分＝"App Store"だけを抽出して照合するように
修正）。

Memory Context全体の注入順序（最終形）：
CEO Inbox Summary → CEO Decision Summary → Weekly Board Meeting Summary →
Scenario Planning Summary → Capital Allocation Summary → Executive Summary →
Strategic Goal Summary → Initiative Summary → KPI Summary → KPI Alert Summary →
Autonomous Issue Summary → Reflection Summary → Failed Decision Summary →
Confidence History Summary → Meeting Quality Summary

## 動作確認結果
- 実データ実行 → `outputs/capital_allocation.md`が生成され、
  App Store公開準備45% / User Acquisition45% / Onboarding Improvement10%
  （合計100%）とReason（Annual Goal直結・Weekly Board MeetingでPriority指定・
  High Risk Scenario等）が正しく表示されることを確認
- シグナルが1つも無い一時ディレクトリ（memory・outputsとも空）で実行 →
  例外を投げず、Scenario Planningの高リスクシナリオ分（固定データのため
  常に存在）が反映された結果になることを確認。さらにScenario Planningの
  シグナルも人為的に0にしたテストでは、3施策均等配分（34% / 33% / 33%、
  合計100%）にフォールバックすることを確認
- `load_company_memory()`の出力に`## Capital Allocation Summary`が、
  `## Scenario Planning Summary`の直後・`【経営サマリー】`より前に
  含まれることを確認
- `services/capital_allocation_service.py` / `services/scenario_planning_service.py` /
  `services/memory_service.py` / `main.py`ともastによる構文チェックOK

## 次候補
- 配分ルールの重み（+30/+15/+20/+10/+10/+15）をCEOの実際の判断結果と
  突き合わせて調整する仕組み（Confidence History的なフィードバックループ）
- 配分対象（現在は3つの実Initiative＋その他固定）を、登録されている
  Initiative全件から動的に生成する
- Capital Allocationの推奨をCEO Decision Centerと連携させ、配分方針自体に
  approve/hold/rejectを記録できるようにする

## DAFの状態
- 「状況把握 → リスク事前準備 → 資源配分の提案」までの経営支援レイヤーが
  一通り完成した
- CEOは毎週、CEO Inbox・Weekly Board Meeting・Scenario Planning・
  Capital Allocationを順に見ることで、何が起きたか・何に備えるべきか・
  どこに時間を使うべきかを把握できる

---

# 最新状況（2026-07-05・Quest85）

## 完了
- Quest85：Self Improvement Loop

## Quest85の内容
Strategic Goals〜Capital Allocation（Quest76〜84）は、すべて「プロダクト
（mofulog）をどう成長させるか」に関する提案だった。Quest85で初めて
「DAF OS自身のどこが弱く、次に何を改善すべきか」を提案する自己改善ループを
追加した（AI会社→自己分析→次のQuest提案）。

- `services/self_improvement_service.py`：新規。
  - v1改善ルール（該当すればすべて提案、優先度順にソート）：
    1. Critical KPI Alertが3件以上 → `Notification Center`（Priority: High）
    2. Pending Approvalsが5件以上 → `Decision Dashboard`（Priority: Medium）
    3. Autonomous Issueが10件以上 → `Issue Prioritization Engine`（Priority: Medium）
    4. Meeting Qualityが70点未満 → `Meeting Improvement Engine`（Priority: High）
    5. Capital Allocationが毎週大きく変化 → `Resource Planning Engine`（Priority: Low）
    6. 該当なし → 「現在、大きな改善テーマはありません。」
  - Rule 1は本来「3回以上"続いた"」（時系列の継続）を意図しているが、v1では
    アラート発生履歴をまだ持たないため「現時点でアクティブなCritical KPI
    Alertが3件以上」で代替した（他のQuestで採用している「件数で代替する」
    v1簡略化と同じ方針）。
  - Rule 5はCapital Allocationの週次履歴をまだ持たないため、v1では常に
    非該当として扱う（虚偽の代替指標を作るより「まだ判定できない」ことを
    明示する方が誠実と判断し、常にFalseを返すスタブ関数にした）。
  - `generate_self_improvement_suggestions()` — 上記ルールを適用し、
    `outputs/self_improvement_suggestions.md`に「## Suggested Quest」として
    各提案（Reason / Expected Impact / Priority）を保存する。提案が0件でも
    正常にファイルを生成する。
  - `generate_self_improvement_summary()` — 現在のシグナルから都度再計算し、
    AI会議への短いMarkdown要約（Suggested Quests・Recommendation）を返す。
  - v1方針としてLLMは使わず、決定的なルールベース処理にした。
- `services/memory_service.py`：Capital Allocation Summaryの直後
  （Executive Summaryより前）にSelf Improvement Summaryを注入するよう更新。
- `main.py`：Capital Allocation生成の直後（Notion議事録保存の前）に
  Self Improvement生成を追加。失敗してもDaily Brief/AI会議全体を止めない設計。

検証中、`get_active_kpi_alerts()`にkpi_dirを明示的に渡していなかったため
テスト用一時ディレクトリのスナップショットが読み込まれず、Rule 1（Critical
KPI Alert）が正しく発火しない不具合を発見・修正した（generate_self_improvement_
suggestions() / generate_self_improvement_summary()にkpi_dir引数を追加し、
内部で正しく橋渡しするようにした）。

Memory Context全体の注入順序（最終形）：
CEO Inbox Summary → CEO Decision Summary → Weekly Board Meeting Summary →
Scenario Planning Summary → Capital Allocation Summary →
Self Improvement Summary → Executive Summary → Strategic Goal Summary →
Initiative Summary → KPI Summary → KPI Alert Summary → Autonomous Issue Summary →
Reflection Summary → Failed Decision Summary → Confidence History Summary →
Meeting Quality Summary

## 動作確認結果
- 実データ実行（Critical Alert 0件・承認待ち4件・Autonomous Issue 0件・
  会議品質80点）→ 提案0件で正常終了し、「現在、大きな改善テーマはありません。」
  を正しく出力
- テスト用一時ディレクトリで4条件（Critical KPI Alert 3件・承認待ち6件・
  Autonomous Issue 10件・会議品質0点）をすべて満たす状況を再現 →
  Notification Center（High）・Meeting Improvement Engine（High）・
  Decision Dashboard（Medium）・Issue Prioritization Engine（Medium）が
  優先度順に正しく提案され、指示書の出力例のフォーマット
  （Reason/Expected Impact/Priority）と一致することを確認
- `load_company_memory()`の出力に`## Self Improvement Summary`が、
  `## Capital Allocation Summary`の直後・`【経営サマリー】`より前に
  含まれることを確認
- `services/self_improvement_service.py` / `services/memory_service.py` /
  `main.py`ともastによる構文チェックOK

## 次候補
- Critical KPI Alertの発生履歴を永続化し、Rule 1を本来の「3回以上"続いた"」
  （時系列の継続）判定に強化する
- Capital Allocationの週次履歴を永続化し、Rule 5（配分の大きな変化）を
  実際に判定できるようにする
- 提案されたQuestをCEO Decision Centerと連携させ、そのままapprove/hold/
  rejectを記録できるようにする

## DAFの状態
- 「AI会社 → 自己分析 → 次のQuest提案」という自己改善ループの最初の一歩が
  完成した
- Strategic Goals〜Capital Allocationの「プロダクト成長」系レイヤーに加え、
  Self Improvementの「DAF OS自身の成長」系レイヤーが加わった

---

# 最新状況（2026-07-05・Quest87）

## 完了
- Quest87：Issue Auto Pipeline

（Quest86は本セッションでは実施していない。Quest85の直後にQuest87の指示を受けたため、
指示書の番号どおりQuest87として実装した。）

## Quest87の内容
CEO Decision Center（Quest81）はCEOのapprove/hold/rejectを記録するだけで、
「承認された提案が実際に実装待ちのIssueになる」ところまでは繋がっていなかった。
Quest87で「提案 → 承認 → Issue化」の自動化を追加した（GitHub Issue化・gh CLI
連携はまだ行わない。次のQuest88で「Issue → Claude Code実装」へ繋げる前提）。

- `services/decision_center_service.py`：`_SOURCE_TYPES`に`self_improvement`を
  追加した（Quest85で導入されたSelf Improvement Suggestionsに対してもCEOが
  approve/hold/rejectを記録できるようにするため。既存の4種類は変更なし）。
- `services/self_improvement_service.py`：`get_current_suggestions()`を追加
  （現在のSelf Improvement提案を構造化データで返す公開関数。
  issue_pipeline_serviceがPriorityを引き当てるために使う）。
- `services/issue_pipeline_service.py`：新規。
  - `generate_issue_pipeline()` — `decision_center_service.get_decision_history()`
    から`decision=="approved"`かつ`source_type`が`autonomous_issue` /
    `self_improvement` / `memory_update`のいずれかの提案を対象に、
    `outputs/issue_pipeline/generated_issues.md`へ実装待ち
    （`Status: pending_implementation`）のIssueとして保存する。
    - `autonomous_issue`：`load_autonomous_issues()`で元のIssue案を引き当て、
      severity（critical/warning）からPriority（High/Medium）とAcceptance
      Criteriaを引き継ぐ
    - `self_improvement`：`get_current_suggestions()`で現在のPriorityを引き当てる
      （後述の制約あり）
    - `memory_update`：引き当てる情報源が無いためPriority: Medium固定
  - 重複生成防止：既存の`generated_issues.md`を`_parse_existing_generated_issues()`
    で読み直し、同じTitleのIssueは再生成しない（v1はTitle完全一致で十分と判断）
  - `generate_issue_pipeline_summary()` — 生成済みファイルを読み込み、
    「Pending Implementation」一覧と「Total」件数をMarkdown要約として返す
- `services/memory_service.py`：Self Improvement Summaryの直後
  （Executive Summaryより前）にIssue Pipeline Summaryを注入するよう更新。
- `main.py`：Self Improvement生成の直後（Notion議事録保存の前）に
  Issue Pipeline生成を追加。失敗してもDaily Brief/AI会議全体を止めない設計。

Memory Context全体の注入順序（最終形）：
CEO Inbox Summary → CEO Decision Summary → Weekly Board Meeting Summary →
Scenario Planning Summary → Capital Allocation Summary →
Self Improvement Summary → Issue Pipeline Summary → Executive Summary →
Strategic Goal Summary → Initiative Summary → KPI Summary → KPI Alert Summary →
Autonomous Issue Summary → Reflection Summary → Failed Decision Summary →
Confidence History Summary → Meeting Quality Summary

## 動作確認結果
- 実データ実行（approve済みCEO Decisionが0件）→ 正常終了し、
  「現在、承認された提案はありません。」を正しく出力
- テスト用一時ディレクトリで`autonomous_issue`（Critical→High継承）・
  `self_improvement`・`memory_update`の3件をapprove、`pending_approval`を
  1件approve → `pending_approval`はIssue化対象から正しく除外され、
  残り3件が正しくIssue化されることを確認
- 同じ環境で`generate_issue_pipeline()`を2回連続実行 → Issue数が3件のまま
  変化せず、重複生成されないことを確認
- `load_company_memory()`の出力に`## Issue Pipeline Summary`が、
  `## Self Improvement Summary`の直後・`【経営サマリー】`より前に
  含まれることを確認
- `services/issue_pipeline_service.py` / `services/decision_center_service.py` /
  `services/self_improvement_service.py` / `services/memory_service.py` /
  `main.py`ともastによる構文チェックOK

## 次候補
- Quest88：Issue → Claude Code実装への連携（`outputs/issue_pipeline/
  generated_issues.md`を実装キューへ接続する）
- `self_improvement`提案のPriorityは「承認時点」ではなく「Issue化実行時点」の
  最新シグナルで再評価するため、承認後に状況が変わるとPriorityがズレる
  可能性がある（履歴ベースのPriority保存は今後の課題）
- `memory_update`のIssue化はタイトルのみでPriority・Acceptance Criteriaを
  引き当てる情報源が無く、常にMedium固定（memory_update_suggestions.mdの
  構造化が今後の課題）

## DAFの状態
- 「提案 → 承認 → Issue化」までの自動化が完成し、CEOのapproveが
  実装待ちIssueとして確実に残るようになった
- 次はこのIssue一覧をClaude Codeでの実装フローへ接続する段階

---

# 最新状況（2026-07-05・Dashboard最新化）

## 完了
- Dashboard最新化：Quest80〜87の生成物をWebダッシュボードに表示

## 内容
Quest80〜87（CEO Inbox・CEO Decision Center・Weekly Board Meeting・
Scenario Planning・Capital Allocation・Self Improvement・Issue Auto Pipeline）は
`services/memory_service.py`（AI会議のMemory Context）には注入済みだったが、
`dashboard_web/`（CEOが見るWebダッシュボード）・`services/dashboard_generator.py`
（`outputs/dashboard.md`生成）のどちらにも一切配線されておらず、CEOが目視で
確認する手段が無かった。今回、既存Dashboardの構造・API・ボタンを変更せず、
新しいカードを追加する形で最新化した。

- `dashboard_web/app.py`：`_read_raw_or_none()`ヘルパーを追加し、
  `parse_dashboard()`の戻り値に`ceo_inbox` / `capital_allocation` /
  `issue_pipeline` / `weekly_board_meeting` / `self_improvement`の5キーを追加
  （それぞれ`outputs/ceo_inbox.md` / `outputs/capital_allocation.md` /
  `outputs/issue_pipeline/generated_issues.md` / `outputs/weekly_board_meeting.md` /
  `outputs/self_improvement_suggestions.md`を読み込み専用でそのまま返す。
  ファイル未存在・読み込み失敗時はNoneを返し、例外を投げない）。
- `dashboard_web/templates/index.html`：`renderRawMarkdownCard()`（汎用の
  Markdown本文そのまま表示カード）と、それを使う5つのラッパー関数
  （renderCeoInboxCard / renderCapitalAllocationCard / renderIssuePipelineCard /
  renderWeeklyBoardMeetingCard / renderSelfImprovementCard）を追加。
  `.ac-pre`（既存の折り返し・スクロール対応スタイル）をそのまま再利用し、
  新規CSSは追加していない。`renderDashboard()`の`html`テンプレートの
  **最上部**（既存の「DAFに相談」カードより前）に、指定順序
  （CEO Inbox → Capital Allocation → Issue Pipeline → Weekly Board Meeting →
  Self Improvement Suggestions）で挿入した。既存カード（CEOサマリー・
  CEO Daily Brief・Reflection・実装完了待ち・PR作成準備・承認センターなど）は
  一切変更していない。
- `.claude/launch.json`：新規作成。`dashboard_web/app.py`をプレビュー起動
  できるようにするための設定（`.venv/bin/python dashboard_web/app.py`、
  ポート8000）。

## 動作確認結果
- Preview機能でダッシュボードを起動し、デスクトップ幅で確認 → CEO Inbox・
  Capital Allocation・Issue Pipelineの3カードが指定順序・アクセントカラー付きで
  正しく表示され、内容（Priority別KPI Alert、45%/45%/10%配分、
  「現在、承認された提案はありません。」等）が実際のファイル内容と一致することを確認
- ページ全体のテキストにWeekly Board Meeting・Self Improvement Suggestions・
  既存の「DAFに相談」「CEOサマリー」も含まれていることを確認（新カード追加後も
  既存セクションが失われていないことを確認）
- 承認センタータブに切り替えて確認 → 承認待ち/承認済み/却下済み/実装完了の
  件数表示・承認/却下ボタン・AIアドバイスブロックとも従来通り正常動作
  （新カード追加による既存機能への影響なし）
- ブラウザコンソールにエラーなし
- `dashboard_web/app.py`のastによる構文チェックOK

## 残課題
- v1のためMarkdown本文をそのまま`<pre>`表示しており、Issue Pipelineの
  Title/Source/Priority/Statusをテーブル形式で構造化表示するなどのリッチ化は
  今後の課題
- Capital Allocationの配分比率をグラフ・プログレスバー化するなどの視覚化は未実装
- 5枚とも読み取り専用表示のみで、Dashboard上からの操作（例：Self Improvement
  提案からそのままCEO Decision Centerへapprove記録するなど）は未実装

## DAFの状態
- CEOはWebダッシュボードを開くだけで、CEO Inbox・Capital Allocation・
  Issue Pipeline・Weekly Board Meeting・Self Improvement Suggestionsの
  最新状態を確認できるようになった

---

# 最新状況（2026-07-05・Quest88）

## 完了
- Quest88：Execution Planner

## Quest88の内容
Issue Auto Pipeline（Quest87）は「CEOがapproveした提案 → 実装待ちIssue」までを
自動化したが、「そのIssueを実際にどう作るか（制作工程）」はまだ計画されていな
かった。Quest88で実装待ちIssueをAsset Type（成果物の種類）ごとに分類し、
Deliverables（成果物一覧）とTasks（実行可能な制作タスク）に分解する
Execution Plannerを追加した。まだ成果物生成（Asset Generation）は行わない
（「AIが制作計画を立てられること」までがこのQuestのゴール。次のQuest89で
「Execution Plan → Digital Asset生成」へ接続する）。

- ディレクトリ：`outputs/execution_plans/`を作成
- `services/issue_pipeline_service.py`：`load_generated_issues()`を追加
  （現在の実装待いIssue一覧を読み込み専用で構造化データとして返す公開関数。
  execution_planner_serviceが書き込みを伴わずに参照するため）。
- `services/execution_planner_service.py`：新規。
  - Asset Type（v1固定7種類）：`line_sticker` / `youtube_short` / `blog` /
    `ebook` / `ios_app` / `saas` / `generic`（フォールバック）
  - Asset Type判定：Issueのタイトル・説明文に含まれるキーワード
    （「LINE」「スタンプ」→line_sticker、「YouTube」「Shorts」「動画」→
    youtube_short 等）で簡易判定する。v1では判定材料をタイトル・説明文に
    絞っている（Goal・Initiativeの文言まで含めた判定はv2以降の課題）。
  - `generate_execution_plans()` — `load_generated_issues()`で
    `Status: pending_implementation`のIssueを取得し、Asset Typeごとに分類。
    Asset Typeごとの固定テンプレート（Deliverables・Tasks）を使って
    `outputs/execution_plans/<asset_type>_project.md`に保存する。
    実行タスクType（v1固定9種類）：`planning` / `text_generation` /
    `image_generation` / `audio_generation` / `video_generation` /
    `code_generation` / `python_processing` / `file_generation` / `review`
  - 重複生成防止：同じProject（Issueタイトル）のExecution Planは再生成しない
    （既存ファイルを再読み込みし、Project名が既にあればスキップ。Issue Auto
    Pipelineと同じ方針）。同じAsset Typeに複数のIssueが該当する場合は
    同一ファイル内に複数の`# Execution Plan`ブロックとして追記する。
  - `generate_execution_plan_summary()` — `outputs/execution_plans/`配下を
    集計し、「Active Plans」（ファイル名一覧）・「Asset Types」・
    「Recommendation」（最初のAsset Typeを完成させることを推奨する定型文）を
    Markdown要約として返す。
- `services/memory_service.py`：Issue Pipeline Summaryの直後
  （Executive Summaryより前）にExecution Plan Summaryを注入するよう更新。
- `main.py`：Issue Pipeline生成の直後（Notion議事録保存の前）に
  Execution Planner生成を追加。失敗してもDaily Brief/AI会議全体を止めない設計。

Memory Context全体の注入順序（最終形）：
CEO Inbox Summary → CEO Decision Summary → Weekly Board Meeting Summary →
Scenario Planning Summary → Capital Allocation Summary →
Self Improvement Summary → Issue Pipeline Summary → Execution Plan Summary →
Executive Summary → Strategic Goal Summary → Initiative Summary → KPI Summary →
KPI Alert Summary → Autonomous Issue Summary → Reflection Summary →
Failed Decision Summary → Confidence History Summary → Meeting Quality Summary

## 動作確認結果
- 実データ実行（実装待ちIssue0件）→ `outputs/execution_plans/`ディレクトリは
  作成されるがファイルは生成されず、正常終了（空リストを返す）。Summaryも
  「現在、有効なExecution Planはありません。」を正しく出力
- テスト用一時ディレクトリで7種類のAsset Typeそれぞれに対応するIssueタイトル
  （LINEスタンプ・YouTube Shorts・ブログ・電子書籍・iOSアプリ・SaaS・
  分類不能なタスク）を用意 → 7件すべて正しいAsset Typeに分類され、
  `line_sticker_project.md`はstamp_01.png〜stamp_40.png・main.png・tab.png・
  metadata.md・stickers.zipの44個のDeliverablesと5つのTasks
  （指示書の出力例と完全一致）が生成されることを確認
- 同一データで`generate_execution_plans()`を2回連続実行 → Plan数が7件のまま
  変化せず、重複生成されないことを確認
- 同じAsset Type（line_sticker）に2件目のIssueを追加して再実行 → 既存の
  `line_sticker_project.md`に2つ目の`# Execution Plan`ブロックが正しく
  追記され、Plan数が8件に増えることを確認
- `load_company_memory()`の出力に`## Execution Plan Summary`が、
  `## Issue Pipeline Summary`の直後・`【経営サマリー】`より前に
  含まれることを確認
- `services/execution_planner_service.py` / `services/issue_pipeline_service.py` /
  `services/memory_service.py` / `main.py`ともastによる構文チェックOK

## 次候補
- Quest89：Execution Plan → Digital Asset生成への接続（各Taskの
  `text_generation` / `image_generation`等をLLM・画像生成APIで実行する）
- Asset Type判定にGoal・Initiativeの文言も加える（v1はタイトル・説明文のみ）
- Execution PlanのTaskステータス（pending → in_progress → done）を
  更新できる仕組み（現状は生成時に全件pending固定）

## DAFの状態
- 「実装待ちIssue → 制作計画（Deliverables・Tasks）」までの自動化が完成した
- Strategic Goals → Initiatives → KPI Alerts → Autonomous Issues →
  CEO Decision → Weekly Board Meeting → Scenario Planning →
  Capital Allocation → Self Improvement → Issue Pipeline → Execution Planner
  という一連の経営〜実行支援レイヤーが一巡した
- 次はExecution PlanのTaskを実際にAI（LLM・画像/動画/音声生成）で
  実行し、Digital Assetを完成させる段階

---

# 最新状況（2026-07-05・Quest89）

## 完了
- Quest89：Asset Type Registry

## Quest89の内容
Execution Planner（Quest88）はAsset Typeごとの成果物・タスクをPythonコード内に
ハードコードしていた。Quest89でその知識をコードから切り離し、
`memory/asset_registry/*.json`という読み込み専用の定義書としてDAF OSに
記憶させた。Quest90（Asset Generator）はこのRegistryを参照して実際に
デジタル資産を生成する予定で、今回はその基盤（定義書＋読み込み関数）まで。

- `memory/asset_registry/`：新規ディレクトリ。7つのJSON
  （`line_sticker.json` / `youtube_short.json` / `blog.json` / `ebook.json` /
  `ios_app.json` / `saas.json` / `generic.json`）を作成。各ファイルは共通
  フォーマット（`asset_type` / `display_name` / `deliverables` / `tasks` /
  `review_items` / `publish_package`）。deliverables・tasksはQuest88の
  既存テンプレートと整合する内容にし、review_items・publish_packageは
  Asset Typeの特性に合わせて新規に定義した。
- `services/asset_registry_service.py`：新規。
  - `load_asset_registry(asset_type)` — 該当するJSONを読み込んで返す。
    存在しない場合は`generic.json`にフォールバックする
  - `list_asset_types()` — 登録済みAsset Type名の一覧を返す
    （`line_sticker`→`youtube_short`→`blog`→`ebook`→`ios_app`→`saas`→
    `generic`の固定順。将来追加されたファイルはアルファベット順で末尾に追加）
  - `get_asset_template(asset_type)` — deliverables/tasks/review_items/
    publish_packageだけを抜き出したdictを返す
  - `generate_asset_registry_summary()` — 「Supported Asset Types」
    （genericを除く6種類）と「Recommendation」（最初のAsset Typeから
    実装することを推奨する定型文）をMarkdown要約として返す
  - すべて読み込み専用。ファイル未存在・JSON壊れ・ディレクトリ未存在の
    いずれでも例外を投げず、空のdict/リストにフォールバックする
- `services/execution_planner_service.py`：既存の
  `_asset_deliverables_and_tasks()`を`_fallback_deliverables_and_tasks()`に
  改名した上で、新しい`_asset_deliverables_and_tasks()`ラッパーを追加。
  `asset_registry_service.get_asset_template()`が取得できればRegistryの
  deliverables・tasksを優先し、取得できない・importに失敗した場合は
  既存ロジック（フォールバック）をそのまま使う（「Registryが存在→Registry
  優先→なければ既存ロジック」の指示通り）。RegistryのTasksはType（planning等）
  を持たないため、既存ロジックのTask数と一致する場合のみタイトルだけを
  Registryの文言に差し替え、Type・Statusは既存ロジックの値をそのまま使う
  （件数が一致しない場合は差し替えず、既存ロジックをそのまま使う）。
- `services/memory_service.py`：Execution Plan Summaryの直後
  （Executive Summaryより前）にAsset Registry Summaryを注入するよう更新。
- `main.py`：変更なし（Asset Registryは静的定義のため生成処理は不要。
  Memory Contextへの注入のみで完結する）。

Memory Context全体の注入順序（最終形）：
CEO Inbox Summary → CEO Decision Summary → Weekly Board Meeting Summary →
Scenario Planning Summary → Capital Allocation Summary →
Self Improvement Summary → Issue Pipeline Summary → Execution Plan Summary →
Asset Registry Summary → Executive Summary → Strategic Goal Summary →
Initiative Summary → KPI Summary → KPI Alert Summary → Autonomous Issue Summary →
Reflection Summary → Failed Decision Summary → Confidence History Summary →
Meeting Quality Summary

## 動作確認結果
- `list_asset_types()` → `['line_sticker', 'youtube_short', 'blog', 'ebook',
  'ios_app', 'saas', 'generic']`を正しく返すことを確認
- `load_asset_registry('ios_app')` → 対応するJSONの内容を正しく返すことを確認
- `load_asset_registry('totally_unknown_type')` →
  `generic`（`asset_type: "generic"`）へ正しくフォールバックすることを確認
- `generate_asset_registry_summary()` → 指示書の出力例
  （Supported Asset Types 6種類・「Asset Generatorはline_stickerから
  実装してください。」）と完全に一致することを確認
- Execution Plannerとの連携：line_stickerのIssueで`generate_execution_plans()`を
  実行 → Task 3のタイトルが既存ロジックの「Generate 40 Sticker Images」から
  Registryの「Generate Sticker Images」に正しく差し替わり、Type・Status・
  Deliverablesは従来通り生成されることを確認（既存ロジックを壊していない）
- `load_company_memory()`の出力に`## Asset Registry Summary`が、
  `## Execution Plan Summary`の直後・`【経営サマリー】`より前に
  含まれることを確認
- `services/asset_registry_service.py` / `services/execution_planner_service.py` /
  `services/memory_service.py` / `main.py`（変更なしの確認含む）とも
  astによる構文チェックOK

## 次候補
- Quest90：Asset Generator（Execution Plan → Digital Asset生成への接続。
  Registryのdeliverables/tasksを参照して実際にLLM・画像/音声/動画生成APIを
  呼び出す）
- Registryに「使用するAIモデル・API」「生成パラメータ」などQuest90が
  実際に使う設定値を追加する
- RegistryのTasksにType情報を持たせ、Execution Planner側のTask数一致
  チェックを不要にする（現状はQuest88の固定Typeリストとの位置合わせに依存）

## DAFの状態
- Asset Typeごとの「作り方」の知識がコードから独立した読み込み専用の
  定義書として記憶されるようになった
- Execution PlannerはRegistryを優先的に参照しつつ、Registry不在時は
  既存ロジックで動作し続ける後方互換性を保っている
- 次はこのRegistryを使って実際にデジタル資産を生成するAsset Generator
  （Quest90）を実装する段階

---

# 最新状況（2026-07-05・Quest90）

## 完了
- Quest90：Asset Generator v1

## Quest90の内容
Execution Planner（Quest88）とAsset Type Registry（Quest89）で「何を」「どう」
作るかは計画できるようになったが、実際のデジタル資産はまだ何も生成して
いなかった。Quest90で初めてExecution Planを起点に実際の成果物
（LINEスタンプ素材一式）を生成するAsset Generatorを追加した
（v1では`line_sticker`のみ対応）。「Execution Plan → Digital Asset一式生成」の
パイプライン自体を完成させることを優先し、画像生成AIはまだ使わずPillowで
仮画像を生成している（画像品質の改善はv2以降）。

- 依存追加：`Pillow`を`.venv`にインストールし、`requirements.txt`に追記。
- `services/execution_planner_service.py`：`list_execution_plans(asset_type=None,
  outputs_dir=None)`を追加（現在有効なExecution Plan一覧を読み込み専用で
  返す公開関数。asset_generator_serviceが利用）。
- `services/asset_generator_service.py`：新規。
  - `generate_assets()` — `list_execution_plans(asset_type="line_sticker")`で
    対象Planの有無を確認し、無ければ`{"status": "no_plan"}`で正常終了。
    既に`outputs/generated_assets/line_sticker/metadata.md`が存在し
    Statusが`pending_review`または`approved`なら`{"status":
    "skipped_existing"}`で再生成しない（重複生成防止）。それ以外の場合、
    `outputs/generated_assets/line_sticker/`に以下を生成する：
    - `phrases.md`：40個のLINEスタンプ用セリフ（v1固定・決定的）
    - `prompts.md`：将来の画像生成API用プロンプト（stamp_01〜40）
    - `stamp_01.png`〜`stamp_40.png`：370×320px・透明背景・Pillowで生成した
      簡単なキャラクター風の丸アイコン（耳・目・口）＋下部にセリフ文字
      （日本語フォントは`AquaKana.ttc`等をmacOS標準フォントから優先的に
      使用し、無ければPillowの既定フォントにフォールバック）
    - `main.png`（240×240px）・`tab.png`（96×74px）：同じキャラクターアイコンの
      文字無し版
    - `metadata.md`：Project/Asset Type/Generated At/Status
      （`pending_review`固定）/Files一覧/Notes
    - `stickers.zip`：40枚のスタンプ・main.png・tab.png・metadata.mdをZIP化
      （phrases.md・prompts.mdはZIPには含めない。指示書の「生成したPNGと
      metadataをZIP化する」という文言通りの範囲にした）
  - `generate_asset_generator_summary()` — `metadata.md`のStatusを読み取り、
    「Generated Assets」「Output」「Recommendation」をMarkdown要約として返す
  - Pillow未インストール・Execution Plan未生成・画像生成失敗のいずれでも
    例外を投げず、DAF OS全体を止めない
- `services/memory_service.py`：Asset Registry Summaryの直後
  （Executive Summaryより前）にAsset Generator Summaryを注入するよう更新。
- `main.py`：Execution Planner生成の直後（Notion議事録保存の前）に
  Asset Generator生成を追加。失敗してもDaily Brief/AI会議全体を止めない設計。

Memory Context全体の注入順序（最終形）：
CEO Inbox Summary → CEO Decision Summary → Weekly Board Meeting Summary →
Scenario Planning Summary → Capital Allocation Summary →
Self Improvement Summary → Issue Pipeline Summary → Execution Plan Summary →
Asset Registry Summary → Asset Generator Summary → Executive Summary →
Strategic Goal Summary → Initiative Summary → KPI Summary → KPI Alert Summary →
Autonomous Issue Summary → Reflection Summary → Failed Decision Summary →
Confidence History Summary → Meeting Quality Summary

## 動作確認結果
- 実データ実行（line_sticker Execution Planが無い）→ `{"status": "no_plan"}`で
  正常終了。Summaryも「現在、生成されたAssetはありません。」を正しく出力
- テスト用一時ディレクトリにline_sticker Execution Planを用意して実行 →
  `outputs/generated_assets/line_sticker/`配下に46ファイル
  （stamp_01〜40.png・main.png・tab.png・phrases.md・prompts.md・
  metadata.md・stickers.zip）が正しく生成されることを確認
- 画像サイズ：`stamp_01.png`/`stamp_40.png` = 370×320px、`main.png` =
  240×240px、`tab.png` = 96×74px、すべてRGBA（透明背景）であることを確認
- `stamp_01.png`を実際に開いて確認 → キャラクター風の丸アイコン（耳・目・口）と
  「おはよう」という日本語テキストが文字化けせず正しく描画されていることを確認
- `stickers.zip`の中身 → 43ファイル（stamp_01〜40.png・main.png・tab.png・
  metadata.md）が正しく含まれていることを確認
- 同一データで`generate_assets()`を2回連続実行 → 2回目は
  `{"status": "skipped_existing", "existing_status": "pending_review"}`で
  再生成されないことを確認。metadata.mdのStatusを`approved`に書き換えて
  再実行 →`{"status": "skipped_existing", "existing_status": "approved"}`と
  なることも確認（重複生成防止が両ステータスで機能）
- `load_company_memory()`の出力に`## Asset Generator Summary`が、
  `## Asset Registry Summary`の直後・`【経営サマリー】`より前に
  含まれることを確認
- `services/asset_generator_service.py` / `services/execution_planner_service.py` /
  `services/memory_service.py` / `main.py`ともastによる構文チェックOK

## 残課題
- v1画像はPillowによる簡易プレースホルダー。実際の画像生成AI連携は
  prompts.mdの内容を使ってv2以降で実装する
- 対象Asset Typeは`line_sticker`のみ。他のAsset Type
  （youtube_short・blog・ebook・ios_app・saas等）への対応は未実装
- Status（`pending_review` → `approved`）を切り替えるCEOレビューの
  UI・コマンドはまだ無く、手動でmetadata.mdを編集する運用のまま

## DAFの状態
- 「Execution Plan → Digital Asset一式生成」のパイプラインが初めて現実になった
- Strategic Goals → ... → Execution Planner → Asset Type Registry →
  Asset Generatorという一連の「経営判断 → 制作計画 → 実際の制作」の
  流れが（line_stickerに限り）一巡した
- 次はCEOレビュー後の承認フロー・他Asset Typeへの対応拡大・
  本格的な画像生成AI連携が課題

---

---

# 最新状況（2026-07-05・Quest91）

## 完了
- Quest91：Artifact Review Center

## Quest91の内容
Asset Generator（Quest90）はデジタル資産を`pending_review`状態で生成する
ところまでで、その後は手動で判断するしかなかった。Quest91で「生成 →
レビュー → 承認 → 公開準備」の状態管理を行うレビューセンターを追加した。
CEOはapprove/revision/reject/publishのいずれかを選ぶだけで完結する。

- ディレクトリ：`outputs/reviews/{approved,revision_requested,rejected,
  published}/`を作成
- `services/asset_generator_service.py`：Quest90で生成するmetadata.mdに
  レビュー用フィールドを追加した（`Generated By`・`Reviewer`・
  `Reviewed At`・`Review Decision`・`Review Reason`・`Published At`）。
  `Generated By`はAsset Typeごとの制作担当AI社員（v1固定、docs/organization.md
  のDigital Asset Crewに対応）で、`line_sticker`は`Lyra` / `Vega` / `Pulsar`。
  生成直後はReviewer以降すべて「（未定）」。
- `services/artifact_review_service.py`：新規。
  - `review_asset(asset_type, decision, reason=None)` — decisionは
    `approve`→`approved` / `revision`→`revision_requested` /
    `reject`→`rejected` / `publish`→`published`にマッピングし、
    対象のmetadata.mdのStatus・Reviewer（固定で"CEO"）・Reviewed At・
    Review Decision・Review Reasonを更新（publishの場合はPublished Atも
    更新）。同時に`outputs/reviews/<status>/`へレビュー記録
    （frontmatter付きMarkdown）を保存する。metadata.md未存在・不正な
    decisionの場合は`{"ok": False, "error": ...}`を返し、例外は投げない。
  - `get_review_history()` — レビュー記録を新しい順で一覧にして返す
  - `generate_artifact_review_summary()` — `outputs/generated_assets/*/
    metadata.md`のStatusを集計し、「Pending Review」「Approved Assets」
    「Published Assets」の件数と「Recommendation」を返す
  - CLI：`python services/artifact_review_service.py approve|revision|
    reject|publish <asset_type> [理由]`
  - main.pyの自動実行フローには追加していない（レビューはCEOが明示的に
    呼んだ時のみ実行される想定のため、指示通り）。
- `services/memory_service.py`：Asset Generator Summaryの直後
  （Executive Summaryより前）にArtifact Review Summaryを注入するよう更新。

Memory Context全体の注入順序（最終形）：
CEO Inbox Summary → CEO Decision Summary → Weekly Board Meeting Summary →
Scenario Planning Summary → Capital Allocation Summary →
Self Improvement Summary → Issue Pipeline Summary → Execution Plan Summary →
Asset Registry Summary → Asset Generator Summary → Artifact Review Summary →
Executive Summary → Strategic Goal Summary → Initiative Summary → KPI Summary →
KPI Alert Summary → Autonomous Issue Summary → Reflection Summary →
Failed Decision Summary → Confidence History Summary → Meeting Quality Summary

## 動作確認結果
- テスト用一時ディレクトリで生成したline_sticker Assetに対し、
  `revision`→`approve`→`publish`の順で`review_asset()`を実行 → 都度
  metadata.mdのStatus・Reviewer（CEO）・Reviewed At・Review Decision・
  Review Reasonが正しく更新され、`generate_artifact_review_summary()`の
  Pending Review／Approved Assets／Published Assetsの件数が正しく
  増減することを確認（指示書の出力例と同じ0件表示も含め一致）
- `get_review_history()` → 3件のレビュー記録が新しい順で正しく取得できることを確認
- 存在しないasset_type・不正なdecisionを指定 →
  `{"ok": False, "error": ...}`を返し、例外を投げないことを確認
- 実データ（`outputs/generated_assets/`が空）でCLI実行 →
  「metadata.mdが見つかりません」と表示され、正常に終了することを確認
- `load_company_memory()`の出力に`## Artifact Review Summary`が、
  `## Asset Generator Summary`の直後・`【経営サマリー】`より前に
  含まれることを確認
- `main.py`は変更していないことを確認（自動実行フローにはレビューを
  追加しない、という指示通り）
- `services/artifact_review_service.py` / `services/asset_generator_service.py` /
  `services/memory_service.py`ともastによる構文チェックOK

## 残課題
- レビューUI（Dashboard上でのapprove/revision/reject/publishボタン）は
  未実装。現状はCLI・Pythonからの直接呼び出しのみ
- `revision_requested`になったAssetをAsset Generatorが自動的に再生成する
  連携はまだ無い（`generate_assets()`の重複生成防止は`pending_review`/
  `approved`のみを見ており、`revision_requested`は現状「既存ファイルが
  残ったまま」になる。再生成トリガーの設計はQuest92以降の検討課題）
- Reviewerは"CEO"固定（複数レビュアーやAI社員によるプレレビューは
  想定していない）

## DAFの状態
- 「Digital Asset → Human Approval」が完成し、CEOが最終判断だけを行える
  状態になった
- Project → Issue → Execution Plan → Digital Asset生成 → Human Approval
  という一連の制作フローが（line_sticker限定ながら）通しで動くようになった
- 次はQuest92「AI社員への自動タスク割当」で、docs/organization.mdの
  Digital Asset Crew（Vega/Lyra/Nebula/Polaris/Pulsar）へ実際にタスクを
  割り当てる仕組みを検討する

---

## DAF Organization

DAF OSは、Executive BoardとDigital Asset Crewの2層構造を持つAI会社として定義した。

Executive Board：
- Orion
- Atlas
- Sirius
- Nova
- Cosmos

Digital Asset Crew：
- Vega
- Lyra
- Nebula
- Polaris
- Pulsar

詳細は `docs/organization.md` を参照。

---

# 最新状況（2026-07-06・Quest92）

## 完了
- Quest92：Notification Center

## Quest92の内容
Project → Issue → Execution Plan → Asset生成 → Reviewというパイプラインが
完成した（Quest76〜91）が、Asset生成完了やレビュー待ちになってもCEOが
気づきにくいままだった。Quest92でDAF OS内の重要イベントを1つのMarkdown
通知ログ（outputs/notifications.md）に集約するNotification Centerを追加した。
v1ではSlack・メール・Discordなどの外部通知は行わない。

- `services/notification_service.py`：**既存ファイルを拡張**（重要な発見：
  同名のファイルが既に存在し、Mac通知センター向けの`notify()`
  （main.py末尾で呼ばれる、osascriptを使った完了通知）を提供していた。
  上書きすると既存機能を壊すため、`notify()`とその関連ヘルパーはそのまま
  残し、Quest92の新機能を追記する形で実装した）。
  - `add_notification(title, message, level="info", source="system")` —
    通知を`outputs/notifications.md`に追記する。同じ(title, source, message)
    の組み合わせが既に存在する場合は追加しない（重複通知防止）。
  - `generate_notifications()` — 現在の状態をスキャンし、該当すれば通知を
    追加する：
    - Review Requested：`outputs/generated_assets/*/metadata.md`の
      Statusが`pending_review`のAsset Typeがあれば
    - Critical KPI Alert：`kpi_alert_service.get_active_kpi_alerts()`に
      CRITICALがあれば
    - Pending Implementation：`issue_pipeline_service.load_generated_issues()`
      に`pending_implementation`があれば
  - `generate_notification_summary()` — 通知をLevel別
    （Critical → Warning → Info → Success）にグルーピングしたMarkdown要約を返す
- `services/asset_generator_service.py`：`generate_assets()`が成果物生成に
  成功した直後、`add_notification("Asset Generated", ...)`を呼ぶよう連携
  （通知失敗時も生成自体の成功扱いは変えない）
- `services/artifact_review_service.py`：`review_asset()`が成功した直後、
  `add_notification("Review Decision", f"{asset_type} が {status} に
  なりました。", ...)`を呼ぶよう連携
- `services/memory_service.py`：Artifact Review Summaryの直後
  （Executive Summaryより前）にNotification Summaryを注入するよう更新。
- `main.py`：Asset Generator生成の直後（Notion議事録保存の前）に
  Notification Center更新（`generate_notifications()`）を追加。
  失敗してもDaily Brief/AI会議全体を止めない設計。

検証中、KPI AlertsをQuest85・Quest90でも遭遇した既知の問題
（`get_active_kpi_alerts()`に`kpi_dir`を明示的に渡さないと、テスト用の
一時ディレクトリではなく実リポジトリのKPIスナップショットを参照してしまう）
に再度遭遇したため、`generate_notifications()`・`_has_critical_kpi_alert()`に
`kpi_dir`引数を追加して修正した。

Memory Context全体の注入順序（最終形）：
CEO Inbox Summary → CEO Decision Summary → Weekly Board Meeting Summary →
Scenario Planning Summary → Capital Allocation Summary →
Self Improvement Summary → Issue Pipeline Summary → Execution Plan Summary →
Asset Registry Summary → Asset Generator Summary → Artifact Review Summary →
Notification Summary → Executive Summary → Strategic Goal Summary →
Initiative Summary → KPI Summary → KPI Alert Summary → Autonomous Issue Summary →
Reflection Summary → Failed Decision Summary → Confidence History Summary →
Meeting Quality Summary

## 動作確認結果
- 実データ（重要イベント無し）で`generate_notifications()`実行 →
  新規通知0件、Summaryも「現在、通知はありません。」を正しく出力
- テスト用一時ディレクトリでpending_reviewのAsset・Critical KPI Alert
  （D1 Retention -40%）・pending_implementationのIssueを用意 →
  3件すべての通知が正しく追加され、Summaryも指示書の出力例と完全に
  一致することを確認（Critical/Warning/Infoの区分・文言とも一致）
- 同一状態で`generate_notifications()`を2回連続実行 → 2回目は新規通知
  0件（重複防止が機能）であることを確認
- `add_notification()`を同じ内容で2回呼ぶ → 1回目True・2回目Falseで
  重複が防止されることを確認
- `generate_assets()`→`review_asset('approve')`を通しで実行 →
  `outputs/notifications.md`に"Asset Generated"（success）→
  "Review Decision"（info、"line_sticker が approved になりました。"）の
  順で正しく記録されることを確認
- `load_company_memory()`の出力に`## Notification Summary`が、
  `## Artifact Review Summary`の直後・`【経営サマリー】`より前に
  含まれることを確認
- 既存の`notify()`（Mac通知）関数が引き続きimport・呼び出し可能で
  あることを確認（既存機能を壊していない）
- `services/notification_service.py` / `services/asset_generator_service.py` /
  `services/artifact_review_service.py` / `services/memory_service.py` /
  `main.py`ともastによる構文チェックOK

## 次候補
- Slack・メール・Discordなど外部通知への接続（v2以降）
- Dashboard UIへの通知一覧表示
- 通知の既読・未読管理（現状は全通知が常にSummaryへ表示される）

## DAFの状態
- 「重要イベント → Notification Center → CEO確認」の仕組みが完成した
- Asset生成・レビュー判断・KPI悪化・実装待ちIssueなど、パイプライン各所の
  重要イベントが1つのログに集約され、CEOが見逃しにくくなった

---

# 最新状況（2026-07-06・Quest93）

## 完了
- Quest93：Project Management Service

## Quest93の内容
Strategic Goals（Quest76）〜Notification Center（Quest92）まで、既に
プロダクト（mofulog）が存在する前提の経営支援・制作支援レイヤーは完成
していたが、「新しいプロジェクトを立ち上げる入口」が存在せず、手動で
フォルダを作る必要があった。Quest93でCEOがDashboardから「New Project」を
作るだけでDAF OSが動き始める起点を追加した。

- ディレクトリ：`projects/`を作成。各プロジェクトは
  `projects/<id>_<slug>/`（project.md / goals.md / initiatives.md /
  assets/ / outputs/）という構成
- `services/project_service.py`：新規。
  - `create_project(name, asset_type, vision, success_metrics=None)` —
    自動採番（001, 002, ...）・slug生成（名前から英数字トークンを抽出、
    無ければ`project_<id>`にフォールバック）・project.md/goals.md/
    initiatives.mdの生成を行う。Statusは`active`から開始する
  - `list_projects()` / `archive_project(project_id)` /
    `get_project_summary()` — 指示書の仕様通り
  - 自動起動（v1）：Goal生成・Issue生成・Execution Plan生成は
    決定的処理として常に実行する（vision/success_metricsをgoals.mdへ、
    Visionから簡易Issue案をoutputs/issues.mdへ、Asset Type Registry
    （Quest89）のテンプレートをoutputs/execution_plan.mdへ書き出す）。
    Asset Generatorまでは実行しない（試験運用では重い処理を避ける、
    という指示通り）。
  - **AI役員会議の自動実行について**：実装・検証中に、Dashboardの
    「Create」ボタンから実際にOpenRouter APIを呼ぶAI役員会議
    （crews.meeting_crew.run_meeting_crew()）が自動起動され、
    リクエストが2分近く応答を返さない状態になることを発見した
    （`.env`に実際のAPIキーが設定されているため）。CEOに確認したところ
    「デフォルトではOFF」の方針が明確に示されたため、
    `auto_launch_meeting=False`を既定値とし、Goal/Issue/Execution Plan
    生成（すべてLLM不使用・決定的）のみを自動実行するようにした。
    AI役員会議は`auto_launch_meeting=True`を明示的に指定した場合のみ
    （かつOPENROUTER_API_KEYがある場合のみ）試行する。
- `services/memory_service.py`：Memory Contextの最上部
  （CEO Inbox Summaryより前）にProject Summaryを注入するよう更新。
- `dashboard_web/app.py`：`/api/projects`（GET）・`/api/projects/create`
  （POST）・`/api/projects/archive`（POST）を追加。指示書は
  `POST /projects/create`等のパスを挙げていたが、既存APIがすべて
  `/api/`配下に統一されているため、既存構成に合わせて`/api/projects...`とした。
- `dashboard_web/templates/index.html`：新しいタブ「🗂️ プロジェクト」を追加。
  New Projectフォーム（Project Name / Asset Type / Vision / Success
  Metrics / Createボタン）とProject一覧（ID・Name・Statusバッジ・
  Asset Type・Archiveボタン）を実装。既存のダッシュボード・承認センター
  タブ・APIは変更していない。
- `dashboard_web/static/style.css`：`.project-form` / `.project-input`と
  `.badge-none`（Archived用）を追加。既存スタイルは変更していない。
- `main.py`：変更なし（指示通り。Project作成時のみ起動するため、
  main.pyの自動実行フローには追加しない）。

Memory Context全体の注入順序（最終形）：
Project Summary → CEO Inbox Summary → CEO Decision Summary →
Weekly Board Meeting Summary → Scenario Planning Summary →
Capital Allocation Summary → Self Improvement Summary → Issue Pipeline Summary →
Execution Plan Summary → Asset Registry Summary → Asset Generator Summary →
Artifact Review Summary → Notification Summary → Executive Summary →
Strategic Goal Summary → Initiative Summary → KPI Summary → KPI Alert Summary →
Autonomous Issue Summary → Reflection Summary → Failed Decision Summary →
Confidence History Summary → Meeting Quality Summary

## 動作確認結果
- `create_project()`で2件のプロジェクトを作成 → 自動採番（001/002）・
  複数プロジェクト対応・project.mdの内容が指示書の例と一致することを確認
- `list_projects()` → 2件を正しい構造（id/name/asset_type/status/path）で取得
- `archive_project('001')` → Statusが`active`から`archived`に正しく変更されることを確認
- `get_project_summary()` → Active/Completed Projectsの一覧とRecommendation
  （0件/1件/複数件で文言が変わる）が指示書の出力例と一致することを確認
- 自動起動（Goal/Issue/Execution Plan生成）→ 0.01秒で完了し、
  AI役員会議は`skipped_by_default`になることを確認（安全性の確認）
- Previewでダッシュボードを起動し、「🗂️ プロジェクト」タブから実際にフォーム入力
  →Create→一覧表示→Archiveまで一通り動作することを確認（Active→Archivedの
  バッジ切り替え、Archiveボタンの表示/非表示を含む）
- 既存の「ダッシュボード」「承認センター」タブ・APIには影響が無いことを確認
  （ブラウザコンソールにエラーなし）
- `load_company_memory()`の出力の最上部（`=== DAF 会社メモリ ===`ヘッダー
  直後）に`## Project Summary`が含まれることを確認
- `services/project_service.py` / `services/memory_service.py` /
  `dashboard_web/app.py`ともastによる構文チェックOK

## 残課題
- slug生成はASCII文字トークンの抽出のみ（翻訳・意味的な変換は行わない）。
  日本語のみのプロジェクト名は`project_<id>`にフォールバックするか、
  Vision等に含まれる英単語からslugが決まるため、必ずしも直感的な
  英語名にはならない
- AI役員会議の自動実行（`auto_launch_meeting=True`）はDashboard UIから
  選択できない（現状はサービス層の引数でのみ制御可能。UIトグルは今後の課題）
- Completed Statusへの遷移（active→completed）を行うAPI・UIはまだ無い
  （現状はarchiveのみ実装）
- プロジェクト単位のoutputs/（meeting_log.md・issues.md・execution_plan.md）
  と、会社全体のグローバルなoutputs/（Issue Pipeline・Execution Planner・
  Asset Generator等）は現状連携しておらず、別々のパイプラインとして存在する
  （プロジェクト単位のAsset Generator接続はQuest94以降の検討課題）

## DAFの状態
- 「CEO → New Project → DAF OS起動」の入口が完成した
- 複数プロジェクトを同時に管理できるようになり、CEOはDashboardから
  プロジェクトを作成・一覧確認・アーカイブできる
- ここでコストの高い自動化（AI役員会議の自動実行）について、CEOの
  明示的な意思決定を確認した上で安全側（デフォルトOFF）に倒す判断を行った
- これでDAF OSの試験運用を開始できる状態になった

---

# 最新状況（2026-07-06・Dashboard v1試験運用版）

## 完了
- Dashboard v1（試験運用版）：CEO Home・Projects改善・Generated Assets・Notifications

## 内容
Quest93でProject管理の入口ができたが、CEOが毎日開いて「今何が起きているか・
次に何をすればいいか」を一目で把握できる状態にはなっていなかった。今回、
CEOの試験運用向けホーム画面として、既存Dashboardを壊さない形で4項目
（CEO Home・Projects改善・Generated Assets・Notifications）を追加した。

- **CEO Home**：ダッシュボードタブ最上部に追加。Active Projects・Pending
  Reviews・Notifications・Pending Implementationの4タイルと、優先順位ルール
  （① pending_reviewのAssetがあれば「◯◯をレビューしてください。」
  ② pending_implementationがあれば「実装待ちIssueがあります。」
  ③ activeなProjectがあれば「Execution Planを確認してください。」
  ④ 何もなければ「新しいProjectを作成してください。」）に基づくNext Actionを表示する。
- **Projectsタブ改善**：既存の「🗂️ プロジェクト」タブのProject一覧を、
  リスト表示からテーブル表示（ID・Name・Asset Type・Status・Created At・
  Next Action・Archiveボタン）に変更。Next Actionはプロジェクト単位に
  縮小した同じ優先順位ロジックで決まる。既存のNew Projectフォーム・
  Create/Archive機能は変更していない。
- **Generated Assets（新規タブ）**：outputs/generated_assets/*/metadata.mdを
  集計し、Asset Type・Status・Files Count・Generated At・ZIP Pathを
  テーブル表示。データが無い場合は「まだ生成されたAssetはありません。」
- **Notifications（新規タブ）**：outputs/notifications.mdを新しい順で
  Time・Level・Messageのテーブル表示。データが無い場合は
  「まだ通知はありません。」

### 変更ファイル
- `services/asset_generator_service.py`：`list_generated_assets()`を追加
  （Generated Assetsタブ・CEO Home両方から参照される読み込み専用関数）
- `services/notification_service.py`：`get_notifications()`を追加
  （新しい順でパース済み通知一覧を返す読み込み専用関数）
- `services/project_service.py`：`list_projects()`の戻り値に`created_at`
  フィールドを追加（project.mdの「Created At」を読み取るだけの後方互換な拡張）
- `dashboard_web/app.py`：`GET /api/dashboard/home`・
  `GET /api/generated-assets`・`GET /api/notifications`を追加。
  各エンドポイントは情報源ごとに個別にtry/exceptで守り、1つが失敗しても
  他の値・Dashboard全体には影響しない設計にした
- `dashboard_web/templates/index.html`：CEO Homeカード（ダッシュボードタブ
  最上部）、Generated Assets・Notificationsの新規タブ、Projectsタブの
  テーブル化を実装。既存のダッシュボード・承認センター・プロジェクトタブの
  既存機能（フォーム、承認/却下ボタン等）は変更していない
- `dashboard_web/static/style.css`：`.simple-table` / `.table-scroll`
  （汎用テーブル・横スクロール用）、`.badge-none`を追加

### 実装中に見つけて直したバグ
1. **Flaskのテンプレートキャッシュ**：このアプリは`app.run(..., debug=False, ...)`
   のため、Jinja2のテンプレート自動リロードが無効になっており、実行中の
   プレビューサーバーが編集前の`index.html`をメモリ上にキャッシュし続けて
   いた。動作確認中に新しいタブ・関数が一切反映されない現象として発覚し、
   プレビューサーバーを再起動することで解決した（アプリ側のコードは変更
   していない。今後も`index.html`を編集した際はサーバー再起動が必要）。
2. **モバイルでのテーブル崩れ**：`.simple-table`に`display:block`＋
   `word-break:break-word`を指定していたため、モバイル幅ではテーブルの
   各列が1文字ずつ縦に割れてしまうバグがあった。テーブル自体はtable
   レイアウトのまま横スクロール専用の`.table-scroll`ラッパーで包む方式に
   修正し、Projects/Generated Assets/Notificationsの3テーブルすべてに適用した。

## 動作確認結果
- Previewでダッシュボードを起動し、CEO Homeがダッシュボードタブ最上部に
  正しく表示されることを確認（4タイル・Next Action）
- テスト用データ（プロジェクト1件・生成済みAsset1件・通知2件）を用意し、
  CEO Homeが`Active Projects:1 / Pending Reviews:1 / Notifications:2 /
  Pending Implementation:0`、Next Actionが
  「line_sticker をレビューしてください。」と正しく表示されることを確認
  （優先順位ルール①が正しく適用された）
- Projectsタブのテーブルに ID・Name・Asset Type・Status・Created At・
  Next Action・Archiveボタンが正しく表示されることを確認
- Generated Assets・Notificationsタブとも、データありの表形式・
  データ無しの「まだ〜ありません」表示の両方を確認
- モバイル幅（375px）でテーブルが文字化け・縦割れせず、横スクロールで
  正しく表示されることをDOM計測（scrollWidth > clientWidth）で確認
- 既存の「ダッシュボード」「承認センター」タブの動作に影響が無いことを確認
  （ブラウザコンソールにエラーなし）
- `services/project_service.py` / `services/notification_service.py` /
  `services/asset_generator_service.py` / `dashboard_web/app.py`ともast
  による構文チェックOK、`index.html`内のJavaScriptもNode.jsで構文チェックOK
- テスト用に作成したプロジェクト・Generated Asset・通知はすべて削除済み
  （実データへの影響なし）

## 残課題
- Review Center・Execution Planの高度なUI（承認/却下ボタン、Task進捗表示等）
  は指示通り今回は実装していない
- Generated Assets・NotificationsタブはCEO Homeと同様に自動更新（30秒毎の
  ポーリング）の対象ではなく、タブを開いた時のみ取得する（既存のProjects
  タブと同じ挙動）
- Notificationsの既読・未読管理は無い（Quest92から変わらず）

## DAFの状態
- CEOが毎朝Dashboardを開くだけで「今何が起きているか・次に何をすれば
  いいか」がCEO Homeの4タイル＋Next Actionで一目で分かるようになった
- Projects・Generated Assets・Notificationsが独立したタブとして整理され、
  試験運用を開始できる最小限のホーム画面が完成した

---

# 最新状況（2026-07-06・Quest94：LINEスタンプ生成 v2 改善）

## 完了
- Quest94：LINEスタンプ生成 v2 改善

## 実装内容
Pillowのみで40枚のLINEスタンプにバリエーションを追加した。

- 表情8種類
  - normal
  - smile
  - sleepy
  - surprised
  - worried
  - cheer
  - sorry
  - joy
- 装飾7種類
  - ハート
  - 星
  - 音符
  - しずく
  - キラキラ
  - 背景丸
  - 足あと
- 文字レイアウト6種類
  - 下部中央
  - 上部中央
  - 吹き出し
  - 斜め配置
  - 大きめ文字
  - 2行表示

## Dashboard改善
- Generated Assetsタブに「🐶 LINEスタンプ生成結果」セクションを追加
- 40枚のサムネイル一覧表示
- main.png / tab.png の表示
- stickers.zip のダウンロード
- metadata.md の折りたたみ表示
- フォルダを開かずに成果物確認が可能になった

## API追加
- GET `/api/generated-assets/line-sticker`
- GET `/generated-assets/line-sticker/<filename>`

## 動作確認
- 40枚の組み合わせが全て重複なし
- `python services/asset_generator_service.py` 正常動作
- Dashboard上でプレビュー・ZIPダウンロード正常動作
- Quest90〜93への影響なし
- 画像生成API未使用（生成コストなし）

## 変更ファイル
- services/asset_generator_service.py
- dashboard_web/app.py
- dashboard_web/templates/index.html
- dashboard_web/static/style.css

## 残課題
- フレーズの意味と表情が一致しない場合がある
- 装飾位置が固定的
- 40枚一括ロード方式

## 次候補
- Quest95：フレーズの意味に応じた表情・装飾・レイアウトの自動選択

---

# 最新状況（2026-07-07・Quest100：DAF Organization v2）

## 完了
- Quest100：DAF Organization v2 — AI Company Foundation

## 内容
Quest95〜99（LINEスタンプ品質改善・Dashboard UX・Project別Asset管理・
Image Generation Pipeline準備・Vega/Creative Brief導入）で積み上げてきた
実装を踏まえ、DAFを「AIを使ったシステム」から「AI社員が協働するデジタル
企業」として正式に定義し直した。新機能の追加ではなく、組織・憲章の明文化が
主目的。

- `docs/organization.md` を全面改訂：Mission・Vision・Core Valuesを追加、
  Vega（🎨）をDigital Asset CrewからExecutive Boardへ正式昇格（CDO）、
  AI Company Workflow（Idea→Nova→Sirius→Vega→Atlas→Cosmos→Orion→CEO
  Approval→Publish→Reflection→Memory→Next Product）を追加、DAF
  Departments（Executive Board / Product / Creative / Engineering /
  Marketing / Operations / Memory & Intelligence / Digital Asset Factory）
  を整理、DAF OS v1（Quest1〜99・Foundation Phase）/ v2（Quest100〜・
  AI Company Phase）を明文化
- `docs/ceo_handbook.md` を新規作成：CEOの仕事（Vision/Decision/Priority/
  Final Approval）とCEOがやらないこと（コーディング/デザイン/市場調査/
  品質確認の委譲先）を明文化
- `docs/ai_employee_handbook.md` を新規作成：Executive Board 6名＋Digital
  Asset Crew 4名について、Role/Responsibility/Input/Output/KPI/Reports Toを
  実装済みの仕組み（Creative Brief・Image Generation Service・KPI Alert等）
  に基づいて定義

コード変更は無し（ドキュメントのみ）。既存Quest1〜99の実装・Dashboard・
サービス層への影響は無い。

## 次候補
- Product Division・Marketing Divisionへの専任AI社員配置（現状はSirius/
  Nova自身が兼務）
- memory/vega.md 等、Executive Board全員分の「社員手帳」の整備
  （現状atlas.md/cosmos.md/nova.md/orion.md/sirius.mdのみ）
- Nebula（Video Producer）のAsset Generator実装（line_sticker以外の対応）

---

# 最新状況（2026-07-08・Quest101：Reference Intelligence Engine）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 1：Creative Intelligence**

## 完了Quest
Quest101まで完了。

## Quest101内容
- Reference Intelligence Engine
- Reference Library（`outputs/reference_library/`：animals/cute/simple/
  pastel/manga/realistic の6カテゴリ、画像ごとに`reference.json`を保存）
- Vega Reference Report（`services/reference_analysis_service.py`。配色・
  線の太さ・キャラクター性・世界観・デザインキーワードを集計）
- Creative Briefとの連携（`services/creative_brief_service.py`に
  「## Reference Summary」セクションを追加、Creative Brief生成時に
  Reference Reportも自動更新）
- Dashboard「🎨 Reference Library」カード追加（登録画像数・タグ一覧・
  最新登録画像・Reference Summary）

画像解析AI（Vision API・マルチモーダルLLM等）はまだ導入していない
（登録済みメタデータの集計のみ）。既存Quest90〜100への影響は無し。

## 現在のAI組織（Executive Board）
- CEO
- Orion（COO）
- Atlas（CTO）
- Sirius（CPO）
- Nova（CMO）
- Cosmos（CIO）
- Vega（CDO）

## 次のQuest
**Quest102：Reference Upload UI**

目的：Dashboardから
- 参考画像登録
- タグ付け
- Project紐付け
- Reference Summary更新

を行えるようにする。画像解析AIはまだ導入しない。

## 今後のロードマップ
- Quest103：画像解析AI
- Quest104：Character Bible強化
- Quest105：画像生成AI導入

---

# 最新状況（2026-07-07・Quest102：Reference Upload UI）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 1：Creative Intelligence**

## 完了Quest
Quest102まで完了。

## Quest102内容
Quest101で用意したReference Library（`outputs/reference_library/`）は
画像バイナリの置き場のみで、登録はCEOがフォルダへ手動で画像＋
`reference.json`を置く前提だった。Quest102でDashboardから直接アップロード・
タグ付け・Project紐付けができるUI（🎨 Referencesタブ）を追加した。
画像解析AI（Vision API・マルチモーダルLLM等）は今回も導入していない
（タグ・Descriptionは引き続きCEOの手入力）。

- `services/reference_analysis_service.py`：
  - `save_reference_image()` — アップロードされた画像バイナリを
    `outputs/reference_library/<category>/`へ保存し、`register_reference_metadata()`
    を呼んで`reference.json`を登録する（拡張子はpng/jpg/jpeg/webpのみ許可、
    ファイル名は`ref_<timestamp>_<uuid8>_<safe_stem>.<ext>`に丸めて衝突・
    パストラバーサルを防止）。Descriptionは既存スキーマの`memo`項目に保存する。
  - `refresh_all_reference_summaries()` — 登録済みの全project_idについて
    `generate_vega_reference_report()`を呼び直す（project_id未紐づけの画像は対象外）。
  - `get_default_categories()` — 既定6カテゴリをDashboardの選択肢用に公開。
- `dashboard_web/app.py`：
  - `GET /api/references` — 参考画像一覧・既定カテゴリ・登録済みProject一覧
  - `POST /api/references/upload` — 画像アップロード（multipart/form-data）
  - `POST /api/references/summary/refresh` — Reference Summary再生成
    （project_id指定で単一Project、未指定で登録済み全Projectを一括更新）
  - `GET /reference-library/<path:filename>` — 画像配信（拡張子ホワイトリスト、
    `.reference.json`は404）
- `dashboard_web/templates/index.html` / `static/style.css`：
  🎨 Referencesタブ（アップロードフォーム・Reference一覧テーブル・
  Summary Refreshボタン）を追加。既存タブ構成・カード/フォームのCSSクラス
  （project-form・simple-table・reference-tag等）をそのまま踏襲。
- `tests/test_quest102_reference_upload.py`：新規（リポジトリに既存の
  テスト基盤が無かったため`tests/`を新設）。`save_reference_image()`の
  正常系・拡張子バリデーション・`refresh_all_reference_summaries()`の
  project_id集約・`get_default_categories()`の非破壊性を検証。

## 既知の制約（CEO確認済み・Quest102スコープ内でOK）
1. **Creative Briefは自動追従しない**：Referencesタブの「Summary Refresh」は
   `outputs/reference_library/<project_id>/vega_reference_report.md`のみ更新する。
   `outputs/creative_briefs/<project_id>/creative_brief.md`内の
   「## Reference Summary」は`generate_creative_brief()`実行時点のスナップショット
   であり、これはProjectsタブの「Generate Assets」（line_stickerのみ、
   `services/project_service.py`の`generate_project_assets()`経由）でのみ
   再生成される。Creative Brief単体の再生成UIは無い（→ 別Quest候補）。
2. **reference.jsonから常に復元される**：`list_reference_images()`は
   メモリキャッシュを持たず毎回ディスクを読み直すため、Dashboard/サーバー
   再起動後もReference一覧は失われない（プロセスを跨いで確認済み）。
3. **1画像＝1Project設計**：`reference.json`の`project_id`は単一文字列で
   配列ではない。同じ画像を複数Projectに紐づけたい場合は現状Projectごとに
   再アップロードが必要（ファイルも複製される）。将来的に`project_ids: list[str]`
   等へ拡張する可能性あり（v1では未対応、CEO了承済み）。

## 動作確認結果
- Dashboard起動・Referencesタブ表示：OK（既存タブに回帰なし）
- 画像アップロード（curl・実UIとも）→ `outputs/reference_library/<category>/`に
  画像＋`reference.json`が保存され、一覧に反映されることを確認
- 拡張子バリデーション（.txt等）→ 400エラーで拒否されることを確認
- Summary Refresh（project_id指定・全件一括）→ `vega_reference_report.md`が
  正しく更新されることを確認
- `tests/test_quest102_reference_upload.py`：4件全てpass

## 次のQuest
**Quest103：画像解析AI**（Vision API等の導入を検討）

## 今後のロードマップ
- Quest103：画像解析AI
- Quest104：Character Bible強化
- Quest105：画像生成AI導入

---

# 最新状況（2026-07-07・Quest103：Reference Image Analysis AI）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 1：Creative Intelligence**

## 完了Quest
Quest103まで完了。

## Quest103内容
Quest101〜102では「画像解析AIは使わない」方針だったが、Quest103で初めて
Reference画像へのAI画像解析を導入した。ただしAI解析は"自動確定"ではなく、
CEOが確認・修正できる"提案"にとどめている（reference.jsonへの反映は
CEOがSaveを押した時だけ）。画像生成AIの導入・Creative Briefの自動再生成・
Reference Summaryの自動連鎖はいずれも行っていない。

- `services/reference_analysis_service.py`：
  - `analyze_reference_image(image_path)` — Vega（CDO）視点のプロンプトで
    参考画像1件をAI解析し、tags/animal/color/mood/memoの提案を返す。
    `crews/meeting_crew.py`と同じOpenRouter経由`openrouter/openai/gpt-4o-mini`
    （画像入力対応）を`litellm.completion()`で直接呼ぶ。`OPENROUTER_API_KEY`
    未設定・画像未存在・AI呼び出し失敗のいずれでも例外を投げず、
    `{"ok": False, "error": ..., "tags": [], ...}`の安全なStubを返す。
  - `update_reference_metadata()` — 既存`reference.json`のtags/animal/color/
    mood/memoだけを部分更新する（title/project_id/registered_at等は保持）。
    category・filenameの検証（スラッシュ・".."拒否）でパストラバーサル対策済み。
    対象が存在しない場合は`error: "not_found"`を返す。
- `dashboard_web/app.py`：
  - `POST /api/references/analyze` — `{category, filename}`を受け取りAI解析
    結果を返す（reference.jsonへの保存はしない）
  - `POST /api/references/update` — `{category, filename, tags, animal,
    color, mood, memo}`でreference.jsonを部分更新（対象なしは404）
- `dashboard_web/templates/index.html` / `static/style.css`：Reference一覧の
  各行に「✨ Analyze / Edit」トグルを追加。展開パネルで
  「🤖 Analyze with AI」→ tags/animal/color/mood/memoの編集欄に提案を反映
  → 内容を確認・修正 →「💾 Save Analysis」で保存、という一連の操作を追加。
  既存のアップロードフォーム・Reference一覧・Summary Refreshには変更なし。
- `tests/test_quest103_reference_analysis.py`：新規（9件）。
  `OPENROUTER_API_KEY`未設定時の安全なStub、画像未存在時のエラー、
  `update_reference_metadata()`の正常マージ・既存フィールド保持・
  パストラバーサル拒否・404、Flask API層での不正input（400）・
  存在しないReference（404）を検証。実際のOpenRouter APIへは接続しない
  （ネットワーク非依存・再現性を優先）。

AI呼び出しに新規ライブラリは追加していない：`litellm`は既存の
`crewai==0.80.0`（requirements.txt記載済み）の依存として`.venv`に
既にインストール済みであり、`requirements.txt`の更新は不要だった。
APIキーはコードに直書きせず、`os.getenv("OPENROUTER_API_KEY")`で
`.env`（gitignore対象）からのみ読む。

## 既知の制約・確認済み事項（CEO確認済み）
1. `.env`・`OPENROUTER_API_KEY`はgit管理対象に含まれない
   （`.gitignore`で`.env`除外、`.env.example`のみ追跡対象）。
2. AI解析失敗時（キー未設定・認証エラー・タイムアウト等）もサービス層・
   APIルートの両方でtry/exceptしており、Dashboard全体は落ちない。
   実際に不正なAPIキーで`litellm.AuthenticationError`を誘発させ、
   例外を投げず`{"ok": False, "error": ...}`が返ることを確認済み。
   フロントエンドは`data.success`がfalseの場合、編集パネル内の
   ステータス欄に`⚠️ ...`を表示するのみで、他のUIには影響しない。
3. Quest102の制約（Creative Brief非自動追従／1画像＝1Project設計）は
   Quest103でも変更していない（今回のスコープ外）。

## 動作確認結果
- Dashboard起動・Referencesタブ表示：OK（既存機能に回帰なし）
- 実画像アップロード→「Analyze with AI」（実際にOpenRouter APIを呼び出し）→
  編集欄に反映→「Save Analysis」→`reference.json`が正しく更新されることを
  実ブラウザ操作で確認（`project_id`/`category`/`filename`/`registered_at`は
  保持されたまま`tags`/`animal`/`color`/`mood`/`memo`のみ更新）
- 画像ファイルが実在しないサンプルデータ（Quest101動作確認用）でAnalyzeを
  押すと404エラーがUI上に正しく表示され、ページ全体は落ちないことを確認
- Summary Refresh・Projectsタブ等：回帰なし
- `tests/`配下13件（Quest102の4件＋Quest103の9件）すべてpass

## 次のQuest候補
- Quest104：Character Bible強化
- Quest105：画像生成AI導入
- Creative Brief単体の再生成UI（Quest102から持ち越しの既知の制約）

## 今後のロードマップ
- Quest104：Character Bible強化
- Quest105：画像生成AI導入

---

# 最新状況（2026-07-08・Quest104：IP Memory Engine）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 2：IP Intelligence（開始）**

## 完了Quest
Quest104まで完了。

## Quest104内容
Quest101〜103はReference画像（1件単位）の登録・解析までだった。Quest104で
「Character単体ではなくIP全体の知識を蓄積・成長させる基盤」として
IP Memory Engineを導入した。設計思想は
`Reference（画像）→ Analysis（Quest103のAI解析）→ IP Memory（本質の蓄積）
→ Asset Generation（将来）`という流れ。

IP Memoryは1つのIPにつき`DNA / Character Bible / World Bible / Style Guide /
Prompt History / Review History / Evolution History`の7セクション構造とし、
今回実装したのはDNAのみ。他セクションはキーだけ確保した空のプレースホルダ
（Dashboard上はComing Soon表示）で、将来のQuestでも`ip_memory.json`の
スキーマ自体は変えずに実装を追加できる。

- `services/ip_memory_service.py`：新規。
  - `create_ip(ip_name)` — DNA（identity/personality/visual/brand/rules/
    keywords）含む全セクションの空箱を作成。既存IPがあれば上書きせず
    既存データを返す（誤って空箱で潰さない安全策）。
  - `load_ip()` / `save_ip()` — `outputs/ip_memory/<ip_name>/ip_memory.json`の
    読込・全体保存。`save_ip()`は`metadata.updated_at`更新・`version`
    インクリメントを行う。
  - `list_ips()` — 登録済みIP一覧（Dashboard向け、dna_name/version/
    updated_at付き）。
  - `update_dna(ip_name, dna_updates)` — DNAグループ単位で部分更新し、
    未指定フィールド・他セクション・`metadata.created_at`は保持する。
    IP未作成なら`create_ip()`相当で新規作成してから更新。
  - `generate_dna_from_reference(ip_name, project_id=None, category=None)` —
    登録済みReference（Quest103解析済みのtags/animal/color/mood/memo）を
    project_id/categoryで絞り込み、複数件の共通特徴からDNAの"提案"を
    生成する（**保存はしない**。呼び出し側がupdate_dna()/save_ip()を
    呼んで初めて反映）。Referenceの複製ではなく「複数枚に共通する本質」を
    抽出するようVega視点のプロンプトで指示。`OPENROUTER_API_KEY`設定時は
    `crews/meeting_crew.py`と同じOpenRouter経由`gpt-4o-mini`を
    `litellm.completion()`で呼ぶ（画像は渡さず、Quest103解析結果という
    テキストメタデータのみを渡す）。未設定・AI失敗時は頻出タグ/動物/
    配色/雰囲気の単純集計にフォールバックし、例外を投げない。
  - IP名は`_safe_ip_name()`で英数字・ハイフン・アンダースコアのみに
    丸め、パストラバーサル対策済み。`outputs/reference_library/`とは
    物理的に完全分離（`outputs/ip_memory/`）。
- `dashboard_web/app.py`：
  - `GET /api/ip-memory` — IP一覧
  - `GET /api/ip-memory/<ip_name>` — IP詳細（DNA含む全セクション）
  - `POST /api/ip-memory/create` — 新規IP作成
  - `POST /api/ip-memory/dna/update` — DNA部分更新・保存
  - `POST /api/ip-memory/dna/generate` — ReferenceからDNA提案を生成（保存しない）
- `dashboard_web/templates/index.html`：🧬 IP Memoryタブを追加。New IP作成
  フォーム／IP一覧テーブル／IP選択でDNA編集パネル展開（Identity/
  Personality/Visual/Brand/Rules/Keywordsの各フィールドを個別input化）／
  「🤖 Generate DNA from Reference」（project_id・category任意指定）→
  提案を編集欄に反映→「💾 Save DNA」で保存、という一連の操作を追加。
  Character Bible等は`<details>`内にComing Soon文言で表示。既存CSSクラス
  （project-form・simple-table・reference-edit-actions等）を再利用し、
  style.cssの変更は無し。
- `tests/test_quest104_ip_memory.py`：新規（16件）。IP作成・上書き防止・
  空名拒否、save/load往復、DNA部分更新（既存フィールド保持）、
  IP未作成時のupdate_dnaからの自動作成、list_ips、Reference無し時の
  エラー、`OPENROUTER_API_KEY`未設定時のフォールバック集計、Flask API層
  の入力バリデーション（空名・不正ip_name・存在しないIP）を検証。

## 確認済み事項（CEO確認済み）
1. `.env`・`OPENROUTER_API_KEY`はgit管理対象に含まれない（`.gitignore`で
   `.env`除外、コード内にキーのハードコード無し、`os.getenv()`のみ使用）。
2. `outputs/ip_memory/`は`.gitignore`の`outputs/`ルールに含まれ、テスト
   生成物・実データともcommit対象外。
3. IP名は`_safe_ip_name()`（サービス層、`\w\-`以外を`_`へ丸める）・
   `_safe_ip_name_param()`（app.py、URLパス用に`^[\w\-]+$`で拒否）の
   二重チェックでパストラバーサル対策済み。
4. AI生成失敗時（不正なAPIキーで`litellm.AuthenticationError`を実際に
   誘発させて確認）も例外を投げず、`ok=True, source="fallback_aggregation"`
   で簡易集計結果を返すため、Dashboard全体は落ちない。

## 動作確認結果
- Dashboard起動・IP Memoryタブ表示：OK（既存タブに回帰なし）
- 実ブラウザ操作でIP作成→自動でDNAパネル展開→実際にOpenRouter APIを呼び出し
  「Generate DNA from Reference」でDNA提案を生成→編集→「Save DNA」→
  `ip_memory.json`が正しく更新（`version`自動インクリメント）されることを確認
- References・Projectsタブ等：回帰なし
- `tests/`配下29件（Quest102の4件＋Quest103の9件＋Quest104の16件）すべてpass

## 次のQuest候補
- Character Bible（IP Memory内の空プレースホルダを実装）
- World Bible / Style Guide
- Prompt History / Review History / Evolution Historyの記録開始
- Quest105：画像生成AI導入

## 今後のロードマップ
- Character Bible強化
- World Bible / Style Guide実装
- Quest105：画像生成AI導入

---

# 最新状況（2026-07-08・Quest105：IP Bible Generator）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 2：IP Intelligence**

## 完了Quest
Quest105まで完了。

## Quest105内容
Quest104で構築したIP Memory（DNA）から、人とAIが共通認識として使える
「IP Bible」（IP全体の設計書。Character設定だけでなくWorld・Brand・Style
まで含む）をMarkdownで生成できるようにした。設計思想（全体の流れ）：
`Reference → Reference Analysis（Quest103）→ IP Memory（Quest104）→
IP DNA → IP Bible（本Quest）→ Prompt Builder（将来）→ Asset Generation（将来）`。

- `services/ip_bible_service.py`：新規。
  - `generate_ip_bible(ip_name)` — IP DNAを入力に、Vega（Chief IP Designer）
    視点のプロンプトでIP Bible（Markdown）の"提案"を生成する（**保存は
    しない**。Quest103/104と同じ「AIは提案、CEOが確認・保存」方針）。
    `OPENROUTER_API_KEY`設定時はOpenRouter経由`gpt-4o-mini`を
    `litellm.completion()`で呼び、Identity/Story/Core Personality/
    Visual Identity/Color Palette/World/Brand Position/Style Rules/
    Forbidden Rules/Prompt Examples/Future Evolutionの11見出しを含む
    Markdownを要求する（応答に`## Identity`が無い等、期待構造を満たさない
    場合もテンプレートへフォールバック）。未設定・AI失敗時は、DNAの値を
    そのまま差し込む決定的なテンプレート（`_template_ip_bible()`）を返す。
  - `save_ip_bible(ip_name, markdown)` — `outputs/ip_memory/<ip_name>/
    ip_bible.md`へ保存する（プレーンなUTF-8テキストファイル。HTML化・
    特殊フォーマットはしない）。IP未作成の場合はエラー。
  - `load_ip_bible(ip_name)` — 保存済みip_bible.mdを読み込む。未存在なら
    Noneを返す。
  - **IP Memory（`ip_memory.json`）には一切書き込まない**：generate/save/
    loadいずれの関数も`ip_memory.json`をread-onlyでしか参照しない
    （`save_ip()`/`update_dna()`の呼び出しなし）。実際にIP Bible生成・
    保存の前後で`ip_memory.json`のSHA-256ハッシュ・mtimeが完全一致する
    ことを確認済み（CEO確認事項、後述）。
- `services/ip_memory_service.py`：`ip_dir_path()`を公開追加（IPフォルダの
  Pathを組み立てるロジックを`ip_bible_service.py`と共有し、パス組み立ての
  重複実装を避けるため。既存関数への変更は無し）。
- `dashboard_web/app.py`：
  - `POST /api/ip-memory/bible/generate` — IP Bible提案を生成（保存しない）
  - `POST /api/ip-memory/bible/save` — 生成済みMarkdownをip_bible.mdへ保存
  - `GET /api/ip-memory/<ip_name>/bible` — 保存済みIP Bibleを取得（Preview用）
- `dashboard_web/templates/index.html` / `static/style.css`：IP Memoryタブの
  DNAパネル下に「📖 IP Bible」カードを追加。`📖 Generate IP Bible`（AI提案
  生成）→ `<pre>`でMarkdownをそのままプレビュー → `👀 Preview`（未生成なら
  保存済みip_bible.mdを取得表示、生成済みなら表示トグル）→ `💾 Save`で保存、
  という一連の操作を追加。Character Bible等は引き続きComing Soon表示。
- `docs/organization.md` / `docs/ai_employee_handbook.md`：Creative
  Divisionに「IP Team」を新設（ドキュメント上の役割分担のみ、実際の
  Agent分離は将来Quest）：
  - 🎨 Vega — Chief IP Designer（IP Bible全体の統括・最終出力）
  - 🌙 Luna — Story Designer（Story / Core Personality / Future Evolution）
  - ☀️ Sol — Visual Designer（Visual Identity / Color Palette / Style Rules）
  - 🛰️ Astra — Brand Guardian（Brand Position / Forbidden Rules）
  Quest105時点では`services/ip_bible_service.py`のAI呼び出しはVega視点の
  プロンプト1本で、Luna/Sol/Astraの担当領域もすべてVegaの出力に含まれる
  （個別Agent化は未実装）。
- `tests/test_quest105_ip_bible.py`：新規（11件）。テンプレートフォールバック
  生成（11見出しすべて含む・DNA値がそのまま反映される）、IP未存在時の
  エラー、空DNAでも生成できること、save/load往復、Reference Libraryとは
  別フォルダに保存されること、Flask API層の入力バリデーション
  （空名・存在しないIP・空Markdown）を検証。

## 確認済み事項（CEO確認済み）
1. `ip_bible.md`はプレーンなMarkdownテキストファイル（`file`コマンドで
   "Unicode text, UTF-8 text"、HTML等でラップしない）。Markdown Viewer
   以外（`cat`・テキストエディタ等）でも問題なく読める。
2. `ip_memory.json`のスキーマは既にQuest104で`character_bible` /
   `world_bible` / `style_guide`を空のプレースホルダとして確保済み。
   `ip_bible_service.py`は完全に独立した新規ファイルであり、将来
   Character Bible / World Bible / Style Guideを個別生成する場合も、
   同じパターン（新規service + 既存プレースホルダへの書き込み）で
   現在の構成を変更せず追加だけで実現できる。
3. IP Bible生成・保存の前後で`ip_memory.json`が変更されないことを実際に
   ハッシュ比較で確認済み（生成後・保存後ともSHA-256・mtimeが完全一致）。
   コード上も`ip_bible_service.py`内に`save_ip`/`update_dna`/`json.dump`の
   呼び出しは無い。

## 動作確認結果
- Dashboard起動・IP Memoryタブ表示：OK（既存タブに回帰なし）
- 実ブラウザ操作でIP作成→DNA生成→DNA保存→IP Bible生成（実際にOpenRouter
  APIを呼び出し）→Preview表示→Save→`ip_bible.md`が`ip_memory.json`と
  同じフォルダに正しく保存されることを確認
- 保存済みIP Bibleの再Preview（ディスクからの読込）も確認
- References・Projectsタブ等：回帰なし
- `tests/`配下40件（Quest102の4件＋Quest103の9件＋Quest104の16件＋
  Quest105の11件）すべてpass

## 次のQuest候補
- Character Bible個別生成（IP Memory内の空プレースホルダを実装）
- World Bible / Style Guide個別生成
- Luna / Sol / Astraの実際のAgent分離（現状はVegaのプロンプト1本が代行）
- Prompt Builderとの接続（IP BibleをPrompt Builderへ渡す導線）
- 画像生成AI導入

## 今後のロードマップ
- Character Bible / World Bible / Style Guide個別実装
- IP Team（Luna/Sol/Astra）の実Agent化
- Prompt Builder連携
- 画像生成AI導入

---

# 最新状況（2026-07-08・Quest106：Quality Control Engine）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 2：IP Intelligence**

## 完了Quest
Quest106まで完了。

## Quest106内容
DAF OSは「Lean AI First」（Python → Rule Engine → Template → AI → CEOの
優先順位で、まず一番安価で決定的な層から実装する）を採用している。
Quest106でその先頭のPython層として、AI Review（Vision API・LLM判定等）
ではなくPythonの決定的なルールだけで生成物（Digital Asset）の品質を
機械的にチェックするQuality Control Engineを追加した。OpenRouter等の
外部AI APIは一切呼ばない。

- `services/quality_control_service.py`：新規。
  - `validate_image(image_path)` — PNG形式・背景透過（アルファ値の実際の
    透明ピクセル有無まで確認）・寸法（1〜4096px）・解像度（DPI、無くても
    WARNING止まり）・縦横比・ファイルサイズ（1MB/5MBを閾値にPASS/WARNING/
    FAIL）をチェック。画像未存在・破損でも例外を投げず、該当項目をFAILで
    返す。
  - `validate_metadata(metadata_path)` — メタデータのJSON存在・必須キー
    （version/timestamp相当、`ip_memory.json`のように`metadata`キー配下に
    ネストされていても検出）をチェック。既存パイプライン（LINEスタンプ等）
    が使うMarkdown形式`metadata.md`にも後方互換で対応し、その場合は
    「存在するがJSONではない」としてWARNING（必須キー検証はできないため）。
  - `validate_ip(ip_name)` — IP Memory（Quest104 `ip_memory.json`）・
    IP Bible（Quest105 `ip_bible.md`）の存在をread-onlyで確認。ip_name未指定
    ならWARNING（現状のline_stickerパイプラインはまだIPと未連携のため、
    単独では不合格にしない）。
  - `validate_reference(project_id)` — 登録済みReference
    （`outputs/reference_library/`、Quest101〜102）の有無をread-onlyで確認。
  - `validate_asset(asset_dir)` — Assetフォルダ内の代表画像（main.png →
    tab.png → 最初のpng）・メタデータ（metadata.json → metadata.md）を
    自動検出してvalidate_image()/validate_metadata()を実行。
  - `generate_quality_report(asset_dir, ip_name=None, project_id=None)` —
    上記すべてを統合し、各チェックに重み（合計100）を割り当てて加重平均
    スコアを算出、`{"passed", "score", "checks"}`を返す。PASS=満点／
    WARNING=半分／FAIL=0点。`passed`はスコア≧70かつ"PNG"チェックが
    FAILしていないことで判定（画像が開けない場合のみ無条件不合格。
    Metadata/IP/Referenceは現時点では参考情報で、単独では不合格にしない
    設計。実際にIP Memory・Reference Libraryのファイルハッシュが実行前後で
    完全一致することをテストで確認済み＝read-onlyでの参照のみ）。
- `dashboard_web/app.py`：`POST /api/quality/check` を追加
  （`{"asset_type": "line_sticker", "project_id": ..., "ip_name": (任意),
  "reference_project_id": (任意)}` → Quality Reportを返す。現状
  asset_type=line_stickerのみ対応）。
- `dashboard_web/templates/index.html`：専用の「Quality」タブは作らず、
  Generated Assetsタブの「🐶 LINEスタンプ Project別成果物」各カードに
  「🧪 Run Quality Check」ボタンを追加。クリックで即座にPASS/FAIL・
  スコア・チェック項目ごとのPASS/WARNING/FAILテーブルを表示する。
- `docs/organization.md` / `docs/ai_employee_handbook.md`：Operations
  Division配下にQuality Teamを新設（ドキュメント上の役割分担のみ、実際の
  Agent分離は将来Quest）：
  - 🌠 Altair — Quality Lead（Quality Control Engine全体の統括、
    Reports To: Orion）
  - 🌍 Terra — Validation Engineer（画像・メタデータ・IP/Reference連携の
    実チェック、Reports To: Altair）
  当初案では🌠 Lyra（Quality Lead）・🛰️ Astra（Brand Guardian、Quest105）
  としていたが、既存の✍️ Lyra（Content Creator）・🛰️ Pulsar（Automation
  Engineer）と名前・絵文字が重複し将来の混乱要因になるとCEOから指摘があり、
  commit前にQuality Leadを🌠 Altairへ改名、Astraの絵文字を⭐へ変更した
  （Astra自体の名前・役割はQuest105のまま維持）。
- `tests/test_quest106_quality_control.py`：新規（26件）。PNG判定（正常・
  透明ピクセル無し・アルファチャンネル無し・拡張子違反・ファイル未存在）、
  JSON判定（正常・必須キー欠落・ip_memory.json形式のネスト検出・不正JSON・
  レガシーMarkdown・未存在）、IP/Reference判定、Quality Report全体の
  PASS/FAIL・IP Memory/Reference Libraryが変更されないことの確認、Flask
  API層の入力バリデーション（不正asset_type・不正project_id・404）を検証。

## 確認済み事項
1. AI・OpenRouterは一切呼ばない（`services/quality_control_service.py`に
   litellm・API呼び出しの類は無く、Pythonの決定的なルール＋Pillowの画像
   検査のみ）。
2. IP Memory（`ip_memory.json`）・Reference Library
   （`outputs/reference_library/`）へは一切書き込まない（read-onlyでの
   参照のみ。テストでファイルハッシュの完全一致を確認済み）。
3. 実データ（`outputs/generated_assets/line_sticker/`の実LINEスタンプ）で
   動作確認：PNG/Transparency/Size/Aspect Ratio/File SizeはPASS、
   Resolution（DPI未設定）・Metadata（既存metadata.mdはMarkdownのため）・
   IP Memory/IP Bible/Reference（未連携のため）はWARNING、総合スコア75点で
   passed=trueという、既存v1パイプラインの実態に即した妥当な結果が出た。

## 動作確認結果
- Dashboard起動・Generated Assetsタブ表示：OK（既存タブに回帰なし）
- 実ブラウザ操作で「🧪 Run Quality Check」ボタン→Quality Reportが
  PASS/WARNING/FAILのテーブルとスコアで正しく表示されることを確認
- IP Memory・References・Projectsタブ等：回帰なし
- `tests/`配下66件（Quest102の4件＋Quest103の9件＋Quest104の16件＋
  Quest105の11件＋Quest106の26件）すべてpass

## 次のQuest候補
- Quality Control EngineのRule Engine層強化（アセットタイプ別の閾値、
  LINEスタンプ規格準拠チェック等）
- Quality Reportの永続化（`outputs/quality_reports/`等への保存、履歴比較）
- Character Bible個別生成・World Bible / Style Guide個別生成
- Luna / Sol / Astra、Altair / Terraの実際のAgent分離
- 画像生成AI導入

## 今後のロードマップ
- Quality Control EngineのRule層強化・レポート永続化
- Character Bible / World Bible / Style Guide個別実装
- IP Team・Quality Teamの実Agent化
- 画像生成AI導入

---

# 最新状況（2026-07-08・Quest107：Creative Style Engine）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 2：IP Intelligence**

## 完了Quest
Quest107まで完了。

## Quest107内容
`Reference → Reference Analysis（Quest103）→ IP Memory（Quest104）→
IP DNA → IP Bible（Quest105）`の流れの最後の変換層として、IP DNA・
IP Bibleから実制作（イラスト・画像生成AI・LINEスタンプ等）で使う具体的な
描画ルール「Style Guide」（Markdown）と、Prompt Builder（将来）が機械的に
使えるルール「Prompt Rules」（JSON：always/prefer/avoid/never）を生成する
Creative Style Engineを追加した。

- `services/creative_style_service.py`：新規。
  - `generate_style_guide(ip_name)` — IP DNA・IP Bibleを入力に、Vega
    （Chief IP Designer）視点のプロンプトでStyle Guide（Markdown）の
    "提案"を生成する（**保存はしない**。Quest103〜106と同じ「AIは提案、
    CEOが確認・保存」方針）。`OPENROUTER_API_KEY`設定時はOpenRouter経由
    `gpt-4o-mini`を`litellm.completion()`で呼び、Color Rules/Line Rules/
    Shape Rules/Expression Rules/Composition Rules/Typography Rules/
    Negative Rulesの7見出しを含むMarkdownを要求する（`## Color Rules`が
    応答に無い等、期待構造を満たさない場合もテンプレートへフォールバック）。
    未設定・AI失敗時は、DNAの値をそのまま差し込む決定的なテンプレート
    （`_template_style_guide()`）を返す。
  - `generate_prompt_rules(ip_name)` — 同じくIP DNA・IP Bibleを入力に、
    `{"always": [], "prefer": [], "avoid": [], "never": []}`のPrompt
    Rules（JSON）の"提案"を生成する（保存はしない）。フォールバック時は
    `visual.color_palette`/`line_style`/`rules.must_have`をalwaysへ、
    `keywords`をpreferへ、`rules.must_not`をneverへ機械的に分類する
    （`_template_prompt_rules()`）。
  - `save_style_guide()` / `load_style_guide()` — `outputs/ip_memory/
    <ip_name>/style_guide.md`への保存・読込（プレーンなUTF-8テキスト、
    `file`コマンドで"Unicode text"と確認済み）。
  - `save_prompt_rules()` / `load_prompt_rules()` — `outputs/ip_memory/
    <ip_name>/prompt_rules.json`への保存・読込。保存時に
    always/prefer/avoid/neverの4キーを必ず埋める（入力に無いキーは
    空配列で補完）ため、保存後のJSONは常にこの4キーを持つ。
  - **`ip_memory.json`本体には一切書き込まない**：`ip_bible_service.py`と
    同じ設計方針で、Style Guide/Prompt Rulesは`ip_bible.md`と同じフォルダに
    別ファイルとして保存する（`ip_memory.json`の`style_guide`プレースホルダ
    キーはQuest104から変わらず空`{}`のまま）。生成・保存の前後で
    `ip_memory.json`のSHA-256ハッシュが完全一致することを確認済み
    （CEO確認事項、後述）。
  - Image Generation・Asset Generator・Quality Control Engineのいずれにも
    触れない（読み込みも書き込みもしない、完全に独立したService）。
- `dashboard_web/app.py`：
  - `POST /api/ip-memory/style/generate` — Style Guide・Prompt Rulesの
    提案を生成（保存しない）
  - `POST /api/ip-memory/style/save` — 生成済みMarkdown・JSONを両方保存
  - `GET /api/ip-memory/<ip_name>/style` — 保存済みStyle Guide・Prompt
    Rulesを取得（Preview用）
- `dashboard_web/templates/index.html`：IP Memoryタブ、IP Bibleカードの
  下に「🎨 Creative Style」カードを追加。`🎨 Generate Style Guide`
  （AI提案生成）→ Style Guide（Markdown）とPrompt Rules（JSON）を
  `<pre>`でそれぞれプレビュー → `👀 Preview`（未生成なら保存済みファイルを
  取得表示、生成済みなら表示トグル）→ `💾 Save`で両ファイルを保存、という
  一連の操作を追加。Coming Soon文言から「Style Guide」を除外し、Character
  Bible/World Bible/Prompt History/Review History/Evolution Historyのみ
  残した。
- `docs/organization.md` / `docs/ai_employee_handbook.md`：IP Team
  （Vega/Luna/Sol/Astra、Quest105で新設）の担当領域にCreative Style
  Engineを追加（ドキュメント上の役割分担のみ、実際のAgent分離は将来
  Quest）：Vega＝統括、Luna＝Expression Rules、Sol＝Style Guide統括
  （Color/Line/Shape/Composition/Typography）、Astra＝Negative Rules・
  Prompt Rulesのavoid/never。
- `tests/test_quest107_creative_style.py`：新規（17件）。テンプレート
  フォールバック生成（7見出しすべて含む・DNA値がそのまま反映される）、
  Prompt Rulesの4キー固定・DNA値の機械的分類、IP未存在時のエラー、空DNA
  でも生成できること、save/load往復、`ip_memory.json`が変更されないこと、
  Flask API層の入力バリデーション（空名・存在しないIP・不正な
  markdown/rules）を検証。

## 確認済み事項（CEO確認済み）
1. `style_guide.md`はプレーンなMarkdownテキストファイル（`file`コマンドで
   "Unicode text, UTF-8 text"、HTML等でラップしない）。
2. `prompt_rules.json`は`save_prompt_rules()`が常にalways/prefer/avoid/
   neverの4キーを埋めるため、保存後のJSONには必ずこの4キーが存在する
   （入力で一部キーが欠けていても空配列で補完されることをテストで確認）。
3. `style_guide.md`・`prompt_rules.json`保存の前後で`ip_memory.json`の
   SHA-256ハッシュが完全一致することを実際に確認済み（コード上も
   `creative_style_service.py`内に`save_ip`/`update_dna`の呼び出しは無い）。
4. AI失敗時（`OPENROUTER_API_KEY`未設定）も`generate_style_guide()`/
   `generate_prompt_rules()`いずれも`ok=True, source="template"`で
   テンプレート生成結果を返すことを確認済み（例外を投げない）。

## 動作確認結果
- Dashboard起動・IP Memoryタブ表示：OK（既存タブに回帰なし）
- 実ブラウザ操作でIP作成→DNA生成・保存→IP Bible生成・保存→
  「Generate Style Guide」（実際にOpenRouter APIを2回呼び出し）→
  Style Guide・Prompt Rulesの両方をプレビュー→「Save」→
  `style_guide.md`・`prompt_rules.json`が`ip_bible.md`と同じフォルダに
  正しく保存され、`ip_memory.json`は変更されないことを確認
- Generated Assets・References・Projectsタブ等：回帰なし
- `tests/`配下83件（Quest102の4件＋Quest103の9件＋Quest104の16件＋
  Quest105の11件＋Quest106の26件＋Quest107の17件）すべてpass

## 次のQuest候補
- Prompt Builder（既存`services/prompt_builder_service.py`）とprompt_rules.json
  の接続（画像生成プロンプトへ実際に反映する導線）
- Character Bible個別生成・World Bible個別生成
- Luna / Sol / Astra、Altair / Terraの実際のAgent分離
- 画像生成AI導入

## 今後のロードマップ
- Prompt Builder × Creative Style連携
- Character Bible / World Bible個別実装
- IP Team・Quality Teamの実Agent化
- 画像生成AI導入

---

# 最新状況（2026-07-08・Quest108：Prompt Builder v2）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 2：IP Intelligence → Production Phaseの開始**

## 完了Quest
Quest108まで完了。

## Quest108内容
`Reference → Reference Analysis（Quest103）→ IP Memory（Quest104）→
IP DNA → IP Bible（Quest105）→ Creative Style（Quest107）`で積み上げてきた
IPの知識を、画像生成AIへ渡すプロンプト文字列へ変換する「Prompt Builder
v2」を実装した。Production Phaseの開始となるQuest。

- `services/prompt_builder_v2.py`：新規。既存のPrompt Builder v1
  （`services/prompt_builder_service.py`、Quest98、Character Bible＝
  `outputs/character_bibles/`ベース）とは完全に独立した別モジュール
  （v1・Asset Generator・Image Generation Serviceには一切手を加えていない）。
  - `build_character_prompt()` / `build_style_prompt()` /
    `build_expression_prompt()` / `build_output_prompt()` — IP DNA・
    IP Bible・Style Guide・Reference Summary・Asset Typeからそれぞれの
    プロンプト断片を組み立てる（優先順位：IP DNA/Style Guide → IP Bible →
    Reference Summary → 汎用フォールバック、いずれも欠けていても例外を
    投げず動作継続する）
  - `merge_prompt()` — 4断片とCreative Style（Quest107）のPrompt Rules
    （always/prefer/avoid/never）を1つのプロンプト文字列に統合する
  - `build_prompt(project_id, ip_name=None, save=True)` — 上記すべてを
    統合するエントリポイント。ProjectはまだIP名を保存する仕組みが無い
    ため、ip_nameは任意引数（未指定でもReference Summary・Project
    Visionだけでプロンプトを組み立てる）
  - `save_prompt()` / `list_prompts()` / `load_prompt()` —
    `outputs/prompts/<project_id>/prompt_NNN.txt`への連番保存・一覧・読込
    （既存ファイルは上書きしない）
  - 画像生成AI（OpenAI / Google / Stability AI等）へは一切依存しない
    （Lean AI First、Prompt Builder自体もAIを呼ばない決定的な文字列組み立て）
- `dashboard_web/app.py`：
  - `POST /api/projects/build-prompt` — プロンプトを生成・保存（1回の
    実行で生成→保存→表示まで行うDashboard側のUXに合わせsave=Trueで呼ぶ）
  - `GET /api/projects/<project_id>/prompts` — 保存済みプロンプト一覧
- `dashboard_web/templates/index.html`：Projectsタブの各Project行に
  「④ プロンプト生成」ボタンを追加。クリックで生成・保存・内容表示までを
  1回の実行で完了する。
- `tests/test_quest108_prompt_builder.py`：新規（20件）。各サブビルダーの
  IP有無での分岐、merge_prompt()のルール統合、build_prompt()の
  IP有無両パターン・保存・Project未存在時のフォールバック、save/list/load
  の連番保存、Flask API層の入力バリデーションを検証。

## 動作確認結果
- Dashboard起動・Projectsタブ表示：OK（既存機能に回帰なし）
- 実ブラウザ操作で「④ プロンプト生成」を実行 → IP未紐づけのProjectでも
  Reference Summaryを取り込んだ空でないプロンプトが生成され、
  `outputs/prompts/<project_id>/prompt_001.txt`として保存、2回目実行で
  `prompt_002.txt`が連番作成されることを確認
- IP Memory・References等：回帰なし
- `tests/`配下103件（Quest102の4件＋Quest103の9件＋Quest104の16件＋
  Quest105の11件＋Quest106の26件＋Quest107の17件＋Quest108の20件）
  すべてpass

## commit / push
- commit hash：`a3c0374`（`feat: add prompt builder v2`）
- push：成功、origin/mainと同期済み
- `memory/meeting_quality_history.md`・`projects/`は今回も意図的にcommit
  対象外（CEO指示により継続）

## 次のQuest候補
- Prompt Builder v2で生成したプロンプトを実際に画像生成AIへ渡す導線
  （OpenAI / Google / Stability AI等、Quest108では未接続）
- ProjectとIP（ip_name）の紐付けを永続化する仕組み（現状は都度指定）
- Character Bible個別生成・World Bible個別生成
- Luna / Sol / Astra、Altair / Terraの実際のAgent分離

## 今後のロードマップ
- 画像生成AI導入（Prompt Builder v2の出力を実際に消費する）
- Project × IP Memoryの紐付け永続化
- Character Bible / World Bible個別実装
- IP Team・Quality Teamの実Agent化

---

# 最新状況（2026-07-08・Quest109：Image Generation Pipeline）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 2：IP Intelligence → Production Phase**

## 完了Quest
Quest109まで完了。

## Quest109内容
Quest108のPrompt Builder v2が保存した最新プロンプトを使い、実際に画像を
生成・保存し、DashboardでPreviewできるところまでをつなげた
（`Prompt → 画像生成 → 保存 → Dashboard表示`）。Production Phaseの中核
として、本Questでは画像生成AIの利用を許可した（Lean AI Firstの優先順位
は維持しつつ、AI未設定・失敗時は必ずPillowへフォールバックする設計）。

- `services/image_generation_pipeline.py`：新規。
  - `get_latest_prompt(project_id)` — Quest108の`list_prompts()`/
    `load_prompt()`をそのまま利用し、保存済み最新プロンプトを読み込む
    （Prompt Builder v2側には一切変更を加えていない）
  - `generate_images(project_id, asset_type="line_sticker", count=1)` —
    最新Prompt取得→画像生成→保存→`metadata.json`保存までを1回で行う。
    countは1〜3枚（`MAX_GENERATION_COUNT`定数、将来40枚へ拡張する場合も
    この定数を変えるだけで済む設計）。先頭1枚でAI画像生成
    （`OPENAI_API_KEY`設定時、`litellm.image_generation()`経由でDALL-E系
    モデル）を試行し、失敗したらバッチ全体をPillowフォールバック
    （既存の`services/image_generation_service.py`のrender_stamp_image()
    をそのまま再利用、Quest98実装への変更なし）へ切り替える（画像ごとの
    AI/Pillow混在を避けるため、切替はバッチ単位）
  - `list_generated_images(project_id, asset_type)` — 保存済み画像一覧・
    metadataを読み取り専用で返す
  - 保存先：`outputs/generated_assets/line_sticker/<project_id>/
    sticker_001.png ... metadata.json`（既存Asset Generator・Quest90〜97
    が使う`stamp_*.png`/`main.png`/`tab.png`/`metadata.md`とファイル名が
    衝突しないため同じディレクトリを安全に共用。1回の実行が「その時点の
    生成結果」を表し、`sticker_001.png`から毎回上書き保存する）
  - metadata.jsonの必須キー：project_id / asset_type / prompt_file /
    image_files / generated_at / generation_mode（"ai" or "fallback_pillow"）
- `dashboard_web/app.py`：
  - `POST /api/projects/generate-image` — 画像生成・保存を実行
  - `GET /api/projects/<project_id>/generated-images` — 生成済み画像・
    metadata一覧を返す
  - `GET /api/generated-assets/image/<path:filename>` — 画像配信
    （png限定、`outputs/generated_assets/`配下を広く対象にする汎用ルート。
    既存の`/generated-assets/line-sticker/<path:filename>`とは独立）
- `dashboard_web/templates/index.html`：Projectsタブの各Project行に
  枚数選択（1枚／2枚／3枚のプルダウン）＋「⑤ 画像生成」ボタンを追加。
  クリックで生成・保存・サムネイル表示までを1回の実行で完了する
  （生成方式＝AI生成／Pillowフォールバックのラベルも表示）。
- `tests/test_quest109_image_generation_pipeline.py`：新規（16件）。
  最新プロンプト読込、画像生成の呼び出し・ファイル保存・metadata.json
  保存（必須6キー）、count上限（999指定でも3枚に丸まる）・下限（0指定でも
  1枚）、プロンプト未生成時のエラー、Dashboard APIのバリデーション
  （不正project_id・画像一覧取得・png以外の配信拒否）を検証。

## 動作確認結果
- Dashboard起動・Projectsタブ表示：OK（既存機能に回帰なし）
- 実ブラウザ操作でProject 001に対し「④ プロンプト生成」→枚数を2枚に
  設定して「⑤ 画像生成」→`OPENAI_API_KEY`未設定のためPillow
  フォールバックが自動選択され、`sticker_001.png`/`sticker_002.png`が
  正しく保存されDashboard上にサムネイル表示されることを確認
- `GET /api/projects/001/generated-images`がmetadata.jsonの内容
  （generation_mode: fallback_pillow等）を正しく返すことを確認
- Generated Assets・IP Memory・Referencesタブ等：回帰なし
- `tests/`配下119件（Quest102〜108の103件＋Quest109の16件）すべてpass

## commit / push
- commit hash：`ef39900`（`feat: add image generation pipeline`）
- push：成功、origin/mainと同期済み
- `memory/meeting_quality_history.md`・`projects/`は今回も意図的にcommit
  対象外（CEO指示により継続）

## 次のQuest候補
- LINE Creators Market提出用ZIP化・Export Engine（Quest109では対象外、
  Quest111以降で実装予定）
- 実際のAI画像生成API（`OPENAI_API_KEY`）を設定した上での本番動作確認
- 40枚生成への拡張（`MAX_GENERATION_COUNT`の引き上げ）
- ProjectとIP（ip_name）の紐付け永続化
- Character Bible個別生成・World Bible個別生成

## 今後のロードマップ
- Export Engine（ZIP化、Quest111以降）
- 画像生成AIの本番接続確認・40枚生成対応
- Project × IP Memoryの紐付け永続化
- Character Bible / World Bible個別実装

---

# 最新状況（2026-07-08・Quest110：AI Review Engine）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 2：IP Intelligence → Production Phase**

## 完了Quest
Quest110まで完了。

## Quest110内容
Quest109で生成したLINEスタンプ画像を、必要な時だけAIレビューできる
仕組みを追加した。DAFのLean AI First方針における判定の優先順位
`Python Quality Check → Rule Engine → AI Review → CEO承認`を実装で
明示的に踏襲し、AIは「最後の専門家」として常時実行せず、CEOがDashboard
から手動で依頼した場合（またはPython Quality CheckがWARNING/FAILを
検出した場合）のみ実行する設計にした。

- `services/ai_review_engine.py`：新規。
  - `get_generated_images(project_id)` — Quest109の
    `image_generation_pipeline.list_generated_images()`へ委譲（読み取り
    専用）
  - `should_run_ai_review(manual_request, quality_report)` —
    manual_request=True、またはPython Quality CheckにWARNING/FAILが
    含まれる場合にTrueを返す判定関数
  - `review_images(project_id, ip_name=None, manual_request=True)` —
    生成画像一覧取得→metadata取得→Creative Style/IP Bible/Prompt参照→
    `services/quality_control_service.generate_quality_report()`
    （Quest106）を先に実行→レビュー対象判定→必要な画像だけAIレビュー→
    `review_report.json`保存、までを1回で行う
  - AIレビューはOpenRouter経由gpt-4o-mini（`OPENROUTER_API_KEY`、
    Quest103/105/107と同じ方針。Quest109の画像生成AI＝`OPENAI_API_KEY`
    とは別の鍵）で実施。未設定・呼び出し失敗時は例外を投げず
    `fallback_rule_review`（Python Quality Check・生成metadataに基づく
    決定的なルールベース簡易レビュー）へ自動フォールバックする
  - レビュー観点6項目：character_consistency / style_consistency /
    line_sticker_usability / text_readability / emotional_clarity /
    commercial_quality（各`{"score":1-5,"comment":str,"needs_fix":bool}`）
  - `save_review_report()` / `load_review_report()` —
    `outputs/reviews/<project_id>/review_report.json`への保存・読込
- `dashboard_web/app.py`：
  - `POST /api/projects/review-images` — レビュー実行（manual_request=True固定）
  - `GET /api/projects/<project_id>/review-report` — 保存済みレポート取得
- `dashboard_web/templates/index.html`：Projectsタブに「⑥ AIレビュー」
  ボタンを追加。overall_score・summary・needs_fixの有無・各画像の簡易
  コメントをDashboard上に表示する。
- `tests/test_quest110_ai_review_engine.py`：新規（18件）。
  should_run_ai_review()の判定分岐、review_report.jsonの保存、
  `OPENROUTER_API_KEY`未設定時のfallback_rule_review成功、review_mode
  記録、overall_score・items（6項目すべて含む）の返却、生成画像が無い
  場合の安全なエラー、Flask API層のバリデーションを検証。テスト実施中に
  `services/image_generation_service.py`が内部で使う`config.py`の
  import時`load_dotenv()`により、`os.environ.pop()`後もAPIキーが
  再読込されるケースを発見し、`review_images()`呼び出し直前に再度popする
  形でテスト分離を担保した（実運用への影響なし）。

## 動作確認結果
- Dashboard起動・Projectsタブ表示：OK（既存機能に回帰なし）
- 実ブラウザ操作でProject 001に対し「④ プロンプト生成」→「⑤ 画像生成」
  （2枚）→「⑥ AIレビュー」を実行 → 実際にOpenRouter経由でAIレビューが
  動作し、6項目のスコア・needs_fix・実ファイル名（sticker_001.png等）に
  基づく画像ごとのコメントがDashboardに正しく表示されることを確認
- `GET /api/projects/001/review-report`が保存済みレポート
  （review_mode: ai、overall_score: 4等）を正しく返すことを確認
- Generated Assets・IP Memory・Referencesタブ等：回帰なし
- `tests/`配下137件（Quest102〜109の119件＋Quest110の18件）すべてpass

## commit / push
- commit hash：`360a96e`（`feat: add AI review engine`）
- push：成功、origin/mainと同期済み
- `memory/meeting_quality_history.md`・`projects/`は今回も意図的にcommit
  対象外（CEO指示により継続）

## 次のQuest候補
- CEOがAIレビュー結果（needs_fix）を踏まえて承認・却下する導線
  （CEO Decision Centerとの連携）
- LINE Creators Market提出用ZIP化・Export Engine（Quest111以降）
- 画像修正・再生成フロー（Quest110では対象外、レビューのみ）
- Project × IP Memoryの紐付け永続化

## 今後のロードマップ
- AIレビュー結果 × CEO承認フローの接続
- Export Engine（ZIP化、Quest111以降）
- 画像修正・再生成フロー
- Project × IP Memoryの紐付け永続化

---

# 最新状況（2026-07-08・Quest111：Export Engine）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 2：IP Intelligence → Production Phase**

## 完了Quest
Quest111まで完了。

## Quest111内容
Production Pipeline（`Prompt → Image Generation → AI Review → CEO確認`）の
最終段として、生成済み画像をLINE Creators Market提出形式へ変換する
Export Engineを追加した。実際の申請（アップロード）は行わず、ローカルに
提出用package・ZIP・レポートを作るところまで。

- `services/export_engine.py`：新規。
  - `BaseExportAdapter` / `LineExportAdapter` — プラットフォーム固有の
    検証・構成ルールをAdapterに閉じ込める設計。Export Engine本体
    （`export_project()`等）は`validate()` / `build_package()`という
    共通インターフェースだけを呼び、LINE専用ロジックは一切書かない。
    `_EXPORT_ADAPTERS`辞書にAdapterを追加するだけで、将来
    `LINE → Discord → Telegram → WhatsApp`等へ拡張できる。
  - `LineExportAdapter`：画像存在・PNG形式・サイズ一致・画像枚数
    （LINE Creators Marketの目安8〜40枚、Quest109時点は最大3枚生成の
    ため今後拡張予定として警告扱い）・main.png/tab.png存在をチェック。
    main.png/tab.pngが未生成の場合はエラーにせず、Export時に
    `services/image_generation_service.render_icon_image()`
    （Quest98、無変更）でその場自動生成する。
  - `check_export_readiness()` — Export前チェックを行いREADY判定を返す
    （保存はしない）
  - `build_export_package()` — `outputs/exports/<project_id>/package/`
    （stickers/・main.png・tab.png・metadata.json）を作成
  - `create_export_zip()` — packageの中身を`line_stickers.zip`へZIP化
  - `generate_export_report()` / `export_project()` — Export Report
    保存、および生成画像取得〜Export Report保存までを1回で行う
    エントリポイント
  - `load_export_report()` — 保存済みexport_report.jsonの読込
- `dashboard_web/app.py`：
  - `POST /api/projects/export` — Export実行（package作成・ZIP化・
    レポート保存）
  - `GET /api/projects/<project_id>/export-report` — 保存済みレポート取得
  - `GET /api/projects/<project_id>/download-export` — ZIPダウンロード
    （export_report.jsonのzip_fileを参照して配信、ファイル名ハードコード
    無し）
- `dashboard_web/templates/index.html`：Projectsタブに「⑦ Export」
  ボタンを追加。READY/NOT READY・errors・warnings・ダウンロードリンクを
  Dashboard上に表示する。
- `tests/test_quest111_export_engine.py`：新規（17件）。ZIP生成
  （main.png/tab.png/metadata.json/stickers/*を含むことを確認）、
  metadata.json・export_report.jsonの必須キー、READY判定（画像0枚は
  false、有効なPNGはtrue）、package作成→ZIP作成の順序依存、
  LineExportAdapterの基本情報、Flask API層のバリデーション
  （不正project_id・画像不足エラー・未Export時の404）を検証。

## 動作確認結果
- Dashboard起動・Projectsタブ表示：OK（既存機能に回帰なし）
- 実ブラウザ操作でProject 001に対し「④ プロンプト生成」→「⑤ 画像生成」
  （2枚）→「⑦ Export」を実行 → `package/`（stickers/sticker_001.png・
  sticker_002.png・main.png・tab.png・metadata.json）と
  `line_stickers.zip`が正しく生成され、Dashboard上にREADY表示・警告・
  ダウンロードリンクが表示されることを確認
- ダウンロードリンクから実際に`line_stickers.zip`を取得し、`unzip -l`で
  中身（5ファイル）が仕様通りであることを確認
- `GET /api/projects/001/export-report`が保存済みレポートを正しく
  返すことを確認
- Generated Assets・IP Memory・Referencesタブ等：回帰なし
- `tests/`配下154件（Quest102〜110の137件＋Quest111の17件）すべてpass

## commit / push
- commit hash：`abfb646`（`feat: add export engine`）
- push：成功、origin/mainと同期済み
- `memory/meeting_quality_history.md`・`projects/`は今回も意図的にcommit
  対象外（CEO指示により継続）

## 次のQuest候補
- 実際にLINE Creators Marketへ提出するフロー（申請自体はQuest111時点で
  未実装、方針として意図的に対象外）
- Discord / Telegram / WhatsApp向けExport Adapterの追加
  （`_EXPORT_ADAPTERS`への登録のみで対応可能な設計）
- CEOがAIレビュー結果を踏まえて承認・却下する導線
  （CEO Decision Centerとの連携）
- 40枚生成への拡張（Quest109の`MAX_GENERATION_COUNT`引き上げ）

## 今後のロードマップ
- 複数プラットフォームExport Adapter追加
- AIレビュー結果 × CEO承認フローの接続
- 40枚生成対応・画像生成AIの本番接続確認
- Project × IP Memoryの紐付け永続化

---

# 最新状況（2026-07-08・Quest112：CEO Production Dashboard）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 2：IP Intelligence → Production Phase**

## 完了Quest
Quest112まで完了。

## Quest112内容
Quest108〜111でProduction Pipeline（`Prompt生成 → 画像生成 → AIレビュー →
Export`）自体は完成していたが、Dashboard上は開発者向けの個別ボタンが
並ぶだけで、CEOが「今どこまで進んでいて、次に何をすればいいか」を一目で
把握できなかった。Quest112でProjectsタブへCEO向けのProduction Step UIを
追加した。新しい状態は一切保存せず、既存Service（Quest104〜111）の
保存済みデータを都度読み直して判定するだけの、完全にread-onlyな追加。

- `services/production_status_service.py`：新規。
  - `get_production_status(project_id, ip_name=None)` — 7ステップ
    （① キャラクターの特徴を作る／② 設定資料を作る／③ 描き方を作る／
    ④ プロンプト生成／⑤ 画像生成／⑥ AIレビュー／⑦ 提出用ZIP作成）の
    状態（pending＝未実行／done＝完了／needs_review＝要確認／
    error＝エラー）・現在の状態サマリー・次のおすすめAction・提出準備
    完了フラグ（ready_for_submission）を返す
  - ①②③（IP DNA/IP Bible/Style Guide）はProjectとIPを紐づける仕組みが
    まだ無いため（Quest108〜111と同じ制約）、ip_name未指定時は
    「未実行」表示のまま次のおすすめAction算出からは除外する（Quest108の
    「IPが無くてもPrompt Builder v2は動作継続する」設計と矛盾させない
    ため。ip_nameを明示的に渡した場合は通常通り判定対象になる）
  - AIレビューが要確認（needs_fix）でも、Exportが完了していれば
    `ready_for_submission: true`とする（Quest111の「Exportはブロック
    しない」設計と整合。current_statusには引き続き要確認の旨を表示し、
    CEOの見落としを防ぐ）
  - 各ステップの確認は個別にtry/exceptで守られ、1つの確認に失敗しても
    他のステップ・DAF OS全体には影響しない
- `dashboard_web/app.py`：`GET /api/projects/<project_id>/production-status`
  を追加（ip_name・asset_typeはクエリパラメータで任意指定可）
- `dashboard_web/templates/index.html`：Projectsタブに
  「📊 進行状況を見る」ボタンを追加。7ステップの状態一覧・現在の状態・
  次にやること・提出準備の有無をカードで表示する。あわせて「⑦ Export」
  ボタンを「⑦ 提出用ZIP作成」へ改名（CEO向け日本語表現に統一する例示に
  該当するため）。IP Memory・Generated Assetsタブの既存ボタン表記は
  今回の主目的（Projectsタブの整理）の範囲外として変更していない。
- `tests/test_quest112_ceo_production_dashboard.py`：新規（11件）。
  7ステップすべてが返ること、next_actionが返ること、未実行Projectでも
  安全に動作すること（全ステップpending、current_status="まだ何も
  実行されていません"）、プロンプト生成後にpromptステップがdoneになる
  こと、画像生成後にimage_generationステップがdoneになりcurrent_status/
  next_actionが指示書の例（「画像生成まで完了」「AIレビューを実行して
  ください」）と完全一致すること、Export後にready_for_submissionが
  trueになること、ip_name指定時に①②③がdoneになること、ip_name未指定時に
  ①②③がNext Actionをブロックしないこと、Flask APIのバリデーションを検証。

## 動作確認結果
- Dashboard起動・Projectsタブ表示：OK（既存機能に回帰なし）
- 実ブラウザ操作でProject 001に対し「📊 進行状況を見る」を実行 →
  7ステップ・現在の状態・次にやること・提出準備の有無が正しく日本語で
  表示されることを確認
- 「④ プロンプト生成」→「⑤ 画像生成」と進めるたびに、進行状況の表示が
  「画像生成まで完了」「次にやること：AIレビューを実行してください」と
  指示書の例通りに更新されることを確認
- 「⑦ Export」→「⑦ 提出用ZIP作成」への改名後も既存のExport機能は
  問題なく動作することを確認
- Generated Assets・IP Memory・Referencesタブ等：回帰なし
- `tests/`配下165件（Quest102〜111の154件＋Quest112の11件）すべてpass

## commit / push
- commit hash：`affe417`（`feat: add CEO production dashboard`）
- push：成功、origin/mainと同期済み
- `memory/meeting_quality_history.md`・`projects/`は今回も意図的にcommit
  対象外（CEO指示により継続）

## 次のQuest候補
- One-Click Production Flow（「LINEスタンプを作る」ボタンで
  Prompt→画像生成→AIレビュー→Exportまで自動実行、Quest112では意図的に
  対象外）
- Project × IP Memoryの紐付け永続化（①②③を毎回ip_name指定せずに
  判定できるようにする）
- CEOがAIレビュー結果を踏まえて承認・却下する導線
- 複数プラットフォームExport Adapter追加

## 今後のロードマップ
- One-Click Production Flow（Quest113）
- Project × IP Memoryの紐付け永続化
- AIレビュー結果 × CEO承認フローの接続
- 複数プラットフォームExport Adapter追加

---

# 最新状況（2026-07-08・Quest113：One-Click Production Flow）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 2：Production Phase**

## 完了Quest
Quest113まで完了。

## Quest113内容
CEOが細かい工程を意識せず、「LINEスタンプを作る」ボタンを押すだけでAI社員が
制作工程を最後まで実行できるようにした。Quest108〜111で完成済みの
Production Pipeline（`Prompt Builder v2 → Image Generation Pipeline →
AI Review Engine → Export Engine`）を、新しい処理を書かずにそのまま
順番に呼び出すオーケストレーション層（Production Orchestrator＝AI社員の
現場監督＝COO）を追加した。

- `services/production_orchestrator.py`：新規。
  - `run_production(project_id, ip_name=None, asset_type=..., count=..., platform=...)` —
    ④プロンプト生成→⑤画像生成→⑥AIレビュー→⑦Exportを1回で実行する。
    各ステップはQuest108〜111の既存関数（`build_prompt()` /
    `generate_images()` / `review_images()` / `export_project()`）を
    そのまま呼ぶだけで、既存Serviceの実装・責務は一切変更していない。
  - いずれかのステップが失敗（`ok=False`または想定外の例外）した場合は
    その時点で停止し、後続のステップは実行しない。`failed_step`（どの
    ステップで止まったか）と`error`（理由）をレポートに記録する。
  - AIレビューで要確認（needs_fix）が出ても停止しない（Quest111の
    Export Engineの「Exportはブロックしない」設計を踏襲）。ただし
    `review_needs_fix`フラグを立て、Dashboard表示でCEOの見落としを
    防ぐ。
  - `save_production_report()` / `load_production_report()` —
    `outputs/production_reports/<project_id>/production_report.json`
    への保存・読み込み。
- `dashboard_web/app.py`：
  - `POST /api/projects/run-production` — Production Orchestratorを呼び、
    1クリックで最後まで実行する（Projectsタブの「🚀 LINEスタンプを
    作る」ボタンから呼ばれる）。
  - `GET /api/projects/<project_id>/production-report` — 保存済み
    production_report.jsonを返す。
- `dashboard_web/templates/index.html`：Projectsタブに
  「🚀 LINEスタンプを作る」ボタンを追加。実行完了後、生成画像枚数・
  レビュー結果（要確認の有無）・ZIP生成状況・次にやること・ダウンロード
  リンクをカード表示する。失敗時は失敗ステップと理由を表示する。
- `tests/test_quest113_production_orchestrator.py`：新規（13件）。
  正常系（4ステップすべて完了・production_report.json生成・
  next_actionが「LINE Creators Marketへ提出してください」）、異常系
  （途中ステップを強制失敗させ、そこで停止し後続ステップが実行されない
  こと・failed_step/errorが記録されること）、Flask APIのバリデーション
  を検証。

## 動作確認結果
- Dashboard起動・Projectsタブ表示：OK（既存機能に回帰なし）
- 実ブラウザ操作でProject 002に対し「🚀 LINEスタンプを作る」を実行 →
  ボタンが「⏳ 制作中...」に変わり、完了後に元のラベルへ戻ることを確認
- 完了後、Dashboard上に次の内容が表示されることを確認：
  「🚀 LINEスタンプ制作が完了しました（Project 002）／生成画像：3枚／
  レビュー：完了（⚠️ 要確認あり）／ZIP：生成済み（line_stickers.zip）／
  次にやること：LINE Creators Marketへ提出してください」
- `outputs/production_reports/002/production_report.json`が実際に
  生成され、`completed_steps`に4ステップすべてが記録されていることを
  確認
- `tests/`配下178件（Quest102〜112の165件＋Quest113の13件）すべてpass

## commit / push
- commit hash：`3f2a65e`（`feat: add one-click production flow`）
- push：成功、origin/mainと同期済み
- `memory/meeting_quality_history.md`・`projects/`は今回も意図的にcommit
  対象外（CEO指示により継続）

## 次のQuest候補
- Project × IP Memoryの紐付け永続化（①②③を毎回ip_name指定せずに
  判定できるようにする）
- CEOがAIレビュー結果を踏まえて承認・却下する導線
- 複数プラットフォームExport Adapter追加
- 実際にLINE Creators Marketへ提出するフロー（申請自体は対象外を継続）

## 今後のロードマップ
- Project × IP Memoryの紐付け永続化
- AIレビュー結果 × CEO承認フローの接続
- 複数プラットフォームExport Adapter追加
- 40枚生成対応・画像生成AIの本番接続確認

---

# 最新状況（2026-07-09・Quest114：Minimal DAF / Dashboard Cleanup Sprint）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 2：Production Phase**

## 完了Quest
Quest114まで完了。

## Quest114内容
Quest113まででLINEスタンプ制作の主要機能は一通り完成したため、今回は
新機能追加ではなく「Minimal DAF / Less UI, More Decisions.」をテーマに、
CEOが迷わず使えるようDashboardを断捨離・整理した。Production Pipeline
自体のロジック（`prompt_builder_v2.py` / `image_generation_pipeline.py` /
`ai_review_engine.py` / `export_engine.py` / `production_orchestrator.py`）
・`dashboard_web/app.py`（API）は一切変更していない。

変更ファイル：
- `dashboard_web/templates/index.html`
- `dashboard_web/static/style.css`

判断基準（毎日使う→残す／CEOが理解しにくい→名前変更／役割が重複→統合／
今使わない→非表示）に沿って、以下を実施した。

- **ProjectsタブをCEO向けに整理**：ID／Asset Type／Created At列を廃止し、
  Project名の下にID・種類を小さく添える形へ統合。CEO向けに残す操作は
  「🚀 LINEスタンプを作る」「📊 進行状況を見る」「⬇ ZIPダウンロード」
  （Exportが完了しているProjectのみ表示）「アーカイブ」（目立たない
  テキストリンク）に絞った。
- **開発者向け操作の折りたたみ**：Generate Assets／④プロンプト生成／
  ⑤画像生成／⑥AIレビュー／⑦提出用ZIP作成は、Project行内の
  `<details>`「🔧 詳細操作を表示（開発者向け）」に収納し、CEO通常画面
  では非表示にした。ボタン自体・呼び出すAPIは変更していない。
- **旧v1系パイプラインの退避**：ダッシュボードタブの「🚀 スタンプを
  作る」（Quest96・Character Bibleベースの旧パイプライン）は、
  「🔧 旧機能 / Developer Mode（旧スタンプ生成パイプライン）」として
  折りたたみ・初期非表示にし、ボタン名も「旧スタンプ生成（Developer）」
  に変更した。現在の推奨導線（Projectsタブの🚀 LINEスタンプを作る）と
  誤って混同しないようにした。
- **🚀ボタンの意味を整理**：CEO画面で主役の🚀は「🚀 LINEスタンプを
  作る」の1つのみとし、「🚀 実装開始」→「実装プロンプトを作成」、
  「🚀 このIssueを実装」→「Issue実装プロンプトを作成」に文言変更した
  （承認センターの実装準備フローは非表示にはせず、🚀の意味の混同のみ
  解消）。
- **日本語UIへの統一**：タブ名（Generated Assets→生成物／
  Notifications→通知／References→参考画像／IP Memory→キャラクター
  管理）、ボタン（Create→作成／Upload→アップロード／Archive→
  アーカイブ）、New Projectフォームのラベル、CEO Homeタイルの表記等を
  日本語化した。
- **結果表示にProject IDを明記**：④〜⑦・📊・🚀の各結果パネルの
  タイトル・エラーメッセージの両方に「Project ${id} の制作結果」の
  形式でProject IDを含めるよう統一した（従来はエラー時のみProject ID
  が欠けているケースがあった）。

## 動作確認結果
- Dashboard起動・ダッシュボードタブ／プロジェクトタブ表示：OK
- ダッシュボードタブで「🔧 旧機能 / Developer Mode」が折りたたみ状態
  で表示され、展開すると「🏭 DAF 制御盤（旧UI）」「旧スタンプ生成
  （Developer）」ボタンが確認できることを確認
- プロジェクトタブでProject行が「プロジェクト／状態／次にやること／
  操作」の4列に整理され、🚀／📊／⬇ ZIPダウンロード（該当Projectの
  み）／「🔧 詳細操作を表示（開発者向け）」／アーカイブが表示される
  ことを確認。「🔧 詳細操作を表示」展開で④〜⑦・枚数選択が現れ、通常時
  は非表示であることを確認
- Project 002で「🚀 LINEスタンプを作る」を実行し、結果パネルに
  「Project 002 の制作結果（🚀 LINEスタンプ制作 完了）」と表示される
  ことを確認
- `tests/`配下178件（Quest102〜113）すべてpass（バックエンドAPI・
  ロジックは無変更のためテスト追加なし）

## commit / push
- commit①：`cf242d0`（`feat: simplify dashboard for CEO workflow`）
- commit②：`docs: update handover after quest114`（本コミット）
- push：成功、origin/mainと同期済み
- `memory/meeting_quality_history.md`・`projects/`は今回も意図的にcommit
  対象外（CEO指示により継続）

## 次のQuest候補
- Quest115：DAFをLINEスタンプ専用ではなく、Digital Asset Factoryとして
  汎用Productionへ昇格させる（asset_type=line_sticker前提の実装
  ・UI表記を、youtube_short／ios_app等の他Asset Typeにも耐えられる形へ
  拡張）
- Project × IP Memoryの紐付け永続化（①②③を毎回ip_name指定せずに
  判定できるようにする）
- CEOがAIレビュー結果を踏まえて承認・却下する導線
- 複数プラットフォームExport Adapter追加

## 今後のロードマップ
- Quest115：汎用Productionへの昇格（Digital Asset Factory化）
- Project × IP Memoryの紐付け永続化
- AIレビュー結果 × CEO承認フローの接続
- 複数プラットフォームExport Adapter追加

---

# 最新状況（2026-07-09・Quest115：Universal Production / 汎用Production Factory化）

## 現在地
- **DAF OS v2**
- **Chapter 2：AI Company Phase**
- **Sprint 2：Production Phase**

## 完了Quest
Quest115まで完了。

## Quest115内容
DAF OSは`Digital Asset Factory`であり、LINEスタンプ専用ツールではないという
設計原則を明文化し、Quest108〜113で構築したProduction Pipelineを
「LINEスタンプ専用」から「Digital Asset共通のProduction」へ概念・UI・
Report構造の面で昇格させた。テーマは「Universal Production — Digital
Asset Factory, not LINE Sticker Factory.」。既存Production Pipeline本体
（Prompt Builder v2 / Image Generation Pipeline / AI Review Engine /
Export Engine）は無変更。設計原則として

```
Project → Asset Type → Production → Export Adapter
```

を採用し、line_stickerは現在対応済みのAsset Typeの1つ、その他
（youtube_short／ios_app等）は準備中のAsset Typeとして扱う。

変更ファイル：
- `services/production_orchestrator.py`
- `dashboard_web/app.py`
- `dashboard_web/templates/index.html`
- `tests/test_quest115_universal_production.py`（新規）

- **Production Orchestratorの汎用化**：`run_production()`の`asset_type`
  引数を`None`許容にし、未指定時はProject情報
  （`services/project_service.list_projects`）から自動取得する
  （`_resolve_asset_type()`）。Project未存在時は従来通り`line_sticker`へ
  フォールバックするため、既存Quest113テストの挙動は変わらない。
  `SUPPORTED_PRODUCTION_ASSET_TYPES = {"line_sticker": "LINEスタンプ"}`を
  新設し、未対応のAsset Typeはどのステップも実行せず
  `{"ok": false, "status": "unsupported_asset_type", "message": "この
  種類の制作フローは現在準備中です。", "asset_type": "...",
  "asset_type_label": "..."}`を安全に返す（production_report.jsonへの
  保存も行わない＝実行していない工程のレポートは残さない）。
  `ASSET_TYPE_LABELS`にProject作成フォームの全種類
  （line_sticker/youtube_short/blog/ebook/ios_app/saas/generic）分の
  CEO向け日本語表示名を持たせた。Export Adapter切り替えの思想
  （line_sticker→LineExportAdapter実装済み、wallpaper／icon→将来の
  Adapter）はコード・コメントで明示したが、`export_engine.py`自体は
  今回変更していない（Production Pipelineの中核ロジックを壊さない
  方針のため、Asset Type軸のAdapter切り替えは将来のQuestで対応）。
- **`dashboard_web/app.py`**：`/api/projects/run-production`が
  asset_typeを強制せず、未指定時はOrchestrator側の自動解決に委ねる
  ように修正。
- **`dashboard_web/templates/index.html`**：Projectsタブの主ボタンを
  「🚀 LINEスタンプを作る」から「🚀 このProjectを制作する」へ変更。
  完了メッセージも「Project ${id} の制作が完了しました」＋「種類：
  ${asset_type_label}」という汎用形式にし、未対応Asset Typeの場合は
  エラー扱いにせず「🚧 この種類の制作フローは現在準備中です。」と
  表示する。Project行にも「種類：LINEスタンプ」「種類：YouTube
  Short（制作フロー準備中）」のように表示するASSET_TYPE_LABELS・
  SUPPORTED_PRODUCTION_ASSET_TYPESをJS側にも追加（バックエンドの
  定義と対応させている）。旧パイプライン（Developer Mode内）の文言も
  あわせて更新。
- `tests/test_quest115_universal_production.py`：新規（15件）。
  line_stickerが従来通りProduction成功すること、production_reportに
  asset_type/asset_type_labelが記録されること、未対応asset_typeが
  安全に失敗しレポートを残さないこと、Project情報からのasset_type
  自動解決、Flask APIレベルの検証、Dashboardの主ボタン文言変更を確認。

## 動作確認結果
- Dashboard起動・プロジェクトタブ表示：OK（既存機能に回帰なし）
- 主ボタンが全Project行で「🚀 このProjectを制作する」に統一され、
  各行に「種類：LINEスタンプ」が表示されることを確認
- Asset Type「youtube_short」の新規Projectを作成し、行に「種類：
  YouTube Short（制作フロー準備中）」と表示されることを確認
- そのProjectで「🚀 このProjectを制作する」を実行 →
  「Project 008 の制作結果／種類：YouTube Short／🚧 この種類の
  制作フローは現在準備中です。」と安全に表示され、DAF OS全体には
  影響がないことを確認
- Project 002（line_sticker）で従来通り実行 → 「Project 002 の
  制作結果／Project 002 の制作が完了しました／種類：LINEスタンプ／
  生成画像：3枚／…」と表示されることを確認
- `outputs/production_reports/002/production_report.json`に
  `"asset_type": "line_sticker"`・`"asset_type_label": "LINEスタンプ"`
  が記録されていることを確認
- `tests/`配下193件（Quest102〜114の178件＋Quest115の15件）すべてpass

## commit / push
- commit hash：`ceaf393`（`feat: generalize production for asset types`）
- push：成功、origin/mainと同期済み
- `memory/meeting_quality_history.md`・`projects/`は今回も意図的にcommit
  対象外（CEO指示により継続）

## 次のQuest候補
- wallpaper／icon等、line_sticker以外のAsset Typeの実際のProduction
  実装（Image Generation・Export Adapterの拡張）
- Export Adapter軸をplatformからAsset Typeベースへ整理する将来設計の
  具体化
- Project × IP Memoryの紐付け永続化（①②③を毎回ip_name指定せずに
  判定できるようにする）
- CEOがAIレビュー結果を踏まえて承認・却下する導線

## 今後のロードマップ
- 複数Asset Type（wallpaper／icon等）の実Production対応
- Export Adapterの複数プラットフォーム・複数Asset Type対応
- Project × IP Memoryの紐付け永続化
- AIレビュー結果 × CEO承認フローの接続
