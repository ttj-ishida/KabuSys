# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システムの実行・監視・レポート生成を行うスクリプト群・ユーティリティ群を含みます。  
README はソースツリー（`src/kabusys`）にある主要なエントリポイントと設定方法、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

- 自動発注エンジン（ExecutionEngine）の起動・実行
- システム監視（SystemMonitor）のポーリング
- ザラ場（インデイ）監視コマンドラインツール
- 各種レポート生成（Pre-Market / Market Close / Performance / Position Reconciliation / Signal Queue / Execution Startup / Night Batch 等）
- Paper Trading 環境向けの検証ツール（paper_verification_report）
- .env 対話式設定ウィザードと設定検証ツール

主要なデータストア:
- DuckDB: 分析用（デフォルト `data/kabusys.duckdb`）
- SQLite: 監視・発注履歴（デフォルト `data/monitoring.db`）
- Paper trading 用 SQLite（Paper 環境時は `data/paper_trading.db` を使用）

---

## 機能一覧

- run_execution: ExecutionEngine 起動（`KABUSYS_ENV=paper_trading` 時は MockBroker を使用、Paper DB に分離）
- run_monitoring: SystemMonitor ポーリングループ起動（ポーリング間隔は環境変数で調整可）
- run_intraday_monitor: ザラ場中監視 CLI（ワンショット / 監視モード）
- run_pre_market_report, run_market_close_report, run_performance_report, run_position_reconciliation_report, run_signal_queue_report:
  各種レポートの生成（CLI オプションで JSON / 保存 / watch 等に対応）
