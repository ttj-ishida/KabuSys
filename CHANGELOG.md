CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-23
--------------------

Added
- 基本機能の初期実装を追加。
  - kabusys.config: アプリケーション設定管理
    - .env / .env.local の自動読み込み機能を搭載（OS環境変数を保護して上書き制御）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - _parse_env_line により export プレフィックス、クォート内のエスケープ、インラインコメントの扱いなどを適切に処理する堅牢な .env パーサーを実装。
    - Settings クラスを提供し、環境変数から型付きで設定値を取得（必須取得時の例外発生、Paper Trading 用 DB パスや fill モードの検証等）。
  - kabusys.config_setup: 対話式 .env 作成/更新ウィザード（CLI）
    - 複数の設定項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）。
    - シークレット項目のマスク表示、選択肢/デフォルト表示、既存 .env の読み込みと Enter による再利用。
    - .env ファイル生成時に「絶対に Git にコミットしないこと」などの注意を付与。
  - kabusys.validate_config: 起動前設定検証 CLI（python -m kabusys.validate_config）
    - 必須環境変数の存在チェックとプレースホルダ検出（"_here" や "your_value" の警告）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検証（有効値の列挙）。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と PyYAML があればパース検証（PyYAML 未インストール時はスキップし警告）。
    - KABUSYS_ENV=live の追加ガード（LINE 設定チェック、KILL_FLAG_CLEAR_ON_START の危険設定検出）。
    - --strict オプションで警告を FAIL（exit(1)）扱いにできる。
  - 実行用スクリプト:
    - run_execution: ExecutionEngine を起動するエントリポイント
      - paper_trading 環境時は paper_trading 用 SQLite を使用して本番 DB と完全分離。
      - プロセス優先度設定、PID ファイル書き込み、停止フラグ検知、DB 初期化処理を実装。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト
      - MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒、値検証あり）。
      - 監視は環境に関係なく本番 sqlite_path を使用する設計。
  - Execution エンジンおよび関連コンポーネント:
    - execution_engine: Signal Queue Pull 型発注エンジンを実装
      - 発注ウィンドウ（8:50–9:10）と push ドレイン（9:10–15:30）を管理。
      - WebSocket push を受け取るスレッド（stream_push を持たない broker はスキップ）。
      - kill_switch ロジック（全 active 注文をキャンセルしてループ停止）。
      - PID ファイル管理、kill.flag の起動時挙動（KILL_FLAG_CLEAR_ON_START による自動クリア対応）。
      - DuckDB への position_entries 更新（発注成功時に entry/sell 日付を記録）。
      - 監視 DB（MonitoringDB）へのトレードイベント記録フック。
    - order_record: 注文状態マシンの純粋なデータモデル
      - OrderState 列挙と許可遷移テーブル（不正遷移で InvalidStateTransitionError を送出）。
      - transition_to メソッドで updated_at の自動更新やオプションフィールド更新を提供。
    - order_manager: OrderRecord と OrderRepository を組み合わせた外向き API
      - create_order: signal_id ベースでの重複検出（DuplicateOrderError）、UUID による client_order_id 採番、SQLite の部分ユニーク制約違反の明示的変換。
      - send_order: クラッシュ耐性を考慮した二相永続化フロー（OrderSent に永続化→ broker 呼び出し→ broker_order_id 保存→ OrderAccepted に遷移）。OrderRejectedError, OrderSentPendingError の扱いを明確化。
      - sync_order: broker 側ステータスから内部状態へのマッピングと部分約定時の差分更新処理。
      - cancel_order: キャンセル不可能状態の判定と broker cancel 呼び出し → Cancelled 遷移の実装。
    - reconciler / risk_manager 用のフック呼び出し（リコンシリエーション・ゲートチェックに対応）。
  - kabu_client: KabuStation REST API クライアント実装（同期 httpx ベース）
    - API トークンの遅延取得と自動再取得（401 時リトライ）。
    - レスポンス JSON パース時の例外変換、429（レート制限）と >=500 のサーバーエラー処理、タイムアウト・ネットワークエラーの BrokerAPIError への変換。
    - kabu の状態コード → 内部ステータスへのマッピング。
    - 将来の async 対応を意識した設計（httpx.Client からの移行が容易）。
  - 監視周り: monitoring_db の初期化呼び出しを組み込み（init_monitoring_db）。
  - プロセス優先度・ロギングセットアップ呼び出しを run_* スクリプトの先頭で実行（utils の関数を利用）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- .env を生成する際にファイルを Git にコミットしない旨の注意を明記。
- シークレット値はウィザード表示時にマスクして表示。

Migration notes / 使用上の注意
- 初回セットアップ:
  1. python -m kabusys.config_setup を実行して .env を生成/更新してください。
  2. python -m kabusys.validate_config で検証を行ってください（--strict で警告も FAIL にできます）。
- Paper Trading を利用する場合は KABUSYS_ENV=paper_trading に設定し、PAPER_TRADING_SQLITE_PATH（オプション）で専用 DB を指定できます。
- kill.flag や KILL_FLAG_CLEAR_ON_START の扱いに注意してください。本番（live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- PyYAML がインストールされていない環境では config/*.yaml のパース検証はスキップされます（validate_config が警告を出します）。YAML 検証を有効にするには PyYAML をインストールしてください。

問い合わせ / 補足
- 実行スクリプトは run_execution.run() / run_monitoring.main() を直接呼ぶか、各モジュールを python -m で起動してください。
- 本 CHANGELOG はコードベースの内容を元に推測して作成したものであり、実際のコミット履歴とは一致しない可能性があります。必要に応じて追記・修正してください。