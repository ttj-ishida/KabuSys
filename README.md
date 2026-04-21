# KabuSys

日本株向けの自動売買システム（簡易リファレンス / README）

このリポジトリは「KabuSys」と呼ばれる日本株自動売買システムのコードベースです。
この README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、
およびディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys はローカル環境やペーパートレード環境で安全に動作する自動売買フレームワークです。
設計のポイントは次の通りです。

- 発注フローのクラッシュ安全性（OrderCreated → OrderSent の2相永続化など）
- 起動時のリコンシリエーション（OrderSent 状態の注文をブローカーと突合）
- 3段階のリスクガード（Gate1: シグナルレベル、Gate2: レート制限/サーキットブレーカー、Gate3: ドローダウン監視）
- テスト/開発用の MockBrokerClient を備え、kabuステーションを用いずに動作確認可能
- 環境設定は .env / config/*.yaml ベースで管理。ウィザードと検証 CLI を提供

---

## 主な機能一覧

- 環境設定ウィザード（対話式 .env 生成）: `kabusys.config_setup`
- 設定検証ツール（.env と config/*.yaml を起動前にチェック）: `kabusys.validate_config`
- 発注エンジン (ExecutionEngine) によるシグナル駆動発注
- ブローカークライアント抽象化（実装: MockBrokerClient、将来的に KabuStationClient）
- 注文状態管理（OrderRecord の状態遷移検証）
- 注文永続化（SQLite）
- 起動時の Reconciler による注文・ポジション突合
- 監視ループ（SystemMonitor） — 監視データは SQLite / DuckDB に保存
- データ側: マーケットカレンダー管理、RSS ニュース収集などのユーティリティ

---

## システム要件

- Python 3.10 以上（PEP 604 記法などを使用しているため）
- 推奨パッケージ（最低限、実行に必要なもの）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml（config YAML の検証を行いたい場合）
  - defusedxml（news_collector の XML パース用）
- 標準ライブラリ: sqlite3, threading, logging, pathlib など

（プロジェクトに requirements.txt は付属していない想定のため、環境に応じて pip インストールしてください。）

例:
pip install duckdb httpx websocket-client pyyaml defusedxml

---

## セットアップ手順

1. リポジトリをクローン / コピー
   - 例: git clone <repo-url>

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb httpx websocket-client pyyaml defusedxml

4. .env を作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
     - ウィザードが .env を生成します（デフォルトはプロジェクトルートの `.env`）
   - 手動で作成する場合は、最低限以下の必須環境変数を設定してください:
     - JQUANTS_REFRESH_TOKEN=<your_token>
     - KABU_API_PASSWORD=<your_kabu_password>
   - その他の推奨環境変数:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

注意: .env は絶対に Git にコミットしないでください（ウィザードも同様に警告文を出力します）。

5. 設定検証（必須ではないが起動前に推奨）
   - python -m kabusys.validate_config
   - 警告もエラーとして扱う厳密モード:
     - python -m kabusys.validate_config --strict
   - Exit code: 0 = OK、1 = FAIL（errors があるか --strict で warnings がある場合）

---

## 使い方（実行例）

- 設定ウィザード（.env の作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン（Execution）を起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV に応じて MockBrokerClient を使用（paper_trading / development）
    - paper_trading の場合、設定により paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に保存
    - 停止フラグファイルが存在すると起動を拒否（KILL_FLAG_CLEAR_ON_START が 1 の場合は自動クリアされる）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）

- 停止方法
  - プロセスを停止する、またはプロジェクトルートの data/stop_requested.flag を作成すると run_* スクリプトが停止処理を行います。
  - ExecutionEngine は停止時に全 active 注文をキャンセルする kill_switch を実行します。

---

## 主要環境変数（一覧）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

任意 / 推奨:
- KABUSYS_ENV — execution 環境 (development | paper_trading | live)。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 用）
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station の Base URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知設定
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0|1、デフォルト 0）
- PAPER_FILL_MODE — paper_trading 時のモック約定動作（instant|partial|never|reject）

設定自動読み込み:
- デフォルトでプロジェクトルートの `.env` と `.env.local` を自動読み込みします。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に有用）。

---

## .env の最小例

（ウィザードで生成されますが、手動編集時の参考）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

※ セキュアな値（トークン / パスワード）は漏洩しないよう取り扱ってください。

---

## 実行時のファイル / フラグ

- data/execution.pid（ExecutionEngine が PID を書き込む）
- data/stop_requested.flag（作成すると監視・実行ループが停止）
- data/kill.flag（存在する場合、ExecutionEngine は起動を拒否 or 自動クリア動作に従う）
- DUCKDB / SQLite ファイルは parent ディレクトリが存在しない場合に警告が出力されることがあります（多くのケースで起動時に自動作成されますが、パーミッション等に注意してください）。

---

## 開発者向けメモ

- ブローカークライアント:
  - MockBrokerClient: テスト・開発用。PAPER_FILL_MODE に応じた動作を模倣します。
  - KabuStationClient: 実運用での kabu station REST API 実装（HTTP + WebSocket push）。
  - create_broker_api(mock=True/False) で切り替え。
- 注文の永続化は SQLite（orders テーブル）に行われます。init_orders_db(conn) でテーブルを作成します。
- Reconciler は起動時に OrderSent 状態の注文を broker 状態と突合して復旧を試みます。
- news_collector, calendar_management などの data 層は DuckDB を利用する想定です。
- config/*.yaml の存在とパース検証は validate_config で確認します。PyYAML がインストールされていない場合は YAML 内容の検証はスキップされます。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョンなど）
  - config.py — 環境変数 / .env の読み込みと Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（エントリポイント）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - execution/
    - broker_api.py — Broker API 用のデータモデル、Protocol、ファクトリ、例外
    - kabu_client.py — kabuステーション REST/WebSocket クライアント（HTTPX / websocket）
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — Settings に基づいて適切なブローカークライアントを生成
    - order_record.py — Order の状態モデルと遷移ロジック（純粋ビジネスロジック）
    - order_repository.py — SQLite を用いた永続化層
    - order_manager.py — 外向けの注文 API（作成・送信・同期・キャンセル）
    - execution_engine.py — 発注エンジン（シグナル処理 + WebSocket ドレイン）
    - reconciler.py — 起動時のリコンシリエーション（注文/ポジション突合）
    - risk_manager.py — 3 段階リスクガードの実装
  - monitoring/
    - monitoring_db.py — 監視用 DB 初期化 / 書き込み（参照のみ。実装ファイルがある想定）
    - system_monitor.py — システム監視ロジック（参照のみ）
  - data/
    - calendar_management.py — JPX カレンダー管理 / 営業日判定
    - news_collector.py — RSS ニュースの収集と前処理
  - utils/
    - logging_setup.py — ロギング設定ユーティリティ（参照）
    - process_priority.py — プロセス優先度設定ユーティリティ（参照）

（上記に挙げたファイルは本リポジトリの主要コンポーネントと役割を簡潔にまとめたものです。）

---

## 注意点 / 運用上のヒント

- KABUSYS_ENV=live を使用する場合は本番向けの慎重な確認が必要です。validate_config では live の場合に追加警告を出します（LINE 通知設定未設定など）。
- 本番運用では KILL_FLAG_CLEAR_ON_START を 0（無効）にすることを推奨します。誤ってクリアされて起動すると既存の kill.flag を無視してしまいます。
- .env は決してリポジトリにコミットしないこと（認証情報や秘密値を含みます）。
- DuckDB / SQLite のファイルは運用環境のバックアップ方針に従って管理してください。
- テストでは MockBrokerClient を使用してブローカー依存のテストを行うと高速に検証できます。

---

必要であれば、README に含めるサンプル .env.example、requirements.txt、起動時の systemd ユニットや docker-compose の例なども追加で作成できます。どの情報を優先して追記したいか教えてください。