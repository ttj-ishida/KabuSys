# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは Keep a Changelog に準拠しています。

現在のバージョン: 0.1.0 — 初回リリース

## [0.1.0] - 2026-04-23

### Added
- 初回リリース。日本株自動売買フレームワーク "KabuSys" の基本機能を実装。
- 環境設定 / 実行用 CLI を追加
  - python -m kabusys.config_setup: 対話式 .env 作成/更新ウィザードを実装。項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連等）を備える。
  - python -m kabusys.validate_config: 起動前チェック CLI を実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、`--strict` モードで警告も失敗扱いにする機能を提供。
  - run_monitoring/run_execution 起動スクリプトを追加（監視ループ / 実行エンジンのエントリポイント）。
- 設定管理モジュールを追加（kabusys.config）
  - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサ実装: export 形式、クォート／エスケープ、インラインコメント処理に対応。
  - Settings クラス: 環境変数から型付きプロパティ（パス, bool, float 等）を提供。PAPER_FILL_MODE の妥当性チェック等を内蔵。
- 実行エンジン（ExecutionEngine）を実装
  - シグナル処理（指定時間帯）と WebSocket push ドレインループを備えるセッション実行機構。
  - Gate ベースのリスクチェックフロー（Gate1: シグナル単位、Gate2: 発注レート制御、Gate3: ドローダウン監視）を実装。NG の場合は kill_switch を発動。
  - kill.flag / PID ファイルの扱い（起動時の kill.flag チェック、KILL_FLAG_CLEAR_ON_START による自動クリアのサポート）。
  - WebSocket push を受け取り _push_queue に投入するワーカー実装（broker 側に stream_push がある場合）。
  - position_entries への約定予定日の記録（buy/sell の扱いを区別）。
- 注文管理・状態機構を実装
  - OrderRecord: 状態遷移ロジック（OrderState 列挙、許可遷移表、transition_to メソッド）を純粋なビジネスロジックとして実装。InvalidStateTransitionError を定義。
  - OrderManager: signal_id に基づく重複検知（DuplicateOrderError）、発注フロー（create_order / send_order / sync_order / cancel_order）を実装。
    - send_order はクラッシュ安全性を考慮した 2 段階永続化（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）を採用。
    - OrderSentPendingError / OrderRejectedError の扱いを明確化。
    - sync_order は broker 側の状態を取得して DB に同期（部分約定の更新や状態遷移補完を含む）。
    - cancel_order はキャンセル不可状態をチェックして適切に振る舞う。
- ブローカークライアント実装（kabu station 向け）
  - KabuStationClient: httpx を用いた同期 REST クライアント。トークン取得（遅延初期化）・401 での再取得およびリトライ、429 を RateLimitError にマッピング、ネットワーク/タイムアウト例外のラッピングなどを実装。
  - order 状態コードを内部ステータスに変換するマップを実装。
  - websocket 経由の push 受信（stream_push を想定）が可能（WebSocket 用の処理を用意）。
- 監視関連
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（MONITOR_POLL_INTERVAL で間隔変更可、デフォルト 60 秒）。
  - 監視用 DB（SQLite）初期化処理を呼び出し、DuckDB との接続も確立。
  - ExecutionEngine の発注イベントは monitoring DB にログ可能（監視 DB が渡された場合）。
- データベース
  - DuckDB/SQLite を併用。paper_trading 環境では専用の SQLite（data/paper_trading.db）を使用して本番 DB と分離。
- プロセス優先度 / ロギング
  - 起動時にプロセス優先度を設定するユーティリティを呼び出す（set_process_priority）。
  - セクション単位でのログレベル設定に対応（LOG_LEVEL 環境変数）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- （初版のため該当なし）

注記:
- validate_config は PyYAML が未インストールの場合、YAML の中身検証をスキップするようフォールバックする（警告を表示）。
- .env ファイルは絶対に Git にコミットしない旨を config_setup が明記している。
- Settings の一部プロパティは不正値で例外を送出する（例: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL）。起動前に validate_config でチェックすることを推奨します。