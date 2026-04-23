# CHANGELOG

すべての注目すべき変更点を記載します。フォーマットは「Keep a Changelog」に準拠しています。

全般:
- 初期リリース。基本的な実行エンジン、設定管理、検証ツール、監視プロセス、および kabuステーション向けクライアントを含みます。
- パッケージバージョン: 0.1.0

## [0.1.0] - 2026-04-23

### Added
- パッケージメタ情報
  - __init__.py にてパッケージバージョンを "0.1.0" として追加。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を自動ロードする仕組みを追加。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応（テスト用）。
    - プロジェクトルート検出は .git または pyproject.toml を探索して行う（CWD 非依存）。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート文字列のエスケープと適切な終了引用符の処理。
    - クォートなしの行でのインラインコメント認識（直前がスペース/タブの場合のみ）。
  - _load_env_file による上書き制御:
    - override フラグと protected キーセット（OS 環境変数保護）に対応。
  - Settings クラスを提供し、各種設定値（トークン、パス、閾値、環境種別など）をプロパティで安全に取得可能に。
    - 必須環境変数取得時に未設定であれば ValueError を送出する _require を実装。
    - PAPER_FILL_MODE の検証（有効値チェック）やパスの Path 変換などを含む。
    - 環境（development / paper_trading / live）・ログレベルの検証ロジックを含む。

- .env 作成/更新ウィザード CLI (src/kabusys/config_setup.py)
  - 対話式ウィザードで .env を初期作成・更新する機能を追加。
  - 構成項目一覧と説明を持ち、シークレット項目は表示時にマスク。
  - 既存 .env の読み込み、入力の検証（選択肢のチェック）、キャンセル時の中断対応。
  - 最終確認画面と .env ファイル書き込みロジックを提供。
  - デフォルト値、オプション項目扱い（空欄でスキップ）、および注意文言（.env を絶対に Git にコミットしない等）を出力。

