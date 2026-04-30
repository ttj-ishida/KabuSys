# KabuSys

日本株向け自動売買システムの一部を含むコードベースのドキュメントです。  
この README ではプロジェクトの概要、主要機能、初期セットアップ、よく使うコマンド例、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は、J-Quants / kabuステーション 等の外部 API と連携してシグナル生成・ポートフォリオ構築・自動発注・監視・レポート作成を行う自動売買システムの一部です。  
このリポジトリには、実行エンジン（Execution）、監視（Monitoring）、各種運用レポート生成（Pre-Market / Market Close / Performance / Signal Queue / Position Reconciliation / Night Batch など）や運用支援ツールが含まれます。

主な特徴：
- 実行（ExecutionEngine）と監視（SystemMonitor）の独立した起動スクリプト
- Paper Trading（ペーパートレード）モードの分離（専用 SQLite DB）
- DuckDB を用いた分析 / レポート生成
- 起動時・夜間バッチ・引け後などのチェック／サマリ生成とアーティファクト保存
- .env 対応の設定管理（ウィザード・検証ツール有り）

---

## 機能一覧（抜粋）

- 実行関連
  - run_execution: ExecutionEngine を起動（本番 / paper_trading 対応）
  - BrokerClientFactory によるブローカークライアントの切替（paper_trading では Mock）
  - リコンシリエーション（起動時にブローカーとローカル注文・ポジションの同期）
  - リスク管理（config/risk_config.yaml を使用）

- 監視 / オペレーション
  - run_monitoring: SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可能）
  - run_intraday_monitor: インタラクティブなザラ場モニタ（1回出力 or watch モード）
  - kill / stop フラグ (data/stop_requested.flag, data/kill.flag 等) による外部停止制御

- レポート / 集計
  - run_pre_market_report: 朝の自動執行可否チェック（Pre-Market Report）
  - run_market_close_report: 引け後の当日締めチェック（Market Close Summary）
  - run_performance_report: 日次/週次/月次の運用成績レポート（DuckDB 参照）
  - run_position_reconciliation_report: ブローカーとローカルのポジション照合レポート
  - run_signal_queue_report: 翌営業日の発注シグナル確認ビュー
  - tools/paper_verification_report.py: ペーパートレード DB の検証レポート

