# CHANGELOG

すべての変更は「Keep a Changelog」フォーマットに準拠して記載しています。  
バージョン情報はパッケージバージョン（src/kabusys/__init__.py の __version__）に合わせています。

すべての項目はコードベースから推測して記載しています。実装の意図や振る舞い、CLI の使い方などを含めています。

## [Unreleased]

### Added
- validate_config CLI（src/kabusys/validate_config.py）
  - .env と config/*.yaml の起動前チェックを行うコマンドラインツールを追加。
  - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の値検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向け追加ガードを実装。
  - 警告・情報・エラーを集約し、標準出力に INFO/WARNING/ERROR を出力。--strict オプションで警告を失敗扱い（exit(1)）にできる。

- 環境設定ウィザード CLI（src/kabusys/config_setup.py）
  - 対話式で .env を初期作成／更新するウィザードを追加。
  - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 周りなど）と説明、選択肢、シークレット表示（マスク）に対応。
  - 既存 .env の読み込み・再利用、確認プロンプト、.env ファイルの生成および書き込み機能を提供。

- 環境変数読み込み・設定管理（src/kabusys/config.py）
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動ロードを実装（優先度: OS 環境 > .env.local > .env）。
  - .env のパース実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープを考慮した値パース
    - クォートなしでのインラインコメント処理（'#' の直前が空白/タブの場合のみコメントとみなす）
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数をサポート（テストなどで利用可能）。
  - Settings クラスを追加し、型付きプロパティで設定値を取得:
    - 必須変数取得時は未設定で ValueError を投げる _require を使用（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
    - 路用値・変換ロジックを提供（Path に変換、float 変換、enum 検証等）。
    - paper_fill_mode（instant/partial/never/reject）の検証と取得。
    - paper_trading 用の paper_sqlite_path を分離して取得。
    - 各種監視しきい値（CPU/MEM/DISK）や kill flag 設定等を環境変数から取得。

- 実行エントリポイント／デーモン化関連
  - run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine を組み立ててデーモン的に実行するスクリプト。
    - paper_trading 環境時には専用 SQLite（paper_trading.db）を使用して本番 DB と完全分離。
    - プロセス優先度設定（set_process_priority）、PID ファイル管理、停止フラグ（data/stop_requested.flag）による停止監視。
  - run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。

- Execution エンジン本体（src/kabusys/execution/execution_engine.py）
  - Signal Queue Pull 型の発注エンジンを実装。
  - シグナル処理（デイリールーチン 8:50–9:10）と WebSocket push ドレインループ（9:10–15:30）を分離して実行。
  - Gate 1/2/3 による多段リスクチェックを実装:
    - Gate 1: シグナルレベル検査（個別シグナルの妥当性）
    - Gate 2: エグゼキューションレベル（レート制限、Circuit Breaker） — リトライ最大 3 回、回路遮断（CIRCUIT_BREAKER）時はシグナルループ停止
    - Gate 3: ドローダウン監視で規定値を超えた場合は kill_switch を発動
  - size_multiplier の適用（BUY のみ）や qty を 100 単位に丸める処理、0 qty のスキップなどを行う。
  - 発注後に position_entries を DuckDB に記録（発注成功/保留に応じた処理）し、失敗しても発注フローは継続する耐性設計。
  - WebSocket push（broker.stream_push）を別スレッドで受信し、push に基づいて同期（sync_order）や Gate 3 評価を実施。

- OrderRecord / OrderState（src/kabusys/execution/order_record.py）
  - 注文状態マシンを OrderState enum で定義（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
  - 許可遷移テーブルと状態遷移検証を実装。InvalidStateTransitionError を投げることで不正遷移を防止。
  - OrderRecord dataclass に updated_at を自動更新する transition_to メソッドを用意。broker_order_id、filled_qty、avg_fill_price、error_message の更新をサポート。

- OrderManager（src/kabusys/execution/order_manager.py）
  - OrderRecord（メモリ上のビジネスロジック）と OrderRepository（SQLite）を組み合わせた外向き API を提供: create_order, send_order, sync_order, cancel_order。
  - create_order:
    - signal_id に対して既存の active 注文がある場合は DuplicateOrderError を raise。
    - client_order_id を uuid4 で生成して DB 保存。DB の部分ユニークインデックス違反は DuplicateOrderError に変換。
  - send_order:
    - クラッシュ耐性を考慮した 2 相永続化パターンを採用（OrderSent を DB に commit → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）。
    - OrderRejectedError は Rejected に遷移。OrderSentPendingError（broker が注文番号を発行したが約定しない）を特別扱いして broker_order_id を保存したまま OrderSent のままにして発生を伝播。
    - その他の例外はキャッチせず、OrderSent のまま残して list_uncertain()/reconciliation の対象にする設計。
  - sync_order:
    - broker.get_order_status を呼んで状態同期。status マッピングと、既に同一状態だが部分約定数が更新された場合は個別更新を行う。
    - OrderSent → Filled/PartialFill の直接遷移不可を考慮して OrderAccepted を経由する回復ロジックを実装（リコンシリエーションを想定）。
  - cancel_order:
    - 終端状態（Closed / Filled / Cancelled / Rejected）の場合はキャンセル不可として InvalidStateTransitionError を投げる。
    - ブローカー注文ID があれば API による取消を行った上で Cancelled に遷移。

- ブローカークライアント（kabuステーション）実装（src/kabusys/execution/kabu_client.py）
  - KabuStationClient を追加（httpx を同期クライアントとして利用）。
  - トークン取得（/token）を内部で管理し、401 発生時はトークン再取得→1回リトライの実装。
  - レスポンス JSON パース失敗やネットワーク/タイムアウト、HTTP ステータス（401/429/5xx）に応じた例外変換（BrokerAPIError, RateLimitError 等）を実装。
  - kabu station の状態コードから内部 status へのマップを定義（open/partial/filled/cancelled/rejected）。
  - WebSocket push（stream_push）のコールバックで ExecutionEngine の _push_queue に投入できるように設計。将来的な async 対応も容易な構成。

- Reconciler / RiskManager / MonitoringDB 等を結合するためのフックを Engine に追加（実装ファイルの存在を示唆するインポートと利用）。

- その他ユーティリティ
  - process_priority 設定フック（set_process_priority）を実行開始時に呼ぶことでプロセス優先度を上げる（run_execution/run_monitoring）。
  - 監視DB初期化（init_monitoring_db）を起動時に呼び出してテーブル存在を保証。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

---

## [0.1.0] - 2026-04-22

初回リリース。上記の機能群を含むリリース。

- パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- CLI/ライブラリの追加:
  - config 自動ロードと Settings 取得 API
  - config_setup（.env ウィザード）
  - validate_config（起動前チェック）
  - run_execution（ExecutionEngine エントリポイント）
  - run_monitoring（SystemMonitor エントリポイント）
- Execution フレームワーク:
  - ExecutionEngine（Signal 処理、WebSocket ドレイン、kill_switch、PID 管理）
  - OrderRecord（状態遷移ロジック）
  - OrderManager（create/send/sync/cancel 実装）
  - KabuStationClient（HTTP トークン管理、エラー処理、状態マッピング、WebSocket 入力）

Breaking Changes: なし（初回リリース）。

---

作成にあたっての注記:
- CHANGELOG はソースコードの実装から挙動・仕様を推測して作成しています。実際のドキュメントやコミット履歴がある場合は、そちらに合わせて文言を調整してください。
- 日付は本ファイル作成時点（2026-04-22）を使用しています。必要に応じてリリース日を変更してください。