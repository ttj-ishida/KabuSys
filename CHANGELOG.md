# Changelog

すべての重要な変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠します。  

※ 内容はリポジトリ内コードから推測して作成しています。

## [Unreleased]

- ドキュメント化や細かいリファクタ、テストの追加待ち。

---

## [0.1.0] - 2026-04-23

初期リリース。

### Added
- 全体
  - パッケージ初期版公開。モジュール名: `kabusys`、バージョン `0.1.0`。
  - アプリケーション設定管理（src/kabusys/config.py）
    - .env ファイルおよび環境変数から設定を読み込み。自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行う。
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env のパースは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
    - Settings クラスを提供し、各種設定（API トークン、DB パス、監視/閾値、KABUSYS_ENV 等）をプロパティで取得できる。
    - `PAPER_FILL_MODE` の値検証（"instant" / "partial" / "never" / "reject"）を実装。
  - 環境設定ウィザード（src/kabusys/config_setup.py）
    - 対話形式で .env を初期作成 / 更新する CLI を提供。
    - デフォルト値、選択肢、秘密入力（マスク表示）、保存確認機能を備える。
    - 書き出しテンプレートに注意書き（.env を絶対に Git にコミットしない）を含む。
  - 設定検証ツール（src/kabusys/validate_config.py）
    - .env と config/*.yaml の設定不備を起動前に検出する CLI。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）・値のプレースホルダ検出。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（有効な値の列挙）と本番環境（live）向けの注意喚起。
    - DB パスの親ディレクトリ存在チェック（起動時に自動作成される旨の警告）。
    - PyYAML があれば config/*.yaml のパース検証を行い、未インストール時はスキップして警告。
    - `--strict` オプションで警告を FAIL（exit code 1）として扱う。
  - 実行スクリプト
    - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
      - ExecutionEngine を起動するエントリポイント。
      - `paper_trading` 環境では専用の Paper Trading 用 SQLite DB を使用して本番 DB と分離。
      - プロセス優先度設定、PID ファイル管理、停止フラグ（stop_requested.flag）検知機能を実装。
    - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
      - SystemMonitor のポーリングループを実行。`MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で間隔を上書き可能。
      - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。
      - 停止フラグ検知と例外ハンドリング（次のポーリングまで待機）を実装。
  - 実行ロジック（execution パッケージの主要機能）
    - OrderRecord（src/kabusys/execution/order_record.py）
      - 注文状態を表す State Machine を純粋ロジックとして実装（DB には依存しない）。
      - 許可された状態遷移テーブルと InvalidStateTransitionError を提供。
      - transition_to により状態遷移時に updated_at を UTC で自動更新し、関連フィールドを安全に更新可能。
    - OrderRepository / OrderManager（OrderManager の外向き API）
      - signal_id 単位の重複検出（DuplicateOrderError）を実装。
      - create_order: UUID（client_order_id）を採番し OrderCreated を永続化、DB 制約違反の解釈。
      - send_order: 二相永続化の設計（OrderSent を DB に書き込んでから broker 呼び出し、その後 broker_order_id を保存、さらに OrderAccepted へ遷移）によりクラッシュ時に復旧（Reconciliation）可能な設計。
      - OrderSentPendingError の扱い（注文番号は保存するが状態は Sent のまま残し呼び出し元へ伝播）。
      - sync_order: broker 側のステータス照合と状態同期、部分約定の数量/平均価格更新処理。
      - cancel_order: 終端状態の扱い、broker 呼び出しによる取消処理。
    - ExecutionEngine（src/kabusys/execution/execution_engine.py）
      - シグナル読み込み（DuckDB）→ Gate 1/2（リスクチェック）→ 発注ループ（8:50-9:10）、および push ドレインループ（9:10-15:30）というセッション制御を実装。
      - size_multiplier の適用（買いのみ、100 株刻み切り捨て）や Gate によるリジェクトの挙動を実装。
      - レート制限のリトライ、Circuit Breaker が開いた場合の挙動（シグナルループを停止）を実装。
      - 発注成功/保留/失敗でのリスクカウンタ更新、position_entries への約定記録（duckdb）処理。失敗時も発注フローを継続する設計。
      - WebSocket push の受信（broker が stream_push を提供する場合）を別スレッドで行い、受信 payload を処理して同期（sync_order）と Gate 3（ドローダウン監視）評価を行う。
      - Gate 3 が NG の場合は kill_switch を発動して全 active 注文をキャンセル。
      - kill.flag の存在検査と KILL_FLAG_CLEAR_ON_START の挙動（1 ならクリアして起動）を実装。
  - ブローカ / kabu ステーションクライアント（src/kabusys/execution/kabu_client.py）
    - KabuStationClient を実装（同期 httpx Client を使用）。
    - トークン取得と自動再取得、401 リトライ、429 レート制限ハンドリング、ネットワーク/タイムアウト例外の BrokerAPIError 変換を実装。
    - WebSocket 受信用に websocket（別実装）を併用する設計（stream_push を想定）。
  - その他ユーティリティ
    - 監視 DB 初期化ヘルパー（init_monitoring_db の利用）や process priority / logging setup の呼び出しポイントを各 run スクリプトに追加。
    - 設定値に基づく DB パス/PID/Kill Flag 等の path 管理を一元化。

### Changed
- 初版リリースのため、既知の設計決定とデフォルト挙動を明記（例: monitoring は常に本番 sqlite を使用する等）。
- .env 読み込みの優先順位: OS 環境変数 > .env.local > .env（コード設計として明示）。

### Fixed
- N/A（初版のため既知のバグ修正履歴はなし。以降のリリースで細かな修正を追加予定）

### Security
- .env は絶対に Git にコミットしない旨をテンプレートとドキュメントで強調。

---

注記:
- 上記はコードから推測した変更点・機能一覧です。実際のコミット履歴が存在する場合はそれに合わせて更新してください。