Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-23
--------------------

Added
- プロジェクト初版リリース。
- 環境設定 / 設定検証ツールを追加
  - 対話式 .env 作成ウィザード: python -m kabusys.config_setup
    - KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DUCKDB_PATH / SQLITE_PATH などの主要設定を対話的に生成・更新。
    - シークレット値はマスク表示。選択肢・デフォルトをサポート。
    - .env の読み書きロジックを実装（.env/.env.local を生成・更新）。
  - 設定検証 CLI: python -m kabusys.validate_config
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の未設定を検出。
    - 値のプレースホルダ（*_here / your_value）を警告。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（有効値を照合）。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック。
    - config/*.yaml の存在確認および PyYAML がある場合は YAML パース検証（PyYAML 未インストール時はスキップ）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL（exit 1）扱いにできる。

- 設定読み込み / Settings
  - .env 自動ロード（優先順: OS 環境変数 > .env.local > .env）。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パーサは export 前置、クォート、バックスラッシュエスケープ、行内コメントなどを考慮して読み込み。
  - Settings クラスで各種設定プロパティを提供:
    - jquants_refresh_token / kabu_api_password / kabu_api_base_url
    - line_channel_access_token / line_user_id
    - duckdb_path / sqlite_path / paper_sqlite_path
    - pid_file_path / kill_flag_path / KILL_FLAG_CLEAR_ON_START
    - 各種しきい値（CPU/MEMORY/DISK）
    - env / log_level / is_live / is_paper / is_dev
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）

- 実行スクリプト（デーモン化や監視）
  - run_execution: ExecutionEngine 起動スクリプト
    - paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - プロセス優先度設定、PID ファイル書き込み、stop flag（data/stop_requested.flag）監視を実装。
  - run_monitoring: SystemMonitor ポーリングループ起動
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視でも常に本番 sqlite_path を使用。

- 注文処理コア
  - OrderRecord（状態遷移を行う純粋ドメインモデル）
    - OrderState 列挙と許可遷移を定義。InvalidStateTransitionError を導入。
    - transition_to により状態遷移とオプションフィールド（broker_order_id, filled_qty, avg_fill_price, error_message）の更新を一元化。
  - OrderManager（外向き API: create/send/sync/cancel）
    - create_order: signal_id の重複チェック（DB の部分ユニークインデックス違反を DuplicateOrderError に変換）。
    - send_order: クラッシュ耐性を考慮した二相永続化フロー（OrderSent を先に永続化 → broker 呼出し → broker_order_id 永続化 → OrderAccepted へ遷移等）。OrderRejectedError / OrderSentPendingError を適切に処理。
    - sync_order: broker 側の状態を取得して DB と同期。部分約定の増分更新にも対応。
    - cancel_order: 終端状態のチェックと broker cancel 呼び出し、Cancelled への遷移。
    - DuplicateOrderError / InvalidStateTransitionError の導入。
  - ExecutionEngine
    - シグナル取得（DuckDB）→ Gate1（シグナルレベル）/ Gate2（実行レベル・レート制限）を経て発注。
    - size_multiplier の適用（BUY のみ、100株単位切り捨て）。
    - 発注時の latency 計測と監視 DB へのログ（MonitoringDB が提供されている場合）。
    - WebSocket push ドレイン処理（push 受信で sync_order 呼び出し、Gate3 ドローダウン評価）。
    - Gate3（ポートフォリオ評価）で NG の場合は kill_switch を発動して全 active 注文をキャンセル。
    - kill.flag の存在に応じた起動拒否や自動クリア（KILL_FLAG_CLEAR_ON_START）。
    - PID ファイル作成／削除処理。
    - run_session によりセッション時間に応じた処理（シグナル処理時間帯 / ドレイン時間帯）。
  - Broker/Client
    - KabuStationClient: kabu station REST API クライアント（httpx 同期クライアント）
      - トークン取得の遅延初期化と 401 時のトークン再取得リトライを実装。
      - レスポンス JSON パース失敗 / ネットワークエラー / タイムアウトを BrokerAPIError 等に変換。
      - 429 (rate limit) を RateLimitError に変換。
      - （将来の async 対応は httpx.AsyncClient へ切替可能な設計）
  - Reconciler / RiskManager / OrderRepository などのコンポーネントを組み合わせた実行フローを実装（ExecutionEngine 側で利用）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- .env ファイルは絶対に Git にコミットしない旨を生成ヘッダに明示。

Notes / 開発者向けメモ
- プロジェクトバージョンは kabusys.__version__ = "0.1.0"。
- YAML のパース検証は PyYAML がインストールされている場合に限る（validate_config は未インストール時にスキップして警告）。
- 自動ロードの動作を抑止したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用すること。
- ExecutionEngine の一部処理（_process_signals / _drain_push_queue）はテスト時に直接呼び出せるように設計済み。

