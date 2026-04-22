# Changelog

すべての注目すべき変更点をここに記録します。フォーマットは Keep a Changelog に準拠します。

なお、このファイルはリポジトリの現状（初回リリース相当）からコード内容を推測して作成しています。

## [0.1.0] - 2026-04-22

### Added
- 基本パッケージの初期実装を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`

- 設定管理
  - src/kabusys/config.py
    - .env ファイル（および環境変数）から設定を読み込む Settings クラスを実装。
    - 自動ロードロジック:
      - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用）。
    - .env パーサーは以下をサポート:
      - export プレフィックス（`export KEY=val`）
      - シングル/ダブルクォートを考慮した値（バックスラッシュエスケープ対応）
      - クォートなしでのインラインコメント処理（`#` 判定は直前が空白/タブの場合のみ）
    - 必須設定取得用のヘルパ `_require`（未設定時は ValueError を送出）。
    - 各種設定プロパティ:
      - J-Quants / kabu API トークンやパスワード、DB パス、PID / kill flag パス、閾値、環境（KABUSYS_ENV）やログレベル等。
      - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）。不正値は ValueError。
      - KABUSYS_ENV / LOG_LEVEL のバリデーション。

- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 秘匿項目は表示をマスク（****）。
    - 選択肢/デフォルト提示、既存 .env の読み込み再利用機能。
    - .env 書き込みフォーマット（コメント付きテンプレート）。書き込み後に validate_config の実行を推奨。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env と config/*.yaml（想定ファイル群）の存在・形式を起動前に検証する CLI。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - プレースホルダ検出（末尾が "_here" / 値が "your_value" の警告）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検査（許容値リスト）。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と（PyYAML がインストールされている場合の）パース検証。PyYAML 未インストールならパース検証をスキップして警告を出力。
    - KABUSYS_ENV=live の追加ガード:
      - LINE 通知設定未設定の警告、KILL_FLAG_CLEAR_ON_START=1 の危険性警告など。
    - 出力カテゴリ: INFO / WARNING / ERROR。--strict フラグで警告も失敗扱いにできる（exit 1）。

- 実行エントリ / デーモン類
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプト。
    - プロセス優先度を "high" に設定（起動時）。
    - paper_trading 環境では paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 監視 DB 初期化処理（init_monitoring_db）を呼び出す。
    - 停止フラグ（data/stop_requested.flag）検出による起動抑止 / 停止処理。

  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60 秒、0 以下はデフォルトにフォールバックして警告）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検出でループ終了。例外はログに出力してループ継続。

- 実行エンジン / 発注関連
  - src/kabusys/execution/execution_engine.py
    - Signal Queue Pull 型の ExecutionEngine を実装（セッション運用の流れを実装）。
    - EngineConfig により発注窓口・締切・マーケットクローズ時間を指定可能（デフォルト: 8:50〜9:10 発注、15:30 終了）。
    - run_session の全体フロー:
      - 起動時リコンシリエーション（Reconciler があれば実行）、
      - kill.flag の検査（KILL_FLAG_CLEAR_ON_START による自動クリア挙動あり）、
      - PID ファイル書き出し、
      - WebSocket スレッド起動（ブローカが stream_push を提供する場合）、
      - シグナル処理（_process_signals） → push ドレインループ（_drain_push_queue）。
    - シグナル処理の詳細:
      - size_multiplier 適用、qty を 100 単位で揃える等のロジック。
      - Gate 1: シグナルレベルの RiskManager チェック（通過しない場合はスキップ）。
      - Gate 2: 実行レベルの Rate Limit 等のチェック（最大リトライ 3 回）。回路遮断（Circuit Breaker）発生時はシグナルループを停止。
      - 発注後に position_entries テーブルへ約定日（翌営業日）を記録（buy は追加、sell は sell_date 更新。ただし pending sell は除く）。
      - 発注レイテンシを監視 DB にログ可能（monitoring_db が指定されている場合）。
    - push ハンドリング:
      - broker からの push（OrderID）で client_order_id を探し sync_order を実行。
      - Gate 3: ドローダウン監視によりポートフォリオ価値が閾値を超えたら kill_switch 発動。

  - src/kabusys/execution/order_record.py
    - OrderState 列挙と、許容遷移テーブルを実装。
    - OrderRecord dataclass と transition_to ロジック:
      - 不正遷移は InvalidStateTransitionError を raise。
      - transition_to により updated_at を UTC 現在時刻に更新し、broker_order_id / filled_qty / avg_fill_price / error_message をキーワードで更新可能。

  - src/kabusys/execution/order_manager.py
    - OrderManager: OrderRecord と OrderRepository (SQLite) を組み合わせた外向き API。
    - create_order:
      - signal_id ごとの同一アクティブ注文チェック（DB とメモリ両方）。重複時は DuplicateOrderError。
      - client_order_id に uuid4 を採番し OrderCreated レコードを永続化。
      - SQLite の一意制約違反（orders.signal_id）を DuplicateOrderError に変換。
    - send_order:
      - クラッシュ耐性を考慮した 2 相永続化フローを採用:
        1) OrderSent に遷移して commit（broker 呼び出し前に永続化）
        2) broker.send_order 呼び出し
        3a) 成功: broker_order_id を先に commit（state は Sent のまま）
        3b) OrderAccepted に遷移して commit
      - OrderRejectedError 発生時は Rejected に遷移して commit。
      - OrderSentPendingError（注文番号は得られたが約定しないケース）は broker_order_id を永続化した上で OrderSent 状態のまま残し、発生を呼び出し元に伝播（Reconciliation 対象）。
      - それ以外の例外はキャッチせず OrderSent のまま残す（list_uncertain() で検出される想定）。
    - sync_order:
      - broker.get_order_status で外部状態と同期。状態変化に応じて transition_to を用いて更新。
      - 同じ状態でも filled_qty / avg_fill_price が変化している場合は直接フィールド更新して永続化する。
      - OrderSent → Filled/PartialFill の場合は一旦 OrderAccepted を経由して遷移（不整合回復）。
    - cancel_order:
      - 終端状態（Closed / Filled / Cancelled / Rejected）の場合はキャンセル不可で InvalidStateTransitionError を送出。
      - broker_order_id があれば broker.cancel_order を呼び、Cancelled に遷移して永続化。

  - src/kabusys/execution/kabu_client.py
    - KabuStationClient 実装（httpx を使用した同期 REST クライアント）。
    - トークン管理（遅延取得・401 リトライ）を内包:
      - /token エンドポイントでトークンを取得。タイムアウトやネットワークエラーは BrokerAPIError にラップ。
      - 401 受信時はトークン再取得して 1 回リトライ。
    - レスポンス JSON パース失敗を BrokerAPIError に変換。
    - ステータスコードに応じた例外処理:
      - 401 → 認証エラー
      - 429 → RateLimitError
      - >=500 → BrokerAPIError（サーバーエラー）
    - kabu ステーションの内部状態コードと内部状態文字列のマッピングを実装。
    - WebSocket push を受け取るための stream_push（ブローカー実装側）を想定している（実装有無に応じて WebSocket スレッドをスキップ）。

- Monitoring / DB
  - duckdb と sqlite（監視 DB）を併用する設計を採用。
  - init_monitoring_db を用いて監視テーブルの初期化（冪等）を保証。

- ユーティリティ
  - process 優先度設定、ログ設定ユーティリティを利用する設計（setup_logging, set_process_priority）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 本リリースでは、.env を絶対に Git に含めない旨を明記する注意書きを config_setup に追加（.env ファイルの取り扱いに関する注意）。

---

備考:
- 本 CHANGELOG はソースコードの内容から推測して作成しています。細かい実装意図や未公開の依存関係（例: logging_setup, process_priority の実装詳細、monitoring/system_monitor の内部実装など）については含めていません。必要であればさらに細分化したリリースノート（ファイル単位の詳細や既知の制限/TODO）を作成できます。