- 設定支援 / 検証
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env と config/*.yaml の事前検証（--strict オプション有り）

- レポート保存
  - artifacts/ 以下に report.md / summary.json / warnings.json 形式で保存

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンして Python 仮想環境を用意
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 本リポジトリに requirements.txt がある想定で:
     - pip install -r requirements.txt
   - 最低限必要になりやすいパッケージ（例）:
     - pip install duckdb PyYAML

   ※ 実プロジェクトでは pyproject.toml / requirements.txt を参照してください。

3. .env の作成
   - 設定ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
     - ウィザードが ./.env を作成または更新します。
   - あるいは手動で .env を作成（.env.example を参照する想定）
   - 自動ロードについて:
     - デフォルトでプロジェクトルートの `.env` / `.env.local` を自動読み込みします。
     - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ作成（必要に応じて）
   - data/ ディレクトリなど（SQLite / DuckDB のデフォルトパス）を作成しておくと安全です。
   - 例: mkdir -p data artifacts

---

## 環境変数（主要）

必須（少なくとも設定しておくべき）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- JQUANTS_BULK_API_KEY — J-Quants Bulk API キー
- KABU_API_PASSWORD — kabuステーション API パスワード

オプション / デフォルト
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant / partial / never / reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START — 起動時に Kill Flag をクリアするか（0/1、デフォルト: 0）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）

プロセス / 停止フラグ
- 停止フラグ: data/stop_requested.flag を作成すると run_execution / run_monitoring 等が停止を検知して終了します。
- PID ファイル:
  - data/execution.pid（Execution 側）
  - data/monitoring.pid（Monitoring 側）
- kill フラグ: デフォルト KILL_FLAG_PATH 環境変数で設定（Settings.kill_flag_path）

注意:
- Settings クラスはデフォルトでプロジェクトルートの .env / .env.local を自動ロードします。
- .env 内のプレースホルダ（your_value 等）は validate_config により警告されます。

---

## 使い方（主要コマンド例）

各コマンドはパッケージモジュールとして実行できます。プロジェクトルートで仮想環境を有効化してから実行してください。

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - リスク設定ファイル: config/risk_config.yaml（存在必須）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）に記録されます。

- 監視ループを起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒数で上書き（例: MONITOR_POLL_INTERVAL=30）
  - 停止は data/stop_requested.flag を作成（touch data/stop_requested.flag）または Ctrl+C

- ザラ場中監視 CLI（1回表示 / 監視モード）
  - python -m kabusys.run_intraday_monitor
  - 監視モード: python -m kabusys.run_intraday_monitor --watch --interval 60

- Pre-Market レポート（朝 08:00 想定）
  - python -m kabusys.run_pre_market_report
  - 保存: --save、JSON: --json

- Market Close レポート（引け後）
  - python -m kabusys.run_market_close_report --date 2026-04-28 --save --json

- Performance レポート（日次/週次/月次）
  - python -m kabusys.run_performance_report --type daily --from 2026-01-01 --to 2026-04-30 --save
  - --env live|paper_trading（既定 live）

- Position Reconciliation レポート
  - python -m kabusys.run_position_reconciliation_report --date 2026-04-28 --save
  - --watch モードで定期ポーリングが可能

- Signal Queue 確認ビュー
  - python -m kabusys.run_signal_queue_report --date 2026-04-28 --save --json
  - 戻り値: report.status == "READY" だと exit code 0、それ以外は非ゼロ

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ペーパートレード検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

注意事項:
- 多くのレポートコマンドは DuckDB を read-only で参照します（Settings.duckdb_path）。
- run_execution は起動時に monitoring 用テーブルがあるかを保証するため init_monitoring_db を呼び出します（冪等処理）。

---

## アーティファクト保存先

各レポートはデフォルトで `artifacts/` 以下に保存できます（--save オプション）。例:
- artifacts/pre_market/{YYYY-MM-DD}/
- artifacts/market_close/{YYYY-MM-DD}/
- artifacts/performance/{env}/{type}/{period}/
- artifacts/signal_queue/{YYYY-MM-DD}/
- artifacts/execution_startup/{YYYY-MM-DD}/
- artifacts/night_batch/{YYYY-MM-DD}/

各ディレクトリに report.md / summary.json / warnings.json 等が作成されます。

---

## ディレクトリ構成（主要ファイルのみ）

典型的なリポジトリ内の構成（src/kabusys 配下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - run_intraday_monitor.py   — ザラ場中監視 CLI
  - run_pre_market_report.py  — Pre-Market Report
  - run_market_close_report.py— Market Close Summary
  - run_performance_report.py — Performance Summary
  - run_position_reconciliation_report.py
  - run_signal_queue_report.py
  - operations/                — 各種レポート生成ロジック（純粋関数群）
    - pre_market_report.py
    - market_close_report.py
    - performance_report.py
    - performance_collector.py
    - signal_queue_report.py
    - execution_startup_report.py
    - night_batch_report.py
    - position_reconciliation_report.py (参照)
  - execution/                 — 実行関連コンポーネント（BrokerClientFactory, Engine, OrderManager 等）
  - monitoring/                — 監視関連（SystemMonitor, monitoring_db 等）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - など

この README の内容はコード内の docstring / コメントに基づいています。実際に利用する場合は各モジュールの docstring や help 表示（--help）を参照してください。

---

## トラブルシューティング

- DB 接続エラー:
  - 設定されている DUCKDB_PATH / SQLITE_PATH を確認、ファイルの存在やパーミッションをチェックしてください。
  - validate_config で事前チェックを実行できます。

- 設定が読み込まれない:
  - .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索します。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動ロードにしてください。

- 実行停止:
  - 停止させたい場合は data/stop_requested.flag を作成してください。run_execution/run_monitoring はこれを検知して安全に停止します。
  - PID ファイルは data/*.pid に書き出されます（実行中のプロセス管理用）。

---

この README は主要な操作・設定を速やかに把握するための概要です。各コマンドの細かいオプションやリスク設定の詳細等は、該当するモジュール内の docstring と config/*.yaml（risk_config.yaml 等）を参照してください。必要であれば README を拡張して、さらに詳細な運用手順やデプロイ手順を追加します。