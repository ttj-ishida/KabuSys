README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした小規模なフレームワークです。  
このリポジトリは以下の主要機能を持ちます。

- 実行エンジン（ExecutionEngine）による発注 / 注文管理（本番・ペーパートレード対応）
- 監視コンポーネント（System / Trade / Risk）のポーリングとアラート
- ポートフォリオ構築ユーティリティ（候補選定、重みづけ、ポジションサイズ計算）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算等、DuckDB ベース）
- AI を用いたニュースセンチメント・レジーム判定（OpenAI）
- 各種 CLI（.env 設定ウィザード、設定検証、ペーパートレード検証レポート）

主な設計方針
- 実行と監視は分離（監視は本番の監視 DB を参照）
- Paper Trading（KABUSYS_ENV=paper_trading）は本番と DB を分離（data/paper_trading.db）
- 設定は .env/.env.local と環境変数で管理（自動ロード機構あり）
- DuckDB を分析用途に採用。SQLite は監視・履歴用

機能一覧
--------
- run_execution: ExecutionEngine を起動して発注処理を実行（本番/ペーパー切替）
  - KABUSYS_ENV=paper_trading のとき MockBrokerClient を使用し、paper_trading DB を使う
  - 停止フラグ（data/stop_requested.flag）検出で安全に停止
- run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）
  - 監視は常に production の sqlite_path を使用
  - 停止フラグ検知でループ終了
- config_setup: 対話式 .env 作成ウィザード
- validate_config: .env と config/*.yaml の整合性チェック（--strict モードあり）
- tools.paper_verification_report: ペーパー取引ログから検証レポート生成
- ai.news_nlp / ai.regime_detector: OpenAI を使ったニュースセンチメント算出・レジーム判定
- portfolio.*: 候補選定、重み付け、リスク調整、ポジションサイズ計算
- monitoring.*: 監視 DB（SQLite）操作、監視エンジン、Kill Switch、Risk Monitor など
- utils: ロギング設定・プロセス優先度設定ユーティリティ等

セットアップ手順
----------------

1. リポジトリをクローンし、作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール
   - 最低依存（例）:
     pip install duckdb psutil openai
   - validate_config で YAML 検証を有効にしたい場合:
     pip install PyYAML
   - 実際の運用では requirements.txt があればそちらを使ってください。

4. .env を作成する
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - あるいはプロジェクトルートに .env を手動で作成
   - 自動ロード: デフォルトで .env / .env.local をプロジェクトルートから読み込みます
     - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

重要な環境変数（主要）
- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API トークン
- KABU_API_PASSWORD      — （必須）kabuステーション API パスワード
- KABUSYS_ENV            — 実行環境: development / paper_trading / live （デフォルト: development）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視 DB（monitoring.db）のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL              — ログレベル（DEBUG/INFO/…）
- OPENAI_API_KEY         — OpenAI を利用する機能で必要
- MONITOR_POLL_INTERVAL  — run_monitoring のポーリング間隔（秒、デフォルト 60）

例: 最小 .env（例）
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO

使い方
------

実行系
- ExecutionEngine（発注実行）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH を使用
    - 起動時に data/stop_requested.flag が存在すれば起動を中止
    - 実行中に stop フラグが作成されると安全に停止する
  - ExecutionEngine は data/execution.pid に PID を書き込む（設定により変更可）

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60）
  - 監視は常に settings.sqlite_path を使用（環境に依らず本番 path を参照）
  - 停止は data/stop_requested.flag を作成

設定 / 検証
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

ツール
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

AI 機能
- ニューススコア算出 / レジーム判定には OPENAI_API_KEY が必要
- ai.news_nlp.score_news や ai.regime_detector.score_regime が公開 API（内部で OpenAI）を呼びます

ログ
- ログはデフォルトで logs/ ディレクトリへ出力されます（app_name によるファイル名 prefix）
  - 例: logs/execution.log, logs/monitoring.log
- setup_logging によりコンソール（stdout）と日次ローテートファイルハンドラが設定されます

停止 / Kill Switch
- 手動停止:
  - data/stop_requested.flag を作成すると run_* スクリプトは次回ポーリング時に停止します
- Kill Switch（自動停止）:
  - monitoring が条件を満たすと data/kill.flag を書き込み ExecutionEngine 側が検出して停止できます
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag が自動クリアされます（本番では 0 推奨）

ディレクトリ構成
----------------

以下は本リポジトリの主要なディレクトリ / ファイル構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI）によるスコア算出
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py      — SQLite テーブル作成 / 永続化 API
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py      (リポジトリ内に存在)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py      (リポジトリ内に存在)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                   —（実行時に使用する DB / フラグファイル等）
    - monitoring.db         — 監視用 SQLite（デフォルト）
    - paper_trading.db      — ペーパートレード用 SQLite（paper_trading 時）
    - kabusys.duckdb        — DuckDB（デフォルト path: data/kabusys.duckdb）
    - stop_requested.flag   — 停止リクエスト用フラグファイル
    - kill.flag             — Kill Switch フラグファイル
    - execution.pid         — 実行エンジンの PID を格納
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - research/               — ファクター計算・探索用モジュール
  - portfolio/              — ポートフォリオ構築ユーティリティ群

開発・運用上の注意
-----------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください
- KABUSYS_ENV=live（本番）では特に設定を慎重に行ってください（validate_config で警告表示）
- OpenAI を利用する箇所は API コストが発生します。テスト時はモック化して実行する設計になっています
- DuckDB / SQLite のパスは環境変数でオーバーライド可能です。バックアップや権限に注意してください
- process_priority.set_process_priority はプラットフォーム依存の権限問題で失敗することがあり、ログで警告されますが安全です

トラブルシュート
-----------------
- ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソール出力のみになります
- validate_config で YAML パースを行うには PyYAML が必要です。未インストール時は警告が出ます
- OpenAI の呼び出しでエラーが発生する場合、該当機能はフォールバック（0.0 等）やスキップで安全に継続する設計です

ライセンス・バージョン
---------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）

以上。必要であれば各コンポーネント（ExecutionEngine、MonitoringEngine、AI モジュール、ポートフォリオ関数など）の詳細ドキュメントや使用例を追加で作成します。どの部分を詳しく書いて欲しいか教えてください。