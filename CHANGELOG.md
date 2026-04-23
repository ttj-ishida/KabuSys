CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。
フォーマットは "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-04-23
-------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基盤機能を追加。
- 設定関連 CLI/ユーティリティを追加:
  - kabusys.config_setup: 対話式ウィザードで .env の作成・更新を支援する CLI。
    - 複数の設定項目定義（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン等）。
    - シークレット項目は表示をマスク。保存前に確認プロンプトを表示。
    - .env の既存値読み込み・上書きロジックを備える。
  - kabusys.validate_config: 起動前に .env および config/*.yaml の基本チェックを行う CLI。
    - 必須環境変数の存在チェック、プレースホルダ値の検出（例: "..._here", "your_value"）で警告。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、live 環境時の追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START 等）。
    - config/*.yaml の存在確認と PyYAML があればパース検証。
    - --strict オプションで警告を FAIL（exit code=1）扱いにできる。
- 環境設定・読み込み機能を追加:
  - kabusys.config.Settings: 環境変数を抽象化して提供する設定オブジェクト。
    - 自動 .env 読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env / .env.local の読み込み順（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - _load_env_file による保護された上書き（OS 環境キーを保護）と override オプション。
    - 各種プロパティ提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, duckdb/sqlite パス, PID/KILL フラグパス, スロットル閾値等）。
    - PAPER_FILL_MODE の検証（"instant","partial","never","reject" を有効値として検証）。
- 実行系・監視関連のエントリポイント追加:
  - run_execution: ExecutionEngine を起動するスクリプト。
    - paper_trading 時は専用 SQLite（paper_trading.db）を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検知、スレッドによる実行ループ。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒。無効値はフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
- 発注エンジンと注文管理コア:
  - execution.ExecutionEngine: シグナルプル型発注エンジンを実装。
    - シグナル処理ウィンドウ（デフォルト 08:50-09:10）、WebSocket push ドレインループ（09:10-15:30）。
    - Gate1/2/3 によるリスクチェック連携（RiskManager）。
    - size_multiplier の適用（BUY のみ）、position_entries の DuckDB 書き込み処理（ON CONFLICT DO NOTHING 等）。
    - WebSocket からの push を _push_queue に投入し同期処理で注文同期 + Gate3 チェックを実行。
    - kill_switch による全 active 注文のキャンセル処理と停止フラグ管理。
  - execution.order_manager.OrderManager:
    - create/send/sync/cancel の外向き API を提供。
    - create_order で signal_id の重複を検出して DuplicateOrderError を送出。
    - send_order はクラッシュ耐性を考慮した 2 相永続化フローを実装（OrderSent 保存 → broker 呼出 → broker_order_id 保存 → OrderAccepted）。
    - OrderSentPendingError の扱い（broker が注文番号を返すが約定しないケース）に対応し、DB に broker_order_id を残して呼び出し元へ伝播。
    - sync_order により broker 側状態に基づく同期処理（部分約定の更新、OrderSent→Filled のような直接遷移の補正）。
    - cancel_order は終端状態の判定（キャンセル不可状態は InvalidStateTransitionError を発生）と broker cancel 呼出しを実行。
  - execution.order_record.OrderRecord:
    - 注文状態を列挙した OrderState と許容遷移テーブルを実装。
    - transition_to により遷移検証と updated_at 自動更新を実行。InvalidStateTransitionError を定義。
- broker クライアント:
  - execution.kabu_client.KabuStationClient:
    - httpx 同期クライアントを使った kabu station REST API 実装。
    - Token の遅延取得・自動再取得（401 時に再取得してリトライ）。
    - レスポンス JSON パース失敗やタイムアウト/ネットワークエラーを BrokerAPIError にラップ。
    - 429/5xx のステータスを専用例外（RateLimitError / BrokerAPIError）として扱う。
    - kabu ステータスコード → 内部ステータスマッピングを追加（1..7 => "open","partial","filled","cancelled","rejected" 等）。
- 監視 DB 連携:
  - 監視系コードから監視 DB（SQLite）への初期化・書き込み処理を追加（init_monitoring_db, MonitoringDB.log_trade_event 呼び出し箇所）。
- ユーティリティ改善:
  - .env パーサーの強化: export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの取り扱い（クォート有無で動作を分ける）。
  - ファイル入出力でのエラーハンドリング（.env 読み込み失敗時の warnings.warn）。
  - stop/kill フラグの検出や KILL_FLAG_CLEAR_ON_START の挙動を明確化。

Changed
- デフォルトパスと環境変数のデフォルト値を一元化:
  - DUCKDB_PATH デフォルト: data/kabusys.duckdb
  - SQLITE_PATH デフォルト: data/monitoring.db
  - KABU_API_BASE_URL デフォルト: http://localhost:18080/kabusapi
- validate_config の出力を INFO/WARNING/ERROR に分類して分かりやすく表示。終了コードの判定ロジックを整備（errors→exit 1、warnings + --strict → exit 1）。
- ExecutionEngine の起動順序と安全対策を明確化:
  - 起動時に最初にプロセス優先度を設定。
  - kill.flag の存在時の挙動（KILL_FLAG_CLEAR_ON_START=1 時はクリアして起動可能、そうでなければ起動拒否）。
  - PID ファイルの書き込みと終了時の削除を実装。

Fixed
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）の場合に ValueError を回避してデフォルトにフォールバックするように修正。
- .env 読み込みで OS 環境変数を誤って上書きしないよう protected 引数を導入。
- send_order のクラッシュケースに対して DB に broker_order_id を残す二相永続化を導入し、リコンシリエーションでの復旧を容易にした（Issue #32 に対応する設計）。
- sync_order が同一状態でも部分約定の進行（filled_qty / avg_fill_price の変化）を検出して更新するよう改善。
- WebSocket の未実装機能を持つ broker を安全にスキップするチェックを追加（hasattr(stream_push)）。

Notes / その他
- settings.env の検証は Settings プロパティ側でも行うため、設定値の不整合は早期に発見できる設計になっています（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の検証）。
- 実運用では .env を Git 管理に入れないこと（config_setup にも警告コメントを出力）。
- 今後の課題: 非同期対応（httpx.AsyncClient への切替）、より詳細な監視メトリクスの追加、テストカバレッジの拡充。

---