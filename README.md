# KabuSys — README (日本語)

このリポジトリは、日本株向けの自動売買運用ツール群（KabuSys）の一部です。  
ここに含まれるスクリプトは、監視・実行・レポート生成など運用に必要なコマンドラインエントリポイントを提供します。

以下は、このコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は自動売買システムの運用周り（Execution、Monitoring、各種レポート生成、設定ウィザード、検証ツールなど）を含むモジュール群です。  
主に以下の役割を持つコンポーネントがあります。

- 実際の発注ループ（ExecutionEngine）
- システム状態・リソース監視（SystemMonitor）
- 各種運用レポート（Pre-Market、Market Close、Performance、Signal Queue、Position Reconciliation 等）
- 設定のウィザードおよび検証ツール（.env 作成・検証）
- ペーパートレード用の検証スクリプト

設定は環境変数（.env）で行い、DuckDB / SQLite をデータ参照先として使用します。

---

## 主な機能一覧

- 実行エンジン起動: `python -m kabusys.run_execution`
  - KABUSYS_ENV によって本番 / paper_trading を切り替え
  - Paper Trading の場合、専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し Mock Broker を利用
  - 起動時にリコンシリエーションを実施し Execution Startup Summary を生成・保存可能
  - PID ファイル: `data/execution.pid`
  - 停止フラグ: `data/stop_requested.flag` を検知して安全停止

- 監視プロセス起動: `python -m kabusys.run_monitoring`
  - SystemMonitor のポーリングループを実行（デフォルト 60 秒）
  - 環境変数 `MONITOR_POLL_INTERVAL` で間隔を上書き可能
  - Monitoring は環境にかかわらず本番の `sqlite_path` を使用
  - PID ファイル: `data/monitoring.pid`
  - 停止フラグ: `data/stop_requested.flag` を検知して安全停止

- ザラ場監視 CLI: `python -m kabusys.run_intraday_monitor`
  - 単発または監視モード（`--watch`）で実行状態 / リスク / システム指標を表示

- 各種レポート生成:
  - Pre-Market Report: `python -m kabusys.run_pre_market_report`（--save / --json）
  - Market Close Summary: `python -m kabusys.run_market_close_report`（--date / --save / --json）
  - Position Reconciliation Report: `python -m kabusys.run_position_reconciliation_report`（--date / --save / --json / --watch）
  - Signal Queue Confirmation View: `python -m kabusys.run_signal_queue_report`（--date / --save / --json）
  - Performance Report（daily/weekly/monthly）: `python -m kabusys.run_performance_report --type daily`（--env / --from / --to / --save）
  - Execution Startup Summary の生成は Execution 起動時にも実行される

- 設定周り:
  - 対話式 .env 作成: `python -m kabusys.config_setup`
  - 設定検証ツール: `python -m kabusys.validate_config`（`--strict` で警告を FAIL 扱い）

- ペーパートレード検証ツール:
  - `python -m kabusys.tools.paper_verification_report`（期間指定可）  
    - paper_trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）に対して稼働率・注文成功率・レイテンシ等の検証を実行

---

## 必須環境変数（代表）

主要な必須/重要な環境変数例（.env に設定）:

- JQUANTS_REFRESH_TOKEN（必須）
- JQUANTS_BULK_API_KEY（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（`development` / `paper_trading` / `live`、デフォルト `development`）
- DUCKDB_PATH（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH（デフォルト `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH（paper_trading の場合の専用 DB、デフォルト `data/paper_trading.db`）
- LOG_LEVEL（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意; アラート用）

その他:
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒; デフォルト 60）
- PAPER_FILL_MODE（paper_trading の fill 動作: `instant`/`partial`/`never`/`reject`）

設定作成は `python -m kabusys.config_setup` を推奨し、作成後に `python -m kabusys.validate_config` で検証してください。

---

## セットアップ手順（簡易）

1. Python 環境準備（推奨: 3.9+）
2. 必要パッケージをインストール
   - duckdb, pyyaml 等が使われます。以下は例:
     - pip install duckdb pyyaml
   - 実プロジェクトでは requirements.txt または poetry 等を使用してください（本コードルートには明示されていません）。
3. リポジトリルートで対話式設定ウィザードを実行
   - python -m kabusys.config_setup
   - これにより `.env` が生成されます（デフォルト: プロジェクトルートの `.env`）。
4. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば表示に従って修正
5. データディレクトリ作成（必要に応じて）
   - デフォルトでは `data/`、`artifacts/` などにファイルを保存します。自動作成される箇所もありますが、権限等のため事前に作っておくと安全です。
6. DuckDB / SQLite データを用意
   - 分析用の DuckDB (`data/kabusys.duckdb`) と monitoring 用 SQLite (`data/monitoring.db`)、paper_trading 用 SQLite (`data/paper_trading.db`) を準備します（夜間バッチや別スクリプトで生成される想定）。

---

## 使い方（主なコマンド例）

各コマンドはモジュールとして実行できます（Python モジュール実行: `-m kabusys.<module>`）。

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - Paper Trading モード例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 注意: 起動時にリコンシリエーションが行われ、Execution Startup Summary を表示・保存します。
  - 停止: プロジェクトルートに `data/stop_requested.flag` を作成するとプロセスは次のループで安全に停止します。

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ザラ場監視（対話的表示）
  - python -m kabusys.run_intraday_monitor
  - 監視モード:
    - python -m kabusys.run_intraday_monitor --watch --interval 60

- Pre-Market レポート
  - python -m kabusys.run_pre_market_report
  - オプション:
    - --save（artifacts/pre_market/YYYY-MM-DD/ に保存）
    - --json（JSON で出力）

- Market Close レポート
  - python -m kabusys.run_market_close_report [--date YYYY-MM-DD] [--save] [--json]

- Position Reconciliation レポート
  - python -m kabusys.run_position_reconciliation_report [--date YYYY-MM-DD] [--save] [--json]
  - 監視モード:
    - --watch --interval N

- Signal Queue レポート
  - python -m kabusys.run_signal_queue_report [--date YYYY-MM-DD] [--save] [--json]

- Performance レポート
  - python -m kabusys.run_performance_report --type daily --env live --from YYYY-MM-DD --to YYYY-MM-DD [--save]
  - --type: daily / weekly / monthly

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告をエラー扱い）:
    - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - DB 指定は `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で行えます

