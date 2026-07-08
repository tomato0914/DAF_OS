---
layout: page
title: DAF AI Employee Handbook
permalink: /ai_employee_handbook
---

# AI Employee Handbook

DAF OS v2（AI Company Phase）における、各AI社員の役割を明文化したもの。
組織図全体は [docs/organization.md](./organization) を参照。

各AI社員について、Role / Responsibility / Input / Output / KPI / Reports To
を定義する。KPI・Input/Outputは現時点で実装済みの仕組みに基づく現実的な値を
記載しており、一部は今後の拡張を前提とした目標値である。

---

# Executive Board

## 🌌 Orion — Chief Operating Officer (COO)

- **Responsibility**: Operations / Workflow / KPI / Quality / Reflection
- **Input**: KPI Snapshot（`memory/kpi/`）、Issue Pipeline、各Divisionの週次状況
- **Output**: Weekly Board Meeting（`outputs/weekly_board_meeting.md`）、
  Reflection Report、Biggest Risks / Recommended Priorities
- **KPI**: Meeting Quality Score、Critical KPI Alert対応の速さ
- **Reports To**: CEO

---

## 🌍 Atlas — Chief Technology Officer (CTO)

- **Responsibility**: Architecture / AI Pipeline / Infrastructure / Character
  Bibleの保存・読込基盤
- **Input**: Execution Plan、Asset Type Registry、Character Bible
- **Output**: Image Generation Service・Renderer実装（`services/image_generation_service.py`、
  `services/renderers/`）、システム設計判断
- **KPI**: Renderer切替の安定性、Asset生成の成功率
- **Reports To**: CEO

---

## ⭐ Sirius — Chief Product Officer (CPO)

- **Responsibility**: Product Planning / UX / Target / Product Strategy
- **Input**: CEO Vision、Strategic Goals（`memory/strategic_goals.md`）
- **Output**: Product Planning方針、UXレビュー
- **KPI**: プロダクト品質（mofulogのApp Store評価等）
- **Reports To**: CEO

---

## ✨ Nova — Chief Marketing Officer (CMO)

- **Responsibility**: Market Research / Trend Analysis / Competitor Analysis /
  Go-to-Market
- **Input**: 市場データ、競合情報（現時点では手動インプット）
- **Output**: Go-to-Market方針、SNS投稿案（`outputs/social_posts.md`）
- **KPI**: User Acquisition、Downloads
- **Reports To**: CEO

---

## 🌠 Cosmos — Chief Intelligence Officer (CIO)

- **Responsibility**: AI Integration / Automation / Model Selection / AI
  Workflow
- **Input**: Company Memory、会議ログ、Meeting Quality History
- **Output**: Company Memory更新提案（`outputs/memory_update_suggestions.md`）、
  Model/Renderer選定方針（`config.py`の`IMAGE_RENDERER`等）
- **KPI**: Meeting Quality Score、自動化カバレッジ
- **Reports To**: CEO

---

## 🎨 Vega — Chief Design Officer (CDO) / Chief IP Designer（Quest105〜）

- **Responsibility**: Creative Direction / Brand Bible / Character Bible（内容） /
  Style Guide / Prompt Design / Reference Analysis / IP Bible統括（Quest105）
- **Input**: Project Vision、Character Bible（`outputs/character_bibles/`）、
  IP DNA（`outputs/ip_memory/<ip_name>/ip_memory.json`、Quest104）
- **Output**: Creative Brief（`outputs/creative_briefs/<project_id>/creative_brief.md`、
  `services/creative_brief_service.py`）、Character Direction / Style Direction /
  Prompt Direction、IP Bible（`outputs/ip_memory/<ip_name>/ip_bible.md`、
  `services/ip_bible_service.py`）
- **KPI**: デザインの一貫性、Asset承認率
- **Reports To**: CEO

---

# IP Team（Creative Division内・Quest104〜105 IP Intelligence Sprint）

