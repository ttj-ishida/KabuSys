# ImplementationRoadmap.md

## 1. 目的

本ドキュメントは、日本株自動売買システムの
**実装ロードマップ（Implementation Roadmap）** を定義する。

目的:

-   開発の優先順位を明確化
-   段階的な実装
-   安定した検証プロセス
-   実運用までのステップ整理

対象環境:

-   Single Windows PC
-   Python
-   kabuステーションAPI
-   J-Quantsデータ

------------------------------------------------------------------------

# 2. 開発フェーズ

開発は以下のフェーズで進める。

    Phase 1  Data Platform
    Phase 2  Research Environment
    Phase 3  Strategy Engine
    Phase 4  Backtest Framework
    Phase 5  Portfolio Construction
    Phase 6  Execution Engine
    Phase 7  Monitoring
    Phase 8  Paper Trading
    Phase 9  Live Trading

------------------------------------------------------------------------

# Phase 1 --- Data Platform

目的: 市場データ基盤の構築

実装項目:

-   J-Quants API接続
-   株価データ取得
-   ニュースデータ取得
-   DuckDB構築
-   Parquet保存

作成モジュール

    data/
        data_loader.py
        jquants_client.py
        news_collector.py

成果物

    prices_daily
    fundamentals
    news_articles
    market_calendar

------------------------------------------------------------------------

# Phase 2 --- Research Environment

目的: 戦略研究環境の整備

実装項目

-   Jupyter Notebook
-   データ探索
-   基本ファクター分析

作成モジュール

    research/
        factor_research.py
        feature_exploration.py

成果物

-   基本ファクター候補

------------------------------------------------------------------------

# Phase 3 --- Strategy Engine

目的: 売買シグナル生成

実装項目

-   Feature生成
-   モメンタム指標
-   ボラティリティ指標
-   AIスコア統合

作成モジュール

    strategy/
        feature_engineering.py
        signal_generator.py

成果物

    features
    signals

------------------------------------------------------------------------

# Phase 4 --- Backtest Framework

目的: 戦略検証

実装項目

-   バックテストエンジン
-   ポートフォリオシミュレーション
-   パフォーマンス評価

作成モジュール

    backtest/
        engine.py
        simulator.py
        metrics.py

成果物

    equity_curve
    performance_report

------------------------------------------------------------------------

# Phase 5 --- Portfolio Construction

目的: 投資ポートフォリオ生成

実装項目

-   銘柄ランキング
-   ポジションサイズ計算
-   リスク調整

作成モジュール

    portfolio/
        portfolio_builder.py
        position_sizing.py

成果物

    portfolio_targets

------------------------------------------------------------------------

# Phase 6 --- Execution Engine

目的: 自動発注

実装項目

-   kabuステーションAPI接続
-   注文送信
-   約定管理

作成モジュール

    execution/
        execution_engine.py
        order_manager.py

成果物

    orders
    trades
    positions

------------------------------------------------------------------------

# Phase 7 --- Monitoring

目的: システム監視

実装項目

-   ログ記録
-   Streamlitダッシュボード
-   Slack通知

作成モジュール

    monitoring/
        monitoring_service.py
        alert_manager.py

成果物

    system_logs
    trade_logs

------------------------------------------------------------------------

# Phase 8 --- Paper Trading

目的: 実運用前テスト

実装項目

-   実時間シグナル生成
-   仮想発注
-   ポジション追跡

期間

    2〜4週間

評価項目

-   安定性
-   注文成功率
-   シグナル精度

------------------------------------------------------------------------

# Phase 9 --- Live Trading

目的: 本番運用

条件

-   Paper Trading安定
-   バックテスト検証済

運用開始

    小規模資金
    ↓
    段階的拡大

------------------------------------------------------------------------

# 3. 推奨スケジュール

目安

  Week   Phase
  ------ ------------------------
  1      Data Platform
  2      Research Environment
  3      Strategy Engine
  4      Backtest Framework
  5      Portfolio Construction
  6      Execution Engine
  7      Monitoring
  8      Paper Trading
  9      Live Trading

------------------------------------------------------------------------

# 4. 開発原則

1.  **Small Steps** 小さく作って検証

2.  **Backtest First** 戦略は必ずバックテスト

3.  **Fail Safe** Executionは安全設計

4.  **Logging** すべてログを残す

------------------------------------------------------------------------

# 5. 最終目標

完成システム

    Data Platform
          ↓
    Strategy Engine
          ↓
    Portfolio Construction
          ↓
    Signal Queue
          ↓
    Execution Engine
          ↓
    Broker API

このロードマップに従うことで
**安全かつ段階的に自動売買システムを構築できる。**
