# KabuSys — README

このリポジトリは日本株向けの自動売買システム「KabuSys」のコアスクリプトとレポート生成モジュール群を含みます。  
以下はプロジェクトの概要、主な機能、セットアップ手順、利用方法、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は以下の要素を持つ自動売買システムです。

- 夜間バッチでシグナル生成 → 翌営業日に自動執行するフローを想定
- 実行エンジン（ExecutionEngine）、監視（SystemMonitor）、複数の CLI レポート／診断ツールを備える
- DuckDB（分析用）とSQLite（監視・履歴用）を利用
- 本番（live）／ペーパートレード（paper_trading）／開発（development）を環境変数で切替可能
- レポートは CLI で表示、JSON/Markdown で保存可能（artifacts 配下）

このリポジトリには、起動スクリプト、設定管理、各種レポート生成ロジック、運用診断ツールが含まれています。

---

## 機能一覧

主な機能（抜粋）:

- Execution 起動スクリプト（run_execution）
  - 本番/ペーパートレードのブローカー切替、起動時リコンシリエーション、ExecutionEngine の起動
  - 起動時に Execution Startup Summary を生成・保存可能
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離

- Monitoring（run_monitoring）
  - SystemMonitor のポーリングループを実行。監視データを SQLite に記録
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
  - stop フラグ（data/stop_requested.flag）で安全停止

- CLI レポート群
  - Pre-Market Report（run_pre_market_report）: 朝の運用開始準備チェック（READY / WARN / BLOCKED）
  - Market Close Summary（run_market_close_report）: 引け後チェック（OK / BLOCKED）
  - Night Batch Report（operations/night_batch_report）: 夜間バッチの総合判定
  - Signal Queue Confirmation（run_signal_queue_report / operations/signal_queue_report）
  - Position Reconciliation（run_position_reconciliation_report）
  - Performance Report（run_performance_report）: 日次/週次/月次の成績レポート
  - Intraday Monitor（run_intraday_monitor）: ザラ場中リアルタイム監視表示

