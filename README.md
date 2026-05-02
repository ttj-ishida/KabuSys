KabuSys — 日本株自動売買システム（README）
=====================================

概要
----
KabuSys は日本株向けの自動売買運用を支援する Python コードベースです。  
主な役割はデータ収集・夜間バッチ・シグナル生成・発注（実取引／ペーパートレード）・各種運用レポート生成・稼働監視などです。

このリポジトリには、エンジン起動スクリプト、監視・確認用 CLI、レポート生成ロジック、設定管理ウィザードなどが含まれます。実行時に SQLite（監視・履歴）と DuckDB（分析用）を使用します。

主な特徴
--------
- Execution エンジン（実発注 / ペーパートレード切替可能）
- System Monitoring（監視プロセスのポーリング）
- インタラクティブな環境設定ウィザード（.env を生成）
- 設定検証ツール（validate_config）
- 各種レポート生成（Pre-Market / Market-Close / Performance / Signal Queue / Position Reconciliation / Execution Startup / Night Batch 等）
- Paper Trading 向けの検証・レポートツール
- レポートは CLI 表示・JSON・Markdown 保存をサポート（artifacts/ 配下へ保存）

セットアップ手順
----------------

1. リポジトリをクローン
   - 例: git clone ...

2. Python 環境を準備
   - 推奨: 仮想環境を作成してアクティベートする（venv / poetry / pipenv 等）

3. 依存パッケージをインストール
   - 要件ファイルがあればそれに従ってください。
   - このコードベースで使われている主なライブラリ:
     - duckdb
     - pyyaml (YAMLのロード)
     - sqlite3（標準ライブラリ）
     - そのほかロギング等のユーティリティ

4. .env の作成（推奨）
   - 対話式ウィザードで簡単に作成できます:
     - python -m kabusys.config_setup
   - 生成後に設定が整っているか確認:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

5. データディレクトリの準備
   - デフォルトの DB / PID / フラグのパスは project_root/data 下にあります。必要に応じてディレクトリを作成してください（起動時に自動作成される場合もあります）。
   - 例:
     - data/kabusys.duckdb（DuckDB）
     - data/monitoring.db（SQLite 監視 DB）
     - data/paper_trading.db（ペーパートレード用、KABUSYS_ENV=paper_trading 時に使用）

6. 設定ファイル
   - config/ 以下に YAML ファイル群（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）が期待されます。テンプレートがあればそれを配置してください。
   - risk_config.yaml は Execution 起動時に読み込まれ、パラメータ検証（範囲チェック）を行います。

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- JQUANTS_BULK_API_KEY: J-Quants Bulk API キー（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant / partial / never / reject）
- DUCKDB_PATH: DuckDB のパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill flag を自動クリアするか（1 にするとクリア、デフォルト 0）

使い方（主要コマンド）
---------------------

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db）に分離して記録します。
    - 起動時に起動時総資産を算出し、Reconciler によるリコンシリエーションを実行、ExecutionEngine をスレッドで開始します。
    - 停止は data/stop_requested.flag の作成で受け付けます（スクリプトは起動前にフラグが立っていると起動しません）。
  - 注意: リスク設定は config/risk_config.yaml から読み込み、値の妥当性をチェックします。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（デフォルト 60 秒）。
  - 監視用 SQLite は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。
  - 停止は data/stop_requested.flag を作成。

- ザラ場中監視（対話/ウォッチ）
  - python -m kabusys.run_intraday_monitor
  - 例: python -m kabusys.run_intraday_monitor --watch --interval 60

- Pre-Market レポート
  - python -m kabusys.run_pre_market_report [--json] [--save]
  - 戻り値: status が BLOCKED の場合は exit code 1

- Market Close Summary
  - python -m kabusys.run_market_close_report [--date YYYY-MM-DD] [--json] [--save]

- Performance レポート（日次/週次/月次）
  - python -m kabusys.run_performance_report --type daily --from YYYY-MM-DD --to YYYY-MM-DD [--env live|paper_trading] [--save]

