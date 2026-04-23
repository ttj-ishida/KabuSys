# Changelog

すべての注目すべき変更点を記録します。
このファイルは Keep a Changelog の方針に準拠しています。

## [0.1.0] - 2026-04-23

### Added
- 初期リリース: KabuSys — 日本株自動売買システムのコア機能を追加。
  - パッケージのバージョンは `__version__ = "0.1.0"`。

- 環境設定 & ロード
  - Settings クラスを追加（`kabusys.config.Settings`）。環境変数からアプリケーション設定を取得するプロパティを提供。
    - J-Quants / kabu API トークン、LINE 通知、DB パス、PID/KillFlag 関連、閾値、環境種別（development/paper_trading/live）などを扱う。
    - `PAPER_FILL_MODE` の妥当性検査（"instant" | "partial" | "never" | "reject"）を実装。
    - `KABUSYS_ENV` / `LOG_LEVEL` の妥当性検査を実装（不正値で ValueError）。
    - paper_trading 環境では専用 SQLite DB を使用する（`paper_sqlite_path`）。
  - 自動 .env ロード実装:
    - プロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を自動読み込み。
    - OS 環境変数を保護するため上書きガードを実装。
    - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサを強化:
    - `export KEY=val` 形式対応、シングル/ダブルクォートの取り扱い（バックスラッシュエスケープ対応）、インラインコメント扱いの細かな仕様に対応。

- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを追加。
    - `.env` の初期作成 / 更新を支援。シークレット項目はマスク表示。
    - 選択肢、デフォルト、説明文を表示。
    - 最終確認後に `.env` を出力する `_write_env` 実装。
    - デフォルト項目例: `KABUSYS_ENV`, `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `DUCKDB_PATH`, `SQLITE_PATH`, `LINE_*`, `LOG_LEVEL`, `KILL_FLAG_CLEAR_ON_START`。

- 設定検証 CLI
  - `kabusys.validate_config` を追加:
    - .env および `config/*.yaml` の起動前検証。必須環境変数チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の値チェック、DB パスの親ディレクトリ存在確認、config YAML ファイル存在確認と PyYAML があればパース検証。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）。
    - 出力に INFO/WARNING/ERROR を表示。`--strict` モードで警告も失敗 (exit 1) とする。

- 実行スクリプト
  - `run_execution.py`（ExecutionEngine 起動スクリプト）を追加:
    - プロセス優先度設定、ログ設定、DB 接続（paper_trading のときは専用 SQLite）、DuckDB 接続。
    - ExecutionEngine の起動とセッション管理（PID ファイル管理、停止フラグ検知）。
    - ExecutionEngine は signal 処理（8:50-9:10）→ push ドレイン（9:10-15:30）というフローを持つ。
  - `run_monitoring.py`（SystemMonitor ポーリングループ）を追加:
    - `MONITOR_POLL_INTERVAL` でポーリング間隔を調整可能（デフォルト 60 秒、不正値はデフォルトにフォールバック）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視 DB は本番 DB を参照）。

- 発注エンジンと関連コンポーネント
  - ExecutionEngine の実装（`kabusys.execution.execution_engine.ExecutionEngine`）:
    - シグナル読み込み（DuckDB）、Gate 1/2（シグナル/実行レベルのリスクチェック）、発注フロー、push ドレイン、Gate 3（ドローダウン監視と kill switch 発動）を実装。
    - WebSocket スレッドで kabu push を受信し内部キューに投入する仕組み（broker が stream_push を持つ場合）。
    - セッション起動時に Reconciler を呼び出すオプションを持つ。
    - PID ファイル書き込み・削除処理、kill.flag の扱い（`KILL_FLAG_CLEAR_ON_START` を尊重）を実装。
    - 発注時の監視 DB へのイベントログ（latency 等）出力を想定するフックを持つ。
  - OrderRecord（`kabusys.execution.order_record`）:
    - 注文状態を表す OrderState 列挙型と許可遷移マップを定義。
    - 状態遷移検証と updated_at 自動更新を行う `transition_to` を提供。無効遷移時は `InvalidStateTransitionError` を発生。
  - OrderManager（`kabusys.execution.order_manager`）:
    - `create_order`（重複チェック、DB 保存、DuplicateOrderError）、`send_order`（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移、OrderRejectedError / OrderSentPendingError などの扱い）、`sync_order`（broker 状態照合と同期）、`cancel_order`（キャンセル不能状態の判定）を実装。
    - 永続性とクラッシュ後復旧を考慮した2相永続化（broker_order_id を先に保存する等）を取り入れ、Reconciliation による回復を想定。
    - キャンセル対象外状態の定義（Filled を含む）を明確化。
  - Broker API / KabuStation クライアント（`kabusys.execution.kabu_client.KabuStationClient`）:
    - httpx ベースの同期 REST クライアント。トークン取得（遅延初期化）、401 発生時のトークン再取得と1回リトライ、429/5xx のエラーハンドリング（専用例外: RateLimitError / BrokerAPIError）を実装。
    - レスポンス JSON パース失敗は例外化。
    - kabu station のステータスコードを内部ステータス（open/partial/filled/cancelled/rejected）へマッピング。
    - 将来的な async 対応を見据えた設計（httpx.AsyncClient への置換で対応可能）。
    - WebSocket（push）受信用の仕組みをサポート（websocket 経由の stream_push を想定）。

- モニタリング / DB 初期化
  - `init_monitoring_db` を呼び出して監視用 SQLite の初期化を保証。
  - Monitoring 系で DuckDB と SQLite の両方を利用。

- ユーティリティ
  - ログ設定やプロセス優先度設定のフックを利用する形で run スクリプトに統合（`setup_logging`, `set_process_priority` を使用する想定）。
  - デフォルトパスの明示（`data/kabusys.duckdb`, `data/monitoring.db`, `data/paper_trading.db` など）。

### Security
- .env ファイルの注意書き（`_write_env` で .env を絶対に Git にコミットしないようコメントで明記）。

### Notes / Usage
- 設定作成の推奨ワークフロー:
  1. python -m kabusys.config_setup で .env を生成
  2. python -m kabusys.validate_config で検証
  3. python -m kabusys.run_execution / python -m kabusys.run_monitoring で実行
- 自動 .env ロードをテスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

### Breaking Changes
- （初回リリースのため該当なし）

---

今後のリリースではテストカバレッジ、ドキュメント強化、非同期クライアント対応、さらなる監視指標やリスク制御の拡充を予定しています。