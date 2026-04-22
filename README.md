KabuSys
=======

日本株向けの自動売買システム（軽量プロトタイプ）。  
このリポジトリは発注ロジック、ブローカークライアントの抽象、リスクガード、監視・リコンシリエーション、ニュース収集・マーケットカレンダー管理などを含みます。  
（本 README はソースコードの説明と最小限のセットアップ手順をまとめたものです）

概要
----
KabuSys は以下を目的としたモジュール群です。

- シグナルに基づく発注エンジン（ExecutionEngine）
- kabuステーション（またはモック）とのやり取りを抽象化した Broker API
- 発注の状態管理（OrderRecord / OrderRepository / OrderManager）
- リスクガード（3段階: Gate1/Gate2/Gate3）
- 起動時リコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor を定期実行する run_monitoring）
- .env 対話式ウィザードと設定検証ツール

主な機能
--------
- 環境変数/.env ベースの設定管理（自動読み込み、.env/.env.local）
- .env ファイルを対話式に生成・更新する CLI（kabusys.config_setup）
- 起動前に環境設定と config/*.yaml を検証する CLI（kabusys.validate_config）
- Signal Queue からの発注処理（ExecutionEngine）
- ブローカークライアントの抽象化（Mock / KabuStationClient 経由）
- 注文状態の永続化（SQLite）とリコンシリエーション
- DuckDB を使ったデータ分析（シグナル取得・position_entries 操作など）
- RSS ニュース収集（defusedxml を使用した安全なパーサ）
- マーケットカレンダー管理（J-Quants ベースの更新ロジック）
- 監視プロセス（run_monitoring）による定期チェック

要件（推奨）
-------------
- Python 3.10+
- 必要な外部パッケージ（実行する機能により異なる）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（validate_config の YAML パースを有効にする場合）
- 標準ライブラリ: sqlite3, logging, threading, datetime など

例（最低限のインストール）
- 仮想環境作成（推奨）
  - python -m venv .venv
  - source .venv/bin/activate
- 必要パッケージのインストール（機能に応じて選択）
  - pip install duckdb httpx websocket-client defusedxml pyyaml

セットアップ手順
----------------
1. リポジトリをクローンしてソースを配置
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境を作成し依存パッケージを入れる（上記参照）

3. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成・更新します（.env は絶対に Git にコミットしないでください）

4. 設定検証
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict
   - validate_config は .env と config/*.yaml の存在・基本整合性をチェックします（PyYAML があると YAML のパース検証も行います）

5. データディレクトリの準備
   - デフォルトの DB 等は data/ 以下に配置されます（DUCKDB_PATH / SQLITE_PATH の親ディレクトリがなければ起動時に作成される場合があります）
   - 必要に応じて data/ ディレクトリを作成:
     - mkdir -p data

使い方（主要 CLI / スクリプト）
------------------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup
  - 既存 .env を読み込み、対話形式で編集できます

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit(1) になります

- 実行エンジン起動（発注）
  - python -m kabusys.run_execution
  - KABUSYS_ENV に応じて挙動が変わります:
    - development / paper_trading → MockBrokerClient を使用（paper_trading は paper_trading 用 SQLite に記録）
    - live → 本番ブローカークライアント（未実装の箇所があります。設定に注意）
  - 停止制御:
    - data/stop_requested.flag を作成すると実行中ループは停止します
    - data/execution.pid に PID が書かれます（起動時に PID ファイルが作成され、正常終了時に削除されます）
    - kill.flag（settings.kill_flag_path）を利用した kill-switch が存在します

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は KABUSYS_ENV に関係なく production sqlite_path を使用します
  - 停止は data/stop_requested.flag を作成します

主要な環境変数
----------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意（またはデフォルトあり）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station API の base URL
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（本番環境では設定推奨）
- LINE_USER_ID — LINE 通知先ユーザー ID（本番環境では設定推奨）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

例 .env（テンプレート）
----------------------
# 例（実際の値は秘密にしてください）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
KILL_FLAG_CLEAR_ON_START=0

実行フローの概要（発注）
-----------------------
- ExecutionEngine はセッション（通常 08:50 → 15:30）を想定して動作します
- 8:50 にシグナル処理（_process_signals）を行い、9:10 以降は WebSocket push のドレイン処理
- 発注フローは OrderManager を介して OrderRecord と OrderRepository（SQLite）に永続化され、ブローカー API 呼び出しは 2 段階永続化（OrderSent の永続化 → send_order → broker_order_id 永続化 → OrderAccepted 永続化）でクラッシュ耐性を担保
- リスク管理は RiskManager が Gate1（シグナルレベル）/ Gate2（実行レベル）/ Gate3（約定後メトリクス）を担当
- 起動時に Reconciler によるリコンシリエーションが実行され、OrderSent 状態の注文をブローカーと突合します

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数読み込み・Settings
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor 起動スクリプト
- execution/
  - __init__.py
  - broker_api.py            — Broker API Protocol, データモデル, ファクトリ
  - broker_factory.py        — Settings に基づくクライアント生成
  - kabu_client.py           — kabu station REST クライアント
  - mock_client.py           — テスト用 MockBrokerClient
  - execution_engine.py      — ExecutionEngine（メインロジック）
  - order_record.py          — Order 状態機械のデータモデル
  - order_repository.py      — SQLite 永続化層
  - order_manager.py         — 外向きの注文 API（発注 / 同期 / キャンセル）
  - reconciler.py            — 起動時リコンシリエーション
  - risk_manager.py          — 3 段階リスクガード
- data/
  - calendar_management.py   — マーケットカレンダー管理（DuckDB）
  - news_collector.py        — RSS ニュース収集
  - (jquants_client.py 等が存在すると想定)
- monitoring/
  - monitoring_db.py         — 監視 DB 初期化・操作（参照される）
  - system_monitor.py        — SystemMonitor（参照される）
- utils/
  - logging_setup.py         — ロギング初期化（参照される）
  - process_priority.py      — プロセス優先度設定（参照される）

注意事項 / トラブルシューティング
---------------------------------
- .env は秘密情報を含むため絶対にコミットしないでください
- validate_config は PyYAML がインストールされていない場合、YAML 内容検証をスキップして警告します。PyYAML を入れると config/*.yaml の構文チェックが行えます
- Settings の必須プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）にアクセスすると未設定の場合 ValueError が発生します。起動前に validate_config を実行して確認してください
- KABUSYS_ENV=live を使用する場合は本番リスクに注意。validate_config は live の場合に追加の警告を出します（LINE 通知設定、KILL_FLAG_CLEAR_ON_START など）
- run_execution / run_monitoring は直接バックグラウンドで運用することができますが、プロダクション運用では systemd / supervisor 等でプロセス管理することを推奨します

貢献・拡張案
-------------
- Live ブローカークライアントの整備（現在は Mock が中心）
- 監視・アラートの強化（LINE 以外のチャネル追加）
- テストカバレッジの拡充（ユニット/統合テスト）
- Docker 化・コンテナ運用のサポート

以上。必要があれば README に追記すべき点（例: 実際の requirements.txt、起動用 systemd サンプル、DB スキーマ説明など）を指定してください。