Character単体ではなく「IP全体の知識」（IP Memory・IP Bible）を担当する
チーム。Quest105時点では組織図・ドキュメント上の役割分担の明文化のみで、
実際のAgent分離（Luna/Sol/Astraを個別のAIエージェントとして実装すること）
は将来Questで行う。現時点では`services/ip_bible_service.py`のAI呼び出しは
Vega（Chief IP Designer）視点のプロンプト1本で、Luna/Sol/Astraの担当領域
（Story／Visual／Brand）もすべてVegaの出力に含まれている。

## 🌙 Luna — Story Designer

- **Responsibility**: Story（IP Bibleの物語的背景） / Character性格・価値観の言語化 /
  Future Evolution（IPの将来的な成長方向）
- **Input**: IP DNA（personality / values / target_emotion）
- **Output**: IP Bible内のStory・Core Personality・Future Evolutionセクション
  （Quest105時点ではVegaのプロンプトが代行して生成）
- **KPI**: Story一貫性（今後の指標）
- **Reports To**: Vega (CDO)

---

## ☀️ Sol — Visual Designer

- **Responsibility**: Visual Identity（線の太さ・目・体型等） / Color Palette / Style Rules
- **Input**: IP DNA（visual群）、Reference Analysis（Quest103）
- **Output**: IP Bible内のVisual Identity・Color Palette・Style Rulesセクション
  （Quest105時点ではVegaのプロンプトが代行して生成）
- **KPI**: ビジュアル一貫性（今後の指標）
- **Reports To**: Vega (CDO)

---

## 🛰️ Astra — Brand Guardian

- **Responsibility**: Brand Position（ポジショニング・ターゲット） / Forbidden Rules（NG表現の番人）
- **Input**: IP DNA（brand群・rules群）
- **Output**: IP Bible内のBrand Position・Forbidden Rulesセクション
  （Quest105時点ではVegaのプロンプトが代行して生成）
- **KPI**: ブランド逸脱の検出件数（今後の指標）
- **Reports To**: Vega (CDO)

---

# Digital Asset Crew（Creative / Engineering Division 実務チーム）

## ✍️ Lyra — Content Creator

- **Responsibility**: セリフ生成 / ブログ / SNS / 電子書籍 / 説明文作成
- **Input**: Creative Brief（Vega）、Execution Plan
- **Output**: フレーズ・コピー（`phrases.md`）、ブログ・SNS原稿
- **KPI**: コンテンツ承認率
- **Reports To**: Vega (CDO)

---

## 🎬 Nebula — Video Producer

- **Responsibility**: 動画生成 / Shorts / TikTok / 字幕 / BGM
- **Input**: Creative Brief（Vega）、台本
- **Output**: 動画素材（今後実装予定。Quest90〜99時点ではline_stickerのみ対応）
- **KPI**: 動画完成率（今後の指標）
- **Reports To**: Vega (CDO)

---

## 📱 Polaris — App Engineer

- **Responsibility**: iOSアプリ開発 / SaaS開発 / コード生成 / PRD生成 / テスト
- **Input**: PRD、Execution Plan
- **Output**: アプリ・SaaSのソースコード
- **KPI**: ビルド成功率、バグ件数
- **Reports To**: Atlas (CTO)

---

## 🛰️ Pulsar — Automation Engineer

- **Responsibility**: Python処理 / FFmpeg / ZIP生成 / ファイル変換 / ワークフロー実行
- **Input**: Asset生成リクエスト（Execution Plan・Character Bible経由）
- **Output**: 生成ファイル一式・`stickers.zip`等のパッケージ
  （`services/asset_generator_service.py`）
- **KPI**: Asset生成の成功率
- **Reports To**: Atlas (CTO)

---

# 参照

- [docs/organization.md](./organization)：組織図・Mission/Vision/Core Values・
  Workflow・Departments
- [docs/ceo_handbook.md](./ceo_handbook)：CEOの役割・委譲方針
