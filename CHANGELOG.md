# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、ここに記載した内容はソースコードから推測して作成した変更履歴です。

## [Unreleased]

（現時点で特に未リリースの差分はありません）

---

## [0.1.0] - 2026-04-22

Initial release — 日本株自動売買システム "KabuSys" の最初の公開版。以下の主要機能・実装が含まれます。

### Added
- 全体
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
  - コマンドライン実行可能スクリプト類を提供（モジュール実行：`python -m kabusys.validate_config` / `python -m kabusys.config_setup` など）。

- 設定管理
  - `kabusys.config`
    - プロジェクトルートを `.git` または `pyproject.toml` から自動検出し、CWD に依存しない .env 自動ロードを実装。
    - `.env` と `.env.local` の読み込み順序を実装（OS 環境変数を保護して上書き制御）。
    - .env パーサー強化：
      - `export KEY=val` 形式に対応。
      - シングル／ダブルクォート内のエスケープ処理対応。
      - インラインコメントの扱い（クォート無しの場合の条件付き扱い）。
    - `_require()` による必須環境変数チェック（未設定時に ValueError を送出）。
    - `Settings` クラスを実装し、アプリケーション設定をプロパティ経由で提供（例：`jquants_refresh_token`, `kabu_api_password`, `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, `kill_flag_path`, 各種閾値など）。
    - 環境値検証（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` の検証ロジック）を内蔵。

  - `kabusys.config_setup`
    - 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。
    - 設定項目定義と秘密値のマスク表示、選択肢チェック、既存 .env 読み込み、ファイル書き出しテンプレートを実装。
    - 生成された .env 保存後に `validate_config` での検証を促すメッセージを表示。

  - `kabusys.validate_config`
    - 起動前に環境変数・設定ファイル不備を検出する CLI を追加。
    - チェック内容：
      - 必須環境変数（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）の存在とプレースホルダ値検出。
      - `KABUSYS_ENV` の値検証および `live` 時の注意喚起（本番ガード）。
      - `LOG_LEVEL` の検証（不正値は警告）。
      - DB パス（`DUCKDB_PATH`, `SQLITE_PATH`）の親ディレクトリ存在確認（なければ警告）。
      - `config/*.yaml` の存在確認と、PyYAML が利用可能なら YAML パース検証（PyYAML 未インストール時は検証スキップして警告）。
      - 本番環境時（`KABUSYS_ENV=live`）の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定検出）。
    - 出力レベル別に INFO/WARNING/ERROR を表示。`--strict` フラグで警告も FAIL（exit code 1）扱いにできる。

- 実行/監視スクリプト
  - `kabusys.run_execution`
    - `ExecutionEngine` を組み立てて発注セッションを実行する起動スクリプト。
    - `paper_trading` 環境では専用の paper_trading SQLite DB を使用して本番 DB と完全分離。
    - プロセス優先度（High）設定、PID ファイル書き出し、`stop_requested.flag` による外部停止検出を実装。
  - `kabusys.run_monitoring`
    - `SystemMonitor` のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用する仕様。
    - プロセス優先度（High）、停止フラグ検出、例外時のロギングなどを実装。

- 注文・発注ロジック
  - `kabusys.execution.order_record`
    - 注文状態を列挙する `OrderState`（created, sent, accepted, partial, filled, closed, cancelled, rejected）と許可遷移の定義を追加。
    - `OrderRecord` データクラスを実装。状態遷移検証を行う `transition_to()` を実装し、不正遷移時は `InvalidStateTransitionError` を送出。遷移時に timestamp を更新し、オプションフィールドを更新可能。
  - `kabusys.execution.order_manager`
    - DB（`OrderRepository`）と `OrderRecord` を組み合わせる外向け API を提供：`create_order`, `send_order`, `sync_order`, `cancel_order`。
    - `create_order` は signal_id の重複チェックを行い、重複時は `DuplicateOrderError` を送出。DB の部分ユニークインデックス違反を適切に変換。
    - `send_order` はクラッシュ安全性を考慮した 2 相永続化（OrderSent を永続化 → broker 呼び出し → broker_order_id を保存 → OrderAccepted へ遷移）を実装。`OrderRejectedError`、`OrderSentPendingError` の扱いを実装。
    - `sync_order` は broker からの状態を取得してローカル状態と同期。部分約定の進展はフィールド単位で更新。状態遷移が不正な場合は無視（既終端等）。
    - `cancel_order` は終端状態判定を行い、キャンセル可能な場合に broker API 呼び出しのうえ `Cancelled` へ遷移。

  - `kabusys.execution.execution_engine`
    - Signal Queue Pull 型の発注エンジン `ExecutionEngine` を実装。
    - セッションフロー：シグナル処理（8:50-9:10）→ WebSocket push ドレインループ（9:10-15:30）。
    - 発注ガード（Gate）設計：
      - Gate 1: シグナルレベル検査（`check_signal`）。
      - Gate 2: エグゼキューションレベル検査（レート制限、リトライ最大3回、サーキットブレーカー時はシグナルループ停止）。
      - Gate 3: ドローダウン監視（ポートフォリオ評価に基づき kill_switch 発動）。
    - シグナル処理での実装詳細：
      - `size_multiplier` の適用（BUY のみ、100株単位切捨て）。
      - `DuplicateOrderError` の扱い（重複時はスキップ）。
      - 発注レイテンシ計測、監視 DB へのイベントログ（`monitoring_db` が設定されている場合）。
      - 発注成功時の position_entries への書き込み（duckdb 経由、fill_date は翌営業日を使用）。
    - WebSocket ワーカー（`_websocket_worker`）を別スレッドで起動可能。broker に `stream_push` が無ければスキップ。
    - 起動時リコンシリエーション（`reconciler` が設定されている場合）を実行。
    - kill_switch：全ループ停止と全 active 注文のキャンセル処理を実装。例外別のログハンドリング。

  - `kabusys.execution.kabu_client`
    - kabuステーション REST API クライアント `KabuStationClient` を追加（同期 httpx を使用）。
    - トークン管理（遅延取得・自動再取得）を内部で行い、401 時に再取得＋1回リトライ実装。
    - レスポンス JSON パース失敗やネットワーク/タイムアウト/HTTP ステータス別のエラーを `BrokerAPIError` / `RateLimitError` 等にマッピング。
    - WebSocket（push）処理は `stream_push(on_message, stop_event)` を想定する実装と連携可能。

- リスク管理・再整合（reconciler）・監視
  - RiskManager / Reconciler / MonitoringDB などの利用箇所を想定した組み合わせ実装（`ExecutionEngine` / `OrderManager` 等で利用）。既定の RiskConfig 値が設定されている（例: max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors など）。
  - 監視関連は SQLite（monitoring DB）と DuckDB を併用。

### Changed
- （初リリースのため履歴はなし）

### Fixed
- （初リリースのため履歴はなし）

### Security
- `.env` の取り扱いに関して、`.env` を Git にコミットしないことを README/テンプレートに明示（config_setup のヘッダコメント）。

---

注記:
- 上記はソースコードの実装内容に基づく初期リリースの要約です。より詳細な変更点・設計方針・既知の問題点は各モジュールのドキュメント・コメントを参照してください。