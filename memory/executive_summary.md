# 経営サマリー（Executive Summary）

AI社員が「今の会社状況・最重要課題」を一枚で把握するための記録です。
他のmemoryファイルと内容が矛盾する場合は、このファイルの記述を最優先の事実として扱ってください。
CEOが状況の変化に応じて随時更新してください。

---

## 会社全体の状況

- DAF（Digital Asset Factory）は現在Phase3「Company Memory」に取り組み中
- 会社の価値観・CEOの好み・過去の学びに加え、プロダクトの現状・完了済みIssueもAI社員が会議で参照できるようになった（Quest50〜53）
- 日次の公開準備バッチ（`run_launch_crew` / `./run_daf.sh`）と、CEOが自由に相談できるMeeting Crew（`run_meeting_crew` / Dashboardの「💬 DAFに相談」）が分離済み（Quest55）

## mofulog

- 初めて犬を飼った人のためのペット管理アプリ
- 現状：App Store審査待ち
- セキュリティテスト・法的リスク確認は完了済み（`memory/completed_issues.md`参照）

## DAF_OS

- AI社員が経営会議・Issue管理・実装準備を自動化する社内運用ツール
- Company Memory（Quest50〜54）・AI経営会議UI（Quest52）・Meeting Crew（Quest55）が稼働中

## 最重要課題

- GitHub Open Issuesが10件、対応待ちの状態（`outputs/dashboard.md`時点）
- 承認センターに承認待ちアイテムが4件ある
- 未完了Issue #90 / #122 / #123 が残っている。`gh` CLIが環境に未導入のため中身・ステータスは未確認のまま（`docs/session_handover.md`参照）。次回セッションで`gh` CLI導入または GitHub上での直接確認が必要
- OpenRouterの残高不足で自動化が一時停止した実績がある。運転資金（API残高）の監視が今後の課題

---

## 更新ルール

- 状況が変わったら（Issue解消、App Store審査通過など）このファイルを直接編集する
- 自動では更新されない（MVPのため手動運用）
