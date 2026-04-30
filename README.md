# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム（KabuSys）の一部実装です。運用監視、Execution（発注エンジン）、各種レポート生成、設定ウィザードなどの CLI エントリポイントやレポート生成モジュールを含みます。

---

## プロジェクト概要

- 自動売買の実行（ExecutionEngine）と稼働監視（SystemMonitor）を含む運用向けツール群。
- DuckDB / SQLite を使った分析・監視データの保持とレポート生成。
- 本番環境（live）・ペーパートレード（paper_trading）・開発環境（development）をサポート。
- 起動時検証、設定ウィザード、複数の CLI レポート出力（JSON / Markdown / CLI）を提供。

主な特徴:
- 起動時リコンシリエーションと Execution の安全起動判定（Execution Startup Summary）。
- 夜間バッチ／引け後／寄前などのチェックとレポート（Night Batch / Market Close / Pre-Market / Performance）。
- ザラ場中の状態監視（intraday monitor）と Signal Queue の確認。
- Paper Trading の独立した DB を用意して、本番 DB とデータを分離可能。

---

## 機能一覧（主な CLI / 機能）

- 設定・検証
  - python -m kabusys.config_setup
    - `.env` を対話式で作成・更新するウィザード。
  - python -m kabusys.validate_config [--strict]
    - .env と config/*.yaml の妥当性チェック。`--strict` で警告も失敗扱いに。

- 実行系 / 監視
  - python -m kabusys.run_execution
    - ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、data/paper_trading.db に記録。
  - python -m kabusys.run_monitoring
    - SystemMonitor のポーリングループを起動。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可（デフォルト 60 秒）。
  - 停止制御
    - ループを終了させるにはプロジェクトルートの `data/stop_requested.flag` を作成する。各プロセスは `data/*.pid`（例: execution.pid, monitoring.pid）を作成する。

- 監視・確認用 CLI
  - python -m kabusys.run_intraday_monitor [--watch] [--interval N]
    - ザラ場中の簡易ステータス表示。`--watch` で継続監視。
  - python -m kabusys.run_signal_queue_report [--date YYYY-MM-DD] [--save] [--json]
    - 翌営業日の発注予定シグナル一覧（signals / portfolio_targets から収集）。
  - python -m kabusys.run_position_reconciliation_report [--date] [--save] [--json] [--watch] [--interval]
    - ポジションリコンシリエーションのレポート。
  - python -m kabusys.run_pre_market_report [--save] [--json]
    - 寄前チェック（自動執行の可否判定）。
  - python -m kabusys.run_market_close_report [--date] [--save] [--json]
    - 引け後サマリ（当日の締めが正常かを判定）。
  - python -m kabusys.run_performance_report --type {daily,weekly,monthly} [--env live|paper_trading] [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--save]
    - 運用成績サマリ（DuckDB を参照）。

- ツール
  - python -m kabusys.tools.paper_verification_report [--from] [--to] [--db PATH]
    - Paper Trading の検証レポート（稼働率、注文成功率、レイテンシ等の合否判定）。

---

## セットアップ手順

1. リポジトリのクローン
   - git clone ... （プロジェクトルートは .git または pyproject.toml を基準に自動検出されます）

2. Python と依存パッケージのインストール
   - Python 3.8+ を推奨
   - 依存パッケージ（例）:
     - duckdb
     - pyyaml
     - その他（logging / sqlite3 / zoneinfo 等は標準ライブラリ）
   - インストール例:
     - pip install -r requirements.txt
     - requirements.txt がない場合は最低限 duckdb と pyyaml を入れてください:
       - pip install duckdb PyYAML

3. 環境変数 / `.env` の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を作成。
   - 自動ロード:
     - デフォルトで `.env`（次に .env.local）がプロジェクトルートから読み込まれます（OS 環境変数が優先）。
     - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 問題があれば表示に従って修正。`--strict` を付けると警告も失敗扱いになります。

5. DB / 設定ファイル
   - DuckDB のデフォルトパス: `data/kabusys.duckdb`
   - SQLite（監視用）デフォルト: `data/monitoring.db`
   - Paper Trading 用 SQLite デフォルト: `data/paper_trading.db`
   - 必要に応じて `DUCKDB_PATH` / `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` を `.env` で上書き。

---

## 主要な環境変数（要注意）

- 必須（例）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用に影響する主要変数
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレーディング専用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒 / デフォルト 60）
  - PAPER_FILL_MODE: paper_trading 時の MockBrokerClient の埋め（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill flag を自動クリアするか（0/1）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（本番では必須に近い）

簡単な .env の例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
JQUANTS_BULK_API_KEY=your_bulk_api_key_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方（よく使うコマンド例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- Execution 起動
  - python -m kabusys.run_execution
  - Paper Trading（環境変数指定）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 止めるにはプロジェクトルートの `data/stop_requested.flag` を作成

- 監視起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を指定:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番の sqlite path を使用（コード上の設計）

- ザラ場中モニタ
  - python -m kabusys.run_intraday_monitor
  - 継続表示: python -m kabusys.run_intraday_monitor --watch --interval 60

- Signal Queue 確認
  - python -m kabusys.run_signal_queue_report --date 2026-04-28 --save --json

- Position Reconciliation
  - python -m kabusys.run_position_reconciliation_report --watch --interval 300

- Pre-Market / Market Close / Performance レポート
  - python -m kabusys.run_pre_market_report --save
  - python -m kabusys.run_market_close_report --date 2026-04-28 --save --json
  - python -m kabusys.run_performance_report --type daily --from 2026-01-01 --to 2026-04-30 --save

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

--- 

## 実行挙動に関する注意点

- PID / Stop フラグ
  - 実行プロセスは `data/*.pid` を作成します（例: `data/execution.pid`, `data/monitoring.pid`）。
  - 終了要求はプロジェクトルートの `data/stop_requested.flag` ファイルの存在で判定されます。存在するとループが安全に終了します。

- Monitoring の DB 接続
  - run_monitoring は KABUSYS_ENV に関係なく本番の `sqlite_path` を参照する実装になっています（安全性・設計上の意図に注意）。

- Execution の Paper Trading
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用して発注を模擬し、Paper Trading 用 SQLite（`data/paper_trading.db`）に記録します。本番 DB と完全に分離されます。

- リスク設定
  - run_execution は起動時に `config/risk_config.yaml` を読み込み、検証を行います。ファイルがない・パースに失敗する場合は起動に失敗します。

- ログ・プロセス優先度
  - 起動時にログ設定が初期化され、プロセス優先度が "high" に設定されます（実行環境により権限が必要な場合があります）。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル/ディレクトリ構成（コードベースから抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定読み込みロジック
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — Execution 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - run_intraday_monitor.py  — ザラ場モニタ CLI
  - run_signal_queue_report.py
  - run_position_reconciliation_report.py
  - run_pre_market_report.py
  - run_market_close_report.py
  - run_performance_report.py
  - operations/               — レポート構築ロジック（pure functions）
    - signal_queue_report.py
    - execution_startup_report.py
    - pre_market_report.py
    - market_close_report.py
    - performance_report.py
    - performance_collector.py
    - night_batch_report.py
    - ...
  - execution/                — Execution 実装（ブローカー、リスク管理、注文管理等）
  - monitoring/               — SystemMonitor / monitoring DB 初期化
  - tools/                    — 補助スクリプト（paper_verification_report など）
  - utils/                    — logging_setup, process_priority など共通ユーティリティ
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/
  - monitoring.db             — デフォルト SQLite（監視用）
  - paper_trading.db          — Paper Trading 用（分離）
  - kabusys.duckdb            — DuckDB（デフォルトパスは data/kabusys.duckdb）
  - stop_requested.flag       — 停止要求フラグ（作成でループ停止）
  - *.pid                     — プロセス PID ファイル
- artifacts/
  - pre_market/
  - signal_queue/
  - execution_startup/
  - performance/
  - market_close/
  - night_batch/
  - ...                       — 各種レポートの保存先

---

## 開発・運用時のチェックリスト（推奨）

- .env を作成し、validate_config を実行して警告/エラーを確認する。
- 本番で実行する場合は KABUSYS_ENV=live、LINE 通知などの設定を見直す。
- Paper Trading を試す場合は KABUSYS_ENV=paper_trading を使い、実際の発注を行わないことを確認する（MockBrokerClient が使用される）。
- 自動起動（systemd 等）で使用する場合はプロセス優先度やログ出力、PID 管理、停止フラグ運用を設計に組み込む。

---

この README はソースコード内のドキュメント文字列や実装の意図に基づいて作成しています。さらに詳しい内部仕様（ExecutionEngine の詳細、Reconciler の挙動、BrokerClient 実装等）は該当モジュールのドキュメントやソースコードを参照してください。必要であれば README を拡張して運用手順（systemd ユニット例、ログローテーション、バックアップ方針など）を追加できます。