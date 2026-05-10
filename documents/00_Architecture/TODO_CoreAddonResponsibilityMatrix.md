# Core / Addon Responsibility Matrix

- 目的: KabuSys の現行機能を `Core` / `Addon` / `Gray Zone` に分類し、別リポジトリ化の前提を固定する
- スコープ: 2026-05-06 時点の現行コードベース
- 前提: `Core` は単独で導入・paper・live 運用まで完結すること

---

## 1. 判定基準

`Core`

- これがないと KabuSys の基本売買フローが成立しない
- paper / live の最低限運用に必須
- 外部 API や高機能 UI がなくても動くべき

`Addon`

- 無効・未導入でも `Core` の売買フローが壊れない
- 外部 API / 外部サービス / 高度な分析体験に依存する
- 個別商品として説明しやすい

`Gray Zone`

- 現時点で `Core` に置くか `Addon` に出すか販売設計次第
- 段階的分離の判断対象

---

## 2. Core

### 2.1 実行・監視基盤

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| Execution 起動 | `src/kabusys/run_execution.py`, `scripts/start_system.py` | Core | 売買実行そのもの |
| Monitoring 起動 | `src/kabusys/run_monitoring.py`, `scripts/start_system.py` | Core | 運用継続に必須 |
| 停止処理 | `scripts/stop_system.py` | Core | 障害時の最低限制御 |
| PID / stop flag | `scripts/utils.py`, `scripts/start_system.py` | Core | 運用制御の土台 |
| process priority | `src/kabusys/utils/process_priority.py` | Core | 実行安定性に寄与 |

### 2.2 データ基盤

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| DuckDB / SQLite スキーマ | `src/kabusys/data/schema.py` | Core | 全処理の前提 |
| 基本テーブル管理 | `prices_daily`, `features`, `signals`, `signal_queue`, `positions`, `portfolio_performance` | Core | 基本売買フローに必須 |
| market calendar | `src/kabusys/data/jquants_client.py`, `market_calendar` | Core | 営業日判定に必須 |
| market breadth | `src/kabusys/data/breadth.py`, `market_breadth` | Core | 現行シグナル抑制条件に必須 |

### 2.3 最低限のデータ収集

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| 日次株価取得 | `scripts/run_data_update.py`, `src/kabusys/data/jquants_client.py` | Core | 現行戦略の最低限入力 |
| 財務取得 | `src/kabusys/data/jquants_client.py` | Core | 現行 features / score に必要 |
| 配当取得 | `src/kabusys/data/jquants_client.py` | Core | 現行 value 系に必要 |
| 決算カレンダー取得 | `src/kabusys/data/jquants_client.py` | Core | earnings avoidance に必要 |

### 2.4 戦略本体

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| Universe 定義 | `documents/02_Strategy/UniverseDefinition.md`, 実装一式 | Core | 最低限の銘柄選定 |
| 特徴量生成 | `scripts/run_feature_gen.py` | Core | シグナル生成に必須 |
| シグナル生成 | `src/kabusys/strategy/signal_generator.py` | Core | 商品本体の中心 |
| Bear / breadth / earnings avoidance | `signal_generator.py`, `breadth.py` | Core | 現行売買判断の一部 |
| ポジションサイズ計算 | `scripts/run_portfolio_construction.py`, `src/kabusys/portfolio/*` | Core | 発注候補生成に必須 |
| 保有制御 | `min_holding_days`, `max_holding_days`, `trailing stop` 実装一式 | Core | exit ロジックとして必須 |

### 2.5 リスク管理

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| risk config | `config/risk_config.yaml` | Core | 本番運用の前提 |
| drawdown 制御 | `RiskManager` 関連 | Core | 安全装置 |
| max_position / utilization | `RiskManager`, portfolio sizing | Core | 安全装置 |
| Kill Switch | execution / monitoring 系 | Core | 安全装置 |
| circuit breaker | execution 系 | Core | API 障害対策 |
| reconciliation | `Reconciler`, position reconciliation report | Core | 本番運用の必須確認 |

### 2.6 基本レポート

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| Pre-Market report | `src/kabusys/run_pre_market_report.py` | Core | 朝の運用判断に必須 |
| Market Close report | `src/kabusys/run_market_close_report.py` | Core | 引け後判断に必須 |
| Signal Queue report | `src/kabusys/run_signal_queue_report.py` | Core | 翌営業日準備確認に必須 |
| Position reconciliation report | `src/kabusys/run_position_reconciliation_report.py` | Core | 本番整合性確認に必須 |
| Performance report | `src/kabusys/run_performance_report.py` | Core | 最低限の成績確認 |
| Execution Startup Summary | `src/kabusys/operations/execution_startup_report.py` | Core | 実行時自動保存される運用判断材料 |

