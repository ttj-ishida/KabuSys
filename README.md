# KabuSys

日本株自動売買システム（部分実装） — 設定管理、監視、発注エンジン、ブローカークライアントなどのコアコンポーネントを含むコードベース。

> この README はリポジトリ内のソースコードを参照して作成しています。各種実行には環境変数 (.env) とローカルに配置される DB ファイルが必要です。

---

## 概要

KabuSys は日本株向けの自動売買基盤のコンポーネント群です。主な役割は以下です。

- 環境変数 / 設定ファイルの対話的作成と検証
- 発注エンジン（ExecutionEngine）によるシグナルに基づく発注フロー
- Broker クライアントの抽象化（実運用向けの KabuStationClient / テスト用の MockBrokerClient）
- 注文状態管理（状態遷移、永続化、リコンシリエーション）
- 監視ループ（SystemMonitor）によるリソース・イベント監視
- データユーティリティ（マーケットカレンダー、ニュース収集 等）

このリポジトリはモジュール化されており、開発／ペーパートレード／本番環境の切り替えやモッククライアントを用いたテストが可能です。

---

## 主な機能一覧

- .env の対話的生成ウィザード（kabusys.config_setup）
- .env / config/*.yaml の起動前検証 CLI（kabusys.validate_config）
  - `--strict` を指定すると警告も FAIL 扱いで終了コード 1 を返す
- ExecutionEngine（run_execution.py）
  - シグナルの読み込み、Gate1/2/3 のリスクチェック、発注、WebSocket プッシュ処理
  - paper_trading 環境では MockBrokerClient を使用し、本番 DB と分離
- Reconciler（起動時の OrderSent 状態の自動照合とポジション差分検出）
- Order 管理
  - OrderRecord（状態遷移のビジネスロジック）
  - OrderRepository（SQLite による永続化）
  - OrderManager（発注フローの Orchestration）
- ブローカークライアント
  - KabuStationClient：kabuステーション REST API 実装（httpx, websocket）
  - MockBrokerClient：単体テスト／開発用
- リスク管理（Rate limit / Circuit-breaker / ドローダウン等）
- データユーティリティ
  - calendar_management（JPX 営業日管理）
  - news_collector（RSS 収集、正規化、安全対策含む）
- 監視ループ（run_monitoring.py） — 監視用 SQLite/duckdb 使用

---

## 前提 / 必要環境

- Python 3.10 以上（型注釈に `|` を使用しているため）
- 推奨パッケージ（最小限）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml 内容検証に任意）
- 標準ライブラリの sqlite3, json, logging 等を使用

requirements.txt が無い場合は次のようにインストールしてください（例）:

pip install duckdb httpx websocket-client defusedxml PyYAML

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化する

   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

2. 必要パッケージをインストール

   pip install --upgrade pip
   pip install duckdb httpx websocket-client defusedxml PyYAML

3. .env を作成する
   - 対話式ウィザードを使う（推奨）:

     python -m kabusys.config_setup

     ウィザードは既存の `.env` を読み込み、入力・更新を支援します。
   - または手動で `.env` を作成（.env は絶対に Git にコミットしないでください）。

4. 設定を検証する

   python -m kabusys.validate_config
   # 警告も FAIL として扱う場合:
   python -m kabusys.validate_config --strict

5. DB 初期化
   - Execution 用の orders テーブル等は起動時に明示的に初期化する関数（init_orders_db 等）があります。run_execution/run_monitoring の起動前に SQLite ファイルが必要な場合はディレクトリを作成してください（例: data/）。

---

## 環境変数（主なもの）

必須（少なくとも設定が必要）:

- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨（デフォルト値あり）:

- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station のベース URL
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用（任意）
- LINE_USER_ID — LINE 通知先ユーザーID（任意）
- PAPER_FILL_MODE — paper_trading での fill 挙動（instant | partial | never | reject）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など（監視／安全装置関連）

.env を未作成の場合は config_setup を実行してください。

---

## 使い方（主要な実行コマンド）

- 環境設定ウィザード（.env の作成・更新）:

  python -m kabusys.config_setup

- 設定検証（.env と config/*.yaml のチェック）:

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 発注エンジンを起動（Execution エントリポイント）:

  python -m kabusys.run_execution

  ※ KABUSYS_ENV=paper_trading または development では MockBrokerClient が使われます。
  ※ 起動前に data ディレクトリや SQLite のパス親ディレクトリを作成しておいてください。
  ※ 停止は data/stop_requested.flag を作成するか、プロセスを SIGINT（Ctrl+C）で終了。

- 監視ループを起動（SystemMonitor）:

  python -m kabusys.run_monitoring

  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で変更可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用する旨に注意。

- 開発・テスト:
  - MockBrokerClient を用いた単体テストで発注／約定、キャンセルの挙動を確認できます。
  - ExecutionEngine はテスト時に _process_signals / _drain_push_queue を直接呼ぶことも想定されています。

---

## 注意点 / 運用上の設計注記

- kill switch:
  - 起動時および実行中に `KILL_FLAG`（デフォルト: data/kill.flag）を検出すると kill_switch が発動して全アクティブ注文をキャンセルします。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると、起動時に kill.flag があっても自動でクリアして起動します（本番では 0 を推奨）。

- Reconciliation:
  - 起動時に `Reconciler` が OrderSent 状態の注文と Broker を照合し、状態同期やポジション差分検出を行います。

- DB 分離:
  - paper_trading（ペーパートレード）は paper_sqlite_path（デフォルト: data/paper_trading.db）に記録され、本番の monitoring DB とは分離されます。

- 設定ファイル:
  - config/*.yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）が想定されています。存在しない場合は警告が出ます（generate_config スクリプトで生成する想定）。

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル・ディレクトリ構成（ソースは `src/kabusys` 配下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数の自動ロード、Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — Broker API のデータモデル・Protocol・ファクトリ
    - broker_factory.py      — Settings に基づく Broker クライアント生成
    - kabu_client.py         — KabuStationClient 実装（httpx / websocket）
    - mock_client.py         — MockBrokerClient（テスト用）
    - order_record.py        — OrderRecord と状態遷移ロジック
    - order_repository.py    — SQLite 永続化層
    - order_manager.py       — 発注フロー API（create/send/sync/cancel）
    - execution_engine.py    — ExecutionEngine 実装（シグナル処理・push ドレイン）
    - reconciler.py          — リコンシリエーション（OrderSent 照合・ポジション差分）
    - risk_manager.py        — Gate1/2/3 によるリスクガード
  - data/
    - calendar_management.py — マーケットカレンダー管理（duckdb）
    - news_collector.py      — RSS ニュース収集
    - jquants_client.py      — J-Quants API クライアント（参照のみ）
  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化・記録メソッド（参照）
    - system_monitor.py      — SystemMonitor 本体（参照）
  - utils/
    - logging_setup.py       — ロギング初期化
    - process_priority.py    — プロセス優先度設定

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

- .env (生成/管理対象)  
- data/ (DBファイル・PID/フラグファイル等をここに置く想定)

※ 上記はソース中で参照されているファイル一覧・役割をまとめたものです。実際のリポジトリにはさらにファイルやサブモジュールが存在する可能性があります。

---

## よく使うファイル・パス

- デフォルト DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- ペーパートレード SQLite: data/paper_trading.db
- PID ファイル（実行時）: data/execution.pid（設定により変更可）
- 停止フラグ: data/stop_requested.flag
- kill flag: data/kill.flag

---

## 開発・拡張のヒント

- 本番用 KabuStationClient は API の挙動に依存するため、テストは MockBrokerClient で行うと良いです。
- ExecutionEngine の主要ループはテスト可能なように分割されています（_process_signals / _drain_push_queue / _handle_push など）。
- Reconciler は OrderSent の「不確定」状態を解消するための重要な仕組みです。障害耐性の観点からロギングとテストを充実させてください。
- calendar_management は DuckDB に保存された market_calendar を優先する設計です。カレンダーデータ取得ジョブ（J-Quants）と組み合わせて運用してください。

---

もし README に追加したい利用例（.env のテンプレート、運用フロー図、requirements.txt の具体的内容、CI/CD 用の検証フロー等）があれば教えてください。必要に応じてサンプル .env のテンプレートや起動例、FAQ を追記します。