- Signal Queue 確認（翌営業日の発注予定）
  - python -m kabusys.run_signal_queue_report [--date YYYY-MM-DD] [--json] [--save]
  - exit code: report.status == "READY" ? 0 : 1

- Position Reconciliation View
  - python -m kabusys.run_position_reconciliation_report [--date YYYY-MM-DD] [--json] [--save] [--watch --interval N]

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH で DB を指定可能

ログ・プロセス管理・フラグ
-------------------------
- PID ファイル
  - run_execution は data/execution.pid（デフォルトは Settings.pid_file_path）
  - run_monitoring は data/monitoring.pid
- 停止フラグ
  - data/stop_requested.flag を作成すると run_execution/run_monitoring 等は検知して優雅に停止します。
- Kill Flag
  - Settings.kill_flag_path（デフォルト data/kill.flag）に基づく Kill Switch 機構があります。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します。

データ保存 / レポート保存先
---------------------------
- artifacts/ フォルダ配下に各種レポートを保存できます（--save オプション）。
  - artifacts/pre_market/{YYYY-MM-DD}/
  - artifacts/market_close/{YYYY-MM-DD}/
  - artifacts/performance/{env}/{type}/{period}/
  - artifacts/signal_queue/{YYYY-MM-DD}/
  - artifacts/execution_startup/{YYYY-MM-DD}/
  - artifacts/night_batch/{YYYY-MM-DD}/
- 各保存関数は summary.json / report.md / warnings.json などを出力します。

ディレクトリ構成（抜粋）
-----------------------
以下は主なファイル／ディレクトリです（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数読み込み・Settings クラス
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - run_intraday_monitor.py — インタラクティブなザラ場監視 CLI
  - run_pre_market_report.py
  - run_market_close_report.py
  - run_performance_report.py
  - run_signal_queue_report.py
  - run_position_reconciliation_report.py
  - tools/
    - paper_verification_report.py
  - operations/
    - pre_market_collector.py / pre_market_report.py
    - market_close_collector.py / market_close_report.py
    - performance_collector.py / performance_report.py
    - signal_queue_report.py
    - execution_startup_report.py
    - night_batch_report.py
    - position_reconciliation_report.py
    - intraday_collector.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (ランタイムで使用: DB / pid / flag 等が置かれる想定)
  - config/ (YAML 設定ファイル群)

設計上の注意点・運用メモ
-----------------------
- 環境読み込みの順序:
  - OS 環境変数 > .env.local（上書き） > .env（未設定時のみ）という優先順位で自動ロードされます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ペーパートレード:
  - KABUSYS_ENV=paper_trading の場合、実取引とは完全に分離した SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。PAPER_FILL_MODE により約定の振る舞いを制御できます。
- risk_config.yaml:
  - run_execution は config/risk_config.yaml を読み込み、値の妥当性を厳密にチェックします。設定ミスがあると起動に失敗します。
- 監視:
  - run_monitoring は MONITOR_POLL_INTERVAL（秒）でポーリング。0 以下や不正な値はデフォルト（60 秒）にフォールバックします。
- レポート:
  - 各レポート生成モジュールは基本的に DB 参照部分とレポート構築/フォーマットを責務分離しています。CLI 側は DB 接続やオプション解析を行い、レポートロジックは純粋関数が多く再利用しやすい設計です。

よくある運用コマンド例
---------------------
- .env を作って検証する:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 夜間バッチ完了後に Pre-Market を確認:
  - python -m kabusys.run_pre_market_report --save

- 実エンジンをデーモンで起動（簡易）:
  - nohup python -m kabusys.run_execution &

- 監視プロセス起動:
  - nohup python -m kabusys.run_monitoring &

- 翌営業日のシグナル確認:
  - python -m kabusys.run_signal_queue_report --date 2026-04-28 --json

免責・補足
----------
この README はリポジトリ内のコードから読み取れる仕様をまとめたものです。実際の環境では config/*.yaml や .env の内容、外部ブローカー API の接続設定、DB の初期データなどを適切に準備してください。

問題報告 / 変更点
-----------------
バグ報告や仕様改善は issue を作成してください。大きな設計変更を行う際はまず設計提案（PR）をお願いします。

--- End ---