KabuSys
=======

日本株自動売買システムの簡易実装（ライブラリ + 実行スクリプト群）。

概要
----
KabuSys は日本株の自動売買を想定した小規模なフレームワークです。  
主な目的は以下の通りです。

- シグナルに基づく発注フロー（ExecutionEngine）
- ブローカー API 抽象化（実環境用とモックの切り替え）
- 注文の状態管理・永続化（SQLite）
- 起動時のリコンシリエーション（Reconciler）
- 監視コンポーネント（SystemMonitor／Monitoring DB）
- 環境設定ウィザード（.env 作成）／設定検証 CLI

特徴
----
- 3段階のリスクガード（Gate1: signal、Gate2: execution、Gate3: metrics）
- 発注のクラッシュ安全設計（OrderSent の二段階永続化など）
- Paper trading（モックブローカー）と本番環境を環境変数で切替
- DuckDB / SQLite を用いたデータ管理（分析用 / 監視用）
- 起動時の自動リコンシリエーションで未確定注文を復旧

主な機能一覧
--------------
- 環境設定ウィザード: python -m kabusys.config_setup
  - .env を対話的に作成／更新します
- 設定検証 CLI: python -m kabusys.validate_config [--strict]
  - .env と config/*.yaml ファイルの存在や基本的整合性をチェックします
- 実行エンジン起動: python -m kabusys.run_execution
  - シグナル読み込み → 発注 → WebSocket ドレイン のセッション実行
- 監視ループ起動: python -m kabusys.run_monitoring
  - SystemMonitor のポーリングループを実行し監視データを収集します
- モックブローカー (MockBrokerClient)
  - Paper trading / 開発で動作を再現するためのモック実装
- ブローカーファクトリ（BrokerClientFactory）
  - Settings に基づいて実行時にブローカークライアントを生成

動作要件
---------
- Python 3.10 以上（型ヒントの union 表記などを使用）
- 推奨ライブラリ（インストール推奨）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml (config/*.yaml の中身検証用。未インストールでも動作するが検証はスキップされます)
  - defusedxml (RSS ニュース収集で使用)
- 標準ライブラリ: sqlite3, logging, threading 等

セットアップ手順
----------------

1. リポジトリをクローン / 配布ファイルを展開

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   pip install --upgrade pip
   pip install duckdb httpx websocket-client pyyaml defusedxml

   ※プロジェクト固有の requirements.txt がある場合はそれを使ってください。

4. .env の作成
   python -m kabusys.config_setup
   - 対話式で .env が生成されます。作成後は必ず内容を確認してください（.env は絶対に Git にコミットしないでください）。

5. 設定検証（任意）
   python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit(1) になります。

使い方
------

環境変数（主要なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- 任意／上書き可能:
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 時の SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - KABU_API_BASE_URL — kabuステーション API のベース URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

基本コマンド例
- .env ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（通常は systemd 等でデーモン化）
  python -m kabusys.run_execution

  動作のポイント:
  - KABUSYS_ENV=paper_trading / development のときは MockBrokerClient を使用（実際の発注は行いません）。
  - paper_trading は monitoring / execution の SQLite を分離（PAPER_TRADING_SQLITE_PATH）。
  - 起動時に data/execution.pid（デフォルト）へ PID を書きます。停止指示は data/stop_requested.flag を作成して行います。
  - kill.flag が存在すると起動を拒否（または設定により自動クリア）します。

- 監視ループ起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）。

運用メモ
- .env は絶対にバージョン管理に含めないでください。config_setup は .env の生成を助けます。
- 本番環境（KABUSYS_ENV=live）では LINE 関連や各種設定値を慎重に確認してください（validate_config で警告が出ます）。
- stop は data/stop_requested.flag を作成することで安全に実行プロセスを停止できます。
- PID ファイルやデータディレクトリはデフォルトで data/ に作られます。必要に応じてパスを環境変数で調整してください。

ディレクトリ構成（主なファイル）
---------------------------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス: 環境変数の取り扱い、自動 .env 読み込みロジック
- config_setup.py
  - .env を対話的に作成するウィザード
- validate_config.py
  - 起動前の環境検証 CLI
- run_execution.py
  - ExecutionEngine の起動スクリプト
- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト

src/kabusys/execution/
- broker_api.py
  - BrokerAPIProtocol / データモデル / 例外 / create_broker_api ファクトリ
- broker_factory.py
  - Settings に基づいて Mock / Live クライアントを作成
- kabu_client.py
  - KabuStationClient（kabuステーション REST + WebSocket 実装）
- mock_client.py
  - MockBrokerClient（fill_mode などを指定可能）
- order_record.py
  - OrderRecord（状態遷移ロジック）
- order_repository.py
  - SQLite 永続化層（orders テーブル）
- order_manager.py
  - OrderRecord と Repository / Broker を組み合わせた発注 API
- execution_engine.py
  - ExecutionEngine（シグナル処理・WebSocket ドレイン、セッション制御）
- reconciler.py
  - 起動時のリコンシリエーション処理（OrderSent の復旧）
- risk_manager.py
  - 3段階リスクガード（Gate1/2/3）

src/kabusys/data/
- calendar_management.py
  - マーケットカレンダー管理（DuckDB と J-Quants 統合）
- news_collector.py
  - RSS ニュース収集（defusedxml を使用した安全なパーサ）

src/kabusys/monitoring/
- monitoring_db.py
  - 監視用 SQLite の初期化／ログ書き込み等（run_monitoring で使用）
- system_monitor.py
  - システム監視ロジック（CPU/MEM/DISK 等）

src/kabusys/utils/
- logging_setup.py
  - ロギング設定ユーティリティ
- process_priority.py
  - プロセス優先度設定ユーティリティ

補足
----
- 本リポジトリにおける「live」モードは一部未実装箇所（コメント参照）があります。実取引を行う場合は十分な検証と実装の確認を行ってください。
- YAML ファイル（config/*.yaml）はプロジェクトルートの config ディレクトリに配置して使用します。validate_config は PyYAML がインストールされていれば内容も検証します。
- セキュリティ: .env 内のシークレットは適切に管理し、CI/CD やリポジトリに漏れないようにしてください。

ライセンス / バージョン
-----------------------
パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

（ライセンス情報はリポジトリ付属の LICENSE を参照してください）

以上。運用や拡張に関する質問があれば具体的に教えてください。