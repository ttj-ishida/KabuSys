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
    ├ monitoring_db.py          ← SQLite 永続化層（MonitoringDB / init_monitoring_db）
    ├ monitoring_engine.py      ← 各 Monitor を統括するポーリングエンジン
    ├ system_monitor.py         ← CPU / メモリ / ディスク / プロセス監視
    ├ trade_monitor.py          ← 発注状態監視
    ├ risk_monitor.py           ← DD / ポジション上限 / Circuit Breaker 監視
    ├ alert_manager.py          ← LINE アラート送信
    ├ streamlit_dashboard.py    ← Streamlit Home ページ（エントリーポイント）
    ├ dashboard_data.py         ← 全ページ共通データロード関数（Streamlit 非依存）
    └ pages/
        ├ 2_Signal_Queue.py     ← 発注キュー・シグナル確認ページ
        ├ 3_Performance.py      ← エクイティカーブ・ポジション・取引履歴ページ
        └ 4_Strategy_Lab.py     ← 市場レジーム・AI スコア・シグナル推移ページ

役割:

-   システム監視（CPU / メモリ / プロセス）
-   発注・リスク監視
-   Streamlit 4ページ マルチページ ダッシュボード（Issue #231）

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
    ├ integration/               ← 統合テスト（モジュール間連携）
    │   ├ test_integration.py    ← Portfolio → Execution → Monitoring フロー
    │   └ test_paper_trading.py  ← ペーパートレード検証
    ├ test_execution_engine.py
    ├ test_risk_manager.py
    ├ test_portfolio_construction.py
    ├ test_monitoring_db.py
    └ （その他ユニットテスト）

ユニットテストは `tests/` 直下、モジュール間連携テストは `tests/integration/` に配置する。

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

依存ファイルは3本構成で管理する。

  ファイル               用途
  ---------------------- -----------------------------------------------
  `requirements.txt`     実行時依存（バージョン範囲指定）
  `requirements-dev.txt` 開発・テスト用追加依存（`-r requirements.txt` を含む）
  `constraints.txt`      ピン留めバージョン（サプライチェーンリスク低減）

インストール例:

    # 実行環境（制約付き）
    pip install -c constraints.txt -r requirements.txt

    # 開発環境
    pip install -c constraints.txt -r requirements-dev.txt

主な実行時依存:

    pandas, numpy, scikit-learn
    duckdb, pyarrow
    requests, websocket-client
    PyYAML, openai, httpx, psutil
    streamlit

`constraints.txt` の更新手順（バージョンアップ時）:

    pip install pip-tools
    pip-compile requirements-dev.txt --output-file constraints.txt

注: `requirements-dev.txt` は `-r requirements.txt` を含むため、実行時依存・開発依存の両方がピン留めされる。

------------------------------------------------------------------------

# 6. Git運用

推奨ブランチ構成:

    main        (production)
    develop     (development)
    feature/*   (new feature)

## CI/CD

GitHub Actions により push / PR 時に以下を自動実行する（`.github/workflows/ci.yml`）。

  ジョブ   内容
  -------- -------------------------------------------------
  lint     `ruff check` + `ruff format --check`
  test     `pytest tests/`（ユニットテスト + 統合テスト）

## pre-commit

ローカル開発では pre-commit フックで `ruff` による lint + format チェックを実施する。

    # 初回セットアップ
    pip install pre-commit
    pre-commit install

設定ファイル: `.pre-commit-config.yaml`

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
