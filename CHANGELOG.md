# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。  
日付はこのコードベースのスナップショット作成日（2026-04-23）を使用しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買フレームワーク「KabuSys」の基礎機能を実装しました。

### Added
- 全体
  - パッケージ初版を公開。
  - バージョン情報を src/kabusys/__init__.py にて `__version__ = "0.1.0"` として管理。

- 設定管理
  - Settings クラス（src/kabusys/config.py）を追加。環境変数から各種設定値を取得する共通 API を提供。
    - 必須環境変数取得用の `_require()`。
    - 自動 .env ロード機能（プロジェクトルート検出による .env / .env.local の読み込み）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - PAPER_FILL_MODE の妥当性チェック、パス設定（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）等。
    - KABUSYS_ENV / LOG_LEVEL の検証と便利プロパティ（is_live / is_paper / is_dev）。
  - .env パーサを実装（_parse_env_line）。以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - クォートなしでの行内コメント（直前が空白/タブの場合のみコメント扱い）

- 環境設定ウィザード
  - 対話式 CLI（src/kabusys/config_setup.py）を追加。`.env` の初期作成・更新を支援。
    - 設定項目定義を内包し、シークレット入力、選択肢、デフォルト値をサポート。
    - 既存 .env の読み込み・表示、確認後の保存（テンプレートヘッダ付き）。
    - 保存時に Git にコミットしない旨の注意を出力。

- 設定検証ツール
  - validate_config CLI（src/kabusys/validate_config.py）を追加。起動前に環境変数・設定ファイルをチェック。
    - 必須/任意の環境変数チェック、プレースホルダ値の警告、KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を失敗扱いにするモードをサポート。

- 実行用スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine の起動フロー（プロセス優先度設定、DB 接続、PID ファイル・停止フラグ管理）。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用し、本番 DB と分離。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動。環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）で間隔を上書き可能。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。

- Execution エンジンコア
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）を実装。
    - シグナルの読み込み（DuckDB）→ Gate1/Gate2 によるリスクチェック → 発注 → push ドレインの流れを実装。
    - セッション制御（signal_send_start/ signal_send_end / market_close）に基づく運転。
    - WebSocket push の受信を別スレッドで行い、_push_queue で同期処理。
    - kill_switch の実装（全 active 注文のキャンセル、停止イベント設定）。
    - PID ファイル管理、起動時のリコンシリエーション呼び出し（Reconciler が設定されている場合）。

- 注文関連ロジック
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態列挙 OrderState と許容遷移テーブルを定義。
    - transition_to による状態遷移検査（不正遷移時は InvalidStateTransitionError を raise）。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - create_order / send_order / sync_order / cancel_order を実装。
    - DuplicateOrderError の検出（信号 ID の重複抑止）。
    - send_order における堅牢性設計（OrderSent を DB に永続化してから broker 呼び出し → broker_order_id を先にコミット → OrderAccepted へ遷移する 2 相的な永続化シーケンス）。
    - OrderSentPendingError の扱い（broker が注文番号は発行するが約定しない場合の保留処理）。
    - sync_order による broker 側状態との同期、部分約定の進捗反映。
    - cancel_order は終端状態チェックのうえ broker に cancel を投げる。

- ブローカークライアント
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - kabu ステーション REST API 用クライアント（同期 httpx ベース）を追加。
    - トークン取得の遅延初期化と 401 時の自動再取得・リトライ実装。
    - HTTP ステータスに応じたエラー変換（401, 429, 5xx 等）。
    - WebSocket push（stream_push）を想定した stream 処理呼び出しのサポート（ExecutionEngine の websocket ワーカーと連携）。

- 監視・ログ等ユーティリティ
  - 監視 DB 初期化呼び出し（init_monitoring_db）連携ポイントを追加。
  - 発注イベントの監視 DB へのログ記録（MonitoringDB が注入されている場合、latency 等を記録）。

- その他
  - プロセス優先度設定ユーティリティ（set_process_priority）とロギングセットアップ（setup_logging）を利用する起動フローを採用。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- .env の取り扱いに関して README/ウィザードで「.env をコミットしない」旨を明示して出力するようにした。
- シークレット項目はウィザードでマスク表示。

### Known issues / Notes
- config/*.yaml の深い内容検証は PyYAML がインストールされている場合のみ行う。PyYAML 未インストール時はパース検証をスキップして警告を出す。
- ExecutionEngine の一部振る舞い（Reconciler / Broker 実装依存の挙動等）は外部コンポーネントに依存しており、統合テストでの検証が推奨される。
- run_monitoring/run_execution はローカルのファイルシステム上の stop_requested.flag / pid ファイルに依存するため、実運用時のパスと権限に注意。

---

署名: KabuSys 開発チーム（コードベースから推測して作成）