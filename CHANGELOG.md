CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- Unreleased セクションは次回リリースまでの変更を示します。
- 各リリースは日付付きで分類しています。

Unreleased
----------

- なし

0.1.0 - 2026-04-23
------------------

Added
- パッケージ初期リリース。
- 環境・設定関連
  - 環境変数 / 設定管理モジュールを追加（kabusys.config）。
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索して自動的に .env を読み込む。
    - 自動ロード順序: OS環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env のパース機能を実装（export プレフィックス対応、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの処理など）。
    - _require() を介した必須キー取得で未設定時は ValueError を送出。
    - Settings クラスを追加し、以下のプロパティ経由で型付きに設定を取得可能:
      - jquants_refresh_token, kabu_api_password, kabu_api_base_url
      - line_channel_access_token, line_user_id
      - duckdb_path, sqlite_path, paper_sqlite_path
      - paper_fill_mode（有効値検査: instant/partial/never/reject）
      - pid_file_path, kill_flag_path, kill_flag_clear_on_start
      - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
      - env, log_level, is_live, is_paper, is_dev
- 設定ウィザード CLI
  - kabusys.config_setup を追加（python -m kabusys.config_setup）。
  - インタラクティブに .env の初期作成 / 更新を支援。シークレット項目はマスク表示。
  - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）および選択肢 / デフォルトを定義。
  - .env をテンプレート形式で出力（保存前に確認プロンプトを表示）。ファイルヘッダに「.env は絶対に Git にコミットしないこと」を明記。
- 設定検証 CLI
  - kabusys.validate_config を追加（python -m kabusys.validate_config）。
  - .env と config/*.yaml の起動前チェックを実行。
  - チェック内容:
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の存在とプレースホルダ検出。
    - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）。live 時は注意警告。
    - LOG_LEVEL の妥当性チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（存在しない場合は警告。起動時に自動作成される可能性を注記）。
    - config/*.yaml の存在確認。PyYAML がインストールされている場合は safe_load でパース検証。PyYAML 未導入時はパース検証をスキップして警告。
    - KABUSYS_ENV=live 時の追加ガード（LINE通知設定、KILL_FLAG_CLEAR_ON_START の危険設定など）を実施。
  - --strict オプションを追加（警告も FAIL として exit(1)）。
- 実行系スクリプト
  - run_execution（python -m kabusys.run_execution）を追加。
    - ExecutionEngine の起動スクリプト。
    - settings に応じて paper_trading 時は paper 用 SQLite（paper_sqlite_path）を使用して本番 DB と分離。
    - プロセス優先度を高く設定（set_process_priority）。
    - 停止フラグファイル（data/stop_requested.flag）の存在検知で安全にシャットダウン。
  - run_monitoring（python -m kabusys.run_monitoring）を追加。
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
- Execution / 発注ロジック
  - OrderRecord（kabusys.execution.order_record）を追加。
    - 注文状態列挙体 OrderState と許可遷移定義（_ALLOWED_TRANSITIONS）。
    - transition_to() による遷移検査と updated_at の自動更新。
    - 不正遷移時に InvalidStateTransitionError を送出。
  - OrderManager（kabusys.execution.order_manager）を追加。
    - create_order, send_order, sync_order, cancel_order の外向け API を実装。
    - create_order は signal_id に対する重複アクティブ注文をチェックし、重複時は DuplicateOrderError を送出。
    - send_order はクラッシュ回復を考慮した 2 段階永続化戦略:
      1. DB に OrderSent 化してコミット（broker 呼び出し前）
      2. broker 呼び出し後、broker_order_id を先に永続化（state は Sent のまま）、その後 OrderAccepted に遷移してコミット
      - OrderRejectedError 発生時は Rejected に遷移して保存。
      - OrderSentPendingError（発注は broker_order_id を返すが約定なし）を扱い、broker_order_id を保存して OrderSent のまま残す（Reconciliation 対象） — 例外は上位へ伝播。
    - sync_order は broker の状態を照会して Fill/Partial 等へ同期。部分約定の進行は差分更新で対応。
    - cancel_order は DB の現在状態を確認のうえキャンセル不可状態では InvalidStateTransitionError を返す。API 呼び出しで broker_order_id がある場合は broker.cancel_order を呼ぶ。
  - ExecutionEngine（kabusys.execution.execution_engine）を追加。
    - シグナル取得と Gate 1/2 の検査を行うシグナル処理ループ（デフォルト: 8:50–9:10）。
    - WebSocket push ドレインループ（デフォルト: 9:10–15:30）を実装。push により sync と Gate 3 チェックを実行。
    - Gate チェック:
      - Gate1: シグナルレベル検査（リジェクト時はスキップ）
      - Gate2: エグゼキューションレベル（レート制限、最大リトライ 3 回。サーキットブレーカー開時はシグナルループ停止）
      - Gate3: ドローダウン監視（NG の場合は kill_switch を発動）
    - kill_switch(): 全ループ停止・全 active 注文のキャンセル処理を実装。cancel_order 呼び出し時の例外を適切に扱う。
    - PID ファイルの書き込み（起動・終了時の管理）、kill.flag の検査と KILL_FLAG_CLEAR_ON_START による挙動制御（起動拒否 or 自動クリア）。
    - position_entries テーブルへの約定記録（発注成功時に次営業日を fill_date として DuckDB に記録）。
    - monitoring DB が渡されていれば発注イベント（Sent 等）を監視 DB にログ可能。
- ブローカー（kabu station）クライアント
  - KabuStationClient（kabusys.execution.kabu_client）を追加。
    - httpx.Client を用いた同期 REST 実装。将来の async 対応を容易にする設計。
    - トークン管理（遅延初期化、401 で再取得してリトライ）。
    - レスポンス JSON パース失敗は BrokerAPIError に変換。
    - 401（認証失敗）時はトークン再取得後リトライし、それでも 401 の場合は BrokerAPIError。
    - 429 は RateLimitError として扱う。500 系は BrokerAPIError として扱う。
    - kabu station の注文件示コード → 内部状態マッピングを実装（_KABU_STATUS_MAP）。
    - WebSocket push（stream_push）をサポートするインターフェース呼び出しの前提（提供されない broker の場合は WebSocket スレッドをスキップ）。
- 監視関連
  - monitoring の初期化 / 利用箇所を各スクリプトに組み込み（init_monitoring_db 呼び出し）。
- その他
  - パッケージ __version__ を 0.1.0 に設定。

Changed
- 新規リリースのため特段の変更履歴なし（初回公開）。

Fixed
- 新規リリースのため特段の修正履歴なし（初回公開）。

Notes / Usage
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行（監視 / 実行エンジン）:
  - python -m kabusys.run_monitoring
  - python -m kabusys.run_execution
- 自動ロードを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ライセンスやセキュリティ上の注意
- .env は秘匿情報を含むため絶対に Git 等にコミットしないでください（config_setup の出力ヘッダにも明記）。

以上。