- config_setup: 対話式 .env 作成ウィザード
- validate_config: .env と config/*.yaml の起動前チェック（`--strict` で警告も失敗扱い）
- tools/paper_verification_report: Paper Trading の稼働・発注精度・レイテンシ検証
- operations/*: レポート生成やデータ集計の純粋関数群（テストしやすい設計）
- 設定管理（`kabusys.config.Settings`）: 環境変数読み込み、自動ロード（.env/.env.local）有り

---

## セットアップ手順

前提:
- Python 3.9+（ソース内に明示はないが zoneinfo 等の利用を考慮）
- DuckDB / sqlite3 が利用可能な環境

1. クローン / ワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して依存関係をインストール（プロジェクトに `requirements.txt` がある場合）
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   # ある場合: pip install -r requirements.txt
   ```

3. 対話式で .env を作成（推奨）
   ```
   python -m kabusys.config_setup
   ```
   このウィザードは `.env` を作成・更新します。生成後、`python -m kabusys.validate_config` で検証してください。

4. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も FAIL とする場合:
   python -m kabusys.validate_config --strict
   ```

5. DuckDB / SQLite の準備
   - デフォルトパスは `data/kabusys.duckdb`（DuckDB）と `data/monitoring.db`（SQLite）
   - 必要に応じて `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` を `.env` や環境変数で上書きしてください。

補足:
- 自動環境読み込みはデフォルトで有効。無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 本番環境では `KABUSYS_ENV=live`、ペーパートレード検証には `KABUSYS_ENV=paper_trading` を使用します。

---

## 使い方（主要コマンド例）

全てモジュールとして実行できます: `python -m kabusys.<module>`

一般的なコマンド例:

- ExecutionEngine を起動（バックグラウンド実行 / サービス管理は各自で）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合、MockBroker を使用し、Paper 用 DB（`PAPER_TRADING_SQLITE_PATH`）に記録します。
  - 起動時に開始レポートを CLI に表示・保存します。
  - 停止はプロジェクトルートの `data/stop_requested.flag` を作成することで検知して終了します。

- SystemMonitor を起動（ポーリング）
  ```
  # デフォルト間隔 60 秒。環境変数で上書き可:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - モニタは `data/monitoring.pid` を作成します。停止は `data/stop_requested.flag`。
  - ※Monitoring は常に本番用 sqlite_path を参照します（環境に依存せず）。

- ザラ場監視（1回実行）
  ```
  python -m kabusys.run_intraday_monitor
  ```
  監視モード（定期表示）:
  ```
  python -m kabusys.run_intraday_monitor --watch --interval 60
  ```

- Pre-Market レポート生成
  ```
  python -m kabusys.run_pre_market_report --save
  python -m kabusys.run_pre_market_report --json
  ```

- Market Close レポート生成
  ```
  python -m kabusys.run_market_close_report --date 2026-04-28 --save
  ```

- Signal Queue 確認（翌営業日の発注シグナル確認）
  ```
  python -m kabusys.run_signal_queue_report --date 2026-04-28 --save --json
  ```

- Position Reconciliation（ポジション整合性レポート）
  ```
  python -m kabusys.run_position_reconciliation_report --date 2026-04-28
  # 監視モード
  python -m kabusys.run_position_reconciliation_report --watch --interval 300
  ```

- Performance レポート
  ```
  python -m kabusys.run_performance_report --type daily --from 2026-01-01 --to 2026-04-30 --save
  ```

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

注意:
- いくつかの CLI は `--json` を指定すると JSON を標準出力に出力し、保存先メッセージは stderr に書く動作をします（JSON ストリームを汚染しないための配慮）。

環境変数の例（.env に記載）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
JQUANTS_BULK_API_KEY=your_bulk_key_here
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

重要な設定項目:
- KABUSYS_ENV: development / paper_trading / live
- PAPER_FILL_MODE: paper_trading 時の注文成約挙動（instant / partial / never / reject）
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

停止 / フラグファイル:
- data/stop_requested.flag: 実行ループ（execution / monitoring 等）が検知して安全に停止するためのフラグ
- data/kill.flag: `Settings.kill_flag_path`（Kill Switch）等、運用上の別のフラグとして利用

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数・設定の自動ロード & Settings
    - config_setup.py           — 対話式 .env ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動エントリポイント
    - run_monitoring.py         — SystemMonitor 起動スクリプト
    - run_intraday_monitor.py   — ザラ場中監視 CLI
    - run_pre_market_report.py
    - run_market_close_report.py
    - run_performance_report.py
    - run_position_reconciliation_report.py
    - run_signal_queue_report.py
    - run_performance_report.py
    - run_performance_report.py
    - operations/                — レポート生成やデータ集計の純粋関数群
      - pre_market_report.py
      - market_close_report.py
      - pre_market_collector.py
      - performance_collector.py
      - performance_report.py
      - signal_queue_report.py
      - execution_startup_report.py
      - night_batch_report.py
      - position_reconciliation_report.py
      - intraday_collector.py
    - execution/                 — 実際の発注ロジック（Engine, BrokerFactory 等）
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/                — 監視関連（SystemMonitor, monitoring_db 等）
      - system_monitor.py
      - monitoring_db.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/                      — 実行時に作成される PID / flag / DB など（プロジェクトルート直下）
    - config/                    — YAML 設定テンプレート（system_config.yaml 等）

実際のリポジトリでは上記に加えてテストや追加モジュールが存在する可能性があります。

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）では LINE 等の通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を必ず正しく設定してください。`validate_config` はそのチェックを支援します。
- .env は絶対に Git にコミットしないでください（`config_setup.py` も README 内に警告あり）。
- Paper Trading（`paper_trading`）は本番 DB と完全に分離して動作するよう設計されています（`PAPER_TRADING_SQLITE_PATH` を用いる）。
- プロセス優先度設定: 起動時に `set_process_priority("high")` を呼ぶ実装があり、実行環境で適切な権限が必要となる場合があります。
- ログレベルは `LOG_LEVEL` で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 一部の CLI は定期監視モードを持ちます。監視ループの終了は Ctrl+C または stop flag によります。

---

README は以上です。必要であれば各モジュール（ExecutionEngine の起動手順、Reconciler の振る舞い、RiskConfig の詳しいパラメータや例）について追記できます。どの項目を詳細化したいか教えてください。