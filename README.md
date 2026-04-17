README — KabuSys (日本株自動売買システム)
===============================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。本リポジトリには以下の主要機能が含まれます:
- 実行エンジン（ExecutionEngine）起動用スクリプト
- 監視（Monitoring）コンポーネント（プロセス監視・データ鮮度・注文監視・リスク監視）
- ポートフォリオ構築・位置サイズ計算の純粋関数群
- 研究用ファクター計算・特徴量解析ユーティリティ（DuckDB ベース）
- AI を用いたニュースセンチメント / 市場レジーム判定（OpenAI）
- 環境設定ウィザード・設定検証ツール・検証レポート生成ツール

特徴一覧
--------
- 環境分離:
  - KABUSYS_ENV により development / paper_trading / live を切替え。paper_trading は発注ロジックをモックし、専用 DB（data/paper_trading.db）を使用。
- 監視:
  - system_monitor, trade_monitor, risk_monitor を組み合わせた MonitoringEngine。
  - kill_switch によるフラグファイルで ExecutionEngine を安全に停止可能（data/kill.flag）。
- ポートフォリオ構築:
  - 候補選定、等配分／スコア配分、リスクベースの位置サイズ計算、セクターキャップ適用などの純粋関数実装。
- 研究 (research):
  - DuckDB に格納した prices_daily / raw_financials を参照してファクターや将来リターン、IC、統計サマリを計算。
- AI:
  - OpenAI を使ったニュースの銘柄別センチメント評価（ai.news_nlp.score_news）と、市場レジーム判定（ai.regime_detector.score_regime）。
  - リトライ・バッチ処理・結果検証などの堅牢な実装。
- ツール:
  - .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading の検証レポート生成スクリプト（tools.paper_verification_report）

セットアップ手順
--------------
1. リポジトリをクローン
   - 任意の場所にクローンして下さい。

2. Python 環境を作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 必須: duckdb, psutil
   - AI 機能を使う場合: openai
   - 設定検証で YAML 検証を行うには: PyYAML（任意）

4. .env ファイルの作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参照して手動作成。
   - 最低必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI を使う場合:
     - OPENAI_API_KEY を設定

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする: python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ 以下に DB・PID・フラグが作成されます。自動生成されることが多いですが手動で作る場合:
     - mkdir -p data

基本的な使い方
------------

起動スクリプト
- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
  - 監視は常に production 用の sqlite_path（Settings.sqlite_path）を参照します。
  - 終了: data/stop_requested.flag をプロジェクトルートの data に作成すると監視ループは検知して終了します。

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が既にあると起動せず終了します。
  - 実行中は data/execution.pid に PID が書き込まれます。停止には上書きフラグや kill.flag を使用。

停止・Kill スイッチ
- Kill Switch:
  - リスク条件（例: ドローダウン閾値超過、ポジション上限超過）により data/kill.flag を出力し ExecutionEngine を停止させます。
  - Kill フラグの自動クリアは KILL_FLAG_CLEAR_ON_START=1 で有効（本番では推奨しません）。

Paper Trading 検証レポート
- ツール実行:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定可（デフォルト data/paper_trading.db）。

AI（ニュース / レジーム）
- 関数呼び出し:
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection
    - target_date: date オブジェクト（日付基準）
    - api_key: 省略時は環境変数 OPENAI_API_KEY を参照
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意:
  - OPENAI_API_KEY が未設定だと例外になります。
  - 大量 API 呼び出しはレート制限やコストに注意。

設定管理（Settings）
- Settings クラスは環境変数を参照します。主なプロパティ:
  - env / is_live / is_paper / is_dev
  - duckdb_path（デフォルト: data/kabusys.duckdb）
  - sqlite_path（デフォルト: data/monitoring.db）
  - paper_sqlite_path（デフォルト: data/paper_trading.db）
  - pid_file_path（デフォルト: data/execution.pid）
  - kill_flag_path（デフォルト: data/kill.flag）
  - PAPER_FILL_MODE（paper_trading の fill 動作）
  - CPU / memory / disk の閾値など

その他ユーティリティ
- process_priority.set_process_priority(level) で現在プロセスの優先度設定（psutil 必須）。
- research モジュールは DuckDB 接続を受け取りファクター等を計算する関数群を提供します。

ディレクトリ構成（主要ファイル）
-------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 単体起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite の永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py       — 滞留注文 / 約定異常の監視
    - risk_monitor.py        — ドローダウン・ポジション上限の監視
    - kill_switch.py         — kill.flag 作成 / クリア
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信の抽象化、実装による）
  - execution/                — 発注関連（BrokerClientFactory / ExecutionEngine 等）
  - data/                     — データパイプライン、統計ユーティリティ（DuckDB 参照）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py     — 市場レジーム判定（OpenAI 連携）
  - tools/
    - paper_verification_report.py
  - その他モジュール...

環境変数（主な一覧とデフォルト）
--------------------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / デフォルトあり:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - KABU_API_BASE_URL: http://localhost:18080/kabusapi
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート用）
  - OPENAI_API_KEY（AI 機能）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）
  - PAPER_FILL_MODE（instant, partial, never, reject。paper_trading 用）
  - KILL_FLAG_CLEAR_ON_START（0/1、本番では 0 推奨）

トラブルシューティング（よくある点）
-----------------------------------
- validate_config で YAML 検証をしたいが PyYAML がない:
  - PyYAML をインストールするか、警告は無視して下さい（YAML 検証がスキップされます）。
- OpenAI 関連で Key エラー:
  - OPENAI_API_KEY を .env に追加するか環境変数に設定してください。
- DB ファイルが見つからない:
  - 実行スクリプトは必要時に監視 DB テーブルを作成しますが、DuckDB のデータは事前にロード/準備する必要があります（データパイプライン側参照）。

ライセンス・貢献
----------------
- この README はコードベースに基づく技術ドキュメントです。実際のライセンス・貢献フローはリポジトリ上の LICENSE / CONTRIBUTING を確認してください。

補足
----
- 本 README は現行のソースコード（src/kabusys 以下）を基に作成しています。詳細な実装や追加設定は各モジュールの docstring を参照してください（例: ai.news_nlp, research.*, portfolio.*）。必要であればセクション別の使用例や API 参照を追加で作成します。