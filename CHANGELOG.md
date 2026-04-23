# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、与えられたコードベースの内容から推測して作成した変更履歴です。

## [0.1.0] - 2026-04-23

### Added
- 初回公開: KabuSys 自動売買システムのコア機能群を追加。
  - パッケージメタ:
    - パッケージバージョンを __version__ = "0.1.0" として定義（src/kabusys/__init__.py）。
  - 環境設定管理:
    - .env 自動読み込み機能を実装（OS 環境変数優先、.env → .env.local の順）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能（src/kabusys/config.py）。
    - .env ファイルの柔軟なパース実装（export 形式、クォート文字列、エスケープ、インラインコメント処理対応）（src/kabusys/config.py）。
    - Settings クラスを実装し、環境変数から各種設定を取得するプロパティ群を提供（J-Quants / kabu API / LINE / DB パス / PID / Kill Switch / メトリクス閾値 / env/log level 等）（src/kabusys/config.py）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）を実装。
  - 設定ウィザード:
    - 対話式 CLI による .env 初期作成・更新ウィザードを実装（項目定義・シークレットマスク・選択肢・デフォルト値対応）。生成された .env は Git にコミットしないよう注意喚起（src/kabusys/config_setup.py）。
  - 設定検証ツール:
    - 起動前に環境変数および config/*.yaml の問題を検出する validate_config CLI を実装。
      - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
      - KABUSYS_ENV / LOG_LEVEL の妥当性検査。
      - DB パス（DUCKDB_PATH / SQLITE_PATH）親ディレクトリ存在チェック。
      - PyYAML があれば config/*.yaml のパース検証、未インストールならスキップして警告。
      - KABUSYS_ENV=live の追加ガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START=1 の警告等）。
      - --strict オプションで警告を fail 扱いにする（src/kabusys/validate_config.py）。
  - 実行エントリ:
    - 実行エンジン起動スクリプト (run_execution) を実装。
      - プロセス優先度設定、高優先度設定ユーティリティを利用。
      - paper_trading 環境では paper_trading 用 SQLite を使用して本番 DB と分離（src/kabusys/run_execution.py）。
    - 監視ループ起動スクリプト (run_monitoring) を実装。
      - MONITOR_POLL_INTERVAL によるポーリング間隔オーバーライド、監視用 DB 初期化、停止フラグ検出ロジックを含む（src/kabusys/run_monitoring.py）。
  - 注文関連コア:
    - OrderRecord データモデルと厳格な状態遷移（OrderState enum, transition_to, InvalidStateTransitionError）を実装（src/kabusys/execution/order_record.py）。
    - OrderManager を実装（create_order, send_order, sync_order, cancel_order）。
      - create_order: signal_id ベースの重複検出（DuplicateOrderError）。
      - send_order: クラッシュ耐性を考慮した 2 相永続化（OrderSent の永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 遷移等）と OrderSentPendingError/OrderRejectedError の扱い。
      - sync_order: ブローカー状態から内部状態への同期ロジック（部分約定の差分更新を含む）。
      - cancel_order: キャンセル不可能状態の判定と処理。
      - DB 一貫性（SQLite の部分ユニークインデックス考慮）に配慮。
  - 発注エンジン:
    - ExecutionEngine を実装。
      - シグナル読み込み（DuckDB）、Gate1/Gate2/Gate3 によるリスクチェック、重複回避、サイズ調整、発注フロー、約定後 position_entries の書き込みなどを含む（src/kabusys/execution/execution_engine.py）。
      - WebSocket push のドレイン処理と push による同期（sync_order）をサポート。stream_push 未サポートな broker の場合は警告してスキップ。
      - kill_switch: 全 active 注文キャンセルとループ停止処理を提供。
      - セッション管理（signal_send_start/ signal_send_end / market_close による運用スケジュール）と PID ファイル管理、kill.flag 起動時の挙動（KILL_FLAG_CLEAR_ON_START の挙動含む）。
  - ブローカ / kabu ステーションクライアント:
    - KabuStationClient を実装（httpx 同期クライアント）。
      - トークン取得の遅延初期化、自動再取得（401 の際にリトライ）。
      - HTTP エラー／タイムアウト／ネットワークエラーを BrokerAPIError / RateLimitError 等に変換。
      - kabu ステーションの状態コードを内部ステータスにマップ（open/partial/filled/cancelled/rejected 等）（src/kabusys/execution/kabu_client.py）。
  - その他:
    - monitoring/ 実装と init_monitoring_db / SystemMonitor 利用（参照されるが実装は別ファイルで存在すると仮定）。
    - ロギング設定のセットアップ (`setup_logging`) とプロセス優先度設定 (`set_process_priority`) を起動時に利用する設計（参照箇所あり）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env を絶対に Git にコミットしないことを README/生成ファイル内で明示（config_setup のヘッダメッセージ）。

---

注: 本 CHANGELOG は提示されたソースコードの内容から推測して作成したものであり、実際のコミット履歴やリリースノートと完全に一致しない可能性があります。必要であれば、特定のファイルや機能に関するより詳細な変更点（小さな実装差分やバグ修正の推測）を追記します。