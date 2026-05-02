# KabuSys

日本株向けの自動売買システムの一部（実行/監視/レポート生成ツール群）です。本リポジトリは CLI エントリポイント群、レポート生成ロジック、設定管理ユーティリティなどを含みます。

## プロジェクト概要
- 起動スクリプト（Execution / Monitoring / レポート系 CLI）
- 設定管理（`.env` 自動読み込み、設定ウィザード）
- 各種レポート生成モジュール（Pre-Market / Market Close / Performance / Signal Queue / Execution Startup / Night Batch 等）
- Paper Trading（ペーパートレード）用の分離された DB をサポート
- DuckDB を分析用 DB、SQLite を監視・履歴用 DB として利用

主な目的は「夜間バッチ → 翌営業日のシグナル生成 → 実行エンジン起動 → 監視 / レポート出力」を支援することです。

## 主な機能一覧
- Execution 起動（実注文またはペーパートレード）
  - コマンド: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは `data/paper_trading.db` に保存（本番 DB と分離）
  - 起動時にリコンシリエーションを行い、Execution Startup Summary を生成
- Monitoring（継続実行用ポーリング）
  - コマンド: python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能
  - Monitoring は環境にかかわらず本番の `sqlite_path` を使用
- ザラ場中監視 CLI（リアルタイム監視）
  - コマンド: python -m kabusys.run_intraday_monitor [--watch] [--interval N]
- レポート生成 CLI
  - Pre-Market Report: python -m kabusys.run_pre_market_report [--save] [--json]
  - Market Close Summary: python -m kabusys.run_market_close_report [--date YYYY-MM-DD] [--save] [--json]
  - Position Reconciliation View: python -m kabusys.run_position_reconciliation_report [--date] [--save] [--json] [--watch]
  - Signal Queue Confirmation: python -m kabusys.run_signal_queue_report [--date] [--save] [--json]
  - Performance Report (daily/weekly/monthly): python -m kabusys.run_performance_report --type daily|weekly|monthly [--env live|paper_trading] [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--save]
  - Paper Trading 検証レポート（ツール）: python -m kabusys.tools.paper_verification_report [--from] [--to] [--db PATH]
- 設定関連
  - 対話式 `.env` ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config [--strict]

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 環境を作成し依存パッケージをインストール
   - 主要依存（コードから確認）: duckdb, pyyaml（レポート・設定パースで使用）
   - 例（pipenv/venv 等を利用）:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install duckdb pyyaml
