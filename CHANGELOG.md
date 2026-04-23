# Changelog

すべての変更は Keep a Changelog の慣例に従い記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-23
初回リリース。KabuSys のコア設定管理、実行エンジン、発注フロー、監視周りの基盤を実装しました。

### Added
- パッケージ初期化
  - __version__ を "0.1.0" に設定。
  - パッケージ公開 API の __all__ を定義。

- 設定管理
  - Settings クラス（src/kabusys/config.py）を実装。環境変数から各種設定を取得するプロパティ群を提供。
    - 必須設定の取得用 _require()（未設定時は ValueError）。
    - DUCKDB / SQLite / PID / Kill-flag 等のパス取得（Path に変換して expanduser() を適用）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検証。
    - PAPER_FILL_MODE の妥当性検証（"instant" | "partial" | "never" | "reject"）。
    - Paper Trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）。
  - .env 自動ロード
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を自動読み込み。既存の OS 環境変数は保護。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パース実装（_parse_env_line）
    - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの扱い等をサポート。

- 設定作成ウィザード CLI
  - src/kabusys/config_setup.py に対話式ウィザードを実装。.env の作成・更新を支援。
  - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を含む。
  - シークレット項目は表示をマスク、選択肢／デフォルトをサポート。
  - .env を生成する _write_env() 実装（Git へコミットしない旨の警告ヘッダーを含む）。
  - 実行例メッセージを表示（続けて validate_config を使うことを推奨）。

- 設定検証 CLI
  - src/kabusys/validate_config.py に設定検証ツールを実装。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検査（許容値リスト）。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml（system_config.yaml 等）の存在確認および PyYAML が利用可能ならパース検証。PyYAML 未インストール時はパース検証をスキップして警告を出す。
    - KABUSYS_ENV=live 時の追加ガード（LINE トークン/ユーザー未設定や KILL_FLAG_CLEAR_ON_START=1 の警告）。
    - 出力: INFO/WARNING/ERROR を表示。--strict オプションで警告も FAIL（exit 1）として扱う。
    - 使い方: python -m kabusys.validate_config [--strict]

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを提供。プロセス優先度設定、PID ファイル書き出し、停止フラグ検知、DB 初期化、スレッド管理を実装。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
  - run_monitoring.py
    - SystemMonitor のポーリングループ用スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。

- 発注フローとエンジン
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - Signal Queue Pull 型の発注エンジン（8:50-9:10 のシグナル処理、9:10-15:30 の push ドレイン）。
    - kill.flag の扱い（起動拒否 / 自動クリア KILL_FLAG_CLEAR_ON_START）と PID ファイル管理。
    - WebSocket push の受信を別スレッドで行い、受信ペイロードを _push_queue に投入。
    - シグナル処理の Gate チェック（Gate1: signal-level、Gate2: execution-level rate-limit + circuit breaker、Gate3: ドローダウン監視）。
    - レート制限リトライ (最大 3 回) や発注遅延計測（latency_ms）の監視 DB ログ出力対応。
    - 発注成功時に position_entries へ約定予定日を書き込むロジック（BUY と SELL の扱いに差をつける）。
    - kill_switch() 実装（全 active 注文のキャンセル処理）。

  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態列挙 OrderState と許容遷移定義を実装。OrderRecord クラスで遷移検証とフィールド更新を行う。
    - 不正遷移時は InvalidStateTransitionError を発生。

  - OrderManager（src/kabusys/execution/order_manager.py）
    - create_order, send_order, sync_order, cancel_order の外向き API を実装。
    - create_order は signal_id の重複防止（DB の部分ユニーク制約違反を DuplicateOrderError に変換）。
    - send_order はクラッシュ耐性を考慮した 2 段階永続化（OrderSent を先にコミット → broker 呼び出し → broker_order_id を保存 → OrderAccepted に遷移）を実装。OrderRejectedError / OrderSentPendingError の扱いを定義。
    - sync_order は broker からのステータス取得に基づく状態同期処理（部分約定の進行を反映）。
    - cancel_order はキャンセル不可能な状態の判定と broker cancel 呼び出しの扱いを実装。

  - Broker API 抽象化（インターフェース用の型定義は既存のコード群で利用）
    - OrderRequest/OrderResponse/OrderStatus/Position/例外（OrderRejectedError, OrderSentPendingError, BrokerAPIError, RateLimitError 等）に対応（実装は別モジュール群で提供する前提）。

  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - kabu station REST API クライアント（httpx 同期クライアントを使用）。
    - トークン取得／管理（遅延初期化、401 発生時の再取得・リトライ）、共通リクエストラッパーを実装。
    - レスポンス JSON パース失敗や各種 HTTP エラーを BrokerAPIError / RateLimitError に変換。
    - WebSocket push を想定した stream_push 連携（存在しない場合は警告してスキップできるよう設計）。

- 監視 DB 初期化
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を run_monitoring と run_execution の起動時に呼び出して、監視テーブルが存在することを保証（冪等）。

- ユーティリティ
  - ロギング設定セットアップ（setup_logging を利用する呼び出し箇所を追加）。
  - プロセス優先度設定ユーティリティ（set_process_priority を起動時に呼び出し High に設定）。

### Changed
- （初版）該当なし。

### Fixed
- （初版）該当なし。

### Security
- .env の取り扱いに関する注意喚起を config_setup のヘッダに明記（.env を絶対に Git にコミットしないこと）。

### Notes / ユーザー向けポイント
- CLI:
  - .env を作成するには: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config (必要に応じて --strict)
  - 実行スクリプト:
    - 監視を起動: python -m kabusys.run_monitoring
    - エンジンを起動: python -m kabusys.run_execution
- KABUSYS_ENV の有効値: development, paper_trading, live。settings.env / validate_config で検証される。
- Paper Trading モード:
  - settings.is_paper が True の場合、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番データと隔離する。
- kill.flag の扱い:
  - 起動時に kill.flag が存在すると起動拒否（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動）。
  - 実行中の kill_switch は全 active 注文をキャンセルしループを停止する。
- MONITOR_POLL_INTERVAL は秒数（正の整数）で指定。無効な値はデフォルト 60 秒にフォールバック。

もし特定の変更点やコミット履歴に基づいてより詳細な差分（例: 以前のバージョンからの変更点）を生成したい場合は、該当するコミットログや以前のバージョンのソースを提示してください。