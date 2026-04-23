# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル駆動の発注エンジン、監視プロセス、環境設定ツールなどを含む自動売買フレームワークの一部を実装しています。実運用では kabuステーション等のブローカー API と連携しますが、開発・テスト用にモックブローカーも用意されています。

## プロジェクト概要
- シグナルを元に発注を行う ExecutionEngine（発注フロー、リスク管理、リコンシリエーション含む）
- 起動前に .env と config/*.yaml の設定を検証する CLI（validate_config）
- .env を対話式に生成・更新するウィザード（config_setup）
- システム監視用のポーリングループ（run_monitoring）
- 設定管理（Settings クラス）と自動 .env 読み込み
- DuckDB / SQLite によるデータ永続化、J-Quants / RSS 等のデータ収集補助（Dataモジュール）

## 主な機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）で .env を生成・更新
- 起動前設定検証（python -m kabusys.validate_config）
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、YAML のパース確認（PyYAML があれば実施）
  - --strict オプションで警告も失敗扱いにできる
- ExecutionEngine
  - シグナルを DuckDB から読み発注（Gate1〜3 のリスクチェック）
  - Order 管理（OrderRecord / OrderRepository / OrderManager）
  - ブローカー抽象化（BrokerAPIProtocol）と MockBrokerClient（paper_trading / development 用）
  - リコンシリエーション（再起動時の OrderSent 照合・ポジション差分検出）
  - WebSocket push ドレイン（kabu station push 受信）
- 監視プロセス（SystemMonitor）をポーリングで実行（run_monitoring）
- カレンダ管理（market_calendar をベースに営業日判定、next/prev_trading_day 等）
- ニュース収集（RSS パース・前処理・DB保存、SSRF 対策・XML パース防御など）

## 必要な環境 / 依存パッケージ（例）
以下はソースコード中で使われている主なパッケージです。実際の requirements.txt を用意している場合はそちらを使用してください。

- python 3.9+
- duckdb
- httpx
- websocket-client
- PyYAML（YAML 検証を行う場合）
- defusedxml
- （標準ライブラリ）sqlite3, logging, datetime, pathlib, os, json, threading など

インストール例:
pip install duckdb httpx websocket-client pyyaml defusedxml

## セットアップ手順
1. リポジトリを取得して、Python 仮想環境を作成・有効化する
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールする
   - pip install -r requirements.txt
   または
   - pip install duckdb httpx websocket-client pyyaml defusedxml

3. 環境変数ファイル (.env) を作成する
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
     - 実行後 .env が生成されます（デフォルト: プロジェクトルート/.env）
   - 既に .env を用意済みならこのステップは不要

4. 設定の検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告を失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの確認
   - デフォルト DB パス: data/kabusys.duckdb, data/monitoring.db
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH を変更

## 主要な環境変数
（.env に設定する項目の例）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABU_API_BASE_URL — kabu station のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知設定
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1)
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

自動ロード:
- ライブラリはプロジェクトルートの .env（および .env.local）を自動で読み込みます。
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## 使い方（実行例）
- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（Execution）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、paper_trading 用 DB（data/paper_trading.db）に記録します。
  - run_execution は停止フラグ(data/stop_requested.flag, または kill.flag 等) を監視し、PID ファイル (data/execution.pid 等) を扱います。

- 監視プロセス:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を参照します（設定に依らず）

- プログラム内からの設定参照（例）:
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token

## 注意点 / 運用上のポイント
- KABUSYS_ENV:
  - development: ローカル開発（発注を行わない / mock）
  - paper_trading: ペーパートレード（mock broker を使用、発注は本番 DB と分離）
  - live: 本番（本来は本番ブローカークライアントを使用）
- 本番環境 (live) の場合は LINE 通知等を適切に設定してください（validate_config による警告あり）。
- kill.flag / stop_requested.flag を使った安全停止機能があります。KILL_FLAG_CLEAR_ON_START は本番で慎重に扱ってください（デフォルト 0 推奨）。
- DB スキーマ初期化（orders テーブルや monitoring テーブル）は実行時に初期化関数が呼ばれます（init_orders_db / init_monitoring_db 等）。
- YAML の検証は PyYAML がインストールされている場合のみ実行されます。インストールしておくと設定ファイルの不整合を起動前に検出できます。

## ディレクトリ構成（主要ファイル）
（プロジェクトルート: src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py                     — Settings クラスと .env 自動読み込み
  - config_setup.py               — 対話式 .env 作成ウィザード
  - validate_config.py            — 起動前設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py               — BrokerAPIProtocol, データモデルとファクトリ
    - kabu_client.py              — kabu station REST クライアント（実装）
    - mock_client.py              — テスト用 MockBrokerClient
    - broker_factory.py           — Settings に基づくクライアント生成
    - execution_engine.py         — ExecutionEngine（シグナル処理・ドレインループ）
    - order_record.py             — Order の状態遷移ロジック（純粋ロジック）
    - order_repository.py         — SQLite 永続化層（orders テーブル）
    - order_manager.py            — 外向き Order API（create/send/sync/cancel）
    - reconciler.py               — 起動時リコンシリエーション処理
    - risk_manager.py             — Gate1/2/3 リスクガード
    - ...（その他）
  - data/
    - calendar_management.py      — マーケットカレンダー管理（営業日判定等）
    - news_collector.py           — RSS ニュース収集・前処理
    - ...（jquants_client 等）
  - monitoring/
    - monitoring_db.py            — 監視用 DB 初期化・ログ関数（参照実装）
    - system_monitor.py           — 監視ロジック（referenced by run_monitoring）
  - utils/
    - logging_setup.py            — ロギング設定（参照される）
    - process_priority.py         — プロセス優先度設定ユーティリティ
  - config/                       — YAML 設定ファイル群（例: system_config.yaml 等）
  - .env.example                  — サンプル .env（存在する場合）

（実際のリポジトリに存在するファイルに合わせて調整してください）

## 開発メモ / 拡張
- Live broker client（本番向け kabu client）の実装が未完の場合があります（BrokerClientFactory は NotImplementedError を投げることがあります）。本番接続を有効にする際は kabu_client の実装と検査を行ってください。
- テスト時は MockBrokerClient を活用すると、発注・約定・キャンセルのフローを外部依存なく検証できます。
- DuckDB を用いた分析向けクエリやカレンダー更新ジョブは data モジュールで提供されています。J-Quants の API クライアント実装（jquants_client）は別途実装・設定が必要です。

---

まずは:
1. 仮想環境を準備
2. 依存をインストール
3. python -m kabusys.config_setup で .env を作成
4. python -m kabusys.validate_config で検証
5. python -m kabusys.run_execution / python -m kabusys.run_monitoring を実行

不明点や追加で README に載せたい情報（サンプル .env、requirements.txt、デプロイ方法など）があれば教えてください。