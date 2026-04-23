# CHANGELOG

すべての注目すべき変更点はここに記録します。  
このファイルは Keep a Changelog の慣例に準拠しています。

現在のバージョン: 0.1.0

[Unreleased]

## [0.1.0] - 2026-04-23
初回リリース

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。

- 環境設定 / ロード
  - Settings クラス（kabusys.config）を追加し、環境変数経由で各種設定（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、閾値等）を一元取得可能に。
  - .env ファイルの自動読み込み機能を導入（プロジェクトルートの検出ロジックを使用）。読み込み順序は OS 環境 > .env.local > .env。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパーサーは以下に対応：
    - export プレフィックス（export KEY=val）
    - シングル/ダブルクォート内のエスケープ処理
    - インラインコメント（クォートなしの値では直前に空白がある場合のみコメント扱い）
  - 環境変数取得用ヘルパー `_require()` を導入し、必須変数未設定時に明示的なエラーを発生させる。

- .env ウィザード
  - `kabusys.config_setup` の対話式ウィザードを追加。`.env` の作成・更新を支援する。
  - 秘匿項目は表示時にマスク、デフォルト値・選択肢をサポート。対話終了後にテンプレート形式で `.env` を保存する機能を提供。
  - 書き出しテンプレートにコメントを含め、Git にコミットしない旨の注意を明示。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。`.env` と `config/*.yaml`（存在確認および PyYAML があればパース検証）を起動前に検出。
  - 検証はエラー・警告・情報を収集し出力。`--strict` オプションで警告も失敗扱い（exit code 1）にできる。
  - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）、プレースホルダ値検出、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、`live` 環境向け追加ガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START の警告など）を実装。

- 実行用スクリプト（エンジン・監視）
  - `run_execution.py`：ExecutionEngine の起動用スクリプトを追加。プロセス優先度設定、PID ファイル管理、kill.flag による起動抑止/自動クリア（環境変数による挙動）を実装。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能。Monitoring は環境にかかわらず（paper/live など）本番の sqlite_path を使用する設計。

- Execution 基盤
  - ExecutionEngine（kabusys.execution.execution_engine）を追加：
    - セッション制御（signal 処理ウィンドウ、push ドレイン、session の終了時刻設定）
    - WebSocket push の受信を別スレッドで処理する仕組み（broker の stream_push を使用）
    - kill_switch による全 active 注文キャンセル（外部停止）
    - PID ファイルの書き込み・削除
    - DuckDB からシグナル取得し、position_entries への書き込み（発注成功時に約定日を next_trading_day で算出）
    - 発注遅延（latency）を監視 DB に記録するフック（MonitoringDB が渡された場合）

- 注文管理（Order）
  - OrderRecord（kabusys.execution.order_record）: 注文状態を表す状態機械を導入（列挙型 OrderState と遷移ルール _ALLOWED_TRANSITIONS）。不正遷移は InvalidStateTransitionError を発生。
  - OrderManager（kabusys.execution.order_manager）:
    - create_order：signal_id ごとの重複検出（アクティブ注文が存在する場合は DuplicateOrderError）
    - send_order：クラッシュ耐性を考慮した 2 相永続化戦略を実装（OrderSent を DB に書き出してから broker 呼び出し、broker_order_id を先に保存、続けて OrderAccepted に遷移して保存）。
      - OrderRejectedError のハンドリングは Rejected への遷移と保存。
      - OrderSentPendingError の場合は broker_order_id を永続化した上で OrderSent のまま残し、例外を上位に伝播（Reconciliation 対象）。
    - sync_order：broker 側の状態を照合してローカル状態を更新（部分約定の進行は fill_qty / avg_fill_price を直接更新して最小限の更新を行う）。OrderSent→Filled/PartialFill の直接遷移が発生するケースは OrderAccepted を経由して遷移させる。
    - cancel_order：キャンセル不可能な状態のチェック（Closed/Cancelled/Rejected/Filled はキャンセル不可）を実装。broker_order_id があれば broker.cancel_order を呼ぶ。

- Reconciliation / Risk / Monitoring
  - Execution フローにおいて Reconciler を起動時に実行できる設計（リコンシリエーション結果のログ出力）。
  - RiskManager（概念）を利用した Gate1/2/3 を実装する流れ（シグナル検査 / エグゼキューション検査（rate limit, circuit breaker） / ドローダウン監視）。Gate2 は最大 3 回のリトライ回数を持つ実装。
  - Gate3 が NG の場合は kill_switch を発動して全注文キャンセル。

- Broker クライアント
  - KabuStationClient（kabusys.execution.kabu_client）を追加：
    - httpx（同期クライアント）を使用した REST クライアント実装。
    - トークン取得を遅延初期化し、401 で自動的にトークン再取得して 1 回リトライ。
    - JSON パース失敗／タイムアウト／ネットワークエラーを BrokerAPIError にラップ。
    - 429 を RateLimitError に変換。
    - websocket / push 連携（stream_push）を想定した実装の痕跡を含む。

### Changed
- 設計上の選択
  - paper_trading 環境では SQLite を分離（settings.paper_sqlite_path を使用）して本番 DB と完全に分離する挙動を採用。
  - Monitoring プロセスは KABUSYS_ENV に関係なく本番 sqlite_path を使用する仕様（監視情報は一元管理する意図）。

### Fixed / Hardened
- .env ファイル読み込み時のエラーは警告（warnings.warn）として扱い、処理は継続するように堅牢化。
- `validate_config` における YAML 検証は PyYAML が未インストールの場合はスキップして警告を出すようにした（依存ライブラリに柔軟に対応）。
- `MONITOR_POLL_INTERVAL` の不正値に対してデフォルトへフォールバックし、ログ出力することで ValueError を回避。
- ExecutionEngine の起動時に既存の kill.flag が存在する場合の挙動を明確化（`KILL_FLAG_CLEAR_ON_START=1` で自動クリアするか、そうでない場合は起動拒否）。
- send_order のクラッシュ耐性を強化（broker 呼び出し前後の状態永続化順序を明確化し、Reconciliation により状態回復可能に）。

### Notes / Usage
- 環境の初期化:
  - 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
- 実行:
  - 実行エンジン: python -m kabusys.run_execution
  - 監視ループ: python -m kabusys.run_monitoring
- 開発者向け:
  - 自動 .env 読み込みはパッケージ利用開始時に行われるため、テストから自動ロードを抑止する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

(この CHANGELOG は、ソースコードの内容から推測して作成しています。実際のリリースノートは運用上の決定や変更履歴に基づいて調整してください。)