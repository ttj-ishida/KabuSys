# KabuSys

日本株自動売買システムのコアライブラリ群と実行 / 監視スクリプト群です。  
この README はリポジトリ内の主な機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 本リポジトリはライブラリ＋複数の起動スクリプトを含みます。実際に「発注」を行う機能は KABUSYS_ENV の設定（`paper_trading` / `live`）により挙動が変わります。実行前に必ず `.env` を設定し、`validate_config` で検証してください。

---

## 概要

KabuSys は日本株の自動売買プラットフォームのコア実装（戦略、ポートフォリオ構築、ポジションサイズ計算、リスク制御、実行エンジン、監視、ニュース NLP／レジーム検出など）を収めた Python パッケージです。  
主に以下を提供します：

- ExecutionEngine：発注 / 注文管理 / リスク管理を行う実行系（本番／ペーパートレード対応）
- Monitoring：システム状態、取引ログ、リスク閾値を監視してアラート・Kill Switch を制御
- Research：ファクター計算 / 特徴量解析ユーティリティ（DuckDB ベース）
- AI：ニュース記事を LLM（OpenAI）でスコアリングするモジュール、レジーム判定
- Portfolio：銘柄選定、重み算出、ポジションサイズ算出（純粋関数群）
- Utils：ログ設定、プロセス優先度設定等のユーティリティ
- CLI / スクリプト：環境設定ウィザード、設定検証、実行起動スクリプト、検証レポート生成など

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV による paper/live 切替）
  - run_monitoring.py — SystemMonitor のポーリングループを起動
- 環境設定支援 / 検証
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — .env / config/*.yaml の事前検証 CLI
- 監視・Kill Switch
  - MonitoringDB（SQLite）による監視ログ保存
  - RiskMonitor / SystemMonitor / TradeMonitor / KillSwitch / MonitoringEngine
- 戦略構築ユーティリティ
  - portfolio.* — 候補選定 / 重み付け / セクター制限 / ポジションサイズ算出
  - research.* — ファクター計算（Momentum, Volatility, Value）・特徴量解析（IC 等）
- AI 統合
  - ai.news_nlp.score_news — OpenAI を使ってニュースを銘柄ごとにスコア化（ai_scores テーブルに書込）
  - ai.regime_detector.score_regime — マクロ記事 + ETF MA200 を組み合わせて市場レジーム判定
- ツール
  - tools.paper_verification_report — ペーパートレード DB から検証レポート生成

---

## 必要環境と依存ライブラリ

- Python 3.10+
- 推奨依存パッケージ（必要に応じてインストール）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定 YAML の検証を行う場合）
- インストール例:
  - 仮想環境作成:
    - python -m venv .venv
    - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
  - pip インストール例:
    - pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt があればそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン、作業ディレクトリへ移動
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. .env の準備
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
   - 主に設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（例: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB）
     - OPENAI_API_KEY（AI を使う場合）
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1)
6. データディレクトリ等の作成（.env のパス先に合わせて）
   - 監視 / PID / フラグファイルは `data/` 配下に配置されることを想定

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、データは `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH）に記録され本番 DB と分離されます。
    - 起動時に `data/stop_requested.flag` または `data/kill.flag` が存在すると起動を早期終了します。
- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL — ポーリング間隔（秒）。デフォルト 60 秒。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使います（監視ログ共有のため）。
- Paper Trading 検証レポート生成（CLI）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db で SQLite パスを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- AI / Research のライブラリ関数呼び出し（Python スクリプト内で）
  - News スコアリング例（DuckDB 接続が必要）:
    - from kabusys.ai.news_nlp import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, datetime.date(2026,4,10), api_key="sk-...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, datetime.date(2026,4,10), api_key="sk-...")

---

## 重要な運用・挙動メモ

- DB（SQLite / DuckDB）
  - デフォルトの監視 DB パス: data/monitoring.db（SQLITE_PATH）
  - DuckDB は分析用（prices_daily / raw_financials 等を格納）: data/kabusys.duckdb（DUCKDB_PATH）
  - run_execution は KABUSYS_ENV=paper_trading のとき専用の paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。本番 DB と完全に分離してください。
- Kill / Stop の仕組み
  - data/kill.flag: KillSwitch により ExecutionEngine を停止するために書き込まれるフラグ（存在すると ExecutionEngine 起動で検出・停止）。
  - data/stop_requested.flag: run_monitoring / run_execution のループを優雅に停止するためのフラグとして利用。
- ロギング
  - ログは stdout とファイル（logs/<app_name>.log）に出力され、TimedRotatingFileHandler で日次ローテート・30日保持
  - 環境変数 LOG_LEVEL / LOG_DIR で制御可能
- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼び出します（psutil を利用）。権限不足や未対応 OS では警告を出してスキップします。
- 環境変数自動ロード
  - プロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## .env の主な項目例

（config_setup で生成される項目を抜粋）

- KABUSYS_ENV=development|paper_trading|live
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

注意: .env は機密情報を含むため Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定読み込みユーティリティ
  - config_setup.py — 対話式 .env ウィザード（CLI）
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - execution/ (発注エンジン関連)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py — SQLite スキーマ / 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py — OpenAI 経由のニュース NLP スコアリング
    - regime_detector.py — マクロ + MA200 によるレジーム判定
  - utils/
    - logging_setup.py — ロギング設定
    - process_priority.py — プロセス優先度 / CPU affinity
  - data/ (ランタイムで生成される想定)
    - monitoring.db 等
    - kill.flag, stop_requested.flag, execution.pid
  - logs/ (ログ出力先、デフォルト)

---

## 開発・テストのヒント

- テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動 .env 読み込みを無効化できます。
- AI 機能は OpenAI API に依存するため、単体テストでは `unittest.mock.patch` などで API 呼び出し（_call_openai_api 等）を差し替えてください（コード内にテスト差し替えポイントの記述あり）。
- DuckDB は分析用の読み取り専用接続にも向いています。research モジュール群は DuckDB 接続を受け取り純粋関数的に動作します。

---

もし README に追加したい具体的な利用例（実行ログ例、.env の完全なテンプレート、Docker / systemd の起動例など）があれば教えてください。必要に応じてその内容を追記します。