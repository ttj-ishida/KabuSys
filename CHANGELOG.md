# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
慣例に従い、リリース日付は本ファイル作成日を使用しています。

フォーマットの説明・ガイドライン: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（今後の変更をここに記載）

---

## [0.1.0] - 2026-04-22

初期リリース。KabuSys のコア機能（設定管理・起動スクリプト・発注エンジン・監視・ブローカークライアント等）を実装。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。
  - プロジェクト構成に応じた自動 .env ロード機能を実装（`.env`, `.env.local`、OS 環境変数保護、`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化）。
  - .env の行を堅牢にパースするロジックを追加（`export ` プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメントの扱いなどに対応）。
- 設定・CLI
  - `kabusys.config.Settings` クラスを導入し、環境変数から型安全に設定値を取得可能に。
    - 必須項目 (`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`) は未設定時に例外を送出する `_require` 実装。
    - 環境種別 (`KABUSYS_ENV`)、ログレベル (`LOG_LEVEL`)、データベースパス、kill flag 等のプロパティを提供。
    - Paper Trading 用の分離された SQLite パスと `PAPER_FILL_MODE` の検証実装。
  - 対話式環境設定ウィザード `kabusys.config_setup` を実装。
    - `.env` の初期作成・更新を対話形式で支援。
    - シークレット項目のマスク表示、選択肢のバリデーション、保存プレビューを提供。
  - 設定検証 CLI `kabusys.validate_config` を実装。
    - .env および `config/*.yaml` の存在・基本検証、必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリチェック、live 環境向け追加ガード（LINE 通知、kill flag 設定など）。
    - `--strict` オプションで警告を失敗扱いにするモードを提供。
    - PyYAML が未インストールの場合は YAML 内容チェックをスキップして警告。
- 実行・監視スクリプト
  - `run_execution.py` を実装し、ExecutionEngine を起動するエントリポイントを提供。
    - Paper trading の場合は専用 SQLite（`paper_sqlite_path`）を使用して本番 DB と分離。
    - プロセス優先度設定（`set_process_priority("high")`）、PID ファイル作成、停止フラグ検知に対応。
    - データベース接続（SQLite / DuckDB）確立とクリーンアップ。
  - `run_monitoring.py` を実装し、SystemMonitor のポーリングループ起動を提供。
    - 環境にかかわらず本番用 sqlite_path を使用して監視を実行。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（不正値はデフォルトにフォールバック）。
- Execution エンジン（発注ロジック）
  - `execution.execution_engine.ExecutionEngine` を実装。
    - シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）のセッション制御。
    - Start/Stop の論理、PID ファイル管理、kill flag の扱い、kill_flag_clear_on_start による起動時の自動クリアオプション。
    - シグナルの読み出し（DuckDB）、サイズ補正、Gate 1/2/3 による多段的リスクチェック（Gate 1: シグナル、Gate 2: 実行レート制限、Gate 3: ドローダウン監視）。
    - 発注時のレイテンシ計測と監視DBへの記録（可能な場合）。
    - WebSocket push の受信を別スレッドで処理し、push ペイロードから order_id を検出して同期処理を行う。
    - 全 active 注文のキャンセルを行う kill_switch 実装。
  - `execution.order_manager.OrderManager` を実装。
    - OrderRecord（状態機械）と OrderRepository（SQLite）を組み合わせ、create/send/sync/cancel 操作を提供。
    - send_order の耐障害性を考慮した 2 相的永続化（OrderSent 保存 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 更新）を実装し、クラッシュ時に Reconciliation で回復可能な設計。
    - broker からの各種例外（OrderRejectedError / OrderSentPendingError）に対する個別ハンドリング。
    - 同一 signal_id の重複注文を検出して `DuplicateOrderError` を投げる仕組み。
  - `execution.order_record.OrderRecord` と状態機械を実装。
    - 定義済みの OrderState 列挙と許容遷移マップを提供。
    - 遷移検証（InvalidStateTransitionError）と追加フィールド（broker_order_id、filled_qty、avg_fill_price、error_message）の安全な更新を実装。
  - ExecutionEngine と連携する Reconciler/RiskManager/OrderRepository の呼び出し点を整備（実体は別モジュール）。
- Broker クライアント
  - `execution.kabu_client.KabuStationClient` を実装（httpx 同期クライアント）。
    - トークン取得の遅延初期化と自動再取得（401 時にリトライ）を実装。
    - httpx のタイムアウト・ネットワーク例外を BrokerAPIError に変換して扱う。
    - レスポンス JSON の堅牢なパース処理とステータスコードに基づくエラー分類（401/429/5xx 等）。
    - kabu station の状態コードから内部ステータス文字列へのマッピングを提供。
    - WebSocket push（stream_push）機能に対応する設計（stream_push が存在しない broker でも安全に起動可能）。
- 監視・DB
  - Monitoring 初期化ユーティリティ `monitoring.monitoring_db.init_monitoring_db` を使用して監視テーブルを確実に作成。
  - 発注時に position_entries テーブルへエントリを記録し、BUY/Sell の扱いを分離（SELL は pending の場合は記録しない等）。

### Changed
- （初期リリースにつき該当なし）

### Fixed
- （初期リリースにつき該当なし）

### Security
- 環境変数ファイル（.env）をデフォルトで Git にコミットしないことを README/生成ファイルヘッダで注意喚起。

### Notes / Migration
- デフォルトの設定・パスはローカル開発向け（`KABUSYS_ENV=development`、`DUCKDB_PATH=data/kabusys.duckdb`、`SQLITE_PATH=data/monitoring.db`）。本番運用時は `.env` を作成して `kabusys.config_setup` を利用してください。
- 本番（live）環境では `KILL_FLAG_CLEAR_ON_START` を誤って `1` にしないよう注意してください（自動クリアは危険）。
- Paper Trading は本番 DB と完全分離されるよう専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用します。過去の DB を上書きしないよう注意してください。
- `validate_config` を起動して設定検証（`--strict` オプションあり）を推奨します。
- PyYAML がインストールされていない環境では `config/*.yaml` の内容検証をスキップします（警告が出ます）。YAML 検証を行いたい場合は PyYAML を追加してください。

---

開発・運用に関する問い合わせや不具合は issue を立ててください。