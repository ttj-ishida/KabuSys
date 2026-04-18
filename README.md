KabuSys
=======

日本株向けの自動売買／調査プラットフォーム（ライブラリ + 実行スクリプト群）の一部です。
このリポジトリは次の機能群を含みます：注文実行エンジン（ExecutionEngine）、監視モジュール（Monitoring）、ポートフォリオ構築・ポジションサイジング、ファクター計算／リサーチ、AI（ニュースセンチメント／レジーム判定）等。

この README ではプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
--------------
KabuSys は日本株の自動売買システム向けの共通ライブラリと起動スクリプトを提供します。主な設計方針は以下の通りです。

- 実行用ロジック（発注・リスク管理）と監視ロジックを分離。
- 本番 DB（SQLite / DuckDB）は環境変数で指定できる。Paper trading は本番 DB と分離。
- DuckDB を分析・リサーチ用途に使い、SQLite を監視・ログ用（trade_logs, system_status 等）に使う。
- OpenAI を用いたニュース NLP / レジーム判定機能を備える（API呼び出しは外部設定）。
- .env ウィザード、設定検証 CLI を用意し、起動前に設定を整えられる。

主な機能一覧
------------
- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV に応じて paper_trading モードをサポート）
  - run_monitoring.py — SystemMonitor のポーリング監視ループを起動
- 設定関連
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 環境変数 / config/*.yaml の検証 CLI
  - config.Settings — 環境変数読み込み・検証ロジック（defaults を含む）
- 監視（monitoring）
  - システム監視（CPU/メモリ/ディスク、データ鮮度、プロセス死活）
  - トレード監視（trade_logs の整合性チェックなど）
  - リスク監視（ドローダウン・保有上限）
  - Kill Switch（条件成立時に data/kill.flag を書き込み Execution を安全に停止）
  - MonitoringDB（SQLite に対する永続化レイヤ）
  - MonitoringEngine（各監視をまとめて定期実行）
- Execution（execution）
  - ブローカーファクトリ（本番 or モック）
  - OrderManager / OrderRepository / Reconciler / RiskManager / ExecutionEngine（発注フローを管理）
- Portfolio（portfolio）
  - 銘柄選定・重み計算（等配分・スコア加重）
  - セクターキャップ、レジーム乗数適用
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- Research（research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC（Spearman）計算、統計サマリ
- AI（ai）
  - news_nlp: OpenAI を使ったニュースセンチメント計算および ai_scores への書き込み
  - regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定
- ユーティリティ
  - logging_setup: 統一的なログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - tools.paper_verification_report — Paper Trading の検証レポートを生成する CLI

必須依存（主なもの）
------------------
（実行する機能により必要パッケージが変わります）
- Python >= 3.10 （型ヒントに | を使用）
- duckdb
- psutil
- openai （AI 関連を使う場合）
- PyYAML（validate_config の拡張検証に必要、必須ではない）

セットアップ手順
---------------
1. リポジトリをクローンし、仮想環境を作成・有効化する。
   - python -m venv .venv
   - source .venv/bin/activate  または Windows では .venv\Scripts\activate

2. 必要パッケージをインストールする（例）:
   - pip install duckdb psutil openai
   - （validate_config の YAML 検証を使いたい場合）pip install pyyaml

3. .env を作成する
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照）。重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）

4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

5. ディレクトリ・ファイルの初期作成
   - data/ や logs/ は自動作成されますが、権限に注意してください。

基本的な使い方
--------------
- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 実行前に .env の KABUSYS_ENV を設定してください。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
  - エンジンは data/execution.pid を作成します。停止は data/stop_requested.flag を作るか、監視側の kill.flag により行われます。

- Monitoring を起動（ポーリング監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使って監視ログを書きます。

- 停止制御
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが終了します（これらの起動スクリプトで参照）。
  - Kill Switch (監視) は条件成立時に data/kill.flag を書き込み、ExecutionEngine を停止させる仕組みです（flag の自動クリア設定 KILL_FLAG_CLEAR_ON_START に注意）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能。
  - 内部で稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL を判定します（閾値はツール内定数で定義）。

- AI 機能
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、ニュースのセンチメントを ai_scores テーブルへ書き込みます。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを判定して market_regime テーブルへ書き込みます。
  - API キーは引数か環境変数 OPENAI_API_KEY で指定してください。
  - テスト時は API 呼び出し helper をパッチしてモックできます（モジュール内の _call_openai_api を patch）。

注意点 / 運用上のヒント
---------------------
- run_monitoring は常に Settings.sqlite_path を使って監視 DB を書きます（環境にかかわらず）。監視 DB とペーパートレード DB を分離したい場合は設定を確認してください。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使い、本番 DB とは分離します。
- Logging: kabusys.utils.logging_setup.setup_logging を全スクリプトで呼んでおり、デフォルトで logs/<app_name>.log に日次ローテーションで出力します。ログディレクトリ作成に失敗するとコンソール出力のみになります。
- process_priority: スクリプト起動時にプロセス優先度を "high" に設定する処理があります。権限がない場合は警告が出ます。
- .env の自動読み込みはプロジェクトルート (.git または pyproject.toml を基準) を探索して行われます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config は PyYAML がない場合、yaml ファイルのパース検証をスキップします（警告）。

ディレクトリ構成（主要ファイル）
------------------------------
(リポジトリルート)
- pyproject.toml / setup.cfg / ...（パッケージメタ情報）
- .env, .env.local（環境変数、.env は絶対にコミットしないこと）

src/kabusys/
- __init__.py
- config.py — 環境変数読み込み・Settings クラス
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI

- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring 起動スクリプト

- utils/
  - logging_setup.py — ログ設定
  - process_priority.py — 優先度 / affinity
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, risk_logs, positions, dashboard）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — （存在）トレード関連監視
  - risk_monitor.py — ドローダウン / ポジション上限チェック
  - kill_switch.py — kill.flag 管理
  - monitoring_engine.py — 各監視をまとめる
  - alert_manager.py — （存在）通知送信ロジック（LINE 等）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など（発注フロー）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py など（配分・ポジション管理）
- research/
  - factor_research.py, feature_exploration.py など（DuckDB を使ったファクター計算・分析）
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — レジーム判定（OpenAI + ETF MA）
- data/ （ランタイム生成）
  - monitoring.db（デフォルト SQLITE_PATH）
  - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - kill.flag, stop_requested.flag, execution.pid など
- logs/（ログ出力先）

開発者向けメモ
----------------
- DuckDB 接続オブジェクトを各リサーチ関数に渡す設計なので、テスト時はインメモリ DB や fixture を準備してください。
- OpenAI 呼び出しは内部でラップしており、ユニットテスト時は該当関数を patch して外部通信を避けられます。
- monitoring_db.init_monitoring_db は冪等にテーブル／カラムを作成・マイグレーションします。既存 DB の互換性確保を行っています。
- config._load_env_file の挙動は OS 環境変数の保護（protected set）を考慮しています。テストで環境を完全に差し替える場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか、プロセス環境自体を設定してください。

コンタクト / 追加ドキュメント
----------------------------
- 各モジュール内の docstring に詳細な設計ノートや想定動作が記載されています。実装を読む際にはそちらも参照してください。
- 本 README は主要な使い方をまとめたものです。運用ガイド、PortfilioConstruction.md、StrategyModel.md 等の設計ドキュメントがプロジェクト内に存在する想定です（必要に応じて参照してください）。

以上です。必要であれば README に含めるコマンド例や .env.example のテンプレートを追加で作成します。どのレベルの利用例（最小構成でのローカル起動手順など）を追加しますか？