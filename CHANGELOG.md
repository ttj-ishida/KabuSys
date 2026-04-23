# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して日本語で記載しています。  
以下は与えられたコードベースから推測して作成した変更履歴（初期リリース相当）です。

全体方針: 環境変数 / 設定ファイル管理、実行エンジン、発注フロー、監視、kabu station クライアント、ユーティリティ CLI を整備。安全性（kill flag / PID / 冪等性 / リコンシリエーション）や運用性（ログ・監視・設定ウィザード）に配慮した作りになっています。

## [Unreleased]
- （今後の変更点をここに記載）

## [0.1.0] - 2026-04-23
リリース初版（コードベースから推測）。

### Added
- 環境設定・検証関連
  - config_setup: 対話式ウィザード (python -m kabusys.config_setup) による .env ファイルの生成／更新機能を追加。
    - 複数項目（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DUCKDB_PATH / SQLITE_PATH / LINE 設定 等）を対話形式で設定可能。
    - シークレット値は表示時にマスク。選択肢・デフォルト値・説明を表示。
    - .env の読み取り・既存値の再利用、キャンセル時の挙動をサポート。
  - validate_config: 起動前検証 CLI (python -m kabusys.validate_config) を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML が無ければスキップ）。
    - プレースホルダ値（_here / your_value）検出による警告。
    - --strict モードで警告を失敗扱いにするオプションを追加。

- 環境変数管理
  - config: .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。
    - 読み込み順序: OS 環境 > .env > .env.local (.env.local は上書き)。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションあり。
    - _parse_env_line: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いを備えた堅牢な .env 行パーサを実装。
    - _load_env_file: protected パラメータで OS 環境変数の上書きを防止。
    - Settings クラス: アクセサプロパティで各種設定を提供（トークン・パス・DB パス・ログレベル・KABUSYS_ENV 等）。
      - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
      - paper_trading 用 SQLite パスの分離（PAPER_TRADING_SQLITE_PATH）。
      - kill flag / PID /閾値（CPU/MEM/DISK）設定のプロパティを追加。

- 実行（Execution）コンポーネント
  - run_execution スクリプト: ExecutionEngine 起動用のエントリポイントを追加。
    - paper_trading モード時に専用 SQLite（分離）を使用。
    - プロセス優先度設定、PID ファイル管理、停止フラグ（stop_requested.flag）対応。
  - execution/execution_engine: Signal Queue ベースの発注エンジンを実装。
    - シグナル処理（8:50-9:10）と push ドレイン（9:10-15:30）を分けたフロー。
    - Gate1/Gate2/Gate3 による複数段階リスクチェック（リトライ・サーキットブレーカー対応）。
    - kill_switch 実装: 全 active 注文キャンセルとループ停止。
    - WebSocket push（broker.stream_push）処理、push を受けての同期処理とドローダウン評価。
    - position_entries への約定記録（BUY/Sell の扱い分離、pending の取り扱い）。
    - 発注時のレイテンシ監視を監視DBへ記録するフック（monitoring_db が提供される場合）。

- 発注 / 注文管理
  - execution/order_record: OrderState 列挙型と OrderRecord データクラスを実装。状態遷移検証ロジック（許可遷移テーブル）を追加。
    - transition_to により updated_at 自動更新、broker_order_id/filled_qty/avg_fill_price/error_message の安全な更新。
  - execution/order_manager: OrderManager により OrderRecord と OrderRepository（SQLite）を組み合わせた外向き API を実装。
    - create_order: signal_id 単位での重複防止（DuplicateOrderError）。DB 制約違反を適切にハンドリング。
    - send_order: 2相永続化に近い手順で安全に発注（OrderSent を先に persist → ブローカー呼出 → broker_order_id 永続化 → OrderAccepted 更新）。OrderRejected / OrderSentPending の扱いを明確化。
    - sync_order: broker 側ステータス照合とローカル状態更新（部分約定の増分更新、必要に応じて OrderAccepted を中間に挟む）。
    - cancel_order: 終端状態チェック後に broker cancel を呼び、Cancelled へ遷移。キャンセル不能状態は InvalidStateTransitionError を送出。

- ブローカークライアント
  - execution/kabu_client: KabuStation REST API クライアントを追加。
    - httpx を利用した同期 API 実装、トークンの遅延取得と自動再取得（401 時に1回リトライ）。
    - レスポンス JSON パースエラーやタイムアウト・ネットワークエラーを BrokerAPIError 等にマッピング。
    - status コードマッピング（kabu→open/partial/filled/...）。
    - 429 に対する RateLimitError を区別。

- 監視（Monitoring）
  - run_monitoring スクリプト: SystemMonitor ポーリングループを実装（python -m kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（不正値はデフォルト 60 秒にフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（運用上の注意）。
    - DB 初期化（init_monitoring_db）と DuckDB 接続、停止フラグ検知による安全終了を実装。

- 共通ユーティリティ
  - process_priority ユーティリティを使用して起動時にプロセス優先度を設定する呼び出しを追加（monitoring・execution 起動時）。
  - logging_setup を呼び出してアプリケーション別ログ設定を行う。

### Changed
- プロジェクト構造／起動方針の標準化
  - run_* スクリプト群（monitoring / execution）で同様の起動手順（logging 設定、プロセス優先度設定、DB 初期化、stop flag の尊重）を採用。
  - 設定（Settings）をプロパティ経由で一元管理し、各コンポーネントから参照可能に。

### Fixed / Safety improvements
- 発注のクラッシュ安全性向上
  - send_order の 2 段階永続化（OrderSent の保存 → broker 呼出 → broker_order_id の保存 → OrderAccepted へ遷移）によりクラッシュ時の照合（リコンシリエーション）が可能になる設計を採用。
  - OrderSentPendingError の扱いを定義し、注文番号は保存するが状態は OrderSent のままにして Reconciliation の対象とする。
- リスク管理強化
  - Rate limit / サーキットブレーカーに基づく Gate2 のリトライと停止ロジックを追加。
  - Gate3（ドローダウン）で NG の場合は kill_switch を発動して全 active 注文をキャンセル。
- 運用性向上
  - kill.flag の存在チェックと KILL_FLAG_CLEAR_ON_START による起動時自動クリアオプション。
  - PID ファイルの生成・削除で単一プロセス運用を支援。
  - monitoring のポーリング設定に対する不正値保護（デフォルトフォールバック）。

### Notes / Known limitations
- config/*.yaml のパース検証は PyYAML がインストールされている場合にのみ有効。未インストール時は警告を出してスキップする設計。
- KabuStationClient は同期実装（httpx.Client）で、将来的な async 対応は httpx.AsyncClient への移行が想定されている。
- 一部検証（PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL）は Settings プロパティで ValueError を送出するため、呼び出し側は例外ハンドリングが必要。
- 日付（リリース日はコードからの推測により記載）。

---

この CHANGELOG は提示されたソースコードから実装内容を推測して作成しています。実際のリリースノートとして使用する場合は、添付された変更差分やコミット履歴に基づく確認・調整を推奨します。必要であれば、より細かいチケットや機能ごとの変更履歴に分けて作成できます。