# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買運用支援ライブラリ／スクリプト群です。  
データ処理（DuckDB）、監視（SQLite ベース）、Execution（発注エンジン）や各種レポート生成を含む、運用に必要なユーティリティを提供します。

概要・目的
- 夜間バッチや戦略により生成されたシグナルを使って、自動発注（Execution）を行うための土台。
- 監視（System Monitor）や起動時のリコンシリエーション、Pre-Market / Night-Batch / Signal Queue の各種確認レポートを備える。
- Paper Trading（ペーパートレード）モードをサポートし、本番 DB と分離して検証できる。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine 起動（実際の発注または MockBroker による Paper Trading）
  - run_monitoring: SystemMonitor のポーリングループ（リソース監視等）
  - run_pre_market_report: Pre-Market Report（運用開始可否判定）生成
  - run_signal_queue_report: Signal Queue 確認ビュー生成
  - config_setup: .env を対話式に作成・更新するウィザード
  - validate_config: .env と config/*.yaml の事前検証 CLI

- レポート / 操作モジュール
  - operations/*: Pre-Market / Night-Batch / Execution Startup / Signal Queue レポート作成ロジック
  - portfolio/*: 銘柄選定・重み計算・リスク調整・株数算出などの純粋関数群
  - research/*: ファクター計算、特徴量探索用ユーティリティ
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成

- 設定管理
  - config.py: 環境変数読み込み・Settings クラス（.env 自動読み込み、無効化オプション有り）
  - config_setup.py: .env ウィザード（対話式）

- ユーティリティ
  - logging_setup: 統一的なログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

1. リポジトリを取得
   - git clone などで取得し、プロジェクトルートに移動。

2. Python 環境の準備
   - Python 3.9+ を推奨（コードは型注釈に Optional / list[str] 等を使用）。
   - 仮想環境を作成して有効化:
     ```sh
     python -m venv .venv
     source .venv/bin/activate  # Linux / macOS
     .venv\Scripts\activate     # Windows
     ```
   - 必要パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを使用）:
     ```
     pip install duckdb psutil pyyaml
     ```
     - 注意: 実行環境により schtasks のチェック（Windows Task Scheduler）を使うため Windows での運用を想定した部分があります。
     - PyYAML は config/risk_config.yaml などをパースするために使用します。

3. .env 作成
   - 対話式ウィザードで作成:
     ```sh
     python -m kabusys.config_setup
     ```
   - あるいは .env.example を参考に手動で .env を作成してください。

   - 自動環境変数読み込みを無効にしたい場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。

4. 設定の検証（起動前チェック）
   ```sh
   python -m kabusys.validate_config
   ```
   - 警告も失敗としたい場合は `--strict` を付けます。

5. データベースファイル / ディレクトリ
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - 必要に応じて .env で `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` を上書きしてください。

---

## 使い方（よく使うコマンド）

- Execution 起動（本番 / ペーパーは KABUSYS_ENV で切替）
  - 本番（KABUSYS_ENV=live）:
    ```sh
    python -m kabusys.run_execution
    ```
  - ペーパートレード（DB を完全に分離して記録）:
    ```sh
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - ペーパートレード動作モード:
    - `PAPER_FILL_MODE` 環境変数で挙動を制御（instant / partial / never / reject）

- Monitoring（常駐ポーリング）
  - デフォルトは 60 秒間隔。環境変数で上書き可能:
    ```sh
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 停止はプロジェクトルートの `data/stop_requested.flag` を作成することで検知して終了します。

- Pre-Market レポート生成
  ```sh
  python -m kabusys.run_pre_market_report
  python -m kabusys.run_pre_market_report --save
  python -m kabusys.run_pre_market_report --json
  ```

- Signal Queue レポート（任意日指定・保存・JSON）
  ```sh
  python -m kabusys.run_signal_queue_report --date 2026-04-28 --save --json
  ```

- Paper Trading 検証レポート
  ```sh
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - SQLite ファイルは `PAPER_TRADING_SQLITE_PATH` 環境変数または `--db` オプションで指定可能。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: 実行環境
  - development / paper_trading / live（デフォルト: development）

- JQUANTS_REFRESH_TOKEN, JQUANTS_BULK_API_KEY: J-Quants API 用
- KABU_API_PASSWORD, KABU_API_BASE_URL, KABU_TRADE_PASSWORD: kabuステーション API 用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 sqlite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存先ディレクトリ（default: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 本番で Kill Switch を自動クリアするか（0/1）

注意: `config.py` は起動時にプロジェクトルートの `.env` / `.env.local` を自動読み込みします。自動読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ログ / アーティファクト / 一時ファイル

- ログ
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30 日分保持）
  - コンソールは stdout に出力されます（stderr を汚染しない設計）

- レポート保存先（各レポートモジュール）
  - artifacts/pre_market/{YYYY-MM-DD}/
  - artifacts/signal_queue/{YYYY-MM-DD}/
  - artifacts/execution_startup/{YYYY-MM-DD}/
  - artifacts/night_batch/{YYYY-MM-DD}/

- 制御フラグ / PID ファイル（プロジェクトルートの data/ ディレクトリ）
  - data/stop_requested.flag: 停止フラグ（存在を検知して安全に停止）
  - data/execution.pid: Execution の PID（設定による）
  - data/kabusys.duckdb / data/monitoring.db / data/paper_trading.db（各 DB）

---

## ディレクトリ構成（主要ファイル）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - run_pre_market_report.py
    - run_signal_queue_report.py
    - operations/
      - pre_market_collector.py
      - pre_market_report.py
      - signal_queue_report.py
      - execution_startup_report.py
      - night_batch_report.py
    - execution/
      - (ExecutionEngine, BrokerClientFactory, OrderManager などの実装ファイル)
    - monitoring/
      - (SystemMonitor, monitoring_db 初期化など)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py

※ 実行スクリプトはパッケージモードで起動することを想定しています（python -m kabusys.<module>）。

---

## 開発者向けメモ / 運用上の注意

- 設定検証:
  - 起動前に `python -m kabusys.validate_config` を実行して設定と YAML の基本チェックを行ってください。
  - 本番（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）の設定を推奨します。

- Paper Trading:
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db）に記録されます。本番 DB と完全分離されます。

- プロセス優先度:
  - 起動スクリプトは最初にプロセス優先度を "high" に設定しようとします。アクセス権限や OS により設定できない場合は警告となりスキップされます。

- Windows Task Scheduler:
  - Pre-Market コレクタは `schtasks` を利用して Task Scheduler の状態（Ready かどうか）を確認します。非 Windows 環境ではこのチェックは失敗して `False` を返しますが、ログに警告が出ます。

- ロギング:
  - ログディレクトリの作成に失敗した場合はファイル出力を無効化し、コンソール出力のみで継続します。

---

README はコードの概観と運用上のポイントをまとめたものです。  
追加したい内容（例: API ドキュメント、ExecutionEngine の詳細、ブローカーインターフェース仕様、config/risk_config.yaml の説明等）があれば教えてください。