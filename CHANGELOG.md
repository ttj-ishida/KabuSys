# CHANGELOG

この CHANGELOG は Keep a Changelog の形式に準拠します。  
リリースに含まれる主な変更点は、コードベースから推測して記載しています。

すべての注記は日本語で記載しています。

## [Unreleased]

- ドキュメント化や小さな改善（将来のリリースで詳細を追加予定）。

---

## [0.1.0] - 2026-04-22

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定管理（kabusys.config）
  - .env 自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - .env 行パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - _load_env_file により既存環境変数保護（protected）をサポート。
  - Settings クラスを実装し、環境変数から typed なプロパティを提供：
    - J-Quants / kabu API 用の必須トークン取得（未設定時は ValueError）。
    - DB パス（DuckDB / SQLite / Paper trading 用）や PID/kill flag パス等の Path 型プロパティ。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）。
    - 環境（KABUSYS_ENV）・LOG_LEVEL のバリデーションと is_live / is_paper / is_dev ヘルパ。
    - CPU / memory / disk のしきい値プロパティ。

- 環境設定ウィザード CLI（kabusys.config_setup）
  - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
  - ウィザードは既存の .env を読み込み、既存値を Enter で再利用できる。シークレットはマスクして表示。
  - .env を安全に書き出す `_write_env` を実装（テンプレート化されたコメント付き）。
  - デフォルト値、選択肢、説明テキストを含む設定項目定義を提供。
  - 中断（Ctrl+C 等）時の挙動と確認プロンプトを実装。

- 設定検証ツール CLI（kabusys.validate_config）
  - .env と config/*.yaml の起動前検証 CLI を提供（python -m kabusys.validate_config）。
  - 必須環境変数チェック、placeholder 値チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェックを実装。
  - config/*.yaml の存在確認と、PyYAML があればパース検証を実施（未インストール時は警告スキップ）。
  - KABUSYS_ENV=live のときの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）。
  - 出力は INFO / WARNING / ERROR を列挙し、--strict オプションで警告を FAIL 扱いにする。

- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - paper_trading モード時は paper DB を使用して本番 DB と分離。
    - プロセス優先度を設定し、PID ファイル管理、停止フラグ検知、DB 接続の初期化を行う。
  - run_monitoring: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - 環境にかかわらず本番 sqlite_path を使用して監視を行う。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値はデフォルト 60 秒にフォールバック）。
    - 停止フラグ検知時の適切なクリーンアップを実装。

- Execution（発注）コンポーネント
  - OrderRecord（kabusys.execution.order_record）
    - 注文状態を表す OrderState 列挙型（created / sent / accepted / partial / filled / closed / cancelled / rejected）。
    - 許容される状態遷移テーブルと、遷移チェックを行う transition_to()。不正遷移は InvalidStateTransitionError を送出。
    - Record は純粋なビジネスロジックで DB には触れない設計。
  - OrderRepository（参照されるが実装ファイルはここから推測）と組み合わせる OrderManager を実装（kabusys.execution.order_manager）。
    - create_order: signal_id の重複チェック（DB/メモリ両面）を行い、重複時は DuplicateOrderError を送出。client_order_id は UUID4 を採番。
    - send_order: クラッシュ耐性を考慮した2相的な永続化フローを実装（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を保存 → OrderAccepted に遷移）。
      - OrderRejectedError の場合は Rejected に遷移。
      - OrderSentPendingError（注文番号は発行されたが約定しないケース）を適切に扱い、broker_order_id を保存して例外を再送出。
      - その他の例外は捕捉せず OrderSent のまま残す（後で list_uncertain 等で検出する設計）。
    - sync_order: broker の get_order_status による同期。broker が返すステータスを内部 OrderState にマッピングして状態遷移や filled_qty/avg_fill_price の更新を行う。OrderSent→Filled/Partial を直接遷移不可として OrderAccepted を経由して整合。
    - cancel_order: 終端状態の場合は InvalidStateTransitionError を送出。broker_order_id がある場合は API にキャンセルを投げた上で Cancelled に遷移。
    - cancel の対象不可状態セットを明確に定義（Closed / Cancelled / Rejected / Filled）。
  - ExecutionEngine（kabusys.execution.execution_engine）
    - Signal Queue Pull 型の発注エンジンを実装。
    - セッションのライフサイクル（signal_send_start / signal_send_end / market_close）に基づく処理。
    - kill.flag の検査と KILL_FLAG_CLEAR_ON_START の振る舞いを実装（起動時）。
    - PID ファイル作成/削除を実装。
    - WebSocket プッシュの受信を別スレッドで実施し、_push_queue を介してドレインする仕組みを導入。
    - _process_signals() に Gate 1（シグナルレベル）, Gate 2（実行レベル・レート制限）, Gate 3（ドローダウン監視）の検査を実装し、失敗時は適切にスキップまたは kill_switch を発動。
    - size_multiplier の適用（BUY のみ。最小単位は 100 株）。qty が 0 の場合はスキップ。
    - 発注後に position_entries テーブルへ書き込み（fill_date は next_trading_day を使用）し、失敗しても発注フローは継続。
    - 監視 DB（MonitoringDB）への発注イベント記録を行う（監視 DB 書き込み失敗は警告で許容）。
    - kill_switch を実装し、全 active 注文のキャンセルを試みる（cancel_order のエラー種別ごとにログ/挙動を分岐）。
    - WebSocket が利用できない broker の場合は警告を出してスキップ。
    - run_session において起動時に Reconciler を実行してリコンシリエーションを行う（存在すれば）。

- Broker クライアント（kabusys.execution.kabu_client）
  - KabuStation REST API クライアントを実装（同期 httpx クライアントを使用）。
  - トークン取得の遅延初期化とトークン失効時の自動再取得を実装（_get_token）。
  - 認証付きリクエスト処理で 401 発生時にトークン再取得して 1 回リトライする挙動を実装。
  - HTTP ステータスに応じた例外処理を実装（401 / 429 / >=500 等 → BrokerAPIError / RateLimitError）。
  - kabu station の注文状態コードを内部ステータス文字列にマッピングするテーブルを定義。
  - レスポンス JSON パースエラーは BrokerAPIError に変換。

- 監視周り
  - monitoring 用の DB 初期化関数 init_monitoring_db（モジュール参照）を起動スクリプトで呼び出し、監視テーブルの存在を保証。
  - run_monitoring に SystemMonitor を利用したポーリングループを実装（監視処理の例外はロギングして次ポーリングに進む）。

- ユーティリティ
  - プロセス優先度設定（set_process_priority）の呼び出しを起動時に実行（monitoring / execution）。
  - logging セットアップ（setup_logging）の利用とログレベル管理。
  - stop_requested.flag / execution.pid 等のファイルベースの停止・PID 管理を採用。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

---

注意:
- 記載はソースコードからの推測に基づいており、実際のリリースノートや設計意図と差異があり得ます。必要であれば、特定の機能についてのより詳しい説明や、実装箇所の抜粋を含めた追記を行います。