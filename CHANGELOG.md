# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」の慣習に準拠します。

## [0.1.0] - 2026-04-23

### Added
- 基本パッケージ情報
  - パッケージバージョンを定義: `kabusys.__version__ = "0.1.0"`。

- 環境設定・読み込み
  - 環境変数 / .env 管理モジュールを追加 (`src/kabusys/config.py`)。
    - プロジェクトルートを .git または pyproject.toml から検出して自動的に .env を読み込む仕組み（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env のパース処理を独自実装（`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの扱いに対応）。
    - `_load_env_file()` による上書き制御（OS 環境変数保護機能）。
    - Settings クラスを提供して型付きアクセサ (例: `settings.jquants_refresh_token`, `settings.duckdb_path`)。
    - 設定値の妥当性チェック（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` 等で不正値時に ValueError を発生）。

- 対話式設定ウィザード CLI
  - `.env` 作成/更新用ウィザード (`src/kabusys/config_setup.py`) を追加。
    - 対話式プロンプト、入力補助（デフォルト・選択肢・説明表示）、シークレット値のマスク表示。
    - 既存 .env の読み込みと Enter による再利用、途中キャンセルの扱い。
    - `.env` ファイルのテンプレート出力機能（秘密情報はプレースホルダのまま保存可能）。
    - 実行方法: `python -m kabusys.config_setup`（`--env-file` でパス指定可能）。

- 設定検証 CLI
  - 起動前の設定検証ツール (`src/kabusys/validate_config.py`) を追加。
    - 必須環境変数の未設定チェック (`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`)。
    - 環境変数がプレースホルダのままかどうかの警告検出（末尾が `_here` や `your_value` など）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の妥当性検査と `live` 環境時の追加注意喚起。
    - DB パス（DUCKDB, SQLITE）の親ディレクトリ存在チェック。
    - `config/*.yaml` の存在チェックと PyYAML が利用可能な場合はパース検証（PyYAML 未インストール時は警告を出してスキップ）。
    - `KABUSYS_ENV=live` 時に LINE 通知設定や Kill Switch の設定（`KILL_FLAG_CLEAR_ON_START`）をチェック。
    - CLI オプション `--strict` を用意し、警告を FAIL として exit(1) させることが可能。
    - 実行方法: `python -m kabusys.validate_config`。

- 実行エントリポイント
  - 実運用用スクリプトを追加:
    - `src/kabusys/run_execution.py` — ExecutionEngine 起動スクリプト。
      - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite（デフォルト: `data/paper_trading.db`）を使用し本番 DB と分離。
      - PID / stop フラグファイルの取り扱い、プロセス優先度設定、DB 初期化処理を実装。
    - `src/kabusys/run_monitoring.py` — SystemMonitor ポーリング起動スクリプト。
      - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
      - stop フラグ（data/stop_requested.flag）検出でループ終了。

- Execution / 発注フロー本体
  - ExecutionEngine (`src/kabusys/execution/execution_engine.py`)
    - シグナルの読み込み、Gate1/2/3 によるリスクチェック、発注フロー、WebSocket push のドレイン処理を実装。
    - kill_switch による全 active 注文のキャンセル、PID ファイル管理、Reconciliation の起動ポイントを有する。
    - 発注ループでは rate limit に対するリトライや Circuit Breaker 開放時の挙動を実装。
    - 発注後には position_entries への書き込み処理（買いはエントリ日挿入、売りは sell_date 更新）を行う（失敗しても発注は継続）。
    - Monitoring DB が渡された場合、監視イベントの記録を試みる（失敗しても発注継続）。

  - OrderRecord / 状態遷移モデル (`src/kabusys/execution/order_record.py`)
    - 注文状態列挙 (OrderState) と許容遷移を明示。
    - 不正な遷移で `InvalidStateTransitionError` を送出。
    - 状態遷移時に `updated_at` を自動更新し、broker_order_id / filled_qty / avg_fill_price / error_message をキーワード引数で安全に更新。

  - OrderManager (`src/kabusys/execution/order_manager.py`)
    - DB（OrderRepository）と OrderRecord を組み合わせた外向き API を実装:
      - create_order: client_order_id に uuid4 を採番し `OrderCreated` レコードを保存。signal_id の重複 active 注文を検知して `DuplicateOrderError` を送出。
      - send_order: クラッシュ耐性を考慮した処理順（OrderSent を DB に保存 → broker API 呼び出し → broker_order_id を先に保存 → OrderAccepted へ遷移）を実装。OrderRejected / OrderSentPending の扱いを明確に区別。
      - sync_order: broker 側の状態を取得してローカル状態に同期。部分約定の進行はフィールド更新で対応。
      - cancel_order: 終端状態ではキャンセル不可として `InvalidStateTransitionError` を送出し、そうでない場合 broker API を呼んで Cancelled に遷移。
    - SQLite のユニーク制約違反（signal_id による）を DuplicateOrderError に変換する扱いを実装。

  - Broker クライアント（kabu station）
    - KabuStationClient (`src/kabusys/execution/kabu_client.py`)
      - httpx を用いた同期 REST クライアント実装。
      - トークン取得の遅延初期化、401 時のトークン再取得と1回のリトライを実装。
      - レスポンス JSON のパース失敗は BrokerAPIError に変換。
      - 429（レート制限）は RateLimitError を返す。500 系は BrokerAPIError として扱う。
      - kabu station の状態コードを内部ステータス文字列へマッピング。
      - WebSocket push 受信（`stream_push`）をサポートするインターフェースを想定し、ExecutionEngine 側でコールバック処理。

- 監視・DB 初期化
  - Monitoring DB 初期化呼び出し (init_monitoring_db) の使用箇所を run スクリプトに実装し、監視テーブルの存在を保証する（冪等）。

- ユーティリティ
  - ロギングセットアップ、プロセス優先度設定を行うユーティリティを利用（`setup_logging`, `set_process_priority` を各 run スクリプトで呼び出し）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes
- `config/*.yaml` の内容検証は PyYAML がインストールされていない場合はスキップされ、警告が出ます（`validate_config`）。
- デフォルトの DB ファイルパス:
  - DuckDB: `data/kabusys.duckdb`
  - Monitoring SQLite: `data/monitoring.db`
  - Paper Trading SQLite: `data/paper_trading.db`
- Kill Switch 関連:
  - 起動時に `kill.flag` が存在する場合、`KILL_FLAG_CLEAR_ON_START=1` であればクリアして起動、それ以外は起動を拒否する挙動。
- PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject"。不正値は例外となるため注意。
- MONITOR_POLL_INTERVAL に 0 以下や非整数を指定するとデフォルト（60 秒）にフォールバックする。

---

今後のリリースでは以下の改善を予定しています（例）:
- BrokerAPI の抽象化とテストダブルの提供（テスト容易性向上）
- KabuStationClient の非同期対応 (httpx.AsyncClient)
- 監視・メトリクスの追加項目と更なる堅牢化

（初回リリースのため「Added」が中心の記録です）