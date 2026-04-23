README
======

プロジェクト概要
----------------
KabuSys は日本株自動売買システムのコアライブラリです。本リポジトリは発注エンジン（ExecutionEngine）、発注・状態管理（OrderManager / OrderRepository / OrderRecord）、ブローカー API 抽象（BrokerAPIProtocol と実装）、リスクガード（RiskManager）、起動時のリコンシリエーション（Reconciler）、監視プロセス（SystemMonitor 起動スクリプト）など、実運用を想定したコンポーネント群を提供します。ローカル開発／ペーパートレード（MockBrokerClient）／将来的な本番（kabuステーション）対応を念頭に設計されています。

主な特徴（機能一覧）
------------------
- 環境変数・設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - Settings クラスによる型付けされた設定アクセス
- 設定ウィザード & 検証
  - 対話式 .env 作成/更新スクリプト（kabusys.config_setup）
  - 起動前に環境変数・config/*.yaml を検証する CLI（kabusys.validate_config）
- 発注エンジン
  - Signal Queue Pull 型 ExecutionEngine（シグナル処理・WebSocket push ドレイン）
  - OrderManager / OrderRecord による注文状態マネジメント（状態遷移と検証）
  - OrderRepository（SQLite）による永続化（orders テーブル、インデックス、ユニーク制約）
- ブローカークライアント
  - BrokerAPIProtocol 抽象
  - MockBrokerClient：テスト・開発用の充実したモック（fill_mode 等の挙動制御）
  - KabuStationClient：kabuステーション対話用の同期 HTTP 実装（httpx, websocket）
- リスク管理
  - 3段階リスクガード（Gate1: シグナル、Gate2: 実行/レート制限/CB、Gate3: ドローダウン監視）
  - サーキットブレーカー / トークンバケツ（レート制限）
- 起動時リコンシリエーション
  - OrderSent 状態の注文を照合して状態回復
  - ブローカーポジションとローカル推定ポジションの差分検出
- データ系ユーティリティ
  - マーケットカレンダー管理（DuckDB 利用）
  - RSS ニュース収集（セキュアなパース・正規化ロジック）

セットアップ手順
----------------
1. リポジトリをクローンし、プロジェクトルートへ移動します。
   - ソースは src/kabusys 以下に配置されています（パッケージ形式）。

2. Python 環境（推奨: 3.9+）を用意します。仮想環境を作ることを推奨します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストールします（requirements.txt がある想定）。最低限必要となる主要パッケージ:
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（config ファイル検証を有効にする場合）
   例:
   - pip install duckdb httpx websocket-client defusedxml PyYAML

4. .env の作成
   - 対話式ウィザードで作成するのが簡単です:
     - python -m kabusys.config_setup
   - ウィザードで入力した内容はデフォルトでプロジェクトルートの .env に保存されます。
   - 自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト目的など）。

5. データディレクトリの作成（必要に応じて）
   - デフォルトでは data/ 以下に DB ファイルが作成されます。存在しなければプロセス起動時に自動作成されることがありますが、事前に作る場合:
     - mkdir -p data

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う任意／推奨環境変数
- KABUSYS_ENV            : development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH            : デフォルト data/kabusys.duckdb
- SQLITE_PATH            : デフォルト data/monitoring.db
- LOG_LEVEL              : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL      : kabuステーション API ベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 本番でのアラート用（任意）
- PAPER_FILL_MODE        : paper_trading 時のモック挙動（instant|partial|never|reject）

サンプル .env（config_setup が生成する形式）
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

使い方（主要コマンド）
--------------------
- 環境設定ウィザード（.env の作成／更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いで exit(1)（CI 等で有用）
    - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 動作モード:
    - KABUSYS_ENV=paper_trading または development: MockBrokerClient が使われます（実際の発注は行われません）
    - paper_trading の場合、専用の SQLite (data/paper_trading.db) が使用されます
  - 停止フラグ:
    - プロジェクトルート data/stop_requested.flag を作成すると実行ループを停止します
  - PID ファイル:
    - data/execution.pid に PID を書き込みます（設定により変更可能）

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60 秒）

- テスト用 MockBrokerClient を使った操作
  - BrokerClientFactory が環境に応じてモックを返します（paper_trading / development）
  - モックの挙動は PAPER_FILL_MODE によって制御できます（instant / partial / never / reject）

運用・注意点
-------------
- 本番モード（KABUSYS_ENV=live）では設定内容を慎重に確認してください。validate_config は live 設定時に追加チェックや警告を出します。
- .env は絶対にバージョン管理にコミットしないでください（config_setup でも同様に注意喚起があります）。
- ExecutionEngine は PID ファイルと kill.flag を使って起動制御します。残った kill.flag を自動でクリアしない設定 (KILL_FLAG_CLEAR_ON_START=0) によって誤起動を防げます。
- config/*.yaml の内容検証は PyYAML に依存します。PyYAML 未インストール時はパース検証をスキップします（validate_config 参照）。

ディレクトリ構成
----------------
プロジェクトの主要な構成（src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 設定読み込み / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - execution/
    - __init__.py
    - broker_api.py          — BrokerAPIProtocol / データモデル / ファクトリ
    - broker_factory.py      — 設定に応じたブローカークライアント生成
    - kabu_client.py         — kabuステーション API 実装（httpx / websocket）
    - mock_client.py         — MockBrokerClient（テスト用）
    - order_record.py        — OrderRecord（状態遷移ロジック）
    - order_repository.py    — SQLite 永続化レイヤ
    - order_manager.py       — OrderManager（外向き API）
    - execution_engine.py    — ExecutionEngine（シグナル処理・push ドレイン）
    - reconciler.py          — 起動時リコンシリエーション
    - risk_manager.py        — RiskManager（3段階ガード）
    - ...                    — ほか依存モジュール
  - data/
    - calendar_management.py — マーケットカレンダー（DuckDB）ユーティリティ
    - news_collector.py      — RSS ニュース収集
    - ... 
  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化 / ログ保存（実装は別ファイル）
    - system_monitor.py      — 監視ロジック（実装は別ファイル）
  - utils/
    - logging_setup.py       — ロギングセットアップ（利用箇所あり）
    - process_priority.py    — プロセス優先度設定（利用箇所あり）
  - config/                  — YAML 設定ファイル置き場（system_config.yaml 等）

開発／拡張のヒント
------------------
- 本番（kabuステーション）クライアントは KabuStationClient で実装されていますが、BrokerClientFactory は live 用実装を未実装（NotImplementedError）にしている箇所があります。必要に応じて create_broker_api で kabu_client を有効にしてください。
- ExecutionEngine の run_session は時間帯（8:50〜9:10、9:10〜15:30）に基づく振る舞いをします。テスト時は内部メソッド（_process_signals / _drain_push_queue）を直接呼ぶと制御しやすくなります。
- OrderRepository のスキーマ定義は init_orders_db() で実施されるため、初期化時にこの関数を呼ぶことを忘れないでください（run_execution 内では init_monitoring_db と併せて利用）。

ライセンス・連絡先
-----------------
（本 README はコードベースから自動生成したドキュメントです。ライセンスや連絡先情報はリポジトリのルートにある別ファイルを参照してください。）

以上。質問や追加で README に入れたい内容があれば教えてください。