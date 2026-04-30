# KabuSys

日本株自動売買システム「KabuSys」のリポジトリ向け README（日本語）。

この README はリポジトリ内のスクリプト／モジュールを元に作成しました。実行／運用時の注意点やよく使うコマンド例をまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買オペレーションを支援するツール群です。  
主な目的は次の通りです。

- 夜間バッチでのデータ更新 → シグナル生成 → 翌営業日の自動執行（Execution）
- 実行プロセスの監視（Monitoring）
- 当日／夜間の各種レポート生成（Pre-Market / Market Close / Performance / Signal Queue 等）
- Paper Trading（ペーパートレード）用の分離された実行環境

設計上、環境変数と設定ファイル（`.env`, `config/*.yaml`）で動作を切り替えます。実行中の停止はフラグファイル（`data/stop_requested.flag`）で制御できます。

---

## 機能一覧

- Execution（実際の発注ループ）
  - run_execution.py：ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、paper 用 SQLite に分離して記録します。
- Monitoring（システム監視）
  - run_monitoring.py：SystemMonitor のポーリングループを起動。監視情報は SQLite（monitoring DB）に保存。
- CLI モニタ／確認ツール
  - run_intraday_monitor.py：ザラ場中の簡易監視 CLI（ワッチモードあり）。
  - run_signal_queue_report.py：Signal Queue（翌営業日の発注予定）を表示・保存。
  - run_position_reconciliation_report.py：ブローカーとローカルのポジション差分レポート。
  - run_pre_market_report.py：朝の Pre-Market レポート（自動執行可否判定）。
  - run_market_close_report.py：引け後サマリ（当日締め処理の確認）。
  - run_performance_report.py：日次・週次・月次の運用成績サマリを生成。
- 設定・検証ツール
  - config_setup.py：対話式で `.env` を作成・更新するウィザード。
  - validate_config.py：環境変数や `config/*.yaml` の設定検証。
- Paper Trading 向けツール
  - tools/paper_verification_report.py：paper_trading の稼働・注文成功率・レイテンシ等を検証するレポート生成。
