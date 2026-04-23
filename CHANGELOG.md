# Changelog

すべての notable な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

なお、このリリースノートはソースコードから推測して作成しています。実装の目的や挙動についてはコード本体を参照してください。

## [0.1.0] - 2026-04-23

### Added
- 全体
  - 初期パブリックリリース。本パッケージは日本株自動売買システム「KabuSys」のコア機能群を提供します。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 環境 / 設定関連
  - 環境変数・設定管理モジュール（kabusys.config）を追加。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env を自動読み込み（優先度: OS 環境 > .env.local > .env）。
    - .env の自動ロードを `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env のパースを細かく実装（export プレフィックス対応、シングル/ダブルクォート中のエスケープ、インラインコメント処理等）。
    - 必須環境変数取得ヘルパー `_require()` を提供し、未設定時は ValueError を投げる。
    - Settings クラスを提供（環境別判定、ログレベル検証、DBパス、各種しきい値、paper_trading 用 DB パス等）。

  - 対話式設定ウィザード（kabusys.config_setup）を追加。
    - `.env` の初期作成・更新を支援する CLI。
    - 入力項目一覧（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 等）を定義。
    - シークレット入力のマスク表示、選択肢・デフォルト値対応、既存 .env 読み込み、最終確認画面、.env ファイル書き出し機能を持つ。

  - 設定検証ツール（kabusys.validate_config）を追加。
    - .env と config/*.yaml の起動前チェック用 CLI。
    - 必須環境変数未設定の検出、プレースホルダ値の警告、KABUSYS_ENV と LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML がインストールされている場合） YAML パース検証、KABUSYS_ENV=live 時の追加安全チェック（LINE 設定・KILL_FLAG_CLEAR_ON_START）。
    - `--strict` オプションで警告も失敗（exit code 1）扱いにできる。

- 実行スクリプト
  - 実行系エントリ（kabusys.run_execution）を追加。
    - ExecutionEngine を組み立ててセッション実行を行うスクリプト。
    - 環境に応じて paper_trading 用の専用 SQLite を使用（本番 DB と分離）。
    - PID ファイル管理、停止フラグ検出、プロセス優先度設定、DB 接続管理等を実装。

  - 監視系エントリ（kabusys.run_monitoring）を追加。
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境にかかわらず本番 sqlite_path を使用して監視データを扱う。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で調整可能。不正値は警告してデフォルトにフォールバック。

- 発注・状態管理
  - OrderRecord（kabusys.execution.order_record）を実装。
    - 注文状態を列挙する OrderState（created, sent, accepted, partial, filled, closed, cancelled, rejected）と遷移ルールを定義。
    - 状態遷移検証ロジックと更新（updated_at の自動更新、任意フィールドの更新）を実装。
    - 不正遷移時に InvalidStateTransitionError を raise。

  - OrderManager（kabusys.execution.order_manager）を実装。
    - DB に永続化する OrderRepository と OrderRecord を組み合わせた外向け API（create_order, send_order, sync_order, cancel_order）。
    - 重複注文検知（同一 signal_id の active 注文がある場合 DuplicateOrderError を raise）と信頼性を考慮した永続化順序（OrderSent を永続化 → broker 呼び出し → broker_order_id を保存 → OrderAccepted へ遷移）を採用。
    - broker レスポンスに応じて OrderRejectedError, OrderSentPendingError の扱いを実装。
    - broker 側のステータスを内部 OrderState にマッピングして同期処理を行う（部分約定の進行は個別フィールド更新で対応）。

  - ExecutionEngine（kabusys.execution.execution_engine）を実装。
    - Signal Queue Pull 型の発注エンジン。
    - シグナル処理（デイリーの発注ウィンドウ: 08:50–09:10）と WebSocket push ドレイン（09:10–15:30）を統合。
    - Gate ベースのリスクチェック:
      - Gate 1: シグナルレベル検査（check_signal）
      - Gate 2: エグゼキューションレベル検査（レート制限、3 回リトライ、サーキットブレーカー検出）
      - Gate 3: ドローダウン監視（push イベント時に評価、NG なら kill_switch 発動）
    - DuplicateOrderError の取り扱い、API レイテンシ計測と monitoring DB ログ、position_entries 書き込み（買いは追加、売りは売却日更新）、fill_date の計算は次営業日を利用。
    - WebSocket push を受信する別スレッドを持ち、受信 payload を _push_queue に投入してドレイン処理する設計。
    - kill_switch により全 active 注文のキャンセルを実行、強制停止フローを提供。
    - 起動時に kill.flag の存在を検査し、KILL_FLAG_CLEAR_ON_START=1 時は自動クリアするオプションをサポート。
    - PID ファイル生成／削除によるプロセス管理。

  - ブローカークライアント（kabusys.execution.kabu_client）を実装。
    - kabu station REST API クライアント（同期 httpx ベース）。
    - トークン取得の遅延初期化と 401 時の自動再取得（1 回リトライ）。
    - レスポンス JSON パース失敗やネットワーク/タイムアウトを BrokerAPIError に変換。
    - 429 を RateLimitError、5xx を BrokerAPIError として扱う。
    - WebSocket（push）受信用の stream_push インターフェースに対応する想定。

- モニタリング
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）や SystemMonitor 組み込み（run_monitoring, run_execution から利用）。

- ユーティリティ
  - ログ設定セットアップ、プロセス優先度設定ユーティリティを利用する起動フローを採用。

### Changed
- （初回リリースのため "Changed" は特になし）

### Fixed
- （初回リリースのため "Fixed" は特になし）

### Deprecated
- （初回リリースのため "Deprecated" は特になし）

### Removed
- （初回リリースのため "Removed" は特になし）

### Security
- 本番環境（KABUSYS_ENV=live）においてはセキュリティ・運用面の注意喚起を追加（validate_config による警告、KILL_FLAG_CLEAR_ON_START の危険性の警告等）。

---

開発者向けメモ（実装から推測）
- 設計思想は「クラッシュ安全性」と「Reconciliation による復旧可能性」を重視している（OrderSent の永続化→broker 呼び出し→broker_order_id の先保存→OrderAccepted への遷移等）。
- paper_trading（ペーパートレード）モードでは本番 DB と分離して専用 SQLite を使用することでデータ分離を確保。
- .env のパーサは実運用でありがちなクォートやエスケープ、export プレフィックス、行内コメントを丁寧に扱う実装。
- YAML の検証は PyYAML が存在する場合のみ実行されるため、本番で config/*.yaml のフォーマット検査を自動化可能。

（必要であれば、各モジュールごとの変更点や今後の TODO（テストカバレッジ追加、async 対応、外部 API のモック化など）について別途詳細を作成します。）