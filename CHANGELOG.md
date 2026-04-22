CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従っています。  
セマンティックバージョニングを採用しています。

Unreleased
----------

- （現在のブランチに未リリースの変更はありません）

0.1.0 - 2026-04-22
-----------------

Added
- 初回リリース: KabuSys v0.1.0 を公開。
- 実行エントリ & デーモン化スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度設定、PID ファイル管理、停止フラグ検出、paper_trading の DB 分離に対応。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を変更可能。
- 設定管理
  - config.Settings: 環境変数と .env の読み込み／取得ロジックを提供。自動 .env ロード（.env, .env.local）/ 無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）に対応。
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加（secret 値のマスク表示、選択肢・デフォルト対応）。
  - validate_config: .env および config/*.yaml の起動前検証ツールを追加。--strict オプションで警告を失敗扱いにできる。
- 発注／実行基盤
  - ExecutionEngine: シグナル読み取り → Gate1/Gate2 によるリスクチェック → 発注 → push drain のフローを実装。シグナル処理期間（デフォルト 8:50–9:10）とマーケットクロージャ（15:30）に従う実行モデルを実装。
  - OrderRecord: 注文状態（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）を表す状態機械（State Machine）と遷移検証を実装。InvalidStateTransitionError を導入。
  - OrderManager: OrderRecord と OrderRepository を組み合わせた外向き API を実装（create_order, send_order, sync_order, cancel_order）。重複注文検出（DuplicateOrderError）、送信の 2 段階永続化（クラッシュ耐性）や OrderSentPending の取り扱いを実装。
  - ExecutionEngine 内での発注にあたって、API レイテンシ計測・監視 DB へのログ（任意）・position_entries への記録を実装。
  - Reconciler の起動フックを追加し、起動時にリコンシリエーションを実行できるようにした。
  - kill_switch 実装: 全 active 注文のキャンセルとループ停止を行う安全機構を提供。
- Broker クライアント
  - KabuStationClient: kabu ステーション REST API（同期 httpx ベース）クライアントを実装。トークンの遅延取得・自動再取得（401 リトライ）、HTTP エラーに対する例外化（RateLimitError / BrokerAPIError）、Order 状態コード→内部ステータスマッピングを実装。
  - BrokerClientFactory（参照）により、KABUSYS_ENV に応じたブローカー（実ブローカー / Mock）選択が可能な構成を想定。
- 監視 (Monitoring)
  - monitoring_db.init_monitoring_db 呼び出しにより、監視用 SQLite DB の初期化を保証（冪等）。
  - SystemMonitor 組み込み（run_monitoring で利用）。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
- ユーティリティ
  - .env パーサ：クォートあり/なしの処理、エスケープ、行内コメントの取り扱いを実装。export KEY=val の形式もサポート。
  - パス検証・DB パス確認ロジック（DUCKDB_PATH / SQLITE_PATH）の検出用ユーティリティ。
  - ログレベル・環境値の検証（有効な値セットの制約）。
  - プロセス優先度設定（set_process_priority） / ロギング初期化（setup_logging）呼び出しポイントを各起動スクリプトで利用。

Changed
- （新規リリースにつき大きな API 変更はなし。内部挙動や設計に関する注記は下記を参照）

Fixed
- N/A（初回リリースのため既知の修正は無し）

Security
- .env は絶対に Git にコミットしない旨を config_setup の出力ヘッダに明記。
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を明示し、validate_config で未設定を検出するようにした。

Notes / Important configuration & migration notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。Settings の該当プロパティは未設定時に ValueError を送出する。
- KABUSYS_ENV:
  - 有効な値: development, paper_trading, live。Settings.env は不正値で例外を出す。validate_config でも不正値はエラーとして検出される。
  - paper_trading 時は SQLite DB を paper_trading 用に分離（PAPER_TRADING_SQLITE_PATH / paper_sqlite_path）。
  - live モードでは LINE 通知関連（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）や Kill Switch 設定のチェックを validate_config が行い、警告を出す。
- Kill Switch:
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 の場合、既存の kill.flag を自動クリアして起動する（注意: 本番では 0 を推奨）。
- 発注の耐障害性:
  - send_order の実装はクラッシュ時の不整合を最小化するよう 2 段階の DB 更新を行う。OrderSent のまま残るケースや broker_order_id のみが残るケースを Reconciler / sync_order で補正可能にしている。
- ログレベル設定:
  - LOG_LEVEL は "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL" を想定。validate_config で不正値は警告、Settings.log_level は不正値で例外。
- YAML 検証:
  - validate_config は PyYAML が利用可能な場合に config/*.yaml のパース検証を行う。PyYAML 未インストール時はスキップして警告を出す。
- WebSocket push:
  - broker が stream_push を持つ場合に ExecutionEngine が別スレッドで受信し、push を _push_queue 経由で処理する（_handle_push で sync_order と Gate3 の評価を実施）。
- 注意:
  - このリリースは初期実装のため、詳細な運用検証・負荷試験を推奨します。特に本番環境（KABUSYS_ENV=live）では LINE 通知や Kill Switch の設定を確認し、validate_config を実行してから起動してください。

Contributing
- バグ報告・改善提案は issue を立ててください。プルリクエストはテスト付きで歓迎します。

LICENSE
- 各ファイルのヘッダやプロジェクトルートの LICENSE を参照してください。