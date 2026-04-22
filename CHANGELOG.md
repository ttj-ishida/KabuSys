# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-22

Added
- 初期リリースを追加。
- CLI / ユーティリティ
  - kabusys.config_setup: 対話式の .env 作成/更新ウィザードを追加（python -m kabusys.config_setup）。.env テンプレート生成、既存値の読み込み、シークレット項目のマスク表示、確認後の保存をサポート。
  - kabusys.validate_config: 起動前に .env と config/*.yaml の設定不備を検出する検証ツールを追加（python -m kabusys.validate_config）。--strict モードで警告を FAIL 扱いに可能。
  - run_execution/run_monitoring: 実行用エントリポイントスクリプトを追加（python -m kabusys.run_execution / python -m kabusys.run_monitoring）。
    - run_execution: ExecutionEngine を起動するサポート。paper_trading モードでは専用の paper_trading DB を使用して本番 DB と分離。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- 設定管理
  - kabusys.config.Settings: 環境変数経由の設定アクセスを提供（プロパティベース）。KABUSYS_ENV / LOG_LEVEL 等の値検証を実施し、不正値では ValueError を送出。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動で読み込み。読み込み優先順位は OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサー強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしでのインラインコメント処理（直前が空白/タブの場合に '#' をコメントとみなす）
    - ファイル読み込み時の上書き制御（override, protected）
- 実行/監視インフラ
  - PID ファイル、stop flag（data/stop_requested.flag）、kill flag の検査や起動時の kill_flag_clear_on_start 処理に対応。
  - プロセス優先度設定フック（set_process_priority）、ロギングセットアップ呼び出しを導入。
  - DuckDB / SQLite を用いたデータ接続処理を追加（デフォルトパス: data/kabusys.duckdb, data/monitoring.db）。
- 発注系（execution）
  - ExecutionEngine: シグナル取得 → Gate1/Gate2（リスク検査）→ 発注、および push ドレイン（Gate3）まで含むセッション実行ロジックを実装。
    - シグナル処理は target_date に基づく DuckDB クエリからの読み込み。size_multiplier 適用、buy の数量切り捨て（100単位）に対応。
    - WebSocket push を受け取り _push_queue へ投入、ドレイン時に同期処理（sync_order）および Gate3（ドローダウン監視）を実行。
    - セッション開始時に Reconciler を実行（存在する場合）。
  - OrderRecord: 注文状態遷移を管理する純粋ロジックのデータモデルを追加。許容遷移を定義し、不正遷移時は InvalidStateTransitionError を送出。
  - OrderManager: OrderRecord と OrderRepository を組み合わせた外向け API を提供（create/send/sync/cancel）。
    - create_order: signal_id 単位の部分ユニーク制約を想定し、重複時は DuplicateOrderError を送出。
    - send_order: クラッシュ安全性を考慮した 2 相永続化（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 保存 → OrderAccepted へ遷移等）の実装。OrderRejectedError / OrderSentPendingError の扱いを明確化。
    - sync_order: broker 側のステータス照会によりローカル状態を同期（同一状態でも filled_qty/avg_fill_price の更新を反映）。
    - cancel_order: 終端状態ではキャンセル不可（InvalidStateTransitionError）、それ以外は broker cancel を呼び、Cancelled に遷移。
  - RiskManager / Reconciler と組み合わせた Gate チェック、レート制限リトライ、サーキットブレーカー動作を実装（ExecutionEngine 側の制御）。
  - 発注後の position_entries 書き込み（BUY: 発注日の翌営業日を entry_date として挿入、SELL: sell_date 更新）を実装（DuckDB）。
  - 監視DB へのトレードイベント記録機能を ExecutionEngine 側で呼び出すフックを追加（監視DBは任意で注入可能）。
- ブローカークライアント
  - KabuStationClient: kabu ステーション REST API クライアントを実装（httpx 使用）。
    - トークン取得と自動再取得（401 発生時にトークン再取得して再試行）。
    - レスポンス JSON パースエラー / ネットワークエラー / タイムアウトを BrokerAPIError に変換。
    - 429 を RateLimitError として扱う。
    - kabu order status コード → 内部ステータス（open/partial/filled/cancelled/rejected）へのマッピングを実装。
    - WebSocket push ハンドリング（stream_push が存在する broker に対して）。
- 監視（monitoring）
  - SystemMonitor 用の起動ループ、DB 初期化（init_monitoring_db）を実装。監視ループは停止フラグ検知、例外耐性あり。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能。不正値は警告を出してデフォルトを使う。
- その他
  - パッケージ初期バージョンを __version__ = "0.1.0" として設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 補足
- .env は絶対にリポジトリにコミットしないことを README 等で注意する旨を .env 生成ファイルヘッダに明記。
- Settings の一部プロパティ（PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL）は不正値で ValueError を送出するため、起動前に kabusys.validate_config や config_setup による検証を推奨。
- ExecutionEngine・OrderManager の動作は broker 実装（BrokerAPIProtocol）や OrderRepository（SQLite）の正しい実装に依存する。テストや検証時はモックブローカーを利用することを推奨。

--- 

この CHANGELOG はコードベースから推測した変更点を記載しています。必要であればリリース日や項目の詳細（Issue/PR 番号、著者など）を追記します。