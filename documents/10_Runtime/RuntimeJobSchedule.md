# RuntimeJobSchedule.md

## 1. 目的

本ドキュメントは、日本株自動売買システムの
**日次運用スケジュール（Runtime Job Schedule）** を定義する。

目的:

-   夜間バッチ処理の順序定義
-   ザラ場処理の安全運用
-   Execution 環境の保護
-   Windows Task Scheduler の設定指針

本システムは **Single Windows Node** で稼働するため、
処理負荷を時間帯で分離する。

**本スケジュールは日足スイング戦略専用の設計である。**
夜間バッチでシグナルを生成し、翌営業日の寄付きで執行する。ザラ場中はシグナル生成を行わない（Execution と Monitoring のみ稼働）。デイトレードやザラ場リバランスには対応しない。

------------------------------------------------------------------------

# 2. 日次運用タイムライン

    15:30  Market Close
       ↓
    Night Batch Processing
       ↓
    Signal Generation
       ↓
    Portfolio Construction
       ↓
    Execution Preparation
       ↓
    09:00  Market Open
       ↓
    Execution Monitoring
       ↓
    15:30  Market Close

------------------------------------------------------------------------

# 3. 夜間バッチ（Night Batch）

夜間バッチは **重い計算処理を行う時間帯**。

対象処理:

-   データ更新
-   特徴量計算
-   AI分析
-   戦略シグナル生成
-   ポートフォリオ構築

------------------------------------------------------------------------

## 3.1 データ更新

**時刻**

    15:30

ジョブ

    data_update_job

処理

-   J-Quants から株価・財務・銘柄マスタを取得（市場・財務データの唯一の基盤データ源）
-   Yahoo News から補助ニュース記事を取得（RSS、売買判断の主役にしない）
-   データ保存

更新対象

    prices_daily
    news_articles
    fundamentals

------------------------------------------------------------------------

## 3.2 特徴量生成

**時刻**

    16:00

ジョブ

    feature_generation_job

処理

-   モメンタム
-   ボラティリティ
-   出来高指標

保存

    features

------------------------------------------------------------------------

## 3.3 AI分析

**時刻**

    18:00

ジョブ

    ai_analysis_job

処理

-   ニュースセンチメント分析: score_news(conn, target_date)
    - raw_news + news_symbols → gpt-4o-mini → 銘柄ごとの sentiment_score
-   市場レジーム判定: score_regime(conn, target_date)
    - ETF1321の200日MA乖離（70%）+ マクロニュースLLM（30%）→ regime_score / regime_label

保存

    ai_scores      （sentiment_score: 銘柄単位）
    market_regime  （regime_score / regime_label: 日次1行）

------------------------------------------------------------------------

## 3.4 売買シグナル生成

**時刻**

    20:00

ジョブ

    strategy_signal_job

処理

-   戦略スコア算出（モメンタム / バリュー / ボラティリティ / AIスコア統合）
-   セクター相対強弱フィルタ適用
-   ギャップリスクフィルタ適用
-   決算回避・主要イベント縮小判定（`earnings_calendar` / `config/event_calendar.md` 参照）
-   最低保有日数・再エントリー制限判定（`position_entries` テーブル参照）
-   breadth_stop フィルタ適用（`market_breadth` テーブル参照）
-   銘柄ランキング・シグナル書き込み

保存

    signals（side, score, signal_rank, size_multiplier）

------------------------------------------------------------------------

## 3.5 ポートフォリオ生成

**時刻**

    21:00

ジョブ

    portfolio_construction_job

処理

-   ポジションサイズ計算
-   リスク制御適用

保存

    signal_queue

------------------------------------------------------------------------

# 4. プレマーケット処理

市場開始前に Execution を起動する。

**時刻**

    08:30

ジョブ

    execution_start

処理

-   Execution Engine 起動
-   Signal Queue 読み込み
-   API接続確認

------------------------------------------------------------------------

# 5. ザラ場処理（Market Hours）

ザラ場では **重い処理は禁止**。

稼働プロセス

    execution_service
    monitoring_service

------------------------------------------------------------------------

