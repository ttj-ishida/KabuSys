# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

全ての非破壊的変更はセマンティックバージョニングの原則に従って管理しています。

## [0.1.0] - 2026-04-22

### Added
- 初回公開リリース。
- 環境設定・読み込み
  - Settings クラスを実装し、環境変数から型変換された設定値（パス、閾値、モード等）を提供。
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml により検出し、.env → .env.local の順で読み込む。OS 環境変数は保護）。
  - .env の堅牢なパース実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、コメント処理を正しく処理）。
  - _require() による必須環境変数チェック（未設定時は ValueError を発生）。

- 設定ウィザード CLI
  - config_setup モジュールに対話式ウィザードを追加（python -m kabusys.config_setup）。
  - 対話入力、選択肢、シークレット入力対応、既存 .env の読み込みと Enter による再利用。
  - .env を安全に書き出すテンプレート実装（重要: .env は Git にコミットしない旨のヘッダ付き）。

- 設定検証 CLI
  - validate_config による起動前の設定検証ツールを追加（python -m kabusys.validate_config）。
  - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェックを実施。
  - config/*.yaml の存在確認と（PyYAML があれば）YAML パースチェックを実行。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の注意喚起）。
  - --strict オプションで警告も失敗扱いにできる。

- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。paper_trading モード時は専用 SQLite（paper_trading.db）を使用して本番 DB と完全分離。
  - run_monitoring: SystemMonitor をポーリングする監視プロセス起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用。

- 実行エンジン / 発注フロー
  - ExecutionEngine を実装：シグナル読み取り（DuckDB）、Gate1/2（シグナル・レート等）を通した発注ループ、WebSocket push ドレインループ、Gate3（ポートフォリオ監査）による kill_switch。
  - セッション管理（開始／終了時刻、PID ファイル管理、kill.flag の処理、KILL_FLAG_CLEAR_ON_START による自動クリアオプション）。
  - WebSocket push の受信を別スレッドで行い、push ペイロードを queue に入れて処理する仕組みを提供。
  - 発注時の監視 DB ログ出力（監視 DB が設定されている場合）。

- 発注・状態管理
  - OrderRecord：Order State Machine の純粋なデータモデルを実装。状態遷移ロジック（transition_to）と不正遷移時の InvalidStateTransitionError を提供。
  - OrderManager：外向き API を実装。create_order、send_order、sync_order、cancel_order を提供。
    - create_order は signal_id 重複検出（DB の部分ユニークインデックス違反を DuplicateOrderError に変換）と uuid4 による client_order_id 採番。
    - send_order はクラッシュ耐性のための二相永続化戦略を採用（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted 更新）。
    - OrderRejectedError, OrderSentPendingError 等を適切に処理。OrderSentPendingError は再送出して呼び出し元に伝播。
    - sync_order は broker の状態を取得して DB と同期。部分約定の進行は差分更新で対応し、不正な遷移は無視。
    - cancel_order は終端状態チェック後に broker キャンセルを呼び出し、Cancelled に遷移。

- ブローカークライアント
  - KabuStationClient 実装（httpx を用いた同期 REST クライアント）。
    - トークン取得の遅延初期化と 401 時のトークン再取得＋1回リトライ実装。
    - JSON パース失敗、タイムアウト、ネットワークエラーを BrokerAPIError にマッピング。
    - レスポンスステータス 429 を RateLimitError にマッピング。
    - kabu ステーションの内部状態コード（1..7）→ open/partial/filled/cancelled/rejected へのマッピングを提供。
    - 将来の async 対応を見据えた構成（httpx.Client を使用）。

- リスク管理・リコンサイル（骨組み）
  - RiskManager / Reconciler の利用点を ExecutionEngine に組み込み。Gate チェック・レートリミット回避・リコンシリエーション呼び出しポイントを実装。

- DB 初期化 / 監視
  - init_monitoring_db を呼ぶことで SQLite の監視テーブルが存在することを保証する処理を追加（冪等）。

### Changed
- プロジェクトの設定読み込み仕様を明確化：
  - OS 環境変数は保護され、.env.local は .env を上書きする（override）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を追加。

- ExecutionEngine の発注・監視フローの挙動整理：
  - 発注のクラッシュ耐性（OrderSent 残存、broker_order_id 永続化）に関する設計をコードコメント・実装に反映。
  - Paper trading 向けに DB を分離する挙動を明示（paper_sqlite_path を使用）。

### Fixed
- .env パーサーの細かな取り扱いを改善（クォート内のバックスラッシュエスケープ処理やインラインコメントの扱い）。
- run_monitoring の MONITOR_POLL_INTERVAL が 0 以下の場合に発生しうる time.sleep の ValueError を防ぐため、不正値はデフォルトにフォールバックするように修正。

### Notes / その他
- デフォルトパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - PID / Kill Flag などのファイルは data/ 以下に配置される想定。
- 本番環境（KABUSYS_ENV=live）の起動時は特に注意（LINE 通知の未設定や KILL_FLAG_CLEAR_ON_START の誤設定に対する警告あり）。
- YAML の内容検証は PyYAML がインストールされている場合のみ行う（未インストール時は警告）。

---

今後の予定（例）
- async 対応の Broker client（httpx.AsyncClient）への移行検討。
- より詳細な監視イベントやメトリクス出力の強化。
- Reconciler の堅牢化と自動修復能力の拡張。