### 2.7 paper / backtest

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| paper_trading 環境 | `KABUSYS_ENV=paper_trading`, `paper_trading.db` | Core | 販売後の検証導線として必須 |
| MockBrokerClient | `src/kabusys/execution/mock_client.py` | Core | paper の前提 |
| backtest engine | `src/kabusys/backtest/engine.py` | Core | 検証導線として必須 |
| backtest report | `src/kabusys/backtest/report.py` | Core | 検証結果の可視化 |

---

## 3. Addon

### 3.1 AI Addon

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| News sentiment | `src/kabusys/ai/news_nlp.py`, `scripts/run_ai_analysis.py` | Addon | OpenAI 依存、無効でも Core は動く |
| AI regime 補助 | `src/kabusys/ai/regime_detector.py` | Addon | OpenAI 依存、Core 非必須 |
| quality_score AI tuning | TODO 群 | Addon | 高機能分析であり Core 非必須 |
| AI 対話型調整 | TODO 群 | Addon | 上級者向け商品にしやすい |

### 3.2 Notification Addon

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| LINE 通知 | `src/kabusys/operations/notifier.py`, `src/kabusys/monitoring/alert_manager.py` | Addon | 外部 API 依存、NullNotifier で無効化可能 |
| 将来の通知拡張 | Slack / Discord / Email 想定 | Addon | Core に不要 |

### 3.3 Disclosure / Event Addon

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| TDnet 収集 | `scripts/run_tdnet_collection.py`, `src/kabusys/data/tdnet_collector.py` | Addon | 外部情報拡張、Core 非必須 |
| EDINET 収集 | `scripts/run_edinet_collection.py`, `src/kabusys/data/edinet_collector.py` | Addon | 外部情報拡張、Core 非必須 |
| 開示分類 | `scripts/run_disclosure_classification.py` | Addon | 付加価値機能 |
| disclosure scoring | TODO / 実装一式 | Addon | イベント投資向け拡張 |

### 3.4 Premium Analytics Addon

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| 高度な factor research | `research` / TODO 群 | Addon | 上級者向け |
| 強化 Strategy Lab | Streamlit pages / TODO 群 | Addon | 分析体験の強化 |
| 高度な比較レポート | 将来の analytics | Addon | Core 非必須 |

### 3.5 Strategy Lab Addon

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| Strategy Lab | `src/kabusys/monitoring/pages/4_Strategy_Lab.py` | Addon | 日次運用の必須画面ではなく、分析・改善・研究のための拡張体験だから |

### 3.6 Yahoo News Addon

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| Yahoo News 収集 | `src/kabusys/data/news_collector.py` | Addon | Core 購入者全体にスクレイピング実行可能状態を広げないため |
| Yahoo News を使う AI 解釈 | `src/kabusys/ai/news_nlp.py` 周辺 | Addon | ニュース収集と一体で扱う方が商品境界・運用リスクの両面で自然 |

---

## 4. Gray Zone

### 4.1 Streamlit UI

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| Home ページ | `src/kabusys/monitoring/streamlit_dashboard.py` | Core | 最低限の運用監視導線だから |
| WebManual ページ | `src/kabusys/monitoring/pages/1_WebManual.py` | Core | Core の導入・運用説明そのものだから |
| Signal Queue ページ | `src/kabusys/monitoring/pages/2_Signal_Queue.py` | Core | 翌営業日の発注準備確認は日次運用の基本動作だから |
| Performance ページ | `src/kabusys/monitoring/pages/3_Performance.py` | Core | Core の完成度と信頼感を上げる役割が強いから |

### 4.2 Performance UI / Report の拡張

| 機能 | 主なファイル | 判定 | 理由 |
|---|---|---|---|
| 基本 performance report | `run_performance_report.py` | Core | 運用判断に必須 |
| 将来の比較分析・可視化強化 | Streamlit / premium analytics | Gray Zone | まだ商品境界を固定していない将来拡張のため |

---

## 5. 暫定結論

現時点の暫定商品境界:

`Core`

- 実行基盤
- データ基盤
- 基本戦略
- リスク管理
- 基本レポート
- paper / backtest
- Streamlit `Home`
- Streamlit `WebManual`
- Streamlit `Signal Queue`
- Streamlit `Performance`

`Addon`

- AI
- Notification
- Disclosure / Event
- Premium Analytics
- Strategy Lab
- Yahoo News

`Gray Zone`

- performance の高機能可視化

---

## 6. 次にやること

この責務表を前提に、次の Issue へ進む。

1. `TODO_CoreAddonExtensionPoints.md` を作る
2. `TODO_CoreAddonImportBoundaryAudit.md` を作る
3. `CoreAddonConfigBoundary.md` を作る

---

## 7. 関連

- [TODO_CoreAddonRepoSplit.md](./TODO_CoreAddonRepoSplit.md)
- `documents/Archive/TODO_Decoupling_CoreAndExtensions.md`
