# KabuSys

日本株自動売買システムの一部（起動スクリプト・設定管理・レポート生成等）。  
このリポジトリは、実行エンジン（Execution）、監視（Monitoring）、日中監視や各種レポート生成ツールを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は、銘柄選定やポートフォリオ構築のバッチ処理と、翌営業日の自動発注を行う実行エンジン、ならびに稼働監視や各種レポート生成を行うツール群を提供します。  
主な機能は以下の通りです:

- ExecutionEngine による自動発注（本番 / ペーパートレード）
- SystemMonitor による定期ポーリング監視
- 日中監視 CLI（状態サマリの表示・ウォッチモード）
- Pre-market / Market-close / Performance / Position reconciliation / Signal queue の各種レポート生成
- .env を生成する対話式設定ウィザード、設定検証ツール
- Paper Trading 検証用ツール

データ格納:
- 分析向けに DuckDB（デフォルト: `data/kabusys.duckdb`）
- 監視・注文履歴等は SQLite（デフォルト: `data/monitoring.db`）
- Paper Trading 実行時は専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離

---

## 機能一覧（要点）

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB を利用
  - 起動時にリコンシリエーションを実行し、Execution Startup Summary を出力 / 保存可能
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 停止フラグ / PID 管理を行う（`data/stop_requested.flag`, `data/monitoring.pid` 等）
- run_intraday_monitor.py
  - ザラ場中監視 CLI（ワンショット表示 or --watch 自動更新）
- run_pre_market_report.py / run_market_close_report.py / run_performance_report.py / run_position_reconciliation_report.py / run_signal_queue_report.py
  - 各種レポート生成（CLI 引数で日付指定 / JSON 出力 / 保存）
- config_setup.py
  - .env を対話式に生成・更新するウィザード
