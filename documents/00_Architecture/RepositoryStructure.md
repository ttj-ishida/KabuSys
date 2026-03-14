# RepositoryStructure.md

## 1. 目的

本ドキュメントは、日本株自動売買システムの
**ソースコードリポジトリ構造（Repository Structure）** を定義する。

目的:

-   システムの可読性を高める
-   機能ごとの責務分離
-   拡張性の確保
-   運用・保守の容易化
-   テストの実装を容易にする

本構造は **Single Windows Node + Pythonベースのクオンツシステム**
を前提とする。

------------------------------------------------------------------------

# 2. リポジトリ全体構造

    project-root/
    │
    ├ config/
    ├ data/
    ├ docs/
    ├ research/
    ├ backtest/
    ├ strategy/
    ├ ai/
    ├ portfolio/
    ├ execution/
    ├ monitoring/
    ├ runtime/
    ├ scripts/
    ├ tests/
    ├ logs/
    ├ notebooks/
    │
    ├ main.py
    ├ requirements.txt
    └ README.md

------------------------------------------------------------------------

# 3. 各ディレクトリの役割

## config/

設定ファイルを格納する。

例:

    config/
    ├ system_config.yaml
    ├ trading_config.yaml
    ├ universe_config.yaml
    └ risk_config.yaml

内容:

-   API設定
-   戦略パラメータ
-   リスク制限
-   ユニバース設定

------------------------------------------------------------------------

## data/

ローカルデータ保存領域。

    data/
    ├ raw/
    ├ processed/
    ├ features/
    ├ signals/
    └ portfolio/

用途:

-   J-Quantsデータ
-   ニュースデータ
-   特徴量
-   シグナル
-   ポートフォリオ履歴

推奨形式:

    Parquet
    DuckDB

------------------------------------------------------------------------

## docs/

設計ドキュメントを格納。

    docs/
    ├ SystemArchitecture.md
    ├ RuntimeArchitecture.md
    ├ DataPlatform.md
    ├ PortfolioConstruction.md
    ├ RiskManagement.md
    └ DeploymentArchitecture.md

------------------------------------------------------------------------

## research/

戦略研究コード。

    research/
    ├ factor_research.py
    ├ feature_exploration.py
    └ research_utils.py

用途:

-   ファクター研究
-   データ分析
-   仮説検証

------------------------------------------------------------------------

## backtest/

バックテストエンジン。

    backtest/
    ├ engine.py
    ├ simulator.py
    ├ metrics.py
    └ backtest_runner.py

役割:

-   戦略シミュレーション
-   パフォーマンス評価

------------------------------------------------------------------------

## strategy/

売買ロジック。

    strategy/
    ├ signal_generator.py
    ├ feature_engineering.py
    ├ factor_model.py
    └ strategy_runner.py

役割:

-   特徴量生成
-   シグナル生成

------------------------------------------------------------------------

## ai/

AI関連コード。

    ai/
    ├ news_sentiment.py
    ├ regime_model.py
    └ ai_features.py

用途:

-   ニュース解析
-   センチメント分析
-   市場レジーム判定

------------------------------------------------------------------------

## portfolio/

ポートフォリオ構築。

    portfolio/
    ├ portfolio_builder.py
    ├ position_sizing.py
    └ risk_adjustment.py

役割:

-   銘柄選定
-   株数計算
-   リスク調整

------------------------------------------------------------------------

## execution/

発注処理。

    execution/
    ├ order_manager.py
    ├ broker_api.py
    ├ execution_engine.py
    └ position_manager.py

役割:

-   kabuステーションAPI接続
-   注文送信
-   約定管理

------------------------------------------------------------------------

## monitoring/

監視システム。

    monitoring/
    ├ system_monitor.py
    ├ trade_monitor.py
    ├ risk_monitor.py
    └ alert_manager.py

役割:

-   システム監視
-   注文監視
-   リスク監視

------------------------------------------------------------------------

## runtime/

ジョブスケジュールとパイプライン。

    runtime/
    ├ scheduler.py
    ├ night_batch.py
    ├ market_open.py
    └ runtime_manager.py

役割:

-   夜間処理
-   ザラ場処理
-   ジョブ管理

------------------------------------------------------------------------

## scripts/

運用スクリプト。

    scripts/
    ├ start_system.py
    ├ stop_system.py
    ├ rebuild_features.py
    └ reset_signals.py

------------------------------------------------------------------------

## tests/

テストコード。

    tests/
    ├ test_strategy.py
    ├ test_execution.py
    ├ test_portfolio.py
    └ test_data_pipeline.py

------------------------------------------------------------------------

## logs/

ログ保存。

    logs/
    ├ execution/
    ├ strategy/
    ├ monitoring/
    └ system/

------------------------------------------------------------------------

## notebooks/

Jupyter Notebook。

    notebooks/
    ├ research_factor.ipynb
    ├ data_analysis.ipynb
    └ backtest_experiment.ipynb

------------------------------------------------------------------------

# 4. メインエントリーポイント

    main.py

役割:

-   システム起動
-   サービス初期化
-   runtime起動

------------------------------------------------------------------------

# 5. Python依存関係

    requirements.txt

例:

    pandas
    numpy
    scikit-learn
    duckdb
    websocket-client
    requests
    pyyaml

------------------------------------------------------------------------

# 6. Git運用

推奨ブランチ構成:

    main        (production)
    develop     (development)
    feature/*   (new feature)

------------------------------------------------------------------------

# 7. 実行フロー

    main.py
       ↓
    runtime_manager
       ↓
    night_batch / market_open
       ↓
    strategy
       ↓
    portfolio
       ↓
    execution

------------------------------------------------------------------------

# 8. まとめ

Repositoryは以下の思想で設計する。

-   機能ごとにディレクトリ分離
-   Research / Strategy / Execution を明確分離
-   データ・ログ・設定を独立管理

この構造により **拡張性と運用性の高い自動売買コードベース** を実現する。
