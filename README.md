KabuSys — 日本株自動売買システム（ドキュメント）
=================================

概要
----
KabuSys は日本株の自動売買を想定した軽量なフレームワークです。本リポジトリは以下を含みます（抜粋）:

- 発注フロー（ExecutionEngine / OrderManager / OrderRepository / OrderRecord）
- ブローカークライアント（kabuステーション向け実装と Mock 実装）
- 3段階リスクガード（Gate1〜3、RateLimit / CircuitBreaker / Drawdown）
- 起動時リコンシリエーション（Reconciler）
- マーケットカレンダー管理（DuckDB ベース）
- ニュース収集ユーティリティ（RSS 収集）
- 環境設定ウィザード（.env を対話的に作成）
- 起動前設定検証 CLI（.env / config/*.yaml のチェック）
- 監視プロセス（SystemMonitor のポーリングループ）

主な目的は、発注ロジックとブローカー API 呼び出しを分離し、安全な再起動・リコンシリエーション、リスク制御を備えた運用を容易にすることです。

機能一覧
--------
- ExecutionEngine: シグナル取得 → 発注（Signal Queue Pull 型）および WebSocket プッシュドレイン
- OrderManager/OrderRecord: 注文状態遷移の管理（状態機械）と DB 永続化（SQLite）
- Broker クライアント
  - 実運用向け: KabuStationClient（kabuステーション REST API）
  - テスト/開発向け: MockBrokerClient（fill_mode を切替可能）
- RiskManager: Gate1（シグナル検査）、Gate2（レート制限・サーキットブレーカー）、Gate3（ドローダウン監視）
- Reconciler: 再起動時の OrderSent 注文の突合せとポジション差分検出
- Calendar 管理: DuckDB ベースで営業日判定・カレンダー更新ジョブ
- NewsCollector: RSS から記事収集・正規化・保存（セキュリティ対策込み）
- config_setup: .env を対話式で作成/更新
- validate_config: 起動前に環境変数と config/*.yaml を検証
- run_execution / run_monitoring: 各種プロセスの起動スクリプト

セットアップ手順
----------------
1. Python 環境を用意する（推奨: venv）
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 必要パッケージをインストールする
   - 主に使われる外部ライブラリ:
     - httpx
     - websocket-client
     - duckdb
     - PyYAML（config.yaml のパース用。なくても動くが検証がスキップされます）
     - defusedxml
   - 例:
     pip install httpx websocket-client duckdb PyYAML defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください）

3. プロジェクトルートに移動し、.env を用意する
   - 対話式ウィザード（推奨）:
     python -m kabusys.config_setup
     → 対話に従って .env を作成します。
   - 手動で作成する場合は .env.example を参考にしてください（.env.example が無い場合は README 内の変数説明を参照）。

4. 設定検証
   - 作成後、起動前検証を実行して不備を検出できます:
     python -m kabusys.validate_config
   - 警告をエラー扱いにする（CI など）場合:
     python -m kabusys.validate_config --strict

5. DB 初期化（必要に応じて）
   - Execution に使う orders テーブル等は実行時または手動で初期化できます。
   - 例（Python REPL で）:
     >>> import sqlite3
     >>> from kabusys.execution.order_repository import init_orders_db
     >>> conn = sqlite3.connect("data/monitoring.db")
     >>> init_orders_db(conn)
     >>> conn.close()
   - run_monitoring や run_execution は起動時に監視 DB テーブル等を初期化する処理（init_monitoring_db 等）を呼ぶ箇所があります。

使い方
------
- 環境設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup
  - 対話で各種環境変数を設定し .env を保存します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると WARNING も失敗扱いで exit(1) になります。

- 実行エンジン（Execution）
  - 実際のセッションを開始する:
    python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV により振る舞いが変わります。paper_trading / development はモックブローカーを使用し、本番 DB と分離（paper_trading 用 DB: data/paper_trading.db）。live は本番向けですが未実装の箇所があります（BrokerClientFactory 内で NotImplementedError を投げる場合あり）。

- 監視プロセス（Monitoring）
  - 監視ループを開始:
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60）。

主要な環境変数（抜粋）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD     — kabuステーション API パスワード（必須）

任意（よく使うもの）:
- KABUSYS_ENV           — 実行環境: development / paper_trading / live（デフォルト: development）
  - live の場合は本番運用に関する追加警告が出ます
- DUCKDB_PATH           — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL             — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL     — kabu station API の base URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（任意）
- LINE_USER_ID          — LINE 通知先ユーザーID（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

補足:
- 自動 .env 読み込み:
  - プロジェクトルートに .env / .env.local があれば自動で読み込まれます（OS 環境変数 > .env.local > .env の順）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading の挙動:
  - MockBrokerClient を使用
  - SQLite は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番データと分離されます

停止・PID・フラグ
----------------
- stop_requested.flag（data/stop_requested.flag）を作成すると run_execution / run_monitoring は検知して順次終了します。
- PID ファイル: settings.pid_file_path（デフォルト data/execution.pid）
- kill.flag により ExecutionEngine 側で kill_switch が発動し、全 active 注文をキャンセルします。KILL_FLAG_CLEAR_ON_START を 1 にしておくと起動時に存在する kill.flag を自動で削除して起動できます（本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義・バージョン
- config.py — 環境変数読み込み・Settings クラス（.env 自動読み込みとプロパティ）
- config_setup.py — .env 作成の対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

src/kabusys/execution/
- broker_api.py — Broker API のデータモデル、例外、Protocol、ファクトリ
- kabu_client.py — kabuステーション向け HTTP/WebSocket クライアント実装
- mock_client.py — テスト用 MockBrokerClient（fill_mode 等を指定可能）
- broker_factory.py — Settings に基づく BrokerClient 生成
- order_record.py — OrderRecord（状態遷移ロジック、純粋ビジネスロジック）
- order_repository.py — SQLite を用いた永続化層（init_orders_db 等）
- order_manager.py — OrderManager（外向きの発注 API）
- execution_engine.py — ExecutionEngine（シグナル処理・プッシュドレイン・kill switch）
- reconciler.py — 再起動時のリコンシリエーション
- risk_manager.py — 3段階リスクガード（Gate1〜3）

src/kabusys/data/
- calendar_management.py — マーケットカレンダーと営業日ロジック（DuckDB）
- news_collector.py — RSS 収集・正規化・保存ロジック

src/kabusys/monitoring/ (一部ファイルはコード抜粋に含まれていませんが参照箇所あり)
- monitoring_db.py — 監視用 DB 初期化/書き込みユーティリティ（run_monitoring/run_execution から使用）
- system_monitor.py — 監視ロジック（run_monitoring が使用）

ユーティリティ
- utils/ 以下（logging_setup, process_priority 等） — ロギングとプロセス優先度設定など

設計上の注意点
--------------
- 発注フローはクラッシュ耐性を考慮して設計されています（OrderSent の永続化、broker_order_id の先コミットなど）。
- OrderState の遷移は厳格に定義され、InvalidStateTransitionError による保護があります。
- Reconciler により、再起動時に OrderSent の注文をブローカーに問い合わせて状態を復元し、ポジション差分を検出します。
- モッククライアントを使うことで、kabuステーションが不要な開発・テストが可能です。
- 本番運用（KABUSYS_ENV=live）では十分な確認が必要です。validate_config は live を検出すると警告を出します。

トラブルシューティング
---------------------
- PyYAML がインストールされていないと config/*.yaml のパースチェックはスキップされます（validate_config が警告を出します）。YAML 検証を有効にするには PyYAML をインストールしてください。
- WebSocket 接続や HTTP リクエストでエラーが発生した場合はログに詳細が出力されます。LOG_LEVEL を DEBUG にすると詳細ログが得られます。

貢献・拡張
----------
- Live broker client（実際の kabuステーション連携）や運用用デプロイ手順、監視ダッシュボードの追加などを歓迎します。
- tests/ 配下にユニットテストを整備すると品質向上に寄与します。

ライセンス・その他
------------------
- 本 README はコードベースから読み取れる仕様に基づき作成しています。実際の運用前にはコード全体の確認と十分なテストを行ってください。

以上。必要があれば「起動手順の具体的な例（env 値のサンプル）」「DB 初期化スクリプト例」「よくあるエラーメッセージと対処」を追加で作成します。どちらを優先しますか？