---

## 停止・フラグ / PID ファイル

- 停止フラグ:
  - data/stop_requested.flag
  - 多くの長時間プロセス（Execution / Monitoring）はこのファイルを検知して安全停止します。
- PID ファイル:
  - data/execution.pid（Execution 起動時）
  - data/monitoring.pid（Monitoring 起動時）
  - 起動時にこれらのファイルが書き込まれ、終了時に削除されます（存在チェックやプロセス監視に利用できます）。
- Kill フラグ:
  - 設定上は `KILL_FLAG_PATH`（デフォルト data/kill.flag）を参照する機能があります。設定検証で注意が促されます。

---

## レポートの保存場所（デフォルト）

各レポートは保存フラグを指定すると `artifacts/` 以下に保存されます（モジュールごとにパスは概ね固定）:

- Signal Queue: artifacts/signal_queue/YYYY-MM-DD/
  - summary.json, report.md, warnings.json
- Execution Startup: artifacts/execution_startup/YYYY-MM-DD/
- Pre-Market: artifacts/pre_market/YYYY-MM-DD/
- Market Close: artifacts/market_close/YYYY-MM-DD/
- Night Batch: artifacts/night_batch/YYYY-MM-DD/
- Performance: artifacts/performance/{env}/{type}/{period}/

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なコード配置（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（自動 .env ロード機能あり）
  - config_setup.py               — 対話式 .env 作成ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - run_intraday_monitor.py       — ザラ場監視 CLI
  - run_pre_market_report.py      — Pre-Market レポートエントリ
  - run_market_close_report.py    — Market Close レポートエントリ
  - run_position_reconciliation_report.py — Position Reconciliation レポート
  - run_signal_queue_report.py    — Signal Queue レポート
  - run_performance_report.py     — Performance レポート
  - run_signal_queue_report.py
  - run_performance_report.py
  - run_position_reconciliation_report.py
  - run_pre_market_report.py
  - run_market_close_report.py
  - run_intraday_monitor.py
  - run_monitoring.py
  - run_execution.py
  - operations/                    — 各種レポート生成ロジック（pure function）
    - pre_market_report.py
    - night_batch_report.py
    - market_close_report.py
    - performance_collector.py
    - performance_report.py
    - signal_queue_report.py
    - execution_startup_report.py
    - position_reconciliation_report.py
    - intraday_collector.py
  - execution/                     — Execution 関連（Broker クライアントファクトリ等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/                    — Monitoring 関連（SystemMonitor, monitoring DB 初期化）
    - monitoring_db.py
    - system_monitor.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/（実行時に使うファイル・DB の配置想定）
  - config/（YAML 設定ファイル: risk_config.yaml 等）
  - artifacts/（レポート保存先）

※ 上記はコードから読み取れる主要モジュールの一覧です。詳細な内部実装は各ファイルを参照してください。

---

## ヒント・注意点

- .env の自動ロード:
  - `src/kabusys/config.py` はプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を自動読み込みします。必要な場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。
- DB パス:
  - Monitoring は「環境に関係なく」本番 `sqlite_path` を参照する実装になっています。paper_trading と本番 DB を完全に分離したい場合は注意してください（Execution は `settings.is_paper` の場合 `paper_sqlite_path` を使う）。
- risk_config.yaml:
  - `config/risk_config.yaml` が必要（Execution 側で読み込み）。欠落やパースエラーは起動失敗要因になります。
- Paper Trading:
  - Paper 環境でも動作検証ができるように mock ブローカーと別 DB が用意されています。`PAPER_FILL_MODE` の値は `instant`/`partial`/`never`/`reject` のいずれかに設定してください。
- ロギング:
  - 各スクリプトには `setup_logging` を呼ぶ仕組みがあります。`LOG_LEVEL` を `.env` で調整してください。

---

## 参考コマンド集（まとめ）

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ザラ場監視（継続）
  - python -m kabusys.run_intraday_monitor --watch --interval 30
- Pre-Market レポート
  - python -m kabusys.run_pre_market_report --save
- Market Close レポート
  - python -m kabusys.run_market_close_report --date 2026-04-28 --save --json
- Signal Queue レポート
  - python -m kabusys.run_signal_queue_report --date 2026-04-28 --save
- Performance レポート（日次）
  - python -m kabusys.run_performance_report --type daily --env live --from 2026-03-01 --to 2026-03-31 --save
- ペーパートレード検証
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README はここまでです。  
運用開始前に必ず以下を実行してください:

1. python -m kabusys.config_setup（.env の作成）
2. python -m kabusys.validate_config（設定検証）
3. 必要な DB（DuckDB / SQLite）の準備と config/*.yaml の確認

追加で知りたいコマンドや各レポートの出力フォーマットの詳細、設定項目の説明（.env の全キー一覧など）が必要であれば教えてください。