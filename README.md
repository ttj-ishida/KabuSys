KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なパッケージです。  
主要な機能は以下の通りです:

- 注文の作成・管理・再同期（ExecutionEngine、OrderManager、Reconciler）
- Paper Trading 向けの分離された DB と Mock ブローカー
- 監視（System / Trade / Risk）とアラート（LINE Push）
- 監視結果の永続化（SQLite）とダッシュボード（Streamlit）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング・セクター制限）
- リサーチ用ファクター/特徴量計算（DuckDB を用いた処理）
- ニュースの NLP スコアリング・市場レジーム検出（OpenAI API を利用）
- 各種ツール（例: Paper Trading の検証レポート生成）

主要な設計方針：
- データ分析部分は DuckDB を用い、prices_daily / raw_financials などのテーブルを参照して純粋関数で計算する。
- 実行・発注周りは本番 DB と paper_trading 用 DB を分離可能。
- 外部 API（OpenAI、LINE 等）失敗時はフェイルセーフ（影響を局所化）する実装。

機能一覧
--------
- Execution
  - run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV による paper_trading 切替）
  - OrderManager / OrderRepository / Reconciler による注文管理・復旧処理
  - RiskManager による発注リスク管理（rate limit / utilization / drawdown 等）
- Monitoring
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で調整）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - MonitoringDB: SQLite にログを永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード（read-only 接続可）
  - AlertManager: LINE Push による通知（クールダウン管理）
  - KillSwitch: フラグファイルによる ExecutionEngine 停止シグナル
- Research / Portfolio
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン計算、IC（Spearman）など
  - portfolio: 候補選定、等・スコア加重、ポジション算出、セクターキャップ、レジーム乗数
- AI
  - ai.news_nlp: raw_news を OpenAI に送って銘柄別センチメントを ai_scores に書き込む
  - ai.regime_detector: マクロ記事 + ETF MA200 による市場レジーム判定
- Tools
  - tools.paper_verification_report: Paper Trading DB を集計して検証レポートを出力

セットアップ手順
----------------

前提
- Python 3.10+ を想定
- system に sqlite3（stdlib）、duckdb、psutil、requests、openai、streamlit が必要

推奨手順（開発環境）
1. リポジトリをクローン
   - git clone <repo-url>
   - ソース格納が src/ 配下であることを前提とする構成を想定

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（簡易）
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）
   - pip install -e .   （開発インストール可能であれば）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（デフォルトや説明は次節参照）

5. ディレクトリ作成
   - data/ フォルダ（DB や PID / flag ファイルを格納）を作成するのを推奨
     - mkdir -p data

主要な環境変数（代表）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- SQLITE_PATH: 監視用 SQLite DB のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで利用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE Push）用
- PAPER_FILL_MODE: paper trading の約定挙動（instant|partial|never|reject）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（Settings で参照）

使い方
------

パッケージとして実行する場合は、PYTHONPATH を src に通すかパッケージをインストールすること。

例: 開発時に src を PYTHONPATH に含める
- export PYTHONPATH=$(pwd)/src

1) 監視ループを起動（SystemMonitor を定期実行）
- MONITOR_POLL_INTERVAL を変更したい場合:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- デフォルトは 60 秒（環境変数で上書き）

挙動:
- プロセス優先度を "high" に設定しようとする（psutil を利用。権限不足なら警告で続行）
- monitoring DB (settings.sqlite_path) を接続・初期化（init_monitoring_db）
- SystemMonitor.check_once() のループを回す
- data/stop_requested.flag が存在するとループを終了

2) Execution Engine を起動（発注エンジン）
- KABUSYS_ENV=paper_trading を指定すると MockBroker を使い、paper 用 DB（PAPER_TRADING_SQLITE_PATH）を使用
- python -m kabusys.run_execution

挙動:
- process priority を "high" に設定しようとする
- Settings による環境判定（live/paper_trading/development）
- BrokerClientFactory によりブローカークライアントを生成（本番か Mock）
- ExecutionEngine をスレッドで起動し、data/stop_requested.flag の確認で停止

3) Streamlit ダッシュボード
- 監視 DB の read-only 表示用
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- DB が読めない場合は警告を出す（MonitoringEngine 起動を推奨）

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB は data/paper_trading.db（--db で上書き可能）
- 出力: uptime / fill rate / send rate / latency(P95) などをテキストで表示し PASS/FAIL 判定を行う

5) AI 機能
- ai.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡して実行
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 実行には OPENAI_API_KEY が必要（引数で上書き可能）。失敗時は安全側フォールバック設計あり。

監視 / 停止フラグ
- data/stop_requested.flag: run_monitoring / run_execution の外部停止に使用。存在すると起動中ループは停止する。
- data/kill.flag: KillSwitch が書き込み、ExecutionEngine に停止を促す（Execution は kill.flag を見て停止）。
- PID ファイル: data/execution.pid（Settings.pid_file_path）が用いられ、SystemMonitor は stale PID を検知して削除しアラートを上げる。

DB とスキーマ
- monitoring_db.init_monitoring_db(conn) によりテーブルを作成（冪等）
  - system_status, trade_logs（latency_ms カラムを含む）, positions, risk_logs, dashboard
- MonitoringDB クラスは読み書きのユーティリティを提供（log_system_status, log_trade_event, upsert_dashboard など）
- init_monitoring_db は既存 DB へのマイグレーション（カラム追加）も実施します（peak_value / latency_ms 等）

トラブルシューティング（よくある注意点）
- .env の自動読み込みはプロジェクトルートの検出に .git または pyproject.toml を使います。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- psutil の優先度変更は OS と権限に依存します。権限不足の場合は警告が出て続行します。
- DuckDB の executemany はバージョンによって空リストを渡すとエラーになるため、ai/news_nlp 等は空チェックを行っています。
- OpenAI API を利用する機能は外部サービス依存のため、ネットワーク/API エラー時はフォールバックして継続する実装ですが、スコアが欠落する点は留意してください。

ディレクトリ構成
----------------

（主要ファイルを抜粋して記載。実際のリポジトリは src/ 配下にパッケージがある想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                          — 環境変数 / Settings 管理（.env 自動読み込みロジックを含む）
    - run_monitoring.py                  — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py                   — ExecutionEngine 起動スクリプト（paper_trading 切替）
    - tools/
      - __init__.py
      - paper_verification_report.py     — Paper Trading 検証レポート生成ツール
    - monitoring/
      - __init__.py
      - monitoring_db.py                 — SQLite スキーマと MonitoringDB ラッパー
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - execution_engine.py (想定)
      - broker_factory.py (想定)
      - broker_api.py (想定)
      - order_record.py (想定)
      - risk_manager.py (想定)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/ (実行時に使用するファイルを置く場所)
      - monitoring.db (デフォルト)
      - paper_trading.db (paper_trading 用デフォルト)
      - kabusys.duckdb (DuckDB データファイル)
      - execution.pid / kill.flag / stop_requested.flag

ライセンス・貢献
----------------
- この README はコードベースのドキュメント化を目的に簡潔にまとめたものです。実際のライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。

補足
----
- 実行コマンド例:
  - 監視開始: MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - 実行エンジン起動: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - Streamlit ダッシュボード: streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

もっと詳しい使い方や API、内部設計は各モジュールの docstring（ソース内コメント）を参照してください。必要であれば特定機能の詳しいドキュメント（設定例・API 仕様・シーケンス図など）を別途作成します。