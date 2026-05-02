# KabuSys — 日本株自動売買システム（README）

このリポジトリは、KabuSys と呼ばれる日本株の自動売買システムの一部（起動スクリプト、設定管理、各種レポート生成ロジックなど）を含みます。ここではプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は、J-Quants / kabuステーション 等の API を利用して夜間バッチ→シグナル生成→自動執行までを行う運用向けの自動売買フレームワークです。本リポジトリのコードは以下の責務を担います。

- 実行エンジン（ExecutionEngine）の起動・監視
- SystemMonitoring（システム状態・稼働監視）
- 各種運用レポート（Pre-Market / Market Close / Performance / Signal Queue / Execution Startup など）の生成
- 環境設定ウィザード（.env 作成）と設定検証ツール
- Paper Trading 向け検証ツール

---

## 主な機能一覧

- Execution 起動スクリプト（run_execution）
  - 本番/ペーパートレードを分離して DB を使い分け
  - Broker クライアントの切替（paper_trading 時は Mock）
  - 起動時にリコンシリエーションを実行し Startup Summary を保存/表示
- System Monitoring（run_monitoring）
  - 定期ポーリングで system_status 等を記録・監視
  - ポーリング間隔は環境変数で上書き可能（MONITOR_POLL_INTERVAL、デフォルト 60 秒）
  - 停止フラグ / PID 管理（data/stop_requested.flag / data/monitoring.pid）
- インタラクティブなザラ場監視 CLI（run_intraday_monitor）
  - 単発表示 or watch モード（自動更新）
  - CPU/メモリ/プロセス状態 / ドローダウン / 注文エラー 等を表示
- 各種レポート生成スクリプト
  - run_pre_market_report（Pre-Market）
  - run_market_close_report（Market Close）
  - run_performance_report（運用成績：日次/週次/月次）
  - run_position_reconciliation_report（ポジション整合性確認）
  - run_signal_queue_report（翌営業日のシグナル確認）
- 設定関連
  - .env 対話生成ウィザード（config_setup）
  - 設定検証（validate_config）
- Paper Trading 検証ツール（tools/paper_verification_report）
  - ペーパートレード用 DB から稼働率・注文成功率・レイテンシ等を集計し PASS/FAIL 判定

---

## 前提 / 要件（例）

- Python 3.10 以上（使用している typing / ZoneInfo 等に依存）
- 必要パッケージ（例）
  - duckdb
  - pyyaml
  - その他 Broker クライアント依存パッケージ
- SQLite / DuckDB ファイルの読み書き権限
- kabuステーション や J-Quants の認証情報（環境変数経由）

（実際の requirements はプロジェクトの requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをチェックアウト
   - git clone … && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は pyproject.toml を参照）

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 主要な必須項目:
     - JQUANTS_REFRESH_TOKEN
     - JQUANTS_BULK_API_KEY
     - KABU_API_PASSWORD
   - オプション: LINE 通知設定、KABUSYS_ENV（development / paper_trading / live）など

5. 設定検証
   - python -m kabusys.validate_config
   - 必要に応じて厳格モード: python -m kabusys.validate_config --strict

6. データベースの準備
   - デフォルトのパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite（監視）: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
   - 必要なスキーマや初期データは夜間バッチスクリプト等で生成される想定です。

---

## 使い方（主要 CLI / スクリプト）

各スクリプトは Python モジュールとして直接実行できます（プロジェクトルートで実行するのが推奨）。

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱い

- Execution（自動執行エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード用 DB（data/paper_trading.db）を使用
  - 起動時に execution.pid を書き込み、data/stop_requested.flag の検出で停止

- Monitoring 起動（バックグラウンド監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（秒、デフォルト 60）
  - 監視は環境にかかわらず本番 sqlite_path を使用（監視データは共通で記録される）

- ザラ場監視（CLI）
  - 単発: python -m kabusys.run_intraday_monitor
  - watch モード（自動更新）: python -m kabusys.run_intraday_monitor --watch --interval 30

