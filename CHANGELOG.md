KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。
リリースノートは主要な機能追加・変更点・修正を日本語で記載しています。

Unreleased
----------
（現時点の master に未リリースの変更はありません）

[0.1.0] - 2026-04-23
-------------------
Added
- 全体
  - 初回公開（バージョン v0.1.0）。基本的な実行・監視・設定管理・発注ロジックを実装。
  - パッケージ情報: __version__ = "0.1.0" を追加。

- 設定管理 / .env 自動読み込み (src/kabusys/config.py)
  - .env / .env.local ファイルの自動読み込み機能を実装（読み込み順序: OS 環境 > .env.local > .env）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env ファイルのパーサを実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート文字列とバックスラッシュエスケープを正しく解析
    - クォートなし文字列のインラインコメント処理（直前にスペース/タブがある場合のみ '#' をコメントとして扱う）
  - _load_env_file による上書き制御（override, protected）を導入して OS 環境変数の保護に対応。
  - Settings クラスを提供:
    - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）
    - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）
    - env/log_level の検証（不正値は ValueError を送出）
    - paper_trading 用 DB パスの切替プロパティ（paper_sqlite_path）

- 設定ウィザード CLI (src/kabusys/config_setup.py)
  - .env を対話式に作成・更新するウィザードを実装。
  - 必須/任意項目、選択肢、デフォルト値、シークレット表示（マスク）に対応。
  - 既存 .env の読み込み・既存値の再利用、途中キャンセル、確認表示、ファイル書き込みを実装。
  - --env-file オプションで出力先を指定可能。
  - 書き込みされる .env のテンプレートを整備（コメント・セクション付き）。

- 設定検証 CLI (src/kabusys/validate_config.py)
  - .env および config/*.yaml の設定不備を起動前に検出する CLI を実装。
  - チェック項目:
    - 必須環境変数存在検査（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
    - KABUSYS_ENV の妥当性チェック（development/paper_trading/live）
    - LOG_LEVEL の妥当性チェック
    - DUCKDB/SQLITE のパス親ディレクトリ存在チェック
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の危険値検出など）
  - 結果表示（INFO/WARNING/ERROR）と終了コード制御:
    - --strict を指定すると警告も失敗（exit 1）として扱う。

- 実行/監視用エントリスクリプト
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine を起動するエントリポイントを実装。
    - paper_trading 環境では paper_trading 用 SQLite を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検知、PID ファイル管理、プロセス優先度設定を実装。
  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループを起動するスクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）に対応。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する（監視は常に本番 DB 参照）。

- 発注系コアロジック (src/kabusys/execution/*)
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態 OrderState（created/sent/accepted/partial/filled/closed/cancelled/rejected）を列挙。
    - 許可される状態遷移を定義し、transition_to による遷移検証（不正遷移は InvalidStateTransitionError）。
    - transition_to でオプションフィールド（broker_order_id/filled_qty/avg_fill_price/error_message）を更新し、updated_at を UTC 現在時刻に更新。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - create_order: signal_id ごとの重複防止（DB の部分ユニーク制約により DuplicateOrderError を検出・変換）。
    - send_order: クラッシュ耐性を考慮した 2 相永続化フローを実装:
      1) DB 上で OrderSent に遷移してコミット
      2) broker API 呼び出し
      3a) 成功時は broker_order_id を先に永続化（state は Sent のまま）
      3b) OrderAccepted へ遷移して永続化
      - OrderRejectedError は Rejected へ遷移して更新
      - OrderSentPendingError（注文番号は返るが約定情報がないケース）は broker_order_id を保存した上で例外を再送出（Reconciliation 対象）
    - sync_order: broker 側の状態取得を行い DB を同期。filled_qty / avg_fill_price の進行も更新。OrderSent→Filled 系のクラッシュ後復旧のため OrderAccepted を経由して遷移。
    - cancel_order: キャンセル不可能な状態をチェックしてから broker に cancel を呼び、Cancelled へ遷移。
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - Signal Queue Pull 型の発注エンジンを実装（signal 処理 + push ドレインループ）。
    - Gate 1（シグナルレベル）/ Gate 2（エグゼキューションレベル・レート制限）/ Gate 3（ドローダウン監視）を統合。
    - Gate 2 のレート制限は最大 3 回リトライ、Circuit Breaker 検出時はシグナルループを停止。
    - 発注フロー中に遅延計測・監視 DB へのトレードイベントログ（監視 DB が設定されている場合）を記録。
    - position_entries テーブルへの書き込み（BUY のエントリ追加、SELL の sell_date 更新）を実装（発注 pending の扱いに差異あり）。
    - push (WebSocket) 処理: broker が提供する stream_push を利用して受信 payload を内部キューに投入し、broker_order_id → client_order_id を検索して sync_order を呼ぶ。push の有無に依存しない設計。
    - kill_switch: 全ループ停止と全 active 注文のキャンセルを実行。kill_switch は API エラー等を考慮して継続処理する。
    - 起動時に reconciliation を実行可能（Reconciler が設定されている場合）。
    - 起動時の kill.flag 検査と KILL_FLAG_CLEAR_ON_START を考慮した挙動。PID ファイルの書き出し/削除を実装。

- Broker / KabuStation クライアント (src/kabusys/execution/kabu_client.py)
  - KabuStationClient を実装（同期 httpx クライアントを使用）。
  - トークン取得の遅延初期化と 401 リトライロジックを実装（トークン再取得後1回リトライ）。
  - HTTP タイムアウト / ネットワークエラーを BrokerAPIError に変換。
  - 429 は RateLimitError を送出、5xx はサーバーエラーとして扱う。
  - kabu station のステータスコード (1..7) を内部ステータス(open/partial/filled/cancelled/rejected 等) にマッピング。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を利用して監視用 SQLite の初期テーブルを冪等的に保証（run_monitoring / run_execution で使用）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Internal
- モジュール間の責務分離を意識した実装:
  - OrderRecord は純粋なビジネスロジック（DB 未依存）。
  - OrderRepository（SQLite）と OrderManager（状態遷移ロジック）を分離。
  - ExecutionEngine は broker / repo / risk_manager / reconciler を注入してテスト可能設計。
- ロギング・プロセス優先度・PID ファイル・停止フラグなどの運用向け機能を整備。

Notes / Migration
- .env の書式パーサは従来の単純な "key=value" から、クォート・エスケープ・export 形式等を正しく扱うようになっています。既存 .env を手動で変更する必要は基本的にありませんが、特殊文字を含む値はクォートして保存してください。
- validate_config を使って事前に環境設定を検証することを推奨します（python -m kabusys.validate_config）。
- 実行時の監視や本番運用では KABUSYS_ENV=live 設定に伴う注意喚起や KILL_FLAG_CLEAR_ON_START の値に注意してください。

-----