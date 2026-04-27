# KabuSys

日本株向け自動売買システムの軽量実装（ライブラリ／運用スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・レポート出力までを含む運用用モジュール群を提供します。モジュールはできるだけ純粋関数（副作用を抑えた設計）で実装されており、起動スクリプトから組み合わせて運用できます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド例）
- 環境変数（主要項目）
- 運用フラグ & ファイル
- ディレクトリ構成（主要ファイルと説明）

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を含む Python モジュール群です。

- データ収集 / ファクター計算（DuckDB を想定）
- シグナル生成 / ポートフォリオ構築（等金額・スコア重み・リスクベース等）
- 発注エンジン（kabuステーション API 経由、paper_trading モードでは MockBroker）
- 発注リコンシリエーション・リスク管理
- システム監視（定期ポーリングで system_status 等を記録）
- 多種類の起動時／日次レポート生成（Pre-Market / Execution Startup / Signal Queue / Night Batch / Paper Trading 検証 等）
- ロギング、プロセス優先度制御など運用向けユーティリティ

設計方針として、DB 参照や外部 API を行う箇所は明確に分離され、テストや解析のために純粋関数群も用意されています。

---

## 機能一覧（ハイライト）

- 起動スクリプト
  - run_execution: 発注エンジン起動（reconciliation → 実行ループ）
  - run_monitoring: SystemMonitor のポーリングループ
  - run_pre_market_report: Pre-Market（朝の運用可否）レポート出力
  - run_signal_queue_report: Signal Queue 確認ビュー
  - config_setup: .env 作成ウィザード
  - validate_config: .env / config/*.yaml の起動前検証
- レポートモジュール
  - Execution Startup Summary（起動直後サマリ）
  - Pre-Market Report（08:00頃の起動可否判定）
  - Night Batch Report（夜間バッチ確認）
  - Signal Queue Confirmation（翌営業日の発注予定確認）
  - Paper Trading 検証レポート（tools/paper_verification_report）
- ポートフォリオ関連（純粋関数）
  - 候補選定、重み計算、セクター露出制限、レジーム乗数、株数決定（単元丸め等）
- ユーティリティ
  - ロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
- DB
  - DuckDB：分析データ（デフォルト: data/kabusys.duckdb）
  - SQLite：監視・発注履歴（デフォルト: data/monitoring.db）
  - paper_trading 用 SQLite（paper_trading モード時は data/paper_trading.db）

---

## セットアップ手順

1. リポジトリをクローン／展開する

2. Python 環境を作成（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt があれば: pip install -r requirements.txt
   - 典型的には以下が必要です:
     - duckdb
     - psutil
     - PyYAML
   例:
     pip install duckdb psutil pyyaml

4. 環境変数設定 (.env)
   - プロジェクトルートの `.env`（または `.env.local`）を作成します。
   - 自動ウィザードを使う:
     python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - JQUANTS_BULK_API_KEY
     - KABU_API_PASSWORD
   - 自動ロード挙動:
     - 起動時に OS 環境変数 > .env.local > .env の順で読み込まれます（デフォルトで自動ロード有効）。
     - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 設定検証（起動前）
   python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

6. 初期データ / config の用意
   - config/*.yaml（risk_config.yaml 等）を config/ ディレクトリに配置してください。
   - SQLite / DuckDB のデフォルトファイルは data/ 以下に置かれます（必要に応じて環境変数で上書き）。

---

## 使い方（主要コマンド）

- 発注エンジンを起動
  - 本番または開発モードは KABUSYS_ENV によって切り替え
  - 本番（live）、ペーパートレード（paper_trading）、開発（development）
  - ペーパートレード時は MockBrokerClient を使用し、DB は data/paper_trading.db に記録されます。
  コマンド例:
    python -m kabusys.run_execution

- 監視ループ起動（SystemMonitor）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。
  コマンド例:
    python -m kabusys.run_monitoring
    # 例: 30秒毎にポーリング
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Pre-Market レポート（CLI）
  コマンド例:
    python -m kabusys.run_pre_market_report
    python -m kabusys.run_pre_market_report --json
    python -m kabusys.run_pre_market_report --save

- Signal Queue レポート（対象日指定可）
  コマンド例:
    python -m kabusys.run_signal_queue_report
    python -m kabusys.run_signal_queue_report --date 2026-04-28 --json --save

- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（tools）
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  環境変数:
    PAPER_TRADING_SQLITE_PATH を使って DB パスを指定可能（デフォルト: data/paper_trading.db）

- レポートの保存先
  - artifacts/pre_market/{YYYY-MM-DD}/
  - artifacts/signal_queue/{YYYY-MM-DD}/
  - artifacts/execution_startup/{YYYY-MM-DD}/
  - artifacts/night_batch/{YYYY-MM-DD}/

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development
- JQUANTS_REFRESH_TOKEN (必須)
- JQUANTS_BULK_API_KEY (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL
  - デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH
  - paper_trading モード時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL
  - DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- LOG_DIR
  - ログファイル保存ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE
  - paper_trading の MockBrokerClient の約定モード
  - instant | partial | never | reject

注意: .env は絶対に Git にコミットしないでください。

---

## 運用フラグ & ファイル

- 停止フラグ（自動実行停止）
  - data/stop_requested.flag
  - run_monitoring / run_execution / run_pre_market_report 等はこのファイルの存在を見て安全に停止または起動を抑止します。運用で自動執行を止めたい場合に作成してください。

- Kill フラグ
  - Settings().kill_flag_path（デフォルト: data/kill.flag）
  - 本番での緊急停止等に利用する運用フラグです。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアされます（本番では 0 を推奨）。

- PID ファイル
  - 実行エンジンは data/execution.pid 等の PID ファイルを生成します（Settings().pid_file_path）。

---

## ディレクトリ構成（主要ファイル・モジュールと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings クラス（自動 .env ロード、必須変数チェック）
  - config_setup.py
    - .env を対話式に作成・更新するウィザード
  - validate_config.py
    - 起動前チェック CLI（環境変数・config/*.yaml の存在・簡易パース）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（reconciliation → 実行スレッド）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_pre_market_report.py
    - Pre-Market レポートエントリポイント
  - run_signal_queue_report.py
    - Signal Queue 確認ビューのエントリポイント
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - （監視データベース初期化・SystemMonitor 実装）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
    - （発注ロジック・ブローカー抽象化）
  - operations/
    - pre_market_collector.py
    - pre_market_report.py
    - signal_queue_report.py
    - execution_startup_report.py
    - night_batch_report.py
    - （各種レポート構築ロジック）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
    - （ポートフォリオ構築・株数決定・リスク補正）
  - research/
    - factor_research.py
    - feature_exploration.py
    - （分析・ファクター計算）
  - tools/
    - paper_verification_report.py
    - （運用支援スクリプト）
  - utils/
    - logging_setup.py
    - process_priority.py
    - （ロギング設定、プロセス優先度制御等ユーティリティ）

- config/
  - 各種 YAML 設定ファイル（例: risk_config.yaml, system_config.yaml 等）
  - risk_config.yaml は run_execution 起動時に読み込まれ、形式／値チェックがあります。

- data/
  - デフォルトの DB ファイル、フラグファイル、PIDファイル等を置くディレクトリ（自動生成されることが多い）

- artifacts/
  - 各種レポートの保存先（実行時に生成される）

---

## リスク設定（補足）

- config/risk_config.yaml は run_execution に読み込まれ、以下の値等を検証します:
  - max_position_pct, max_utilization, max_drawdown：0 < 値 <= 1
  - rate_limit_per_sec, circuit_breaker_errors, circuit_breaker_window_sec：1 以上
- フォーマット不備や値範囲外は起動時に例外になりますので、validate_config の結果と合わせて事前に確認してください。

---

## 運用上の注意

- .env は機密情報を含むため、絶対にバージョン管理に含めないでください。
- 本番環境（KABUSYS_ENV=live）では LINE 通知や Kill Switch の設定が重要になります。validate_config は本番向けチェックを含みます。
- run_monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を参照します（監視データは本番 DB に記録される想定）。
- PID / フラグファイル（data/stop_requested.flag など）を使って外部から安全に停止できます。
- ログは stdout と日次ローテートのファイル（logs/<app_name>.log）に出力されます。LOG_DIR を環境変数で変更可能です。

---

## よく使うコマンド例（まとめ）

- .env 作成
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視起動（60秒毎、デフォルト）
  python -m kabusys.run_monitoring

- 発注エンジン起動
  python -m kabusys.run_execution

- Pre-Market レポート（表示 + 保存）
  python -m kabusys.run_pre_market_report --save

- Signal Queue レポートを JSON 出力（対象日指定）
  python -m kabusys.run_signal_queue_report --date 2026-04-28 --json --save

- Paper Trading 検証
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

質問や補足（例えば各モジュールの詳細な使い方、config/risk_config.yaml のサンプル、あるいは起動時のログ出力例）が必要であれば教えてください。必要に応じて README に追記するテンプレートやコマンドの例を追加します。