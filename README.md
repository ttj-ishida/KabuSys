README
=====

概要
----
KabuSys は日本株向けの自動売買システムの基盤コード群です。  
主に以下を含みます:

- 環境変数／設定ファイルの対話的作成・検証ツール
- 発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- ブローカークライアント（実装: Mock / kabuステーション用）
- リスクガード（3段階: Gate1/2/3）、リコンシリエーション（再起動復旧）
- 監視プロセス（SystemMonitor 用ポーリングループ）
- データ側ユーティリティ（マーケットカレンダー管理、ニュース収集 など）

このリポジトリはライブラリ／実行スクリプトの集合体で、主に環境変数とデータベース（DuckDB/SQLite）を使って動作します。

主な機能
--------
- .env 対話式ウィザード（kabusys.config_setup）
- 起動前設定検証 CLI（kabusys.validate_config）
  - 必須環境変数チェック、config/*.yaml の検証（PyYAML があれば厳密検証）
  - --strict で警告も失敗扱いにできる
- ExecutionEngine
  - シグナル読み込み → Gate1/2（発注前チェック） → 発注 → Push ドレイン（同期）
  - kill.flag による安全停止、PID 管理、Reconciler によるクラッシュ復旧
- Broker クライアントファクトリ（MockBrokerClient を用いた paper_trading や開発用）
- Order の状態遷移を表現する OrderRecord（状態遷移の厳格検証）
- RiskManager によるレート制限・サーキットブレーカー・ドローダウン監視
- データユーティリティ（マーケットカレンダー、ニュース収集）

前提条件
--------
- Python 3.10 以上（型表記（X | None）や新しい型表現を使用）
- SQLite（標準ライブラリ sqlite3 を使用）
- 推奨パッケージ（少なくとも以下のいずれかが必要）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml の内容検証を行う場合に必要）

例: 必要なパッケージをインストールする
- 仮想環境作成（推奨）
  python -m venv .venv
  source .venv/bin/activate  # Windows: .venv\Scripts\activate

- pip でインストール（最低限）
  pip install duckdb httpx websocket-client defusedxml

- 追加（YAML 検証）
  pip install PyYAML

セットアップ手順
--------------
1. リポジトリをクローンして作業ディレクトリへ移動します。
2. 仮想環境を作り、依存パッケージをインストールします（上記参照）。
3. .env を作成します（対話式ウィザード推奨）:

  python -m kabusys.config_setup

  ウィザードは既存の .env を読み込んで更新可能です。作成後、.env を絶対に Git にコミットしないでください。

4. 設定検証（起動前確認）:

  python -m kabusys.validate_config
  # 警告を FAIL 扱いにする場合:
  python -m kabusys.validate_config --strict

  必須の環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

  代表的なオプション環境変数:
  - KABUSYS_ENV: development | paper_trading | live
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite DB（paper_trading 実行時）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）
  - KILL_FLAG_CLEAR_ON_START （0/1、本番は 0 推奨）

使い方（実行方法）
-----------------

- 環境設定ウィザード（.env 作成・更新）:

  python -m kabusys.config_setup
  # 生成された .env を編集して必要な値を入れてください。

- 設定検証（起動前チェック）:

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor のポーリング）:

  python -m kabusys.run_monitoring

  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  監視は KABUSYS_ENV に依らず本番用 sqlite_path を使用します。

- 発注エンジン起動（ExecutionEngine）:

  python -m kabusys.run_execution

  KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。live は未実装で起動時に例外が出ます（BrokerFactory で NotImplementedError）。

運用上の注意
-------------
- kill.flag（デフォルト: data/kill.flag）を使って安全に停止できます。ExecutionEngine は起動時に kill.flag があると起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動）。
- PID ファイル（デフォルト: data/execution.pid）を使用して多重起動を防止します。
- 監視 DB（SQLite）と分析 DB（DuckDB）のパスは環境変数で指定できます。親ディレクトリが存在しない場合、起動時に自動作成される箇所と自動作成されない箇所があります（必要に応じてディレクトリを手動作成してください）。
- 本番（KABUSYS_ENV=live）では LINE 通知設定や Kill Switch の取り扱いを慎重に設定してください。validate_config は live の場合に追加警告を出します。

ディレクトリ構成
----------------
主要なソースは src/kabusys 以下にあります。主なモジュールと簡単な説明:

- src/kabusys/
  - __init__.py               — パッケージ定義、バージョン
  - config.py                 — 環境変数の自動読み込みと Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - execution/
    - broker_api.py           — Broker API の Protocol / データモデル / ファクトリ
    - broker_factory.py       — Settings に基づき Broker クライアントを生成
    - kabu_client.py          — kabuステーション REST/WebSocket クライアント
    - mock_client.py          — MockBrokerClient（テスト用）
    - execution_engine.py     — ExecutionEngine（シグナル処理・push ハンドリング）
    - order_record.py         — Order の状態・遷移モデル（純ビジネスロジック）
    - order_repository.py     — SQLite を使った永続化レイヤ
    - order_manager.py        — 発注フローの外向き API（create/send/sync/cancel）
    - reconciler.py           — 再起動時のリコンシリエーション（OrderSent 照合等）
    - risk_manager.py         — Gate1/2/3 を実装するリスク管理
  - data/
    - calendar_management.py  — マーケットカレンダー管理（DuckDB）
    - news_collector.py       — RSS ニュース収集（防御的 XML パース等）
    - (jquants_client.py)     — J-Quants API 関連（参照されるが別途実装）
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite DB 初期化とログ機能（参照）
    - system_monitor.py      — システムリソース監視（参照）
  - utils/
    - logging_setup.py       — ロギング初期化ヘルパー
    - process_priority.py    — プロセス優先度調整ユーティリティ

（注）README に列挙されていない補助モジュールやスクリプトが存在する場合があります。上記は本リポジトリで特に重要視されるコンポーネントの抜粋です。

開発と拡張
------------
- Live ブローカークライアント（KabuStationClient）を本番運用する場合は安全対策（通知・Kill Switch・リコンシリエーションの検証）を十分行ってください。
- 設定ファイルテンプレート（config/*.yaml）や jquants_client の実装は、外部 API や運用フローに合わせて追加・調整してください。
- モッククライアント（MockBrokerClient）はユニット / 結合テストに有用です。fill_mode によって挙動（instant/partial/never/reject）を制御できます。

ライセンス / 作者
-----------------
（ここにライセンスや作者情報を記載してください）

補足
----
- 追記・修正したい箇所や実行に際して不明点があれば、該当モジュールを確認のうえ具体的な質問をしてください。