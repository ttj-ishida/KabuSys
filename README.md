# KabuSys (README)

日本株自動売買システムの軽量コア実装（エントリポイント・設定・レポート生成群）。  
このリポジトリには、Execution（発注エンジン）・Monitoring（監視）・各種レポート生成ツール・設定ウィザードなどが含まれます。

> 注: 本 README はリポジトリ内の Python モジュール群（src/kabusys/*）のコードからドキュメントを起こしたものです。

## 概要（Project overview）

KabuSys は J-Quants / kabuステーション 等を用いた日本株向け自動売買システムの構成要素をまとめたコード群です。  
主に次を提供します。

- ExecutionEngine（発注ループ、リスク管理、注文管理、リコンシリエーション）
- System Monitoring（リソース / プロセス健全性監視）
- 日中監視（CLI で現在状態を確認するツール）
- 各種レポート生成（Pre-Market / Market-Close / Performance / Signal Queue / Execution Startup / Position Reconciliation / Night Batch など）
- 設定ウィザード & 設定検証ツール
- Paper Trading 用検証ツール

設計方針として、レポート生成モジュールは呼び出し元からデータを受け取り純粋関数的にレポートを作るよう分離されています（テストや再利用が容易）。

## 主な機能一覧

- 実行関連
  - ExecutionEngine 起動スクリプト: `kabusys.run_execution`
  - 起動時リコンシリエーション（broker ⇄ local）
  - リスク管理（config/risk_config.yaml）
  - Paper Trading モード（MockBrokerClient、DB を分離）

- 監視関連
  - SystemMonitor ポーリングループ: `kabusys.run_monitoring`
  - ザラ場中監視 CLI（単発/継続表示）: `kabusys.run_intraday_monitor`

- レポート・分析
  - Pre-Market / Market Close / Performance / Signal Queue / Position Reconciliation / Execution Startup / Night Batch レポート生成（CLI で実行可）
  - レポートの CLI 表示・JSON 出力・Markdown 保存（artifacts 以下に保存）

- 開発・運用支援
  - 設定ウィザード: `.env` を対話形式で作成する `kabusys.config_setup`
  - 設定検証: `.env` と config/*.yaml のチェック `kabusys.validate_config`
  - Paper Trading 向け検証レポート: `kabusys.tools.paper_verification_report`

## セットアップ手順

1. リポジトリをクローンし、ソースルートへ
   - (この README は `src/` 配下のモジュールを想定しています)

2. Python 仮想環境を作成して有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 最低限必要なパッケージ例:
     - pip install duckdb pyyaml
   - SQLite は標準ライブラリで提供されます。

4. 環境変数 / .env の準備
   - リポジトリルートに `.env` を作成するか、ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは手動で必要な環境変数を設定します（下の「環境変数一覧」を参照）。

5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリや DB ファイルの場所を確認（必要に応じてディレクトリを作成）
   - デフォルトの DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db

備考:
- 自動で .env を読み込む仕組みが組み込まれています（.env, .env.local）。  
  自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## 環境変数（主なもの）

必須・重要な環境変数とデフォルト値（ない場合は .env を参照）:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- JQUANTS_BULK_API_KEY — J-Quants の Bulk API キー（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABU_TRADE_PASSWORD — 取引パスワード（任意）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（任意）
- LINE_USER_ID — LINE 通知先（任意）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の埋め方（デフォルト: "instant"。有効値: "instant" | "partial" | "never" | "reject"）
- KABUSYS_ENV — 実行環境（デフォルト: development）。有効値: development, paper_trading, live
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — SystemMonitor のポーリング間隔（秒、デフォルト 60）

ファイルベースの制御:
- data/stop_requested.flag — 存在すると実行ループを停止します
- data/kill.flag — （Settings.kill_flag_path）運用用の Kill Switch
- data/execution.pid, data/monitoring.pid — PID ファイル（起動時に書き出されます）

## 使い方（主要 CLI）

各モジュールは Python のモジュール実行（-m）で起動できます。例を示します。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告も fail）
    - python -m kabusys.validate_config --strict

- Execution（発注エンジン）起動
  - KABUSYS_ENV=live（実際の発注）または paper_trading（モック）
  - python -m kabusys.run_execution
  - Paper Trading の場合は .env で KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、データは data/paper_trading.db に記録されます。

- Monitoring（システム監視）起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - python -m kabusys.run_monitoring

- ザラ場中監視（CLI）
  - 単発表示:
    - python -m kabusys.run_intraday_monitor
  - 継続監視（N 秒ごと）:
    - python -m kabusys.run_intraday_monitor --watch --interval 30

- レポート系（例）
  - Signal Queue Confirmation（対象日指定 / JSON / 保存）
    - python -m kabusys.run_signal_queue_report --date 2026-04-28 --json --save
  - Position Reconciliation
    - python -m kabusys.run_position_reconciliation_report --date 2026-04-28 --save
    - 監視モード:
      - python -m kabusys.run_position_reconciliation_report --watch --interval 300
  - Pre-Market Report
    - python -m kabusys.run_pre_market_report --json --save
  - Market Close Summary
    - python -m kabusys.run_market_close_report --date 2026-04-28 --json --save
  - Performance Report（daily/weekly/monthly）
    - python -m kabusys.run_performance_report --type daily --env live --from 2026-01-01 --to 2026-04-30 --save

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

各レポートコマンドは出力を CLI に印字し、`--save` で artifacts 以下に Markdown / JSON を保存します。

保存先の例:
- artifacts/signal_queue/{YYYY-MM-DD}/
- artifacts/execution_startup/{YYYY-MM-DD}/
- artifacts/pre_market/{YYYY-MM-DD}/
- artifacts/market_close/{YYYY-MM-DD}/
- artifacts/performance/{env}/{type}/{period}/
- artifacts/night_batch/{YYYY-MM-DD}/

## 停止・プロセス制御

- 停止フラグ:
  - 実行中に `data/stop_requested.flag` を作成すると多くのデーモン（execution/monitoring 等）は安全にループを抜けて終了します。
- PID ファイル:
  - 起動時に `data/execution.pid` / `data/monitoring.pid` が書き出され、終了時に削除されます。
- Kill Switch:
  - `Settings.kill_flag_path`（デフォルト data/kill.flag）で運用中に強制的に自動執行を阻止する用途に使います（validate_config が live 環境では設定を警告します）。

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル/ディレクトリ（src 配下を中心に）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / .env 自動ロード / Settings クラス
    - config_setup.py           — 対話形式 .env ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor 起動スクリプト
    - run_intraday_monitor.py   — ザラ場中監視 CLI
    - run_signal_queue_report.py
    - run_position_reconciliation_report.py
    - run_pre_market_report.py
    - run_market_close_report.py
    - run_performance_report.py
    - run_performance_report.py
    - run_performance_report.py
    - operations/                — 各種レポート生成ロジック（pure functions）
      - signal_queue_report.py
      - performance_report.py
      - performance_collector.py
      - pre_market_report.py
      - market_close_report.py
      - execution_startup_report.py
      - night_batch_report.py
      - position_reconciliation_report.py (参照/利用)
      - intraday_collector.py (参照)
    - execution/                 — Execution 関連（Engine, OrderManager, RiskManager, BrokerFactory 等）
    - monitoring/                — 監視 DB 初期化や SystemMonitor 実装
    - tools/
      - paper_verification_report.py
    - utils/                     — logging_setup, process_priority 等ユーティリティ

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （存在しない場合は generate や参照箇所で警告が出ます）

- data/
  - monitoring.db (SQLite のデフォルト)
  - paper_trading.db (Paper Trading 用 SQLite)
  - kabusys.duckdb (DuckDB は data/kabusys.duckdb がデフォルト)
  - stop_requested.flag, kill.flag, *.pid

- artifacts/
  - （レポート保存先。コマンドの --save でここに出力されます）

## 設定と YAML の注意点

- risk_config.yaml 等の YAML ファイルは `pyyaml`（yaml.safe_load）で読み込まれます。インストールされていない場合は一部の検証や起動時の読み込みで警告・例外が発生する可能性があります。
- `validate_config` は YAML のパースチェックも行います（PyYAML がある場合）。
- risk_config.yaml の各パラメータは厳密にチェックされます（例: 0 < max_position_pct <= 1、rate_limit_per_sec >= 1 など）。

## 開発者向けメモ

- report モジュール群（operations 以下）は「DB 参照せず受け取ったデータのみでレポートを構築する」設計が基本です。ユニットテストが書きやすく、CLI 側は DB 参照を collect_* 関数で行う実装になっています。
- `.env.local` はローカルでの上書きに使えます（.env の上から上書きされます）。OS 環境変数は保護されます。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで便利です）。

## よくある運用コマンドまとめ

- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 起動（本番・ペーパー）
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視起動
  - python -m kabusys.run_monitoring
- ザラ場中監視（表示）
  - python -m kabusys.run_intraday_monitor --watch --interval 30
- レポート生成（例）
  - python -m kabusys.run_pre_market_report --json --save
  - python -m kabusys.run_signal_queue_report --date 2026-04-28 --save

---

この README はコード内のドキュメント文字列と設定項目をもとに作成しています。実際の運用時は config/*.yaml および .env（機密情報は絶対に Git にコミットしない）を正しく設定し、安全に実行してください。