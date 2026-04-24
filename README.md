README
======

概要
----
KabuSys は日本株の自動売買および関連分析/監視ツール群をまとめたプロジェクトです。本リポジトリには、発注エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、シグナル・ポートフォリオ構築、リサーチ用ファクター計算、AI を使ったニュースセンチメント評価などのモジュールが含まれます。

主な設計方針のポイント
- 本番/ペーパートレードの分離（KABUSYS_ENV による切替。paper_trading は専用 SQLite DB を使用）
- DuckDB を利用した分析（prices_daily / raw_financials 等のテーブルを前提）
- .env による環境変数管理（config_setup.py による対話的生成）
- OpenAI（gpt-4o-mini 想定）を用いたニュース NLP・マクロセンチメント判定機能（API キーが必要）
- 監視（Monitoring）では kill.flag による ExecutionEngine 停止や各種アラート発行をサポート

機能一覧
--------
- Execution
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - ブローカークライアントの切替（本番 / Mock for paper_trading）
  - 注文管理・リスク管理・和解（Reconciler）等の実装（モジュール群内）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（ポーリング）
  - system_status / trade_logs / risk_logs / positions / dashboard を保存する SQLite 層（monitoring_db）
  - KillSwitch（条件で data/kill.flag を書き込む）/ stop フラグによる停止制御
  - run_monitoring スクリプトで定期実行（MONITOR_POLL_INTERVAL で間隔制御）
- Portfolio / Strategy
  - 銘柄選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数などの純粋関数群
- Research
  - ファクター計算（momentum/value/volatility）や特徴量探索（forward returns / IC 等）
  - DuckDB を使った SQL ベースの実装
- AI
  - ニュース NLP による銘柄別センチメント（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI クライアントを使った外部 API 呼び出し（リトライ / バリデーション実装あり）
- ツール
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）
- 設定管理 / ヘルパー
  - .env 対話ウィザード（python -m kabusys.config_setup）
  - 起動前設定検証 CLI（python -m kabusys.validate_config）
  - 統一ログ設定ユーティリティ（kabusys.utils.logging_setup）
  - プロセス優先度設定ユーティリティ（psutil を使用）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必須パッケージのインストール（例）
   - pip install duckdb psutil openai
   - 追加で解析用に PyYAML が必要な箇所（validate_config の YAML 検証など）は optional:
     - pip install pyyaml
   - 実際の requirements.txt は本リポジトリに含まれていない可能性があるため、必要に応じて上記をインストールしてください。

4. .env の初期作成（推奨）
   - 対話的ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動で作成（最低限必要な環境変数は以下参照）。

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト development
  - paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合必須）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、run_monitoring で上書き可）
- PAPER_FILL_MODE: paper_trading の MockBroker 動作モード（instant|partial|never|reject）

参考: .env の雛形（config_setup で生成される形式の例）
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

使い方
------
基本的な CLI の実行例:

- 環境設定ウィザード（.env の作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳密モード（警告をエラー扱い）:
    - python -m kabusys.validate_config --strict

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（例: export MONITOR_POLL_INTERVAL=30）
  - 監視プロセスは data/stop_requested.flag が存在するとループを抜けて終了します
  - 監視側は Settings.sqlite_path（デフォルト data/monitoring.db）を常に使用します（env に依存せず本番 DB を参照する点に注意）

- 実行エンジンの起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、データは data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録されます
  - 起動時に data/stop_requested.flag が既に存在すると起動せず終了します
  - 実行中に停止させたい場合は data/stop_requested.flag を作成するか、Monitoring の KillSwitch により data/kill.flag が作成されると停止シグナルとして機能します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルトの DB パスは data/paper_trading.db。--db で上書き可能

停止・フラグ関連
- stop_requested.flag: run_monitoring / run_execution が監視する「即時停止」フラグ（data/stop_requested.flag）
- kill.flag: KillSwitch が条件を満たした場合に書き込むフラグ（Settings.kill_flag_path、デフォルト data/kill.flag）。ExecutionEngine に対する安全停止要求として使用
- PID ファイル: run_execution で使用される pid ファイルは data/execution.pid（Settings.pid_file_path）

ログ
- ログは標準出力（stdout）と日次ローテーションで logs/<app_name>.log に出力されます（kabusys.utils.logging_setup）
- ログディレクトリは環境変数 LOG_DIR で指定可能（デフォルト logs/）

依存関係（主要）
- Python 3.8+
- duckdb
- psutil
- openai（AI 機能使用時）
- PyYAML（config/*.yaml のパース検証を行う場合に optional）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

注意点 / トラブルシューティング
- OpenAI 機能は API キーが必須です。環境変数 OPENAI_API_KEY を設定してください。
- validate_config が config/*.yaml の検証を行うには PyYAML が必要です。無い場合は警告のみでスキップされます。
- paper_trading モードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH）。
- Monitoring はコード内の設計上「環境にかかわらず本番 sqlite_path を使用する」箇所があるため、設定・運用時は DB パスに注意してください。
- Process Priority / CPU affinity の設定は psutil に依存し、権限の問題で設定できない場合は警告が出ますが処理は継続します。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / 設定管理
- config_setup.py              — .env 対話ウィザード CLI
- validate_config.py           — 設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — Monitoring ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py                — ニュース NLP / AI スコアリング
  - regime_detector.py         — 市場レジーム判定
  - __init__.py
- monitoring/
  - monitoring_db.py           — SQLite テーブル初期化と永続層 API
  - system_monitor.py
  - trade_monitor.py           — （存在: monitor 用ファイル。詳細は実装参照）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py           — （存在: アラート送信用モジュール。実装参照）
- execution/
  - execution_engine.py        — ExecutionEngine 本体（EngineConfig 等）
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- tools/
  - paper_verification_report.py
  - __init__.py
- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py
- monitoring/
  - (上記 monitoring 関連ファイル)

data/（ランタイムで使用・作成されることを想定）
- data/monitoring.db           — 監視 DB（デフォルト）
- data/paper_trading.db        — ペーパートレード用 DB（paper_trading 時）
- data/kabusys.duckdb          — DuckDB ファイル（デフォルト）
- data/stop_requested.flag     — 外部からの停止要求フラグ
- data/kill.flag               — KillSwitch が書き込む停止フラグ
- data/execution.pid           — Execution の PID ファイル

最後に
-----
本 README はコードベースの主要コンポーネントと運用上のポイントをまとめたものです。詳細な実装や追加設定は各モジュール（特に execution/、monitoring/、ai/）の docstring やコード内コメントを参照してください。実行前に python -m kabusys.validate_config で設定検証を行うことを推奨します。