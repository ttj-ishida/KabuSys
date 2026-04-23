# CHANGELOG

この変更履歴は Keep a Changelog の形式に準拠しています。  
コードベースから推測できる機能追加・変更点・修正を日本語で記載しています。

全体方針:
- 初期リリース相当の状態を 0.1.0 としてまとめています。
- 各機能（設定管理、起動スクリプト、発注エンジン、ブローカークライアント、監視等）の主要な実装点と安全対策を列挙しています。

## [Unreleased]

- 現状、未リリースの変更はありません。

## [0.1.0] - 2026-04-23

### Added
- 全体
  - KabuSys パッケージ基礎を追加。パッケージバージョンは __version__ = "0.1.0"。
  - 実行に必要な主要モジュール群を実装: config, config_setup, validate_config, run_execution, run_monitoring, execution/*（order_manager, order_record, execution_engine, kabu_client 等）、monitoring 等。

- 設定管理（src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py）
  - .env ファイル（および .env.local）から環境変数を自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env パーサーは以下をサポート:
    - コメント行、export KEY=val 形式、
    - シングル/ダブルクォート付き値（バックスラッシュエスケープ対応）、
    - クォート無し値のインラインコメント判定（直前が空白/tab の場合のみコメントと扱う）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを導入し、環境変数経由で主要設定を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
  - 対話式環境設定ウィザード（config_setup.py）を実装:
    - python -m kabusys.config_setup で .env の作成・更新が可能。
    - 各種設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DBパス, LINE 設定等）を対話的に入力。
    - シークレット項目はマスク表示、選択肢やデフォルト値の提示、保存前の確認を実施。
  - 設定検証 CLI（validate_config.py）を実装:
    - python -m kabusys.validate_config（--strict オプションで警告も失敗扱い）。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）とプレースホルダ検出。
    - KABUSYS_ENV / LOG_LEVEL の値検証、DBパスの親ディレクトリ存在チェック。
    - config/*.yaml (system_config.yaml 等) の存在確認と（PyYAML がインストールされていれば）パース検証。PyYAML 未インストール時は警告でスキップ。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定確認、KILL_FLAG_CLEAR_ON_START の危険値検出等）。
    - 標準出力に INFO/WARNING/ERROR を表示し、終了コードで失敗判定を返す。

- 実行用スクリプト
  - run_execution.py:
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル書き出し、停止フラグ（data/stop_requested.flag）検出による安全停止を実装。
  - run_monitoring.py:
    - SystemMonitor のポーリングループを起動するスクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用。

- 発注エンジン・注文管理（execution/*）
  - OrderRecord（order_record.py）:
    - 注文状態を表す OrderState 列挙と、許可遷移テーブルを実装。
    - transition_to による状態遷移検証（不正遷移で InvalidStateTransitionError を送出）。
    - 状態遷移時に updated_at を UTC で更新、任意フィールド（broker_order_id, filled_qty, avg_fill_price, error_message）の更新をサポート。
  - OrderRepository（参照）と組合せる OrderManager（order_manager.py）:
    - create_order: signal_id ごとの重複防止（DB の部分ユニーク制約違反を DuplicateOrderError に変換）。
    - send_order: クラッシュ安全性を考慮した 2 段階の永続化手順を実装（OrderSent を先に永続化→ broker 呼び出し→ broker_order_id を永続化→ OrderAccepted に遷移）。
      - OrderRejectedError は Rejected に遷移して保存。
      - OrderSentPendingError（注文番号は発行されたが確定しない状態）は broker_order_id を保存したまま例外を再送出（Reconciliation の対象）。
    - sync_order: broker 側の状態と同期。broker が返す status を内部状態にマッピングし、部分約定の進展はフィールド差分更新で反映。
    - cancel_order: 取消不能状態の判定（Closed/Cancelled/Rejected/Filled を取消不可とする）と broker cancel の呼出し。
  - ExecutionEngine（execution_engine.py）:
    - Signal Queue 型発注フローを実装。シグナル処理（8:50-9:10）→ push ドレイン（9:10-15:30）。
    - Gate チェック設計:
      - Gate1: シグナルレベルの検査（risk_manager.check_signal）。
      - Gate2: エグゼキューションレベル（レート制限・サーキットブレーカー等） — リトライと最大試行回数のロジック。
      - Gate3: ドローダウン監視（リスク測定の結果で kill_switch を発動）。
    - kill_switch: 全ループの停止 & 全 active 注文のキャンセル（例外ハンドリング含む）。
    - WebSocket push（kabu push）を受けて _push_queue に投入、push をもとに sync_order を実行。push が見つからない場合でもポートフォリオ評価を行い Gate3 を実行（spurious push に対する意図的設計）。
    - 発注後の position_entries への書き込み（買いはエントリー登録、売りは sell_date 更新）。duckdb 経由で実行。

- ブローカークライアント（execution/kabu_client.py）
  - KabuStationClient（kabu station REST API クライアント）を実装:
    - httpx.Client（同期）利用でトークン取得/キャッシュ、401 時の自動再取得とリトライ。
    - レスポンスの JSON パース失敗は BrokerAPIError に変換。
    - HTTP ステータスに応じた例外変換（401/429/5xx 等）。
    - kabu station の状態コードを内部ステータス ("open"/"partial"/"filled"/"cancelled"/"rejected") にマッピング。
    - WebSocket push を受ける stream_push API の存在チェックと呼び出し経路を用意（broker が stream_push を持たないときは WebSocket スレッドをスキップ）。

- 監視（monitoring）
  - monitoring_db の初期化（init_monitoring_db）呼出箇所の統合（monitor/run / execution/run 等で監視 DB の初期化を保証）。
  - run_monitoring と run_execution がそれぞれ sqlite3 / duckdb 接続を確立し、セッション中に close する。

- ユーティリティ
  - プロセス優先度設定ユーティリティの利用（set_process_priority）。
  - ロギングセットアップ（setup_logging）呼出しによるコンポーネント別ログ設定。
  - 停止フラグ (data/stop_requested.flag) と kill.flag の扱いを導入し、安全停止・起動禁止の仕組みを提供。

### Changed
- .env 読み込みの挙動
  - OS 環境変数は保護（protected）され、.env.local で上書き可能だが protected なキーは上書きされない。
  - 自動ロードはプロジェクトルートが特定できない場合はスキップする（パッケージ配布後の安全性考慮）。

- 発注の永続化戦略
  - broker 呼び出し前に OrderSent を永続化し、broker_order_id を受け取ったら先に保存することでクラッシュ後のリコンシリエーションを容易にする設計を採用。

### Fixed
- .env パーサーの不具合回避（想定実装より推測）
  - クォート内のエスケープ処理、export プレフィックス、インラインコメント判定の処理を改善し、一般的な .env 形式を耐えられるようにしている。

### Security
- .env ファイルは生成時に「絶対に Git にコミットしないこと」を明記（config_setup のヘッダコメント）。
- シークレット項目はウィザードでマスク表示。環境変数読み込み時に OS 環境変数を優先して保護。

### Notes / Known limitations（コードから推測）
- YAML の内容検証は PyYAML がインストールされている場合にのみ行われ、未インストール時は警告を出してスキップする。CI 等では PyYAML の導入を推奨。
- KabuStationClient は同期 httpx.Client ベース。将来的な非同期対応は httpx.AsyncClient に置換することで対応可能。
- ExecutionEngine の時間帯判定はローカルマシンの時計に依存する（タイムゾーン等の考慮は別途必要な場合あり）。

------------------------------------------------------------
参考: 主要なコマンド/利用方法（コード中の docstring から推測）
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  # 警告も失敗扱い
- 実行/監視 (サーバ起動等):
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

------------------------------------------------------------
（注）本 CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートとは差異がある可能性があります。必要であれば、より詳細な差分（コミット単位・ファイル単位）に基づく CHANGELOG の生成を行います。