# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-23

初回リリース。

### Added
- 基本パッケージ情報
  - パッケージバージョンを追加: `__version__ = "0.1.0"`（src/kabusys/__init__.py）。

- 環境変数／設定管理
  - Settings クラスを実装し、環境変数から設定を取得する API を提供（src/kabusys/config.py）。
    - 必須設定取得用の `_require()` を実装（未設定時は ValueError を送出）。
    - env 値（KABUSYS_ENV）/log level / paper fill mode 等のバリデーション実装。
    - path 系設定（DuckDB/SQLite/PID/Kill Flag 等）を Path 型で返すユーティリティを追加。
    - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で発見）。
    - 自動ロードを無効にするための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env 読み込み時に OS 環境変数を保護する仕組み（protected keys）を実装。

  - .env パーサーの堅牢化:
    - export 形式、クォート（シングル/ダブル）内のバックスラッシュエスケープ、インラインコメントの処理等をサポート（src/kabusys/config.py::_parse_env_line）。

- 環境設定ウィザード CLI
  - 対話式ウィザードで .env を生成・更新するツールを実装（src/kabusys/config_setup.py）。
    - 入力項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE 設定など）。
    - 既存 .env の読み込み・再利用、シークレット値のマスク表示、選択肢とデフォルトのサポート。
    - .env の書き出しフォーマットテンプレートを実装（.env に絶対コミットしない注意書き含む）。
    - CLI エントリポイント: `python -m kabusys.config_setup`（`--env-file` オプションでパス指定可）。

- 設定検証 CLI
  - 起動前に `.env` と `config/*.yaml` を検証する CLI を実装（src/kabusys/validate_config.py）。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV、LOG_LEVEL の妥当性チェック。
    - DUCKDB/SQLITE の親ディレクトリ存在チェック（起動時自動作成の旨を警告）。
    - config/*.yaml の存在確認および PyYAML が存在する場合はパース検証。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告等）。
    - `--strict` オプションで警告も FAIL（exit 1）扱いに可能。
    - CLI エントリポイント: `python -m kabusys.validate_config`。

- 実行エントリポイント（プロセス制御・PID等）
  - 実行（エンジン）起動スクリプトを提供（src/kabusys/run_execution.py）。
    - プロセス優先度設定（set_process_priority 呼び出し）。
    - Settings から DB パスを取得。paper_trading 環境では専用 SQLite（paper_sqlite_path）を使用して本番 DB と分離。
    - stop フラグ検知用ファイル（data/stop_requested.flag）や PID ファイル（data/execution.pid）を利用。
    - DB 接続（sqlite3 / duckdb）を行い、監視 DB 初期化を実行。

  - 監視ループ起動スクリプトを提供（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用。
    - stop フラグ検知と例外ハンドリングによるフォールバック（ループ継続）を実装。

- 発注／実行エンジン
  - ExecutionEngine 実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理フェーズ（signal_send_start ～ signal_send_end）と WebSocket push ドレインフェーズ（signal_send_end ～ market_close）で動作。
    - kill.flag により起動・ループ中の起動拒否・自動クリア（KILL_FLAG_CLEAR_ON_START=1 の場合）をサポート。
    - PID ファイル書き込み／削除の実装。
    - WebSocket スレッドで kabu の push を受信して処理（stream_push がない broker はスキップ）。
    - シグナル処理フロー: size_multiplier 適用（BUY のみ）、Gate1（シグナルレベル）、Gate2（実行レベル・レート制限、最大3回リトライ、サーキットブレーカー時はループ停止）を実装。
    - 発注後、position_entries テーブルに約定日（翌営業日）を記録する処理を実装（duckdb 経由）。
    - Gate3（ドローダウン監視）で閾値超過時は kill_switch を発動。

  - ExecutionEngine の停止／kill_switch 実装:
    - 全 active 注文をキャンセルし、スレッド停止フラグをセット。
    - cancel の過程で BrokerAPIError をハンドリングし継続できる設計。

- 注文管理（Order）
  - OrderRecord（状態遷移ロジック）を純粋ビジネスロジックとして実装（src/kabusys/execution/order_record.py）。
    - 明確な OrderState 列挙と許可遷移マップを定義。
    - transition_to による遷移検証（不正遷移は InvalidStateTransitionError を送出）。
    - updated_at を自動更新し、broker_order_id / filled_qty / avg_fill_price / error_message をキーワード引数で更新可能。

  - OrderManager（外向き API）を実装（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id の重複検査（DB のユニーク制約違反を DuplicateOrderError に変換）。
    - send_order: 2相永続化パターンを採用（OrderSent を DB に書き込んだ後に broker へ送信、broker_order_id を先にコミットしてから OrderAccepted に遷移）し、クラッシュ時の回復性を考慮。
    - send_order での例外ハンドリング:
      - OrderRejectedError → Rejected へ遷移。
      - OrderSentPendingError → broker_order_id を保存した上で OrderSent のまま残して呼び出し元へ伝播（Reconciliation 対象）。
    - sync_order: broker 側ステータス取得→内部状態へ同期。部分約定での filled_qty / avg_fill_price の差分更新を考慮。OrderSent→Filled/PartialFill の場合は中間的に OrderAccepted を経由して遷移。
    - cancel_order: 終端状態（Closed / Filled / Cancelled / Rejected）はキャンセル不可として InvalidStateTransitionError を送出。broker_order_id がある場合は cancel を呼び、Cancelled に遷移。

  - OrderRepository（SQLite を扱う層）と連携する設計（ストアの詳細は本リリースで利用想定）。

- ブローカー API クライアント基盤
  - BrokerAPIProtocol 型を前提とした抽象／実装層を想定（各所で Protocol 型を利用）。
  - KabuStationClient 実装（src/kabusys/execution/kabu_client.py）:
    - 同期 httpx.Client を使用した REST API 実装（将来の async 化を見据えた設計）。
    - トークン管理（遅延取得、401 時の再取得と 1 回のリトライ）を実装。
    - レスポンス JSON パース失敗を BrokerAPIError に変換。
    - 429 に対して RateLimitError を送出、5xx は BrokerAPIError に変換。
    - kabu ステーションの注文状態コードを内部ステータスにマッピング。
    - WebSocket push（websocket ライブラリ）を用いた push 受信インターフェース（stream_push 想定）。

- リスク管理・再構成（Reconciliation）等の統合点
  - RiskManager, Reconciler などのコンポーネントを ExecutionEngine に組み込み、発注フローで利用（設定や呼び出しの流れを実装）。（実装ファイルへの参照が多数あり、実際の内部ロジックは別ファイルで管理）

- 監視（Monitoring）
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）を導入し、run_monitoring/run_execution から利用。
  - ExecutionEngine から発注イベントを監視 DB にロギングするフック（MonitoringDB が渡された場合）。
  - run_monitoring における例外処理と graceful shutdown。

- ユーティリティ
  - process_priority と logging_setup ユーティリティを利用する起動フロー（高優先度設定・ロギング初期化）。
  - duckdb を利用したデータアクセス（signals / portfolio_targets / position_entries 等の読み書き）。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数を .env に保存する際の注意喚起を .env テンプレートに追加（config_setup の出力に記載）。

---

注記:
- 本 CHANGELOG はソースコードの記述から推測して作成しています。各モジュールの詳細実装（例: OrderRepository / RiskManager / Reconciler の内部実装、監視 DB スキーマ、broker_factory の具体的な実装等）は別ファイルに定義されています。実運用前に各コンポーネントのテストと設定検証（`python -m kabusys.validate_config`）を推奨します。