## 5.1 Execution Loop

    execution_loop

処理

-   pending signal取得
-   発注
-   約定確認
-   ポジション更新

------------------------------------------------------------------------

## 5.2 Monitoring Loop

    monitoring_loop

監視

-   Executionプロセス
-   API接続
-   ドローダウン
-   注文エラー

異常時

    LINE Alert
    Kill Switch

------------------------------------------------------------------------

# 6. Market Close処理

**時刻**

    15:30

ジョブ

    market_close_job

処理

-   ポジション更新
-   当日ログ保存
-   パフォーマンス計算

更新テーブル

    positions
    portfolio_performance

------------------------------------------------------------------------

# 7. Windows Task Scheduler 設定

登録スクリプト: `scripts/setup_task_scheduler.ps1`

  時刻    タスク名                       実行スクリプト
  ------- ------------------------------ -----------------------------------------------
  15:30   KabuSys_DataUpdate             scripts\run_data_update.py
  16:00   KabuSys_FeatureGen             scripts\run_feature_gen.py
  18:00   KabuSys_AiAnalysis             scripts\run_ai_analysis.py
  20:00   KabuSys_StrategySignal         scripts\run_strategy_signal.py
  21:00   KabuSys_PortfolioConstruction  scripts\run_portfolio_construction.py
  08:30   KabuSys_ExecutionStart         scripts\start_system.py --component execution
  09:00   KabuSys_MonitoringStart        scripts\start_system.py --component monitoring

登録コマンド（プロジェクトルートで実行）:

    powershell -File scripts\setup_task_scheduler.ps1

既存ジョブは `-Force` で上書き登録される。

------------------------------------------------------------------------

# 8. プロセス優先度

Execution環境を保護する。

  プロセス             優先度     起動スクリプト
  -------------------- -------- -------------------------------------------
  execution_service    High     scripts\start_system.py --component execution
  monitoring_service   High     scripts\start_system.py --component monitoring
  strategy_service     Normal   ライブラリ（夜間バッチから呼び出し）
  ai_service           Low      ライブラリ（夜間バッチから呼び出し）

各起動スクリプトは `src/kabusys/utils/process_priority.set_process_priority("high")` を
先頭で呼び出し、OS優先度を設定してからエンジンを初期化する。
Windows では管理者権限推奨（権限不足時は WARNING ログで続行）。

------------------------------------------------------------------------

# 8.1 停止・制御スクリプト

  スクリプト                     用途
  ------------------------------ ----------------------------------------------------
  scripts\start_system.py        execution / monitoring プロセスを起動（PIDファイル書き込み）
  scripts\stop_system.py         グレースフル停止（10秒タイムアウト後に強制終了）
  scripts\rebuild_features.py    prices_daily のデータ確認後に特徴量を再計算
  scripts\reset_signals.py       signal_queue をクリア（未処理シグナルを削除）

停止フラグファイル: `data/stop_requested.flag`

- `stop_system.py` が作成し、`start_system.py` が次回起動時にクリアする。
- `run_execution.py` と `run_monitoring.py` はメインループでこのフラグを監視してグレースフルに終了する。

PIDファイル:

  プロセス           PIDファイル
  ------------------ ----------------------
  execution_service  data/execution.pid
  monitoring_service data/monitoring.pid

------------------------------------------------------------------------

# 9. 休日・祝日処理

JPXカレンダーを参照する。

    market_calendar

チェック

-   is_trading_day
-   is_half_day
-   is_sq_day

非取引日は **Night Batch のみ実行**。

------------------------------------------------------------------------

# 10. 障害対応

異常フロー

    Monitoring
       ↓
    Alert
       ↓
    Execution Stop
       ↓
    Manual Investigation

------------------------------------------------------------------------

# 11. まとめ

Runtime Job Schedule は以下で構成される。

    Night Batch
       ↓
    Signal Generation
       ↓
    Portfolio Construction
       ↓
    Execution Preparation
       ↓
    Market Execution
       ↓
    Monitoring

このスケジュールにより **Single Windows Node
環境でも安全で安定した自動売買運用**を実現する。
