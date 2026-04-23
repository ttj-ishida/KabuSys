# KabuSys

日本株自動売買システム（KabuSys）の簡易ドキュメント / セットアップガイド

このリポジトリは、kabuステーション（およびテスト用のモック）を用いた発注エンジン、監視プロセス、データ処理ユーティリティ群を含む自動売買基盤の一部実装です。パッケージは src/kabusys 配下に実装されています。

---

## プロジェクト概要

KabuSys は次のような目的で設計されています。

- シグナル駆動の発注エンジン（ExecutionEngine）
- 発注状態管理（OrderRecord / OrderRepository / OrderManager）
- リスクガード（3段階：Gate1/Gate2/Gate3）
- ブローカークライアント（実装: MockBrokerClient / KabuStationClient）
- 起動時のリコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor を用いる監視プロセス）
- データ処理（マーケットカレンダー、ニュース収集など）
- 環境設定ウィザードおよび設定検証ツール

設計方針として、ビジネスロジックと永続化層を分離し、クラッシュ耐性（2相永続化や再照合）や安全停止（kill switch / サーキットブレーカー）を備えます。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話的作成 / 更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env および config/*.yaml のチェック）
  - python -m kabusys.validate_config [--strict]
- 発注エンジン起動スクリプト（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって Mock / 実ブローカーの振る舞いを切替
- 監視プロセス起動スクリプト（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
- ブローカー API 層（Protocol + Mock + KabuStationClient 実装）
- 注文状態機構（OrderRecord の状態遷移検証）
- SQLite（監視/注文）および DuckDB（分析 / シグナル）連携
- マーケットカレンダー管理（J-Quants 経由での更新）
- ニュース収集（RSS 取込、SSRF 対策、前処理）

---

## 必要な環境変数（主要）

以下は本プロジェクトで利用される主要な環境変数です。必須なものは起動前に必ず設定してください。

必須（最低限設定が必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / デフォルトあり
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live` （デフォルト: development）
  - `paper_trading` は MockBroker を使用し、paper DB に記録します
  - `live` は本番（注意が必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行中プロセスの PID 保存先（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1、デフォルト: 0）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）

注意:
- .env ファイルはデフォルトでプロジェクトルートから自動読み込みされます（OS 環境変数が優先）。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate   （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がある場合は `pip install -r requirements.txt` を推奨
   - 手動で最低限必要なパッケージ:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（config の YAML 検証を行いたい場合）
   例:
   - pip install duckdb httpx websocket-client defusedxml pyyaml

4. .env を作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくはルートに .env を手動作成（.env は Git にコミットしないでください）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする（CI 等）場合:
     - python -m kabusys.validate_config --strict

6. データベース初期化（監視・注文テーブル等）
   - run_execution/run_monitoring 内で init_monitoring_db / init_orders_db を呼んでいます。必要に応じてスクリプトまたは REPL で初期化してください。
   - 例（簡易）:
     - python -c "import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; conn=sqlite3.connect('data/monitoring.db'); init_monitoring_db(conn); conn.close()"
     - 注文 DB 初期化: from kabusys.execution.order_repository import init_orders_db

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup
  - オプション: --env-file <path>

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）扱い

- 発注エンジン起動（本番/ペーパーいずれも）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paster_trading（もしくは development）で MockBroker を使用
  - 起動時に data/execution.pid に PID を書き、data/stop_requested.flag による停止に対応

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で監視間隔（秒）を上書き（デフォルト 60）
  - 停止フラグ: data/stop_requested.flag

- ログ・監視
  - LOG_LEVEL 環境変数でログレベルを制御
  - run_execution/run_monitoring は PID / stop フラグ / kill.flag を利用して安全な運用を支援

---

## .env のサンプル（テンプレート）

以下は config_setup により生成される .env の主要項目（例）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

（※ 実運用ではシークレットは平文で管理せず、適切な秘密管理を推奨）

---

## 運用に関する注意点

- KABUSYS_ENV=live を使用する際は本番ブローカーへの発注となるため、LINE 通知設定や kill フラグの取り扱いを入念に確認してください。validate_config は live 時に追加警告を出します。
- kill.flag（KILL_FLAG_PATH）と stop_requested.flag（data/stop_requested.flag）でプロセスの安全停止を行います。設定に応じて起動時の自動クリア（KILL_FLAG_CLEAR_ON_START）に注意してください。
- 発注フローはクラッシュ耐性を考慮して設計していますが、本番運用前に十分なテストを行ってください。
- .env は必ず Git 管理外にしてください（README 内の .env は秘密を含めないテンプレートのみで運用）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — 監視ループ起動スクリプト
  - execution/
    - broker_api.py          — Broker API の Protocol / モデル / 例外 / ファクトリ
    - kabu_client.py         — kabuステーション の REST/WebSocket クライアント
    - mock_client.py         — テスト用モッククライアント
    - broker_factory.py      — Settings に応じたクライアント生成
    - order_record.py        — 注文状態モデルと遷移ロジック
    - order_repository.py    — SQLite 永続化層
    - order_manager.py       — 発注フローの外向き API
    - execution_engine.py    — セッション実行ロジック（シグナル処理 / push ドレイン）
    - reconciler.py          — 起動時リコンシリエーション
    - risk_manager.py        — Gate1/2/3 リスクチェック
  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化 / 書き込み
    - system_monitor.py      — 監視ロジック（推定）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集
    - jquants_client.py      — J-Quants API ラッパ（別ファイル、データ取得用）
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ

（上記はリポジトリ内の主要モジュールを抜粋したものです）

---

## 参考・開発上のヒント

- テストや開発では KABUSYS_ENV=paper_trading または development を使用して MockBrokerClient を利用してください。
- validate_config は PyYAML 未インストール時に YAML 内容検証をスキップします。config/*.yaml の簡易チェックを有効にしたい場合は PyYAML をインストールしてください。
- ExecutionEngine は pid ファイルや kill.flag を用いてランタイムの整合性を保ちます。自動化されたデプロイや systemd / supervisor などでの運用を検討してください。
- DuckDB の接続は軽量で高速な分析に適しているため、シグナルやポートフォリオ集計に利用しています。

---

もし README に追加したい運用手順（例: systemd ユニット、Dockerfile、CI の設定サンプル）や、各モジュールのより詳細なドキュメント（API仕様やテーブル定義の説明）が必要であれば教えてください。必要に応じて追記します。