- 設定検証 CLI (src/kabusys/validate_config.py)
  - 起動前に環境変数および config/*.yaml の不備を検出する CLI を追加。
  - チェック内容:
    - 必須環境変数 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD) の存在確認とプレースホルダ検出。
    - KABUSYS_ENV の妥当性チェック（development/paper_trading/live）。live の場合は追加の注意警告。
    - LOG_LEVEL の妥当性チェック。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（起動時自動作成の可能性を考慮して警告扱い）。
    - config/*.yaml の存在確認。PyYAML がインストールされていればパース検証を実施し、未インストール時はスキップの警告を出す。
    - KABUSYS_ENV=live のときの追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険設定チェックなど）。
  - 出力形式:
    - INFO / WARNING / ERROR を列挙し、--strict オプションで警告を FAIL（exit 1）に昇格可能。
  - プログラム的には validate() が (errors,warnings,infos) を返すためテスト可能。

- 実行 / 監視起動スクリプト
  - 実行エンジン起動 (src/kabusys/run_execution.py)
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - paper_trading 環境では専用の paper_trading SQLite DB を使用し本番 DB と分離。
    - プロセス優先度設定、PID ファイル、停止フラグ(stop_requested.flag) の検出・ハンドリングを実装。
    - DB 接続（SQLite / DuckDB）を開き、監視 DB テーブルの初期化を保証。
    - スレッドで ExecutionEngine を実行し、停止検出時に適切に終了。
  - 監視ループ起動 (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視でも本番 sqlite_path を使用する設計。
    - 停止フラグ検知、例外ハンドリング（check_once() の失敗はログで回復）、リソースクローズを実装。

- 実行エンジン本体および関連コンポーネント（src/kabusys/execution/...）
  - ExecutionEngine (src/kabusys/execution/execution_engine.py)
    - シグナル読み込み / Gate 検査 / 発注フロー / push ドレインを含むセッション実行ロジックを実装。
    - target_date に基づくシグナル処理時間帯（デフォルト 8:50-9:10）および市場クローズ（15:30）を管理。
    - kill.flag による起動拒否、起動時の kill_flag_clear_on_start 処理（設定が 1 の場合はクリアして起動）を実装。
    - PID ファイルの作成・削除、WebSocket ワーカースレッドによる push のキュー取り込み、push に対する同期処理と Gate 3（ドローダウン監視）による kill_switch 発動を実装。
    - シグナル発注時のレートリミット・サーキットブレーカーのリトライ、size_multiplier による数量算出、position_entries への書き込み（DuckDB）などを含む。
    - 監視 DB (MonitoringDB) が提供されている場合は発注イベントのログを残す。
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態を Enum で定義（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可される状態遷移テーブルと、遷移検証を行う transition_to() を実装。不正遷移は InvalidStateTransitionError を発生。
    - 作成/更新日時管理、約定数量や平均約定価格、エラーメッセージの更新をサポート。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - OrderRecord と OrderRepository（SQLite）を組み合わせた外向き API を提供（create_order, send_order, sync_order, cancel_order）。
    - 同一 signal_id の重複注文検出（DB の部分ユニークインデックス違反も DuplicateOrderError に変換）。
    - send_order のクラッシュ安全パターン:
      - OrderSent を先に永続化してからブローカ API を呼び、broker_order_id を先に DB にコミット → その後 OrderAccepted に遷移してコミットすることでリコンシリエーション耐性を確保。
      - OrderRejectedError は Rejected へ遷移して永続化。
      - OrderSentPendingError（注文番号は発行されたが約定しない状況）は broker_order_id を永続化した上で OrderSent のまま残し、呼び出し元へ再送出（Reconciliation の対象とする）。
    - sync_order はブローカからの状態を照合して適切に状態遷移（OrderSent→OrderAccepted を経由する等）し、部分約定の進行はフィールド更新で反映。
    - cancel_order はキャンセル不可状態のチェック（Filled を含む）を行い、broker_order_id がある場合は外部 API にキャンセルを依頼してから状態を Cancelled に遷移。

  - Reconciler / RiskManager / BrokerFactory 等（参照）
    - Engine の組み立て時に Reconciler を実行することで起動時リコンシリエーションを行い、同期結果をログ出力する仕組みを持つ。
    - RiskManager による Gate 検査（Gate1: signal-level、Gate2: execution-level / rate limit、Gate3: portfolio metrics）を統合。

- kabuステーション REST クライアント (src/kabusys/execution/kabu_client.py)
  - KabuStationClient を実装（同期 httpx.Client ベース）。
    - トークン取得の遅延初期化と自動再取得（401 応答時に再取得して1回リトライ）。
    - _request レイヤでタイムアウトやネットワークエラーを BrokerAPIError に変換。
    - 429 (rate limit) は専用の RateLimitError を送出。
    - ステータスコード → 内部注文ステータスマッピングを実装（kabu の状態コードを open/partial/filled/cancelled/rejected 等に変換）。
    - 将来の async 対応のために httpx.AsyncClient への切替が容易な設計。
    - WebSocket (push) 受信用の stream_push を備える broker 実装との連携を想定（ExecutionEngine が存在する場合は push を処理）。

- 監視関連
  - monitoring_db 初期化の呼び出しポイントを run scripts に組み込み（init_monitoring_db）。
  - SystemMonitor を利用した常駐監視ループを提供（run_monitoring.py）。
  - 監視用 DB 書き込みはエラーが発生しても発注フローを阻害しない設計（警告ログのみ）。

### Changed
- （初回リリースのため特段の変更履歴はありません）

### Fixed
- （初回リリースのため特段の修正履歴はありません）

### Removed
- （なし）

### Security
- 機密情報（トークンやパスワード）は .env として取り扱い、config_setup では表示時にマスクする旨をドキュメント化。

注意:
- 本 CHANGELOG はコードから推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース差分を確認のうえ、日付や重要な互換性情報を確定してください。