- レポート生成モジュール（純粋関数群）
  - operations/*.py：各種レポートの構築・フォーマッタ（CLI / JSON / Markdown）と保存ロジックを提供。
- DB
  - DuckDB（分析用）：デフォルト `data/kabusys.duckdb`
  - SQLite（監視・履歴）：デフォルト `data/monitoring.db`
  - Paper Trading 用 SQLite（ペーパートレード実行時）：デフォルト `data/paper_trading.db`

---

## セットアップ手順

以下は典型的なセットアップ手順の一例です。実際はプロジェクトの `requirements.txt` や配布方法に合わせてください。

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 必要に応じて `duckdb`、`PyYAML` などをインストールしてください

4. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - J-Quants トークンや kabu API パスワードなどを対話的に設定できます
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - `--strict` をつけると警告も失敗（exit 1）扱いになります

5. 環境変数の自動ロード
   - `config.py` はプロジェクトルート（`.git` 或いは `pyproject.toml`）を基準に `.env`/.env.local を自動読み込みします
   - 自動ロードを無効にしたい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

6. 初期データベース
   - DuckDB / SQLite は夜間バッチや別スクリプトで作成／更新される想定です
   - 監視 DB（monitoring）は run_monitoring / run_execution 内で必要テーブル（init_monitoring_db）を冪等的に初期化します

注意: `.env` は機密情報を含むので Git にコミットしないでください（config_setup.py でも同様の注意書きがあります）。

必須の環境変数（一部）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
（その他: JQUANTS_BULK_API_KEY, KABU_API_BASE_URL, LINE_* など。`validate_config.py` を参照してください）

主要な設定（Settings クラス）
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- PAPER_FILL_MODE（paper_trading の発注模擬挙動: instant|partial|never|reject）
- LOG_LEVEL, PID ファイルパスなど

---

## 使い方（よく使うコマンド例）

各スクリプトはパッケージモード（-m）で実行することを想定しています。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution（自動執行エンジン）起動
  - python -m kabusys.run_execution
  - 停止はプロセスに `data/stop_requested.flag` を作成（ファイル存在を検出して停止）
  - paper_trading 環境:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading は独立した SQLite（data/paper_trading.db）を使用

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に本番用 `sqlite_path` を参照（環境に依存せず）

- ザラ場中監視（CLI）
  - python -m kabusys.run_intraday_monitor
  - 監視を定期表示（ワッチ）:
    - python -m kabusys.run_intraday_monitor --watch --interval 60

- Signal Queue 確認レポート
  - python -m kabusys.run_signal_queue_report
  - 日付指定、JSON 出力、保存:
    - python -m kabusys.run_signal_queue_report --date 2026-04-28 --json --save

- Position Reconciliation（ポジション照合）レポート
  - python -m kabusys.run_position_reconciliation_report
  - 定期ポーリング:
    - python -m kabusys.run_position_reconciliation_report --watch --interval 300

- Pre-Market / Market-Close / Performance レポート
  - python -m kabusys.run_pre_market_report [--save|--json]
  - python -m kabusys.run_market_close_report [--date YYYY-MM-DD --save --json]
  - python -m kabusys.run_performance_report --type daily|weekly|monthly [--env paper_trading] [--from YYYY-MM-DD --to YYYY-MM-DD] [--save]

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` で DB を指定可能

プロセス制御・停止フラグ
- 起動済みの Execution / Monitoring はそれぞれ `data/execution.pid` / `data/monitoring.pid` を作成します
- 強制停止・自動執行停止には `data/stop_requested.flag`（停止を要求するファイル）を作成します
- kill/フラグ関係は Settings の `kill_flag_path` 等で変更可能

ログ
- ログレベルは `LOG_LEVEL` 環境変数（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- run_* スクリプトは内部で logging を初期化します

---

## ディレクトリ構成（主要ファイル）

以下は主要モジュール／スクリプトの一覧（抜粋）です。実際のツリーはこの README のあるリポジトリ直下に `src/kabusys` 配下にあります。

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数／設定読み込み（.env 自動ロード）
  - config_setup.py                 -- .env 対話式ウィザード
  - validate_config.py              -- 設定検証 CLI
  - run_execution.py                -- ExecutionEngine 起動スクリプト
  - run_monitoring.py               -- SystemMonitor ポーリング起動スクリプト
  - run_intraday_monitor.py         -- ザラ場中監視 CLI
  - run_signal_queue_report.py      -- Signal Queue 確認レポート（CLI）
  - run_position_reconciliation_report.py
  - run_pre_market_report.py
  - run_market_close_report.py
  - run_performance_report.py
  - run_performance_report.py
  - operations/                      -- レポート生成ロジック（pure functions）
    - signal_queue_report.py
    - execution_startup_report.py
    - pre_market_report.py
    - market_close_report.py
    - performance_report.py
    - performance_collector.py
    - night_batch_report.py
    - ...（その他の report/collector）
  - execution/                       -- Execution 関連（broker, engine, order 管理等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py               -- 監視 DB 初期化等
    - system_monitor.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - その他ユーティリティ

- data/                              -- 実行時生成（デフォルト）
  - monitoring.db (SQLite)
  - kabusys.duckdb (DuckDB)
  - paper_trading.db (paper 環境用 SQLite)
  - stop_requested.flag
  - execution.pid
  - monitoring.pid

- artifacts/                         -- レポート保存先（実行時に作成）
  - pre_market/
  - market_close/
  - performance/
  - signal_queue/
  - execution_startup/
  - night_batch/

---

## 実運用時の注意点

- 本番（KABUSYS_ENV=live）では設定やシークレットの管理に十分ご注意ください（LINE 通知などが未設定だとアラートが届きません）。
- `.env` は機密情報を含むため絶対にリポジトリにコミットしないでください。
- run_execution は実際に発注を行います。live 環境で実行する前に必ず `validate_config.py` で設定を確認し、テスト（paper_trading）で動作を確認してください。
- 停止フラグ（data/stop_requested.flag）によるシャットダウンは安全ですが、pid ファイルや DB の状態確認も併せて行ってください。
- Paper Trading は実 DB と分離されています。paper_trading 実行時は `PAPER_TRADING_SQLITE_PATH` を使用します。

---

この README はリポジトリ内のソースから自動的に生成された情報に基づいており、利用方法やコマンドは実装内容の抜粋を示しています。より詳細な挙動（例えば ExecutionEngine の内部、ブローカー実装、DB スキーマなど）は各モジュールの docstring やソースを参照してください。質問や補足が必要であれば教えてください。