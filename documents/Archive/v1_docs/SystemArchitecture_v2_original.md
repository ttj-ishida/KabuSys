# SystemArchitecture.md

## 1. 目的

本ドキュメントは、日本株自動売買システムの
**全体システムアーキテクチャ** を定義する。

本システムは **1台の Windows PC 上で稼働するシングルノード構成**
を前提とする。 その中で機能を
**論理レイヤーとして分離**することで、拡張性と安全性を確保する。

------------------------------------------------------------------------

# 2. 全体アーキテクチャ

システムは以下のコンポーネントで構成される。

    Market Data / News
            ↓
    Data Platform
            ↓
    Feature Generation
            ↓
    Strategy Model
            ↓
    Portfolio Construction
            ↓
    Execution Engine
            ↓
    Broker (kabuステーションAPI)

------------------------------------------------------------------------

# 3. システム構成（Single Windows Node）

本システムは1台のWindows PCで動作する。

    Windows PC
    │
    ├ Data Platform
    ├ Research Environment
    ├ Backtest Framework
    ├ AI Analysis
    ├ Strategy Engine
    ├ Portfolio Construction
    ├ Execution Engine
    └ Monitoring System

すべてのコンポーネントは **同一PC内のプロセスとして動作する。**

------------------------------------------------------------------------

# 4. 論理レイヤー構造

システムは以下のレイヤー構造で整理する。

    Data Layer
    ↓
    Research Layer
    ↓
    Strategy Layer
    ↓
    Portfolio Layer
    ↓
    Execution Layer
    ↓
    Monitoring Layer

  Layer        役割
  ------------ --------------------------
  Data         市場データ・ニュース管理
  Research     戦略研究・AIモデル開発
  Strategy     売買シグナル生成
  Portfolio    銘柄選定・資金配分
  Execution    発注・約定管理
  Monitoring   システム監視・リスク監視

------------------------------------------------------------------------

# 5. Data Platform

役割

-   市場データ保存
-   ニュースデータ保存
-   特徴量保存
-   AIスコア保存
-   売買履歴保存

データソース

-   J-Quants
-   Yahoo News
-   日経ヴェリタス

データ形式

    DuckDB
    Parquet

------------------------------------------------------------------------

# 6. Research Environment

役割

-   データ探索
-   ファクター研究
-   AIモデル開発
-   バックテスト

主なツール

    Python
    pandas
    numpy
    Jupyter
    scikit-learn

------------------------------------------------------------------------

# 7. Backtest Framework

役割

-   戦略シミュレーション
-   パフォーマンス評価
-   パラメータ検証

入力

-   Data Platform

出力

-   Backtest Result

------------------------------------------------------------------------

# 8. AI Analysis

役割

-   ニュース解析
-   センチメント分析
-   市場レジーム判定

出力

    AI Score
    Market Regime

------------------------------------------------------------------------

# 9. Strategy Engine

役割

-   特徴量計算
-   スコア生成
-   売買シグナル生成

入力

    Feature Data
    AI Score
    Market Regime

出力

    Trading Signals

------------------------------------------------------------------------

# 10. Portfolio Construction

役割

-   銘柄ランキング
-   資金配分
-   ポートフォリオ構築

出力

    Target Portfolio

------------------------------------------------------------------------

# 11. Execution Engine

役割

-   発注処理
-   約定管理
-   ポジション管理

通信

    Execution Engine
    ↓
    kabuステーション API
    ↓
    証券会社

------------------------------------------------------------------------

# 12. Monitoring System

監視対象

-   システム状態
-   データ更新
-   戦略実行
-   発注状況
-   ポートフォリオリスク

通知

-   Slack
-   Email

------------------------------------------------------------------------

# 13. システムデータフロー

    Market Data / News
    ↓
    Data Platform
    ↓
    Feature Generation
    ↓
    AI Analysis
    ↓
    Strategy Engine
    ↓
    Portfolio Construction
    ↓
    Execution Engine
    ↓
    Broker

------------------------------------------------------------------------

# 14. スケジューリング

処理は以下のジョブで実行される。

  Job               内容
  ----------------- --------------------
  data_update_job   市場データ更新
  feature_job       特徴量生成
  ai_analysis_job   ニュース解析
  signal_job        売買シグナル生成
  portfolio_job     ポートフォリオ生成
  execution_job     発注処理
  monitor_job       監視

スケジューラ

    Windows Task Scheduler

------------------------------------------------------------------------

# 15. 将来拡張

将来的には以下を検討する。

-   Linux Research Server
-   分散バックテスト
-   GPU AI分析
-   クラウドバックアップ

------------------------------------------------------------------------

# 16. まとめ

本システムは **Single Windows Node Architecture** を採用する。

    Windows PC
    │
    ├ Data Platform
    ├ Research
    ├ Backtest
    ├ AI
    ├ Strategy
    ├ Portfolio
    ├ Execution
    └ Monitoring

この構成により、**シンプルで安定した個人運用の日本株自動売買システム**を実現する。
