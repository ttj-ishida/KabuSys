# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成したリリースノートです。

全般的な注意:
- 本リポジトリはバージョン 0.1.0（初回リリース）相当の機能を含みます。
- 環境変数の自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- DuckDB と SQLite を併用し、paper_trading 時は SQLite を分離して使用します。

## [Unreleased]

### 追加
- CLI / ツール
  - `python -m kabusys.config_setup` : 対話式ウィザードで .env を作成 / 更新する CLI を追加。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を対話的に設定可能。
    - シークレット項目はマスク表示。既存 .env を読み込んで Enter で既存値を再利用可能。
    - 生成される .env に関する注意コメントを出力（.env を Git にコミットしないよう注意喚起）。
  - `python -m kabusys.validate_config` : 起動前に .env と config/*.yaml の設定不備を検出するバリデータを追加。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の未設定チェック、プレースホルダの検出を実装。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック、config/*.yaml の存在 & PyYAML によるパース検証（PyYAML 未インストール時はスキップ）を実装。
    - KABUSYS_ENV=live のときの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険値警告）を実装。

- 設定管理
  - Settings クラスを導入して環境変数を一元管理（プロパティアクセス）。
    - 必須環境変数は _require() で検査し、未設定時は ValueError を送出。
    - 自動 .env 読み込み:
      - プロジェクトルートは .git または pyproject.toml を上位ディレクトリから探索して決定（__file__ 基準で探索）。
      - 読み込み順: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護（上書きされない）。
      - .env のパースは複雑なケース（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱い）をサポート。
  - 各種プロパティを提供:
    - API トークン / パスワード、KABU_API_BASE_URL、LINE 設定、DB パス（duckdb / sqlite / paper_trading の分離）、PID / kill flag パス、閾値（CPU/MEM/DISK）、環境 / ログレベル検証、paper_fill_mode の検証など。

- 実行スクリプト
  - `run_execution.py` : ExecutionEngine を起動するエントリポイントを追加。
    - プロセス優先度設定、PID ファイル管理、stop フラグ検出、paper_trading 時の専用 SQLite 使用（本番 DB と分離）を実装。
    - duckdb と sqlite の接続初期化、監視 DB テーブルの初期化を行う。
  - `run_monitoring.py` : SystemMonitor のポーリングループを起動するスクリプトを追加。
    - ポーリング間隔を MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用。

- 発注実装（Execution）
  - OrderRecord / OrderState
    - 注文状態を列挙する OrderState と、許可される状態遷移を明確化。
    - OrderRecord dataclass に状態遷移メソッド transition_to を実装。無効遷移は InvalidStateTransitionError を送出。
  - OrderRepository（DB 操作）と組み合わせる OrderManager を実装
    - create_order: signal_id の重複チェック（DB の部分ユニークインデックス考慮）と client_order_id の UUID4 発番。重複時は DuplicateOrderError を送出。
    - send_order: 2 相永続化戦略（OrderSent に永続化 → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移）でクラッシュ時の回復性を高める設計。
      - OrderRejectedError を受けた場合は Rejected に遷移。
      - OrderSentPendingError（注文番号は発行されたが約定しないケース）は broker_order_id を保存して例外を伝播（Reconciliation 対象）。
    - sync_order: broker の状態照会によりローカル状態を同期。部分約定進捗の更新と不整合回復ロジックを実装。
    - cancel_order: キャンセル不可能な状態のチェック（終端状態の扱い）と broker API 呼び出し、Cancelled への遷移。
  - ExecutionEngine
    - シグナルを DuckDB から読み込み、Gate1（シグナルレベル）、Gate2（エグゼキューションレベル／レート制限、リトライ最大3回、CB 判定）を通じて発注を実行。
    - シグナル処理期間（デフォルト 8:50-9:10）と push ドレインループ（9:10-15:30）のセッションロジックを実装。
    - WebSocket (kabu push) を別スレッドで受け取り _push_queue に投入、ドレイン時に sync_order を呼び出す。
    - Gate3（ポートフォリオ指標に基づくドローダウン監視）で NG の場合は kill_switch を発動し、active 注文をキャンセル。
    - kill_switch は全アクティブ注文のキャンセル（例外ハンドリングで継続）と全ループ停止を行う。
    - 発注の監視ログ（latency 等）を monitoring DB に記録するフックを持つ（監視 DB が提供されている場合）。
    - position_entries の記録（BUY のみ、fill_date は翌営業日）や SELL の売却更新を実装。DuckDB を使用して next_trading_day を参照。

- Broker / KabuStation クライアント
  - KabuStationClient を実装（httpx を利用する同期クライアント）。
    - トークン取得の遅延初期化と 401 に対する自動再取得（1 回リトライ）を実装。
    - レスポンス JSON パース失敗 / ネットワークエラー / タイムアウトを BrokerAPIError にラップ。
    - 429 は RateLimitError にマッピング。
    - kabu の注文状態コードを内部状態文字列 ("open", "partial", "filled", "cancelled", "rejected") にマッピング。
    - 将来的な async 化を容易にする設計（内部で httpx.Client を使用）。

- 監視（Monitoring）
  - monitoring_db の初期化ユーティリティ（init_monitoring_db）を利用し、実行前に監視テーブルを保証。

- ユーティリティ
  - ロギング初期化（setup_logging）やプロセス優先度変更（set_process_priority）を利用。

### 変更
- .env パーサーの挙動を明確化
  - export プレフィックスのサポート、引用符付き値内のバックスラッシュエスケープ、インラインコメントの扱い（非引用値では '#' の直前が空白/タブであればコメントとみなす）などを扱う実装により既存 .env の柔軟なパースをサポート。

### 修正（挙動設計）
- send_order のクラッシュ耐性向上
  - broker 呼び出し前に OrderSent を永続化し、broker が発行する order_id を先に保存することで、途中クラッシュ時に Reconciliation が broker 情報をもとに状態を回復できるようにした。
- cancel のルール
  - Filled をキャンセル不可として扱う（ポジション追跡上はアクティブだがキャンセル不可能のための扱いを明確化）。

## [0.1.0] - 2026-04-22

最初のパブリック相当リリース（コードベースから推測）。上記の主要機能群を含む。

- 基本機能
  - 環境設定の自動読み込み / 対話式ウィザード / 設定バリデーション CLI を実装。
  - ExecutionEngine / OrderManager / OrderRecord による発注フローと状態管理。
  - KabuStation REST クライアント（トークン管理・エラーラッピング）。
  - 監視ループ（run_monitoring）と実行スクリプト（run_execution）。
  - DuckDB / SQLite を用いたデータ保存と paper_trading 用 DB の分離。
  - kill flag / PID ファイル管理とプロセス優先度設定。
  - 監視 DB への発注イベント記録や position_entries への記録処理。

- ドキュメント・注意
  - .env の取り扱いに関する注意（.env を Git にコミットしない等）をウィザードで明示。

### 既知の制限（推測）
- config/*.yaml の細かいバリデーションは PyYAML がないとスキップされる（validate_config で警告）。
- 一部外部依存（httpx, websocket, duckdb, PyYAML 等）が必要。実行環境により追加パッケージのインストールが必要。

---

この CHANGELOG はコードベースの内容から推測して作成しています。追加の履歴情報（過去の変更ログ、リリース日、影響範囲の詳細等）があれば、より正確に更新できます。