- レポート生成（例）
  - Signal Queue: python -m kabusys.run_signal_queue_report --date 2026-04-28 --save --json
  - Pre-Market: python -m kabusys.run_pre_market_report --save
  - Market Close: python -m kabusys.run_market_close_report --date 2026-04-28 --save --json
  - Performance: python -m kabusys.run_performance_report --type daily --env paper_trading --save
  - Position Reconciliation: python -m kabusys.run_position_reconciliation_report --watch --interval 600

- Paper Trading 検証ツール
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能

注意点:
- 多くのスクリプトは exit code を使って状態を表現します（例えばレポートで BLOCKED / READY の場合 0/1 を返す等）。CI/監視連携時は戻り値を確認してください。
- 実行中の停止には data/stop_requested.flag ファイルを作成する方法が使われます（スクリプトは定期的に存在チェックを行い、見つけると安全に終了します）。

---

## 環境変数の主な項目（抜粋）

- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN, JQUANTS_BULK_API_KEY: J-Quants 用
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading での注文成立シミュレーション（instant/partial/never/reject）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）

詳細は `src/kabusys/config.py` 内の Settings クラスをご確認ください。

---

## 停止・PID・フラグファイル

- 起動スクリプトは data ディレクトリに PID ファイルを書きます（例: data/execution.pid, data/monitoring.pid）。
- 停止するにはプロセスを SIGINT/kill するか、`data/stop_requested.flag` を作成するとスクリプトは検出して安全に終了します。
- 本番環境での Kill Switch 等の挙動は設定で制御されます（KILL_FLAG_CLEAR_ON_START など）。

---

## artifacts / 出力

各レポート生成モジュールは artifacts ディレクトリ配下に保存できます（`--save` オプションで有効）。例:

- artifacts/pre_market/{YYYY-MM-DD}/
- artifacts/market_close/{YYYY-MM-DD}/
- artifacts/signal_queue/{YYYY-MM-DD}/
- artifacts/performance/{env}/{type}/{period}/
- artifacts/execution_startup/{YYYY-MM-DD}/
- artifacts/night_batch/{YYYY-MM-DD}/

保存されるファイルは一般に summary.json / report.md / warnings.json 等です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリングループ起動
  - run_intraday_monitor.py       — ザラ場監視 CLI
  - run_pre_market_report.py      — Pre-Market レポート CLI
  - run_market_close_report.py    — Market Close レポート CLI
  - run_performance_report.py     — 運用成績サマリ CLI
  - run_position_reconciliation_report.py — ポジション照合 CLI
  - run_signal_queue_report.py    — Signal Queue 確認 CLI
  - run_performance_report.py
  - run_pre_market_report.py
  - run_monitoring.py
  - operations/                    — レポート生成ロジック（純粋関数群）
    - pre_market_report.py
    - market_close_report.py
    - performance_report.py
    - performance_collector.py
    - signal_queue_report.py
    - execution_startup_report.py
    - night_batch_report.py
    - position_reconciliation_report.py (呼び出し元あり)
    - intraday_collector.py
  - execution/                     — ExecutionEngine 関連（BrokerFactory, Engine, OrderManager 等）
  - monitoring/                    — monitoring DB 初期化や SystemMonitor 実装
  - operations/                    — 各種データ収集 & レポートビルド
  - tools/                         — 補助ツール（paper_verification_report.py）
  - utils/                         — logging_setup, process_priority などユーティリティ

（上記は本 README に含まれるファイルを抜粋したものです。実際のファイル構成はリポジトリを参照してください）

---

## 開発上の注意 / 補足

- config.py はプロジェクトルート（.git または pyproject.toml）を基準に .env を自動ロードします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- run_monitoring は環境にかかわらず本番の sqlite_path を使用して監視データを記録します（設計上の意図に注意）。
- run_execution は paper_trading 時に専用の paper_sqlite_path を使用して本番データと分離します。
- 重要な環境変数未設定や config/*.yaml の不備は validate_config で検出可能です。
- 実際の運用ではログローテーションやプロセスマネージャ（systemd, supervisord 等）を使ってプロセス管理を行うことを推奨します。

---

この README はコードベースに含まれる CLI スクリプトと設定周りの主要な使い方をまとめたものです。詳細な実装や追加オプションについては各モジュール（src/kabusys/ 以下）の docstring とコードを参照してください。必要であれば、特定のスクリプトの使い方（引数や出力形式）をさらに詳しくまとめたセクションを追加します。