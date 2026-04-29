KabuSys
=======

日本株自動売買システムのサンプル実装。  
本リポジトリは、発注エンジン（Execution）、監視（Monitoring）、各種レポート生成ツール、設定ウィザード／検証ツールなどを含みます。

主な設計方針
- DuckDB（分析用）と SQLite（監視・履歴用）を併用
- 実運用（live）・ペーパートレード（paper_trading）を環境で切り替え可能
- 起動時や夜間バッチ結果の判定ロジックを独立した純粋関数で実装（テストしやすい）
- PID / stop flag による簡易プロセス制御

機能一覧
- Execution エンジン起動（run_execution.py）
  - Broker クライアント（実ブローカー / モック切替）
  - リスク管理（config/risk_config.yaml）
  - 注文管理、リコンシリエーション、起動時サマリ生成
  - paper_trading 環境は data/paper_trading.db に完全分離して記録
- Monitoring（run_monitoring.py）
  - SystemMonitor のポーリングループ（デフォルト 60 秒）
  - system_status / risk_logs 等の監視データ収集
- CLI レポート生成ツール
  - Pre-Market（run_pre_market_report.py）
  - Intraday Monitor（run_intraday_monitor.py）
  - Market Close Summary（run_market_close_report.py）
  - Signal Queue Confirmation（run_signal_queue_report.py）
  - Position Reconciliation View（run_position_reconciliation_report.py）
  - Paper Trading 検証レポート（tools/paper_verification_report.py）
- 設定関連
  - 対話式 .env ウィザード（config_setup.py）
  - 設定検証ツール（validate_config.py）
  - 環境変数ローダ（config.py）: .env / .env.local 自動読み込み（必要に応じ無効化可）
- 各種レポート用ビルダー（operations/*.py）
  - PreMarket / NightBatch / ExecutionStartup / MarketClose / SignalQueue / PositionReconciliation など
  - CLI 表示・JSON / Markdown フォーマット・アーティファクト保存機能

セットアップ手順（ローカル開発用）
1. 必要要件
   - Python 3.10 以上
   - システムにより追加ライブラリ（pip インストール）:
     - duckdb
     - pyyaml
     - psutil
   （プロジェクトに requirements.txt があればそれを使用してください）
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb pyyaml psutil
   - （requirements.txt があれば pip install -r requirements.txt）
4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - JQUANTS_BULK_API_KEY（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV （development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - （必要に応じ）LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗と見なす
6. データベース等の初期化
   - 本リポジトリでは init_monitoring_db 等が起動スクリプト内で呼ばれるため、通常は明示的な初期化は不要です。ただし初回起動時に data ディレクトリ等が作成されることを確認してください。

使い方（主要コマンド）
- Execution（自動売買エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db を利用
- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60）
- Pre-Market レポート生成
  - python -m kabusys.run_pre_market_report [--save] [--json]
- Intraday（ザラ場中）監視 CLI
  - python -m kabusys.run_intraday_monitor [--watch] [--interval N]
- Market Close レポート
  - python -m kabusys.run_market_close_report [--date YYYY-MM-DD] [--save] [--json]
- Signal Queue レポート
  - python -m kabusys.run_signal_queue_report [--date YYYY-MM-DD] [--save] [--json]
- Position Reconciliation レポート
  - python -m kabusys.run_position_reconciliation_report [--date YYYY-MM-DD] [--save] [--json] [--watch]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

プロセス制御 / フラグ
- 停止フラグ（自動停止）
  - data/stop_requested.flag を作成すると run_execution / run_monitoring 等は次回ループで停止を検知して終了します
  - 起動時にこのフラグが既に存在する場合、run_execution は起動を行わず終了する挙動があります
- PID ファイル
  - execution.pid / monitoring.pid を data 以下に書き込むことでプロセス稼働状況を他プロセスが確認できます
- Kill Switch（緊急停止）
  - config の KILL_FLAG_PATH（デフォルト data/kill.flag）ファイルが存在すれば Pre-Market 等は BLOCKED 判定になり、自動執行を防ぎます

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN, JQUANTS_BULK_API_KEY: J-Quants API 用
- KABU_API_PASSWORD, KABU_API_BASE_URL, KABU_TRADE_PASSWORD: kabuステーション API 用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの Fill 動作（instant, partial, never, reject。デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill flag を自動クリアするか（デフォルト 0。本番は 0 推奨）

ディレクトリ構成（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数／.env ローダ
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - run_intraday_monitor.py  — ザラ場中監視 CLI
    - run_pre_market_report.py — Pre-Market レポート CLI
    - run_market_close_report.py — Market Close レポート CLI
    - run_signal_queue_report.py — Signal Queue レポート CLI
    - run_position_reconciliation_report.py — Position Reconciliation CLI
    - operations/
      - pre_market_collector.py
      - pre_market_report.py
      - market_close_collector.py
      - market_close_report.py
      - intraday_collector.py
      - signal_queue_report.py
      - position_reconciliation_report.py
      - execution_startup_report.py
      - night_batch_report.py
    - execution/
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/
  - monitoring.db (default SQLite)
  - kabusys.duckdb (default DuckDB)
  - paper_trading.db (paper_trading 用)
  - stop_requested.flag / kill.flag / execution.pid / monitoring.pid
- artifacts/
  - pre_market/, market_close/, signal_queue/, execution_startup/, night_batch/ など（レポート保存先）

開発者向けメモ / トラブルシューティング
- Python のバージョンは 3.10 以上を推奨（型ヒントに | を使用）
- DuckDB を使用するクエリは read_only モードで接続することが多い（レポート系）
- .env の自動ロードは config.py 内で行われます。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 本番（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）の確認を推奨
- ペーパートレードと本番 DB は分離するよう実装されています（settings.paper_sqlite_path を使用）
- run_execution は起動時にリコンシリエーション（ブローカーとローカルDBの突合）を実施し、Execution Startup Summary を生成します。orders_no_status がある場合は BLOCKED になり、自動執行は中止されます
- 監視（monitoring）は KABUSYS_ENV に関わらず本番 sqlite_path を参照して監視テーブルを初期化します（init_monitoring_db）

ライセンス / 貢献
- （README にライセンス情報が必要であればここに記載してください）

以上がリポジトリの概要と基本的な使い方です。環境や運用に合わせて .env / config/*.yaml を適切に設定してご利用ください。問題がある場合は validate_config を実行して初期設定の不備を検出してください。