# KabuSys

日本株自動売買システムのサンプル実装（モジュール化された Execution / Monitoring / Data レイヤーを含む）。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、kabuステーション API（およびテスト用のモック）を使った日本株の自動売買基盤の骨組みです。  
主な責務は以下です。

- シグナルに基づく発注フロー（ExecutionEngine）
- ブローカーとの同期・リコンシリエーション（Reconciler）
- 発注状態管理（OrderRecord / OrderRepository / OrderManager）
- 3段階リスクガード（RiskManager）
- 監視（SystemMonitor を用いた polling）
- データ処理（マーケットカレンダー、RSS ニュース収集など）
- 開発用モックブローカー（MockBrokerClient）によるローカル検証

設計方針は「DB（永続化）とビジネスロジックの分離」「クラッシュ・リカバリを考慮した永続化手順」「テスト容易性の確保（モック／paper_trading）」です。

---

## 機能一覧

- .env ベースの設定管理（.env / .env.local 自動ロード）
- 対話式 .env 作成ウィザード（kabusys.config_setup）
- 起動前の設定検証 CLI（kabusys.validate_config）
- ExecutionEngine（信号取り込み → Gate1/2 → 発注 → Push ドレイン）
- Broker クライアント抽象化（実ブローカ / モックを同一インターフェースで使用）
- 注文状態遷移の厳密管理（OrderRecord / InvalidStateTransitionError）
- 発注履歴永続化（SQLite）と分析用 DuckDB 統合
- リコンシリエーション（再起動時の OrderSent 照合、ポジション差分検出）
- 3段階リスクガード（シグナルレベル / エグゼキューションレベル / メトリクス）
- 監視ループ（監視 DB へログ、プロセス優先度設定、停止フラグ）
- データモジュール（カレンダー管理、RSS ニュース収集）

---

## セットアップ手順

前提: Python 3.10+ を想定（typing の一部で新しい構文を使用）。

1. リポジトリをクローンし、仮想環境を作成・有効化する。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なパッケージをインストールする。
   - requirements.txt が用意されている場合:
     - pip install -r requirements.txt
   - 主要依存例（最低限）:
     - pip install duckdb httpx websocket-client pyyaml defusedxml

3. 初期設定ファイル（.env）を作成する。
   - 対話型ウィザードを使用:
     - python -m kabusys.config_setup
   - 手動作成する場合はリポジトリルートに `.env` を置く（.env.example を参考に）。

4. 設定の検証:
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

5. DB 初期化はランタイム内で行われます（Execution / Monitoring 起動時に必要テーブルを作成します）。
   - デフォルトの DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading の場合）

注意:
- `.env` は決して Git にコミットしないでください（README ヘッダにも警告を出力する仕様あり）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途）。

---

## 環境変数（主要）

validate_config や config.py に基づく主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（よく使われる設定）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABU_API_BASE_URL: kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知設定
- KILL_FLAG_CLEAR_ON_START: 0|1（起動時に kill.flag を自動クリアするか）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

サンプル（.env の一部）:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 使い方

- 設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 失敗（exit code 1）条件:
    - 未設定の必須環境変数がある場合は常に FAIL
    - --strict を付けると警告も FAIL 扱い

- 実行エンジン起動（発注エンジン）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV が paper_trading または development の場合はモックブローカーを使用
    - 起動時に data/execution.pid（PID）を書き、停止は data/stop_requested.flag を作成して待機ループに伝える
    - kill スイッチは settings.kill_flag_path（デフォルト data/kill.flag）を参照

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境に関係なく本番の sqlite_path を使用して監視テーブルを初期化・更新
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒）

- 開発・テスト
  - MockBrokerClient を用いることで kabuステーションを起動せずに発注フローを検証可能
  - paper_trading 環境では専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）に書き込まれ、本番 DB と分離される

停止方法の例:
- 監視・実行ループを安全に停止するにはプロジェクトルートの data/stop_requested.flag を作成する（run_* スクリプトで検知して終了）。
- kill スイッチを発動させたい（全注文をキャンセル）場合は data/kill.flag を作成する（設定により起動時にクリアされる場合あり）。KILL_FLAG_CLEAR_ON_START に注意。

ログ:
- アプリは settings.log_level を読みます。ログ出力は設定に従って stdout/stderr に出力されます。

---

## ディレクトリ構成（主なファイル）

リポジトリ内の主要モジュール・ファイルの目次（src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings 定義（自動 .env ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — Broker API の Protocol / データモデル / 例外 / ファクトリ
    - kabu_client.py         — kabuステーションの HTTP/WebSocket クライアント
    - mock_client.py         — テスト用 MockBrokerClient
    - broker_factory.py      — Settings に応じたクライアント作成
    - order_record.py        — OrderRecord と状態遷移
    - order_repository.py    — SQLite 永続化層
    - order_manager.py       — 発注フローの上位 API（create/send/sync/cancel）
    - execution_engine.py    — Session 実行ロジック（信号処理／push drain）
    - reconciler.py          — 起動時のリコンシリエーション（OrderSent 照合、ポジション差分）
    - risk_manager.py        — 3 段階リスクガード
  - data/
    - calendar_management.py — マーケットカレンダー管理（J-Quants 統合想定）
    - news_collector.py      — RSS ニュース収集・前処理
    - (その他 jquants_client 等)
  - monitoring/
    - monitoring_db.py       — 監視用 DB 初期化 / 書き込み（参照されている）
    - system_monitor.py      — 監視ロジック（参照されている）
  - utils/
    - logging_setup.py       — ログセットアップユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ

data ディレクトリ（ランタイムに生成されることを想定）:
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/execution.pid
- data/stop_requested.flag
- data/kill.flag

---

## 開発上の注意・運用メモ

- .env は機密情報を含むため、絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では特に LINE の通知設定や KILL_FLAG_CLEAR_ON_START の値に注意してください。validate_config は live の場合に追加警告を出力します。
- Order の永続化と送信はクラッシュ耐性を考慮した手順（OrderSent の永続化・broker_order_id の早期保存など）になっています。実装変更時はクラッシュ復旧シナリオを意識してください。
- DuckDB は分析向けのローカル DB。signals / portfolio_targets などが格納され、ExecutionEngine がそれを参照して発注対象を決定します。
- 実ブローカ実装（KabuStationClient）は API の HTTP と WebSocket を扱います。kabuステーションアプリがローカルで動作していることが前提です。開発時は MockBrokerClient を推奨します。

---

必要に応じて README を拡張します（例: 詳細な .env の説明、SQL スキーマ、CI 実行手順、テスト例など）。どの項目を詳しくしたいか指示してください。