CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-22
--------------------

Added
- 初版リリース: KabuSys 0.1.0 を追加。
- 環境設定 / ロード
  - Settings クラスを追加（kabusys.config）。環境変数から各種設定値を取得するプロパティ群を提供。
  - .env 自動読み込み機構を追加。プロジェクトルート（.git または pyproject.toml を基準）を探索し、.env と .env.local を読み込む（OS 環境変数を上書きしない / 上書きする挙動を保護する仕組みあり）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサを強化（kabusys.config._parse_env_line）:
    - export プレフィックス対応（export KEY=val）。
    - シングル／ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなし値のインラインコメント処理（直前が空白/タブの場合）。
- 設定ウィザード CLI（kabusys.config_setup）
  - 対話式に .env を生成・更新するウィザードを追加（秘密値はマスク表示）。
  - 標準的なキー群（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークンなど）のテンプレート出力機能を搭載。
  - .env のテンプレートは Git へコミットしないよう注意書き付きで出力。
- 設定検証 CLI（kabusys.validate_config）
  - .env と config/*.yaml の起動前検証ツールを追加。
  - 必須 / 任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認などを実行。
  - PyYAML がインストールされている場合は config/*.yaml をパースして内容検証を実施（未インストール時は警告）。
  - --strict フラグを追加：警告も FAIL（exit code 1）扱いにする。
  - KABUSYS_ENV=live の場合に本番向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START チェック等）を実行。
- 実行スクリプト
  - run_execution（kabusys.run_execution）を追加。ExecutionEngine の起動・プロセス管理（PID ファイル、stop フラグ、プロセス優先度設定）を行う。
  - run_monitoring（kabusys.run_monitoring）を追加。SystemMonitor ポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数で周期を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用。
- Execution / 発注基盤
  - ExecutionEngine（kabusys.execution.execution_engine）を追加。
    - シグナル読み込み（DuckDB）→ Gate1/2 によるリスクチェック → 発注 → push ドレインの主要ループを実装。
    - セッション時間（signal_send_start/end、market_close）に従う処理。WebSocket push を別スレッドで受け取り同期処理する設計。
    - kill.flag の検出、KILL_FLAG_CLEAR_ON_START による起動時クリア挙動、PID ファイル管理を実装。
    - 発注レイテンシ等を監視 DB にログ可能（監視 DB が渡された場合）。
    - broker が stream_push を提供しない場合は WebSocket スレッドをスキップしてフォールバック。
  - OrderRecord（kabusys.execution.order_record）を追加
    - 注文状態を列挙する OrderState と許可遷移表を定義。
    - 状態遷移検証（transition_to）と不正遷移時の InvalidStateTransitionError を提供。
  - OrderManager（kabusys.execution.order_manager）を追加
    - create_order, send_order, sync_order, cancel_order の外向き API を実装。
    - send_order はクラッシュ耐性を考慮した 2 相永続化（OrderSent を永続化→broker 呼び出し→broker_order_id を先に永続化→OrderAccepted へ遷移）を実装。
    - OrderSentPendingError の扱い、OrderRejectedError による Rejected 遷移処理、DuplicateOrderError を導入。
    - sync_order により broker 側状態を照合して部分約定・約定の同期を行う（同一状態でも filled_qty/avg_fill_price を更新）。
    - cancel_order は終端状態ではエラーを投げる等のガードを実装。
  - ExecutionEngine 上での position_entries 更新ロジック（buy/sell の取り扱いと pending の扱い）を実装。約定日は次営業日を使用（データ/バックテスト整合）。
  - Reconciler（リコンシリエーション）フックを統合（起動時に自動実行可能）。
- Broker / kabu station クライアント
  - KabuStationClient（kabusys.execution.kabu_client）を追加。
    - httpx を用いた同期 REST クライアント実装（トークン取得の遅延初期化、401 時のトークン再取得＋リトライ）。
    - レスポンス JSON パース失敗、ネットワーク/タイムアウトエラーを BrokerAPIError 等にラップ。
    - 429 を RateLimitError にマップ。
    - kabu station の状態コードを内部ステータス（open/partial/filled/cancelled/rejected）にマップ。
    - WebSocket（push）受信用の仕組み（stream_push を持つ broker 実装を想定）。
- モニタリング DB 初期化 / SystemMonitor 起動フックを追加（kabusys.monitoring.monitoring_db, SystemMonitor の利用を想定）。
- ユーティリティ
  - より堅牢なログセットアップ / プロセス優先度設定ユーティリティを参照して利用（setup_logging, set_process_priority）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Notes / その他
- デフォルト値や有効値のバリデーションが多く導入されています（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。設定値に不正があると Settings のプロパティが ValueError を送出します。
- config/*.yaml の存在確認・パース検証は PyYAML がオプション依存（未インストール時は検証をスキップして警告）。
- paper_trading 環境では監視・発注の SQLite DB を本番 DB と分離（paper_trading 用の別パスを利用）。
- stop / kill フラグ管理、PID ファイルの扱い、プロセス優先度の設定は起動スクリプト側で実行する設計。
- バージョン情報: __version__ = "0.1.0"

今後の予定（例）
- async 対応の httpx.AsyncClient を使った非同期版 KabuStationClient。
- 監視・発注の E2E テスト、より詳細なログ/メトリクス出力の強化。
- config/*.yaml のスキーマ検証（現在は PyYAML safe_load のみ）。