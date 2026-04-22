KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコア部分を実装したコードベースです。
主に以下を目的とします:

- シグナルに基づく発注（ExecutionEngine）
- 発注状態管理とリコンシリエーション（OrderManager / Reconciler）
- リスクガード（3段階: Gate1/Gate2/Gate3）
- 監視ループ（SystemMonitor）と監視データ保存
- データ系ユーティリティ（マーケットカレンダー、ニュース収集等）
- 環境設定ウィザードと起動前設定検証ツール

重要: 本リポジトリは実際の証券会社 API（kabuステーション等）と連携することを想定しています。
テスト・開発用に MockBrokerClient を備え、paper_trading / development モードで証券実装をエミュレートできます。

主な機能
--------
- 環境設定ウィザード（python -m kabusys.config_setup）
  - .env の作成／更新を対話式に支援
- 設定検証ツール（python -m kabusys.validate_config）
  - .env と config/*.yaml を起動前にチェック（--strict で警告も失敗扱い）
- 実行エンジン（python -m kabusys.run_execution）
  - シグナルを読み発注、WebSocket push ドレイン、PID / kill flag 管理
  - paper_trading（MockBrokerClient）と本番の分離（paper_trading 用 DB）
- 監視ループ（python -m kabusys.run_monitoring）
  - SystemMonitor を定期ポーリングして監視データを収集
- 発注層
  - BrokerAPIProtocol（抽象）、KabuStationClient（kabu station 用実装）、MockBrokerClient
  - OrderRequest/OrderResponse/OrderStatus/Position 等のデータモデル
- 注文永続化（SQLite）と状態遷移ロジック（OrderRecord / OrderRepository）
- リスク管理（RiskManager：Gate1/2/3）と Reconciler（クラッシュ復旧）
- データユーティリティ
  - マーケットカレンダー管理（DuckDB 利用）
  - ニュース収集（RSS 収集、正規化、SSRF対策等）

動作要件（推奨）
---------------
- Python >= 3.10（型注釈で | 演算子や list[str] を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（任意：config YAML のパース検証に使用）
  - そのほか標準ライブラリ（sqlite3, threading, logging 等）
- ディスク上に data/ ディレクトリを作成しておくと便利（DB・PID/flag ファイル格納先）

セットアップ手順
----------------
1. リポジトリをクローンしてソースルートに移動
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml PyYAML
   - （実際のプロジェクトでは requirements.txt を用意して pip install -r requirements.txt）
4. data ディレクトリを作成
   - mkdir -p data
5. .env を用意
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - もしくは手動で .env を作成（下記「環境変数一覧」を参照）
6. 設定検証
   - python -m kabusys.validate_config
   - 重要な問題がなければ OK と表示される（--strict オプションで警告も失敗にできます）

環境変数一覧（重要）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意／推奨（.env で設定可能）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 SQLite, デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABU_API_BASE_URL (kabu station のベース URL)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番アラート用）
- KILL_FLAG_CLEAR_ON_START（0/1。本番では 0 推奨）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒））
- PID_FILE_PATH, KILL_FLAG_PATH（ファイルパスを上書き可能）

使い方（主要コマンド）
---------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup
  - 対話式に .env を作成 / 更新します。

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  （警告を FAIL 扱い）

- 実行エンジン起動（本番相当の処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading で起動すると MockBrokerClient を使用し paper_trading DB を利用します。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。

- 開発・テスト
  - ExecutionEngine / OrderManager / MockBrokerClient 等は非ネットワーク環境でもテスト可能です。
  - paper_trading / development では create_broker_api(mock=True) により MockBrokerClient が使用されます。

動作上の注意点
--------------
- paper_trading モードでは本番 DB と分離して paper_trading 用 SQLite を使用します（安全）。
- 実際の kabu station を使う場合は KABU_API_PASSWORD 等の機密情報管理に注意してください。
- .env は絶対に Git にコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。
- 起動時に data/kill.flag が存在すると起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合はクリアして起動する挙動あり）。
- validate_config は PyYAML 未インストール時に YAML の内容チェックをスキップします（警告）。

ディレクトリ構成（主なファイル）
------------------------------
以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み・Settings クラス（.env 自動読み込みロジック含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（発注フロー）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py — execution 層の公開 API
    - broker_api.py — Broker API の Protocol、データモデル、例外、ファクトリ
    - kabu_client.py — kabu station 実装（HTTP + WebSocket）
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — Settings に従いクライアントを生成
    - execution_engine.py — ExecutionEngine（シグナル読み込み／発注／push ドレイン）
    - order_record.py — OrderRecord（状態遷移ロジック）
    - order_repository.py — SQLite 永続化レイヤ（orders テーブル）
    - order_manager.py — Order の外向き API（create/send/sync/cancel）
    - reconciler.py — 起動時の復旧・リコンシリエーション
    - risk_manager.py — Gate1/2/3 によるリスク制御
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集（正規化・SSRF対策等）
    - （jquants_client などの補助モジュールが想定される）
  - monitoring/
    - monitoring_db.py — 監視 DB 初期化・ログ関数（参照されるがここに未列挙の実装が存在）
    - system_monitor.py — 監視ロジック（SystemMonitor）
  - utils/
    - logging_setup.py — ロギング初期化（参照）
    - process_priority.py — プロセス優先度設定（参照）

（注）一部ファイルは README に完全列挙していませんが、上記が主要構成です。実際のツリーはリポジトリを参照してください。

開発時のヒント
---------------
- ローカル開発では KABUSYS_ENV=development または paper_trading を使って MockBrokerClient を使うことを推奨します。
- DB スキーマ（orders テーブル等）は init_orders_db / init_monitoring_db で自動初期化されます。run_execution/run_monitoring により起動時に作成されます。
- リコンシリエーション（Reconciler）は起動時に OrderSent 状態の注文をブローカーと照合して自動回復を試みます。
- テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化できます。

ライセンス・連絡
----------------
- 本 README はコードからの情報に基づく概要ドキュメントです。商用利用・本番接続を行う際は十分なレビューと安全対策（資金管理、ログ監査、アラート設定等）を行ってください。
- 実装依存の追加情報（例: jquants_client のトークン取得方法や Monitoring 実装の詳細）はリポジトリ内の該当ドキュメントや実装コメントを参照してください。

以上。使い始めにまずは:
- python -m kabusys.config_setup
- python -m kabusys.validate_config
を実行して設定を整えてください。