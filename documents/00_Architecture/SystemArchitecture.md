# System Architecture (システム全体構成) - 統合案

- 対象: kabuステーション API と J-Quants Standard プランを用いた日本株自動売買基盤
- 版数: v1.0 (Single Windows Node 完全統合版)

---

## 1. 目的

本ドキュメントは、日本株自動売買システムの **全体システムアーキテクチャ** を定義する。

本システムは、kabuステーション APIの要件に従い、**1台の Windows PC 上で稼働するシングルノード構成（Single Windows Node）** を前提とする。ハードウェアの単一障害点リスクとリソース競合を軽減するため、機能を**論理的なレイヤーおよび別プロセスとして厳密に分離**し、拡張性と安全性を両立する。

---

## 2. 全体アーキテクチャ（データフロー）

実務クオンツファンドの構造を踏襲し、データソースから発注までの責務を以下のコンポーネントに分離する。AIは直接発注を行わず、補助シグナルとして活用することでフェイルセーフを担保する。

```text
【Night Batch (夜間バッチ処理)】
────────────────
J-Quants / News / JPX Calendar
       ↓
[01_Data] Data Platform
       ↓
[02_Strategy] Feature
       ↓
[03_AI_Model] AI Analysis
       ↓
[02_Strategy] Strategy / Portfolio
       ↓
Signal Queue (signals_table / parquet等)

【Market Hours (ザラ場・日中執行)】
────────────────
Signal Queue
       ↓ (Pull型)
[04_Execution] Execution Engine
       ↓
Broker (kabuステーションAPI)
```
※ 全体を傍から監視・統制する独立レイヤーとして `Monitoring / Kill Switch (Operations)` を配置し、検証を行う Analysis Environment として `Research` および `Backtest Framework` を備える。

---

## 3. システム構成（プロセス分離とリソース保護）

**本システムの最大の課題は「すべてを1台のWindowsで動かすことによるリソース競合（フリーズ・発注遅延）」である。**
物理的なサーバー分割を行わない代わりに、「プロセス分離」と「実行スケジューリング」によって執行環境を保護する。

```text
    Windows PC (Single Node)
    │
    ├─ 分析・バッチ系プロセス (重い処理 / 非同期・夜間主軸)
    │  ├ Data Platform (ETL, JPXカレンダー更新等)
    │  ├ AI Analysis (NLP推論ジョブ)
    │  ├ Strategy Engine (シグナル生成バッチ)
    │  └ Portfolio / Signal Queue生成 (DB書き込み)
    │
    ├─ 執行・運用監視系プロセス (軽い処理 / 日中主軸 / 高優先度常駐)
    │  ├ kabuステーション アプリ
    │  ├ Execution Engine (Signal QueueをPull監視・発注)
    │  ├ Monitoring System (リソース・エラー監視の独立プロセス)
    │  └ Kill Switch (Execution死活監視と緊急停止用独立機構)
    │
    └─ Analysis Environment (分析基盤)
       ├ Research Environment
       └ Backtest Framework
```

### 3.1 単一Windowsノードでの安全設計（フェイルセーフ）
1. **プロセスレベルの分離**: 執行系（Execution）と分析・計算系（Data/AI/Strategy）は同じPythonスクリプトに乗せず、完全に別のOSプロセスとして独立稼働させる。
2. **優先度制御 (Priority)**: 執行系プロセスとkabuステーションプロセスにOSの「高優先度」を割り当て、AIタスク等の負荷スパイク時にも発注と損切りが必ず通るようにする。
3. **時間的隔離 (Scheduling)**: AI分析や全銘柄の特徴量計算は相場が開いていない夜間帯（15:00〜翌8:30）のバッチ処理ジョブとして完了させ、ザラ場中（9:00〜15:00）には極力重い計算を走らせない。

---

## 4. 各コンポーネントの基本設計

### 4.1 Data Platform (レイヤー: Data)
- **役割**: 市場データ・ニュース・特徴量・AIスコア・売買履歴の一元化（DuckDB + Parquet等）。JPX Calendar（祝日、半日取引、SQ日）の管理。
- **原則**: すべての履歴を永続化し再現性を保証。JPXカレンダーによりバッチの暴走や無効な日の実行を防ぐ。

### 4.2 Strategy Engine & Portfolio Construction (レイヤー: Strategy)
- **役割**: 特徴量計算、スコア生成、売買シグナル生成、ポジションサイジング（保有株数決定）。
- **原則**: 前日夜間に「翌日エントリーする銘柄と条件」を算出し、DB上の **Signal Queue (例: signals_table / signals.parquet)** に書き込んで処理を終える。

### 4.3 AI Analysis (レイヤー: AI_Model)
- **役割**: ニュースのセンチメント分析（NLP）、市場レジーム判定（Bull/Bear等）。
- **原則**: スコア算出（Feature）に留まり、絶対に直接シグナルを持たない（AI暴走リスクの物理的遮断）。

### 4.4 Execution Engine (レイヤー: Execution)
- **役割**: kabuステーションAPIを通じたREST発注・WebSocket状態監視。
- **原則**: Signal Queueを **Pull型** で取得して執行する。これにより、Strategy側からの予測不可能なPush発注による暴走を防止する。

### 4.5 Monitoring System & Kill Switch (レイヤー: Operations)
- **役割**: システムの死活監視（発注プロセスの生存、エラー検知）、異常時のアラーティング。
- **原則**: Execution Engineとは**完全に別の独立プロセス**として稼働させる。Execution機能がクラッシュした場合でも、独立したKill Switchが作動して全注文を強制キャンセルさせる設計とする。

---

## 5. 段階的導入計画 (Phase)

システムは初期から全結合するのではなく、リスクを制御しながら段階的に構築・運用する。

- **Phase 1: PoC（データ・検証基盤の確立）**
  - J-Quantsからのデータ取得（Data Platform）、特徴量・バックテスト環境の構築。
- **Phase 2: ルールベース本番運用 (Execution層の確立)**
  - Execution層とMonitoring層の構築。AIを使わない（安価で安全な）モメンタム等での単元・少額での自動売買の実証。
- **Phase 3: AIモデル統合 (AI Integration)**
  - ニュース解析、レジーム判定の実装とStrategy層への組み込み。非同期（夜間バッチ）でのAIシグナル連携の実証。
- **Phase 4: 完全自動化と運用拡張 (Ops/Advanced)**
  - ポートフォリオ層による複数戦略の統合、資金配分の動的最適化。Windowsタスクスケジューラを用いた完全な無人運用。