- validate_config.py
  - .env と config/*.yaml のチェックを行い設定ミスを検出
- tools/paper_verification_report.py
  - Paper Trading データを集計し PASS/FAIL 判定を行う検証レポート

その他: 各種 operations モジュールは、レポート構築ロジック（純粋関数）とフォーマッタ（CLI/JSON/Markdown）を提供。

---

## 必要条件（推奨）

- Python 3.10+
- pip（依存パッケージのインストールに使用）
- SQLite（Python に組み込み）
- DuckDB Python パッケージ
- PyYAML（設定ファイル検証・読み込みで使用）

推奨パッケージ（代表例）:
- duckdb
- PyYAML

requirements.txt がある場合は次を実行してください:
```
pip install -r requirements.txt
```
requirements.txt がない場合は最低限:
```
pip install duckdb pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン／配置
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 環境を準備（仮想環境を推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. .env を作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants / kabuステーション の認証情報や DB パスなどを入力します。

   自動ロードを無効化したい場合は環境変数を設定:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告もエラー扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```

5. データベース
   - DuckDB ファイル（デフォルト `data/kabusys.duckdb`）や SQLite（`data/monitoring.db`, `data/paper_trading.db`）は config または .env で指定できます。
   - 必要に応じて初期データを配置してください（本リポジトリに生成スクリプトがある場合はそちらを利用）。

---

## 主要な環境変数（代表）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意／設定項目:
- KABUSYS_ENV = development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））
- PAPER_FILL_MODE（paper_trading のフィルモード: instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START（本番環境での自動 kill フラグクリア: 0/1）

注意: .env は Git にコミットしないでください（config_setup も警告します）。

---

## 使い方（コマンド例）

- 実行エンジン起動（本番 / ペーパートレードは KABUSYS_ENV で制御）
  ```
  python -m kabusys.run_execution
  ```

- 監視プロセス起動
  ```
  python -m kabusys.run_monitoring
  # ポーリング間隔を変更する例（30秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 日中監視（ワンショット）
  ```
  python -m kabusys.run_intraday_monitor
  ```

  監視（更新）モード:
  ```
  python -m kabusys.run_intraday_monitor --watch --interval 60
  ```

- Pre-Market レポート（保存 / JSON 出力）
  ```
  python -m kabusys.run_pre_market_report --save
  python -m kabusys.run_pre_market_report --json
  ```

- Market Close Summary
  ```
  python -m kabusys.run_market_close_report --date 2026-04-28 --save
  ```

- Performance レポート
  ```
  python -m kabusys.run_performance_report --type daily --from 2026-03-01 --to 2026-03-31 --save
  ```

- Position Reconciliation レポート（ウォッチ）
  ```
  python -m kabusys.run_position_reconciliation_report --watch --interval 300
  ```

- Signal Queue Confirmation
  ```
  python -m kabusys.run_signal_queue_report --date 2026-04-28 --save --json
  ```

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- .env 対話式作成
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

停止制御:
- 自動処理を停止させたい場合、プロジェクトルートの `data/stop_requested.flag` を作成します。多くのスクリプトがこのフラグを参照して安全に停止します。
- PID ファイルは `data/*.pid`（例: `data/execution.pid`, `data/monitoring.pid`）に書き込まれます。

出力/保存:
- 各種レポートは `artifacts/` 以下に保存されます（例: `artifacts/pre_market/{date}`、`artifacts/performance/...`、`artifacts/signal_queue/{date}` など）。

---

## 主要ディレクトリ構成

(主要ファイルのみ抜粋)

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込みロジックと Settings クラス
  - config_setup.py          — 対話式 .env 作成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_intraday_monitor.py  — 日中監視 CLI
  - run_pre_market_report.py
  - run_market_close_report.py
  - run_performance_report.py
  - run_position_reconciliation_report.py
  - run_signal_queue_report.py
  - operations/
    - pre_market_collector.py / pre_market_report.py
    - market_close_collector.py / market_close_report.py
    - performance_collector.py / performance_report.py
    - position_reconciliation_report.py
    - signal_queue_report.py
    - execution_startup_report.py
    - night_batch_report.py
    - intraday_collector.py
  - execution/                — 実行系（BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler, OrderRepository 等）
  - monitoring/               — 監視用（SystemMonitor, monitoring_db 初期化等）
  - utils/                    — logging_setup, process_priority 等ユーティリティ
  - tools/
    - paper_verification_report.py

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

- data/
  - monitoring.db (SQLite、デフォルト)
  - kabusys.duckdb (DuckDB、デフォルト)
  - paper_trading.db (Paper Trading 用 SQLite、デフォルト)
  - stop_requested.flag, *.pid など

- artifacts/
  - pre_market/
  - market_close/
  - performance/
  - signal_queue/
  - execution_startup/
  - night_batch/

---

## 実行上の注意点 / 運用メモ

- 本番環境（KABUSYS_ENV=live）では特に以下に注意してください:
  - .env に機密情報を含めない、あるいは適切に管理する
  - KILL_FLAG_CLEAR_ON_START は本番で `0` を推奨（`1` は起動時に停止フラグが自動クリアされるため危険）
  - LINE 通知設定が未設定だとアラートが届きません（本番では設定推奨）
- Paper Trading は本番 DB と完全に分離するよう設計されています（`PAPER_TRADING_SQLITE_PATH` を利用）。
- run_monitoring は `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可能（0 以下は無効化されデフォルト 60 秒にフォールバック）。
- 多くの CLI は JSON / Markdown / 保存オプションを提供しており、自動化パイプラインで利用しやすくなっています。
- DuckDB は読み取り専用接続での使用が多いので、分析用に適したテーブル設計を行ってください。

---

## 開発／拡張

- 各 operations/* モジュールは、DB 参照を分離した純粋関数（レポートビルド）とフォーマット関数に分かれており、テストしやすい設計です。
- 新しいレポートを追加する際は、collector（DB 参照） → build_report（純粋関数） → formatters（CLI/JSON/Markdown） → save_report のパターンを踏襲してください。

---

README に不足している点や、特定コマンドの詳細（例: ExecutionEngine のログ出力や Broker の設定、データベース初期化）について知りたい場合は、対象項目を指定して質問してください。