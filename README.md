KabuSys — 日本株自動売買システム（README）
=================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を構成する Python パッケージ群です。本リポジトリには以下の主要機能があります。

- 実行エンジン（ExecutionEngine）の起動スクリプト（本番 / ペーパートレード切替）
- 監視モジュール（SystemMonitor / TradeMonitor / RiskMonitor）とポーリングエンジン
- Kill Switch（閾値超過時の自動停止）とアラート連携（LINE 等の設定に対応）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- 研究用モジュール（ファクター計算、特徴量探索、IC 計算）
- AI を使ったニュースセンチメント（OpenAI API によるスコアリング）および市場レジーム判定
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）
- ペーパートレード検証レポート生成スクリプト

この README はコードベースに含まれる主要スクリプト・設定の使い方とディレクトリ構成をまとめたものです。

主な機能一覧
-------------
- 実行エンジン起動: run_execution.py
  - KABUSYS_ENV に応じて本番または paper_trading（MockBroker）を自動切替
  - Paper trading は本番 DB と分離（data/paper_trading.db を使用）
- 監視プロセス起動: run_monitoring.py
  - SystemMonitor を定期ポーリングしてシステム指標を SQLite に保存
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視エンジン: MonitoringEngine（各モニタを束ねてアラート / Kill Switch を評価）
- Kill Switch: 閾値到達時に data/kill.flag を作成して ExecutionEngine を停止
- リサーチ: ファクター計算（momentum/value/volatility）、forward returns、IC、統計要約
- AI モジュール:
  - kabusys.ai.news_nlp: raw_news を OpenAI に送って銘柄別センチメントを ai_scores に書き込み
  - kabusys.ai.regime_detector: ETF の MA と LLM によるマクロセンチメントを合成して市場レジーム判定
- ツール:
  - 設定ウィザード: kabusys.config_setup（.env の対話式生成）
  - 設定検証: kabusys.validate_config（.env / config/*.yaml / パス検証）
  - レポート: kabusys.tools.paper_verification_report（ペーパートレード検証レポート）

必要条件（代表）
----------------
（実行環境によって変わります。最低限の依存として以下を想定）
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config 検証で YAML の中身を確認したい場合）
- （標準ライブラリ）sqlite3 等

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリに入る。

2. 仮想環境を作成して有効化（例）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）:
   - pip install duckdb psutil openai PyYAML
   - （要件ファイルがある場合はそれを使ってください）

4. 対話式 .env 作成（推奨）:
   - python -m kabusys.config_setup
   - ウィザードが .env を生成します。既存の .env があれば読み込み・更新します。
   - 重要: .env は Git にコミットしないでください（認証情報を含むため）。

5. 設定検証（必須項目が揃っているか確認）:
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合: python -m kabusys.validate_config --strict

環境変数（主要）
----------------
主な環境変数とデフォルト値（重要なもの）:

- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading: MockBroker を使用し DB を分離
  - live: 実際の発注を行う想定（注意して使用）
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabuステーション API 用）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI を使う機能で必要
- PAPER_FILL_MODE — paper_trading 時の約定モード（instant|partial|never|reject）デフォルト: instant
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db  （Monitoring 用 SQLite）
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — ログ出力先（デフォルト logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 本番で kill.flag を自動クリアするか（0/1、デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動で .env を読み込まない

使い方（起動方法とツール）
--------------------------

1) 設定ウィザード（.env を生成）
   - python -m kabusys.config_setup
   - 生成後は python -m kabusys.validate_config で検証

2) ExecutionEngine（取引エンジン）を起動
   - 本番（KABUSYS_ENV=live）:
     - export KABUSYS_ENV=live
     - python -m kabusys.run_execution
   - ペーパートレード（MockBroker、データを data/paper_trading.db に保存）:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
   - 実行スクリプトはデーモン化は行いません。PID ファイル（data/execution.pid）や停止フラグ（data/stop_requested.flag）を扱います。

3) Monitoring（監視プロセス）を起動
   - デフォルト 60 秒間隔で SystemMonitor をポーリングし monitoring DB（SQLITE_PATH）に記録します:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は本番 sqlite_path を常に使用します（KABUSYS_ENV に依存せず本番用の監視 DB を使う設計）。

4) 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告も FAIL 扱いにできます

5) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で明示的に DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も使用できます。

停止・Kill 動作
---------------
- 手動で ExecutionEngine を停止したい場合:
  - kill switch を発動させたい/自動停止したい場合は KillSwitch が data/kill.flag を作成します（監視結果に応じて自動で書き込まれる）。ExecutionEngine 起動時 / 実行中はこの flag の存在をチェックして停止処理を行います。
- 起動スクリプトを安全に停止するには:
  - run_monitoring.py / run_execution.py は data/stop_requested.flag を検知すると自ら終了します。停止したい場合はこのファイルを作成してください。
  - stop フラグの位置: プロジェクトルート/data/stop_requested.flag

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30日保持）。
- コンソールには stdout 経由で出力されます。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で変更可能。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は主要なディレクトリ / ファイルの抜粋（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理、自動 .env ロード機能
  - config_setup.py                — 対話式 .env ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - execution/                      — 実行（注文・ブローカー・リスク等）関連
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                   — OpenAI を用いたニュースセンチメント
    - regime_detector.py            — MA と LLM を合成した市場レジーム判定
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - data/                           — 実行時生成ファイル（デフォルト）
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - logs/                           — ログ出力先（デフォルト）

設計上の注意点・運用上のポイント
--------------------------------
- .env の自動読み込み: config.py はプロジェクトルート（.git か pyproject.toml を探索）を基に .env, .env.local を自動読み込みします。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper trading は本番 DB と完全に分離されます。KABUSYS_ENV=paper_trading を指定すると paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。
- AI 機能を使用する際は OPENAI_API_KEY を必ず設定してください。ない場合は該当機能が例外を投げます（明示的にチェック）。
- 監視/実行プロセスは stop_requested.flag を検知して安全に終了するため、外部からの停止はそのフラグ作成を推奨します。
- Monitoring モジュールは監視指標を常に本番用 sqlite_path に記録します（監視は環境に依存しない設計）。
- ログディレクトリ作成に失敗してもコンソールログのみで継続するように設計されています。

トラブルシューティング（よくある問題）
----------------------------------------
- .env に必須値 (JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD) がない場合、Settings のプロパティ参照時に ValueError が発生します。config_setup と validate_config を利用して事前確認してください。
- OpenAI API で RateLimitError 等が発生する場合、news_nlp と regime_detector はリトライロジックを持っていますが、API キー/プランの見直しをしてください。
- DuckDB / SQLite のファイルパスが存在しないディレクトリにある場合、validate_config が警告を出します。起動時にディレクトリを自動作成することもありますが、明示的に作成して権限を確認してください。

ライセンス・貢献
----------------
（必要に応じてプロジェクトのライセンス・貢献手順をここに記載してください）

---

この README はコード内の docstring と実装から主要機能・運用方法を抜粋してまとめたものです。より詳細な内部実装や API の仕様は各モジュールの docstring を参照してください。必要であれば各サブモジュールごとの使い方マニュアルも作成できます。