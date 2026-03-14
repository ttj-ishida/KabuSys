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

-   J-Quants から株価取得
-   ニュース取得
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

## 3.3 AIニュース分析

**時刻**

    18:00

ジョブ

    ai_analysis_job

処理

-   ニュースセンチメント
-   市場レジーム判定

保存

    ai_scores

------------------------------------------------------------------------

## 3.4 売買シグナル生成

**時刻**

    20:00

ジョブ

    strategy_signal_job

処理

-   戦略スコア算出
-   銘柄ランキング

保存

    signals

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

    Slack Alert
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

  時刻    ジョブ
  ------- ----------------------------
  15:30   data_update_job
  16:00   feature_generation_job
  18:00   ai_analysis_job
  20:00   strategy_signal_job
  21:00   portfolio_construction_job
  08:30   execution_start
  09:00   monitoring_start

------------------------------------------------------------------------

# 8. プロセス優先度

Execution環境を保護する。

  プロセス             優先度
  -------------------- --------
  execution_service    High
  monitoring_service   High
  strategy_service     Normal
  ai_service           Low

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