3. 環境変数（`.env`）を用意
   - 対話式ウィザードで生成: python -m kabusys.config_setup
   - 生成された `.env` は絶対に Git にコミットしないでください
   - 自動ロード:
     - 起動時、プロジェクトルート（`.git` または `pyproject.toml` のあるディレクトリ）を検出して `.env` / `.env.local` を自動読み込みします
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
4. 設定検証（必須環境変数や config/*.yaml のチェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
5. DB の準備
   - デフォルトパス:
     - DuckDB: data/kabusys.duckdb （環境変数 `DUCKDB_PATH` で上書き可能）
     - SQLite（監視 DB）: data/monitoring.db （`SQLITE_PATH`）
     - Paper Trading SQLite: data/paper_trading.db （`PAPER_TRADING_SQLITE_PATH`）
   - 必要に応じてデータ作成スクリプト・夜間バッチを実行して DuckDB/SQLite を用意してください

## 使い方（主要コマンド例）
- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - ペーパートレードで起動する例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動後は `data/execution.pid` に PID が書き込まれます。停止は `data/stop_requested.flag` を作成すると実行ループが終了します。
- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - `data/monitoring.pid` に PID を書き込み、`data/stop_requested.flag` を検知して終了します
  - 注意: monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を参照します
- ザラ場中監視（単発表示）
  - python -m kabusys.run_intraday_monitor
  - 監視モード（自動更新）:
    - python -m kabusys.run_intraday_monitor --watch --interval 60
- Pre-Market レポート
  - python -m kabusys.run_pre_market_report [--json] [--save]
  - exit code: BLOCKED の場合は 1（運用開始不可）
- Market Close / Position Reconciliation / Signal Queue / Performance:
  - それぞれのスクリプトに `--date` / `--json` / `--save` / `--watch` 等のオプションがあります。詳細は各スクリプトのヘルプ（--help）を参照
- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - `PAPER_TRADING_SQLITE_PATH` 環境変数で DB パスを指定可能

## 設定（主な環境変数とデフォルト）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- JQUANTS_REFRESH_TOKEN, JQUANTS_BULK_API_KEY: J-Quants API 用（必須）
- KABU_API_PASSWORD, KABU_API_BASE_URL, KABU_TRADE_PASSWORD: kabuステーション API 関連
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知（任意）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードのフィルモード（instant/partial/never/reject）

注意: `.env` 自動読み込みの順序は OS 環境変数 > .env.local > .env です。OS 環境変数は保護され、.env から上書きされません。

## レポートの保存先（デフォルト）
- artifacts/pre_market/{YYYY-MM-DD}/
- artifacts/market_close/{YYYY-MM-DD}/
- artifacts/performance/{env}/{type}/{period}/
- artifacts/signal_queue/{YYYY-MM-DD}/
- artifacts/execution_startup/{YYYY-MM-DD}/
- artifacts/night_batch/{YYYY-MM-DD}/

保存時は JSON、Markdown、警告リストなどが出力されます。

## 停止・制御ファイル
- data/stop_requested.flag: これが存在すると実行ループ（Execution / Monitoring 等）が安全に終了します
- data/kill.flag: 設定により Kill Switch（外部からの強制停止）に利用
- data/*.pid: 起動プロセスの PID を記録（例: data/execution.pid, data/monitoring.pid）

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（自動 .env 読み込み等）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — Execution 起動スクリプト（メイン実行エンジン）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動
  - run_intraday_monitor.py  — ザラ場中監視 CLI
  - run_pre_market_report.py — Pre-Market Report CLI
  - run_market_close_report.py — Market Close Summary CLI
  - run_position_reconciliation_report.py — Position Reconciliation CLI
  - run_signal_queue_report.py — Signal Queue Confirmation CLI
  - run_performance_report.py — Performance レポート CLI
  - operations/               — レポート生成や集計ロジック（pure functions）
    - pre_market_report.py
    - market_close_report.py
    - performance_collector.py
    - performance_report.py
    - signal_queue_report.py
    - execution_startup_report.py
    - night_batch_report.py
    - ...（その他レポート関連）
  - execution/                — Execution エンジン周り（BrokerFactory, OrderManager 等）※本コードベースに依存モジュールあり
  - monitoring/               — 監視関連（DB 初期化、SystemMonitor 等）
  - tools/                    — 補助ツール（paper_verification_report 等）
  - utils/                    — ロギング設定やプロセス優先度設定などユーティリティ

（上記は本リポジトリ内の代表的ファイル・モジュールを抜粋した構成です）

## 開発時のヒント / 注意点
- validate_config で設定エラーや警告を事前に確認してください:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります
- Paper Trading は本番 DB と分離されます。KABUSYS_ENV=paper_trading にすると `paper_sqlite_path` が使用されます
- monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を参照します（監視系は常に本番 DB を対象にするため）
- `.env` に秘匿値（API トークン等）を含めるため、Git 管理しないでください
- long-running プロセス（Execution / Monitoring）は PID ファイルと stop flag を利用して制御します。運用時はこれらの取り扱いに注意してください

---

追加で README に記載したい詳細（依存パッケージの一覧、unit tests 実行方法、CI 設定、個別モジュールの API ドキュメント等）があれば教えてください。必要に応じてサンプル .env.example や起動スクリプトの具体例を追記します。