# KabuSys — README (日本語)

KabuSys は日本株向けの自動売買運用ツール群です。本リポジトリには Execution（発注エンジン）、Monitoring（稼働監視）、各種レポート生成スクリプト、環境設定ウィザードなどの CLI モジュールが含まれています。

概要・セットアップ・使い方・ディレクトリ構成をこの README にまとめます。

---

## プロジェクト概要

- 自動売買エンジン（ExecutionEngine）とそれを補助するコンポーネント（OrderManager、RiskManager、Reconciler 等）。
- 運用／監視用モジュール：
  - System Monitor（定期ポーリングでシステム状態を記録）
  - Intraday Monitor（ザラ場中の状態確認 CLI）
  - 各種レポート（Pre-Market / Market Close / Performance / Signal Queue / Position Reconciliation / Night Batch など）
- Paper Trading モードをサポート（本番 DB と分離された mock ブローカー・DB を利用）。
- 設定は環境変数（.env）ベース。config/*.yaml で詳細設定を行う。

---

## 主な機能一覧

- Execution（自動発注）:
  - ブローカークライアント抽象化（実ブローカ or MockBroker）
  - リスク管理（risk_config.yaml に基づく）
  - 注文管理・リコンシリエーション・起動時サマリ生成
- Monitoring:
  - 定期的にシステム状態を SQLite に記録（system_status 等）
  - 停止フラグ監視（data/stop_requested.flag）
- レポート:
  - Pre-Market Report（朝の実行可否判定）
  - Market Close Summary（引け後確認）
  - Execution Startup Summary（起動時の整合性チェック）
  - Signal Queue Confirmation（翌営業日の発注シグナル確認）
  - Position Reconciliation（ポジション差分チェック）
  - Performance（運用成績：日次/週次/月次）
  - Night Batch Report（夜間バッチ結果の判定）
  - Paper Trading 検証用レポート（tools/paper_verification_report）
- 環境管理:
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）

---

## 動作要件（概略）

- Python 3.10+
- 必要ライブラリ（例）:
  - duckdb
  - pyyaml
  - （実際に動かす際は requirements.txt / pyproject.toml を参照してください）
- ファイル書き込み可能な data/ および artifacts/ ディレクトリ

---

## セットアップ手順

1. リポジトリをチェックアウト／クローン
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は duckdb, pyyaml などを個別にインストール）
4. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - または .env.example を参考に .env を作成
   - 自動ロード: パッケージロード時にプロジェクトルートの `.env` / `.env.local` が自動読み込みされます（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
6. データベース初期化 / データ投入
   - DuckDB（data/kabusys.duckdb）や monitoring 用 SQLite（data/monitoring.db）を配置/生成します。
   - night-batch 等の前提データが必要です（実運用では夜間処理により生成）。

---

## 主要な環境変数（代表）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）  
  - paper_trading: MockBroker を使用し、専用 DB(data/paper_trading.db)へ記録
- JQUANTS_REFRESH_TOKEN, JQUANTS_BULK_API_KEY: J-Quants API
- KABU_API_PASSWORD, KABU_API_BASE_URL, KABU_TRADE_PASSWORD: kabuステーション API
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading における約定モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START: 起動時に Kill Flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

注意: Settings クラスは自動で .env を読み込みます。必須環境変数が未設定だと起動時にエラーになります。

---

## .env 作成／更新

対話ウィザード:
- python -m kabusys.config_setup

ウィザードで生成される .env をプロジェクトルートに置いてください。.env は機密情報を含むため Git にコミットしないでください。

.env の自動読み込みはデフォルトで有効です。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 設定検証

- python -m kabusys.validate_config
  - --strict を付けると警告も失敗として exit code 1 を返します

validate_config は .env の値や config/*.yaml の存在・パース可否、DB パスの親ディレクトリの存在などをチェックします。

---

## 実行／操作方法（主要 CLI）

各モジュールはモジュール実行（python -m）で使えます。以下に代表的なコマンド例を示します。

- Execution（自動発注エンジン起動）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると paper_trading 用の MockBroker と data/paper_trading.db を使用します。
  - 起動時にリコンシリエーションを行い、ExecutionEngine を別スレッドで起動します。
  - 停止は data/stop_requested.flag ファイルを作成することで行います。

- Monitoring（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視プロセスは data/monitoring.pid に PID を書き出します。停止も data/stop_requested.flag で行います。
  - 注: Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します。

- ザラ場モニタ（CLI）
  - python -m kabusys.run_intraday_monitor
  - --watch: 一定間隔で更新（--interval で秒指定、デフォルト 30）

- Pre-Market Report
  - python -m kabusys.run_pre_market_report [--save] [--json]

- Market Close Summary
  - python -m kabusys.run_market_close_report [--date YYYY-MM-DD] [--save] [--json]

- Signal Queue Confirmation View
  - python -m kabusys.run_signal_queue_report [--date YYYY-MM-DD] [--save] [--json]

- Position Reconciliation View
  - python -m kabusys.run_position_reconciliation_report [--date YYYY-MM-DD] [--save] [--json] [--watch] [--interval N]

- Performance Report
  - python -m kabusys.run_performance_report --type daily|weekly|monthly [--env live|paper_trading] [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--save]

- Paper Trading 検証スクリプト（ツール）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

- 設定ウィザード
  - python -m kabusys.config_setup

---

## 停止・フラグ・PID ファイルについて

- 停止フラグ:
  - data/stop_requested.flag を作成すると、実行中の Execution / Monitoring は次のポーリングやループ内で停止します。
- PID ファイル:
  - 実行プロセスは data/execution.pid, data/monitoring.pid などに PID を書き出します。プロセス終了時に削除されます（例外時は残ることがあるので注意）。
- Kill Switch / Kill Flag:
  - Settings.kill_flag_path（デフォルト data/kill.flag）で指定されます。設定によっては起動時に自動でクリアすることもあります（KILL_FLAG_CLEAR_ON_START=1）。

---

## レポートの保存（artifacts ディレクトリ）

レポートの多くは artifacts/ 以下に保存できます（--save オプション）。保存先の例:

- artifacts/pre_market/{YYYY-MM-DD}/
- artifacts/market_close/{YYYY-MM-DD}/
- artifacts/signal_queue/{YYYY-MM-DD}/
- artifacts/execution_startup/{YYYY-MM-DD}/
- artifacts/performance/{env}/{type}/{period}/
- artifacts/night_batch/{YYYY-MM-DD}/

保存されるファイル例:
- report.md（Markdown レポート）
- summary.json（集約データ）
- warnings.json（警告一覧）

---

## Paper Trading（ペーパートレード）関連

- KABUSYS_ENV=paper_trading を指定すると、MockBrokerClient を使用します。
- Paper 用 SQLite は PAPER_TRADING_SQLITE_PATH（Settings.paper_sqlite_path）で指定します（デフォルト data/paper_trading.db）。本番 SQLite（SQLITE_PATH）とは完全に分離されます。
- PAPER_FILL_MODE（instant|partial|never|reject）により mock の約定挙動を設定できます。

---

## ログ・プロセス優先度

- 各プロセスは起動時に setup_logging(app_name=...) を呼び、Settings.log_level に従ってログ出力レベルを制御します。
- run_execution / run_monitoring は起動時に set_process_priority("high") を呼んでプロセス優先度を上げます（環境依存）。

---

## よくあるトラブルと対処

- DB 接続エラー:
  - DUCKDB_PATH / SQLITE_PATH のファイルパスや親ディレクトリに書き込み権限があるか確認してください。
- .env が反映されない:
  - プロジェクトルートが自動検出されない（.git や pyproject.toml がない）場合は自動読み込みがスキップされます。明示的に環境変数をエクスポートするか、KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- MONITOR_POLL_INTERVAL に無効な値をセットした場合はデフォルト 60 秒にフォールバックします（警告ログ出力）。
- PID ファイルが残る:
  - 強制終了や例外時に pid ファイルが残ることがあります。該当 PID が存在しないことを確認して手動で削除してください。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリーの主要ファイル / モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 定義、自動 .env ロード
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_intraday_monitor.py  — ザラ場モニタ CLI
  - run_pre_market_report.py — Pre-Market Report エントリ
  - run_market_close_report.py
  - run_signal_queue_report.py
  - run_position_reconciliation_report.py
  - run_performance_report.py
  - run_performance_report.py
  - operations/
    - pre_market_collector.py / pre_market_report.py
    - market_close_collector.py / market_close_report.py
    - execution_startup_report.py
    - signal_queue_report.py
    - position_reconciliation_report.py
    - performance_collector.py / performance_report.py
    - night_batch_report.py
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
  - tools/
    - paper_verification_report.py

- data/       — デフォルトデータベース（data/kabusys.duckdb, data/monitoring.db 等）、flag/pid ファイル
- config/     — system_config.yaml, risk_config.yaml 等（テンプレートは scripts/generate_config.py 等を参照）
- artifacts/  — レポート保存先（実行時に自動作成）

（フルツリーは実際のリポジトリでご確認ください）

---

## 開発者向けメモ

- Settings クラスを通じて設定にアクセスしてください（kabusys.config.Settings）。
- レポートビルド関数は純粋関数として設計されているものが多く、単体テストが容易です（DB 参照をする collect_* と分離）。
- 監視・実行プロセスは stop flag による外部停止を想定しているため、運用では自動化した停止／再起動フローを準備してください。

---

必要に応じて README を追加拡張します。特に導入手順（Docker / systemd ユニット / cron / CI）や詳細な設定例が必要なら教えてください。