- 設定管理・検証ツール
  - 環境設定ウィザード（config_setup）で .env の初期作成・更新を対話式に支援
  - validate_config による .env / config/*.yaml の事前検証

- 開発/運用ユーティリティ
  - Paper Trading 検証レポート（tools/paper_verification_report）など

---

## 前提・準備（Prerequisites）

- Python 3.9+（実行環境の仕様に合わせてください）
- 必要なパッケージ（代表例）
  - duckdb
  - PyYAML
- DuckDB / SQLite を使います。デフォルトパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper-trading SQLite: data/paper_trading.db

パッケージはプロジェクトの requirements.txt / pyproject.toml があればそちらを使用してください。

---

## 環境変数・設定

主に使う環境変数（一部抜粋）:

- JQUANTS_REFRESH_TOKEN（必須）
- JQUANTS_BULK_API_KEY（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABU_TRADE_PASSWORD（任意）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用、デフォルト: data/paper_trading.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとプロジェクト起動時の .env 自動ロードを無効化できます

設定の自動読み込み:
- プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードします。.env に機密情報を含めて Git 管理しないでください。

Settings クラス（config.py）で各種設定へのアクセスを提供しています。

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成してアクティベート
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または pip install duckdb pyyaml
4. 環境変数の設定
   - 対話形式で .env を作る（推奨）:
     - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - 失敗や警告が出たら .env や config/*.yaml を確認
5. 必要に応じてデータディレクトリを用意
   - data/（monitoring.db, kabusys.duckdb, paper_trading.db など）
   - artifacts/（レポートの保存先、実行時に自動作成される）

注意:
- config/risk_config.yaml などの YAML 設定ファイルが必要です。validate_config で存在確認・パース確認を行えます。

---

## 使い方（主要スクリプト）

多くのエントリポイントはモジュール実行（python -m）で利用します。以下に代表的な例を示します。

- 実行エンジン（Execution）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB を使用しモックブローカーが使われます
  - 停止は data/stop_requested.flag を作成（または該当の PID にシグナルを送るなど）

- 監視（SystemMonitor）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ザラ場中監視（CLI）
  - 一回だけ実行:
    - python -m kabusys.run_intraday_monitor
  - 監視モード（自動更新）:
    - python -m kabusys.run_intraday_monitor --watch --interval 60

- Signal Queue 確認
  - python -m kabusys.run_signal_queue_report
  - オプション: --date YYYY-MM-DD, --save（artifacts に保存）, --json（JSON 出力）

- Position Reconciliation レポート
  - python -m kabusys.run_position_reconciliation_report
  - オプション: --date, --save, --json, --watch, --interval

- Pre-Market / Market Close / Performance レポート
  - python -m kabusys.run_pre_market_report [--save] [--json]
  - python -m kabusys.run_market_close_report [--date YYYY-MM-DD] [--save] [--json]
  - python -m kabusys.run_performance_report --type daily|weekly|monthly [--env live|paper_trading] [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--save]

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証（ツール）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

レポートの保存:
- 各レポートは artifacts/ 以下に保存されます（例: artifacts/signal_queue/YYYY-MM-DD/ など）。--json を使うと標準出力に JSON を出力します。

監視・停止関連ファイル:
- data/stop_requested.flag — このファイルが存在すると多くのプロセスが安全に停止します
- data/*.pid — 実行中プロセスの PID を記録

---

## リスク設定（重要）

Execution 起動時に読み込まれる `config/risk_config.yaml` の主要設定項目（例）:

- risk.max_position_pct: 1 を最大とする割合（0 < v <= 1）
- risk.max_utilization: 0 < v <= 1（max_position_pct ≤ max_utilization を推奨）
- risk.rate_limit_per_sec: 1 以上の整数（API レート制限）
- risk.circuit_breaker_errors: 1 以上の整数
- risk.circuit_breaker_window_sec: 1 以上の整数
- risk.max_drawdown: 0 < v <= 1

不正な値や欠落は起動時にエラーとなります。

---

## ディレクトリ構成

主要なソースファイル / モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数 / Settings
    - config_setup.py                # .env 対話ウィザード
    - validate_config.py             # 設定検証 CLI
    - run_execution.py               # Execution 起動スクリプト
    - run_monitoring.py              # Monitoring ポーリングループ起動
    - run_intraday_monitor.py        # ザラ場中監視 CLI
    - run_signal_queue_report.py     # Signal Queue レポート CLI
    - run_position_reconciliation_report.py
    - run_performance_report.py
    - run_pre_market_report.py
    - run_market_close_report.py
    - run_monitoring.py
    - run_position_reconciliation_report.py
    - operations/
      - signal_queue_report.py
      - execution_startup_report.py
      - pre_market_report.py
      - market_close_report.py
      - night_batch_report.py
      - performance_report.py
      - performance_collector.py
      - pre_market_collector.py (参照される実装)
      - intraday_collector.py (参照される実装)
      - position_reconciliation_report.py (参照)
    - execution/
      - execution_engine.py (参照)
      - order_manager.py (参照)
      - order_repository.py (参照)
      - reconciler.py (参照)
      - broker_factory.py (参照)
      - risk_manager.py (参照)
    - monitoring/
      - system_monitor.py (参照)
      - monitoring_db.py (参照)
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py (参照)
      - process_priority.py (参照)
- config/
  - risk_config.yaml (等の YAML 設定ファイル)
- data/
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト: data/kabusys.duckdb)
  - paper_trading.db (ペーパートレード用)
  - stop_requested.flag, *.pid（実行時生成）
- artifacts/
  - signal_queue/
  - pre_market/
  - market_close/
  - performance/
  - execution_startup/
  - night_batch/

各モジュールの実装（execution/、monitoring/、operations/）はアプリケーション固有のロジックを含みます。README に載せきれない詳細はソースコードの docstring を参照してください。

---

## 運用上の注意事項

- 本番環境（KABUSYS_ENV=live）では特に LINE 通知などの設定を確認してください（validate_config で警告を確認できます）。
- .env に機密情報（API トークン、パスワード）を保存する場合は絶対に Git にコミットしないでください。
- 停止はなるべくデータベースや PID/フラグを通じて安全に行ってください（data/stop_requested.flag を利用）。
- ペーパートレードは本番 DB と分離しており、デフォルトで data/paper_trading.db を使用します。

---

## トラブルシューティング

- 設定チェックでエラーが出る:
  - python -m kabusys.validate_config を実行し、エラー／警告メッセージに従って .env や config/*.yaml を修正してください
- DB に接続できない:
  - DUCKDB_PATH / SQLITE_PATH のパスやファイルの有無、アクセス権を確認してください
- 監視が停止した:
  - data/*.pid を確認し、stop flag（data/stop_requested.flag）や監視プロセスのログを確認してください

---

必要であれば、各 CLI やモジュールの詳しい説明（引数、出力フォーマット、保存先パスなど）を追記します。どの部分を詳しく書くか指定してください。