# KabuSys — 日本株自動売買システム

概要
- KabuSys は日本株向けの自動売買フレームワークです。  
  シグナルに基づく発注エンジン（ExecutionEngine）、監視プロセス（SystemMonitor）、ブローカークライアント抽象化、リスクガード、リコンシリエーション機能などを備えています。
- 設定は .env と config/*.yaml で管理し、起動前に検証ツールで不備を検出できます。

主な機能
- 環境設定ウィザード（対話式 .env 生成/更新）
- 起動前の設定検証 CLI（必須環境変数 / config YAML / path 等のチェック）
- ExecutionEngine：Signal Queue からの発注処理（シグナル処理 + WebSocket push ドレイン）
- ブローカー抽象（実装: MockBrokerClient。将来的に KabuStationClient を接続可能）
- Order state machine（OrderRecord）・永続化（SQLite）・OrderManager
- リスク管理（Gate1/2/3：余力・重複・ポジション上限・レート制限・サーキットブレーカー・ドローダウン）
- リコンシリエーション（起動時に OrderSent をブローカーと突合）
- 監視プロセス（SystemMonitor のポーリングループ）
- データ周り：マーケットカレンダー管理（DuckDB）・ニュース収集モジュール（RSS）

前提 / 要件
- Python 3.10+ を想定（型アノテーション等を使用）
- 必要なパッケージ（代表例）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml (config YAML 検証に必要)
  - defusedxml (RSS パース用)
- 仮想環境の作成を推奨:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt  （プロジェクトで requirements.txt を用意している場合）

セットアップ手順
1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成・有効化し依存をインストール
3. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   - オプション: --env-file で別パス指定
4. 設定検証を実行
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにしたい場合: python -m kabusys.validate_config --strict
5. DuckDB / SQLite のデータディレクトリ（デフォルト: data/）は自動作成される場合がありますが、必要に応じて作成しておくと安心です。

重要な環境変数（最低限）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 推奨/オプション
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - KABU_API_BASE_URL — kabu station API ベース（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番での通知設定（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1、デフォルト 0)

例: 最小 .env（ウィザードで生成されます）
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

使い方（主要 CLI）
- 環境設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup
  - オプション: --env-file /path/to/.env

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit code 1）扱い

- 実行エンジン起動（本番/テスト）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込みます。
  - 起動時に data/execution.pid（デフォルト）へ PID が書き込まれ、停止フラグ data/stop_requested.flag を置くと安全停止します。
  - その他停止制御に kill.flag（data/kill.flag）を使用。KILL_FLAG_CLEAR_ON_START=1 の場合、起動時に自動クリアされます（注意して使用してください）。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト: 60 秒）。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — .env 自動読み込み、Settings クラス（環境変数アクセスラッパー）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前検証 CLI（.env / config/*.yaml / paths の検査）
  - run_execution.py — ExecutionEngine 起動スクリプト（PID / stop flag 管理）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py — execution モジュールの主要エクスポート
    - broker_api.py — BrokerAPIProtocol / データモデル / ファクトリ（Mock/Kabu）
    - broker_factory.py — Settings に基づくブローカーファクトリ
    - kabu_client.py — kabu station REST / WebSocket クライアント（httpx, websocket）
    - mock_client.py — テスト用 MockBrokerClient（fill_mode 等指定可能）
    - order_record.py — Order 状態遷移（純粋モデル）
    - order_repository.py — SQLite を使った永続化層（orders テーブル）
    - order_manager.py — Order の高レベル API（create/send/sync/cancel）
    - execution_engine.py — ExecutionEngine（シグナル処理 + push ドレイン）
    - reconciler.py — 起動時リコンシリエーション（OrderSent 照合、ポジション差分検出）
    - risk_manager.py — 3 段階リスクガード（Gate1/2/3）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB ベース）
    - news_collector.py — RSS ニュース収集（defusedxml 使用、SSRF 対策等）
  - monitoring/  — 監視関連コード（monitoring_db, SystemMonitor 等）※実装ファイルは該当ディレクトリ参照
  - utils/  — ロギング設定、プロセス優先度などユーティリティ（logging_setup, process_priority 等）

運用上の注意
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup でも注意喚起しています）。
- KABUSYS_ENV=live を設定すると本番扱いになります。validate_config は live の場合に追加警告を出します。LINE 通知設定など本番用のアラート設定が必要です。
- stop フラグ（data/stop_requested.flag）や kill.flag（data/kill.flag）を使ってプロセスを安全に停止できます。デフォルトのパスは Settings で変更可能です。
- paper_trading モードは本番 DB と完全に分離する設計です（paper_sqlite_path を使用）。
- config/*.yaml ファイルはスクリプト（scripts/generate_config.py）で生成できることが読み出しメッセージに書かれています。PyYAML が無い場合は YAML 内容検証をスキップします。

開発・拡張のヒント
- Broker の切り替えは execution.broker_api.create_broker_api を使う設計です。Mock と実運用クライアントを容易に差し替えられます。
- ExecutionEngine はテストで _process_signals() / _drain_push_queue() を直接呼ぶことで単体テスト可能です。
- Order の状態遷移は order_record.OrderState と OrderRecord.transition_to() で厳格に管理されています。DB 側の制約（orders テーブルの CHECK 等）と合わせて整合性を保っています。

問い合わせ / コントリビュート
- README に記載の依存パッケージや実運用接続（kabuステーション）に関するセットアップを整えた上で、Issue や Pull Request を送ってください。

（以上）