# KabuSys — 日本株自動売買システム（簡易 README）

本リポジトリは日本株自動売買システム KabuSys の主要モジュール群を含みます。  
この README ではプロジェクト概要、機能一覧、セットアップ手順、使い方、主要ディレクトリ構成を日本語でまとめます。

## プロジェクト概要
KabuSys は日本株の自動売買を想定したモジュール群です。主な機能は以下を含みます。
- 発注実行エンジン（ExecutionEngine）とブローカークライアント抽象化（paper/live 切替）
- システム監視（SystemMonitor / MonitoringEngine）とアラート・Kill Switch
- ポートフォリオ構築（候補選定・重み計算・位置サイズ決定・セクター制約）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- AI を使ったニュース NLP（OpenAI を利用したセンチメント評価・市場レジーム判定）
- ペーパートレード検証レポート生成ツール

設計方針の一例：
- DuckDB を用いた分析データ格納（prices_daily, raw_financials 等）
- SQLite を用いた監視 / 発注ログの永続化
- 環境変数 / .env による設定管理（対話式ウィザードあり）
- Paper Trading は本番データベースと分離（別 SQLite）

## 主な機能一覧
- Execution
  - ExecutionEngine（run_execution.py から起動）
  - BrokerClientFactory：KABUSYS_ENV に応じて実環境 or MockBroker を選択
  - OrderRepository / OrderManager / RiskManager / Reconciler
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク / データ鮮度 / プロセス生存監視）
  - TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
  - 永続化層 MonitoringDB（SQLite）
- Portfolio
  - 候補選定（select_candidates）
  - 等配分・スコア配分（calc_equal_weights / calc_score_weights）
  - セクター制約（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ決定（calc_position_sizes）
- Research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算 / IC 計算 / 統計サマリー
- AI
  - ニュースセンチメント（news_nlp.score_news） — OpenAI API 使用
  - 市場レジーム判定（regime_detector.score_regime）
- Tools
  - Paper Trading 検証レポート生成（tools.paper_verification_report）
- 設定補助
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
- 共通ユーティリティ
  - ロギングセットアップ（utils.logging_setup）
  - プロセス優先度設定 / CPU affinity（utils.process_priority）
  - 設定読み込み（config.py）

## 前提 / 必要パッケージ
（主要な外部ライブラリ）
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能使用時）
- PyYAML（config の YAML 検証に任意）
標準ライブラリ：sqlite3, logging, threading, datetime, pathlib など

インストール例（プロジェクトに requirements ファイルがある場合はそちらを利用）:
- pip install duckdb psutil openai
- （開発用）pip install -e .

## 環境設定（.env）
推奨ワークフロー:
1. 対話式ウィザードで .env を作成/更新:
   - python -m kabusys.config_setup
2. 作成後、設定検証:
   - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱い（exit 1）

必須環境変数（validate_config がチェック）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な環境変数（デフォルト値や意味）:
- KABUSYS_ENV: execution 環境（development / paper_trading / live）。デフォルト development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）（Monitoring は常に sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（INFO 等）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除するか (0/1)
- MONITOR_POLL_INTERVAL: run_monitoring が使うポーリング間隔（秒、デフォルト 60）

例 (.env の一部)
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

## セットアップ手順（簡潔）
1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（duckdb, psutil, openai など）
4. .env を作成（対話式: python -m kabusys.config_setup）
5. 設定を検証: python -m kabusys.validate_config
6. data ディレクトリ等必要なディレクトリは起動時に自動作成されるか手動で作成

## 実行方法（主要コマンド）
- ExecutionEngine を起動（本番/paper 切替は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag が作成されると停止リクエストを検出して終了します。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可）
  - Paper trading（KABUSYS_ENV=paper_trading）の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。

- Monitoring を起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルト 60 秒。MONITOR_POLL_INTERVAL 環境変数で上書き可。
  - 監視は常に Settings.sqlite_path（本番監視 DB）を使用します。
  - 停止フラグ: data/stop_requested.flag を検出すると監視ループを終了します。

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- .env ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI 関連（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None) — OpenAI API キーが必要
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

## ログ
- ログ設定ユーティリティでルートロガーを構成します（utils.logging_setup.setup_logging）。
- デフォルト出力先: stdout + 日次ローテートファイル logs/<app_name>.log（30 日保持）
- ログディレクトリやレベルは環境変数（LOG_DIR, LOG_LEVEL）や関数引数で上書き可能

## 停止フラグ / Kill Switch
- KillSwitch（kill.flag）を作成すると ExecutionEngine に対する停止シグナルとなります。flag のパスは Settings.kill_flag_path（デフォルト data/kill.flag）。
- run_execution.py / run_monitoring.py は data/stop_requested.flag を見て外部からの停止リクエストに応答します。
- KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に kill.flag を自動クリアします（本番環境では推奨しない）。

## ディレクトリ構成（主要ファイルの説明）
（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数/.env 読み込み・Settings クラス
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（PID / stop フラグ管理）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL）
  - tools/
    - paper_verification_report.py — Paper Trading 用検証レポート CLI
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite による永続化層（schema 初期化・CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （トレード監視ロジック）※ファイルはリポジトリ内に存在
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch（flag の作成/削除）
    - monitoring_engine.py — モニタリング各コンポーネントを束ねる
    - alert_manager.py — （アラート送信ロジック）※ファイルはリポジトリ内に存在
  - execution/
    - execution_engine.py — ExecutionEngine（主制御ループ）
    - broker_factory.py — BrokerClientFactory（実ブローカ or Mock を作成）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注関連モジュール
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・投資上限・丸め処理
    - risk_adjustment.py — セクター制約・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 制御

（注）上記以外にも data、config/*.yaml、logs ディレクトリ等が運用で利用されます。

## 運用上の注意 / ベストプラクティス
- 本番環境（KABUSYS_ENV=live）では kill.flag 自動クリア（KILL_FLAG_CLEAR_ON_START=1）を無効にすることを推奨します。
- OPENAI_API_KEY や取引 API のシークレットは絶対に Git にコミットしないでください。
- Paper Trading は本番 DB と完全分離するため、PAPER_TRADING_SQLITE_PATH を利用してください。
- monitoring は常に Settings.sqlite_path を使用します（環境に依らず監視 DB を参照する設計）。
- ログディレクトリの作成権限に注意。作成失敗時はコンソール出力のみになります。
- AI の呼び出しは API のレート制限やエラーに対してリトライ・フェイルセーフ設計が組まれていますが、API キー管理とコストに注意してください。

---

さらに詳しい API 仕様や設計文書（PortfolioConstruction.md、StrategyModel.md 等）が別途ある想定です。本 README はコードベースを参照して主要な使い方をまとめた入門ガイドです。追加で「各モジュールの API ドキュメント」や「運用手順（デプロイ / systemd / コンテナ化）」のテンプレートが必要であれば作成しますので教えてください。