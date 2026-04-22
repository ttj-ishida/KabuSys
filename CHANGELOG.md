# CHANGELOG

すべての注目すべき変更履歴を記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 該当時に記載

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-22
初回リリース。KabuSys の基本機能を実装しました。主な追加点および設計上の注目点は以下の通りです。

### Added
- 全体
  - パッケージ初期リリース。バージョンは `0.1.0`。
  - コアモジュール群を実装: data, strategy, execution, monitoring（__all__ に公開）。
- 設定関連
  - 環境変数 / .env 管理モジュール（kabusys.config）
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - .env/.env.local の自動読み込み（OS 環境 > .env.local > .env、保護された OS 環境変数は上書き不可）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env の行パーサーを実装:
      - export KEY=val 形式に対応。
      - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
      - インラインコメントの取り扱い（未引用時の '#' の扱いを調整）。
    - Settings クラスを提供し、プロパティ経由で型変換と妥当性検査を実行（例: env, log_level, PAPER_FILL_MODE 等）。
  - 対話式設定ウィザード CLI（kabusys.config_setup）
    - .env の作成・更新を対話式に支援。
    - 項目定義（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DB パス / LINE 設定 / LOG_LEVEL / KILL_FLAG_CLEAR_ON_START 等）を提供。
    - 既存 .env の読み込み・値のマスク表示・確認画面・保存機能を実装。
- 設定検証 CLI（kabusys.validate_config）
  - .env と config/*.yaml の起動前チェックを実装。
  - 必須/オプション環境変数の存在確認、プレースホルダ検出（末尾が "_here" や "your_value"）で警告。
  - KABUSYS_ENV 値の妥当性チェックと live 環境での注意喚起ガード。
  - LOG_LEVEL の妥当性チェック。
  - DUCKDB / SQLITE の親ディレクトリ存在チェック（存在しない場合は警告）。
  - config/*.yaml の存在確認と PyYAML が利用可能な場合はパース検証（PyYAML 未インストールならスキップして警告）。
  - --strict オプションで警告を失敗（exit status 1）として扱うモードを追加。
- 実行スクリプト
  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - SystemMonitor のポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値は警告でデフォルトにフォールバック。
    - 監視 DB は環境に関わらず本番 sqlite_path を使用する設計。
    - プロセス優先度を High に設定する処理を呼び出し。
    - 停止フラグ（data/stop_requested.flag）によりループを終了。
  - エンジン起動スクリプト（kabusys.run_execution）
    - ExecutionEngine を起動するためのエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - PID ファイル管理、停止フラグ検出、リソースクローズ処理を実装。
- Execution（発注）コア
  - ExecutionEngine（kabusys.execution.execution_engine）
    - Signal Queue Pull 型の発注エンジンを実装。
    - セッションスケジュール: シグナル処理（8:50-9:10）→ push ドレイン（9:10-15:30）。
    - WebSocket push の受信を別スレッドで行い、_push_queue を経由して同期処理。
    - kill.flag の取り扱い（起動時とループ中の検査）と KILL_FLAG_CLEAR_ON_START のサポート。
    - PID ファイル書き込み・削除処理。
    - Reconciler の起動（設定されている場合）と実行結果ログ。
    - position_entries への書き込み（発注成功時に約定予定日を記録）と失敗時の警告サイレントフォールバック。
    - 監視 DB へ発注イベントのログ記録（MonitoringDB が設定されている場合）。
    - Gate1/2/3 によるリスクチェックのフロー（Gate2 のレート制限リトライ、Circuit Breaker の扱い）。
    - kill_switch による全 active 注文キャンセル処理。
  - OrderRecord（kabusys.execution.order_record）
    - 注文状態を表す OrderState 列挙と状態遷移ロジックを実装。
    - 許容される状態遷移テーブルを定義し、不正遷移時は InvalidStateTransitionError を送出。
    - transition_to による updated_at 自動更新と broker_order_id / filled_qty / avg_fill_price / error_message のオプション更新。
  - OrderManager（kabusys.execution.order_manager）
    - DB（OrderRepository）と組み合わせた外向け注文 API を実装:
      - create_order: signal_id の重複検知（部分ユニーク制約・DB 例外処理含む）と UUID 発番。
      - send_order: クラッシュ安全性を考慮した 2 相永続化フロー（OrderSent 永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 更新）。OrderRejectedError / OrderSentPendingError の扱いも実装。
      - sync_order: broker 側の注文状態取得→内部状態に同期（同一状態でも部分約定情報は更新）。
      - cancel_order: キャンセル不可状態のチェック、broker cancel 呼び出し、Cancelled への遷移。
    - DuplicateOrderError を定義して signal_id 重複を表現。
    - キャンセル不可能な状態セット（Closed, Cancelled, Rejected, Filled）を明確化（設計上の注記あり）。
  - Broker / KabuStation クライアント
    - KabuStationClient（kabusys.execution.kabu_client）
      - kabu station REST API 用の同期クライアントを実装（httpx 使用）。
      - トークン取得の遅延初期化と 401 発生時の再取得・リトライ処理を実装。
      - レスポンス JSON パース失敗やネットワークエラーを BrokerAPIError に変換。
      - ステータスコードマッピング（kabu の状態コード → 内部状態 "open"/"partial"/"filled"/"cancelled"/"rejected"）を定義。
      - 429 を RateLimitError として扱う。
      - stream_push を使った WebSocket 受け取りのため websocket ライブラリ等との連携を想定（push handling は ExecutionEngine 側で行う）。
- 監視・DB 初期化
  - monitoring_db 初期化ユーティリティを run_monitoring/run_execution で使用して監視テーブルの存在を保証。

### Changed
- none （初回リリースのため該当なし）

### Fixed
- none （初回リリースのため該当なし）

### Notes / Implementation details
- .env パーサーはシンプルな実装ながら、引用符・エスケープ・インラインコメントに配慮した設計。
- validate_config は PyYAML が無ければ YAML 内容検証をスキップする（警告を出す）。
- ExecutionEngine の設計はフォールトトレラント性を意識しており、クラッシュ時の注文復旧（OrderSent 残留 → Reconciliation）を考慮した 2 相永続化パターンを採用。
- run_monitoring は監視用プロセスとして本番 sqlite を使用する設計（監視は環境に依らない）。
- 設定値の妥当性検証は Settings のプロパティと validate_config の両方で行われる。Settings は未設定時に ValueError を送出し、CLI 側は警告/エラーを分けて報告する。

今後の予定（例）
- KabuStationClient の WebSocket/stream_push 実装の強化（非同期対応検討）。
- テストカバレッジの拡充（OrderManager / ExecutionEngine の統合テスト）。
- config/*.yaml のスキーマ検証追加（PyYAML 有無に関わらず実行できる形でのバリデーション）。

---
（以上）