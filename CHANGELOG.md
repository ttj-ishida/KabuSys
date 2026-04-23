# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

※ 初回リリース (v0.1.0) をコードベースから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-23
### Added
- 基本パッケージメタ情報を追加
  - パッケージバージョンを src/kabusys/__init__.py にて `0.1.0` として定義。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルと環境変数から設定を読み込む自動ローダ実装（プロジェクトルートを .git / pyproject.toml を基準に探索）。
    - .env の独自パース機能を実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理等に対応）。
    - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - Settings クラスを提供し、アプリケーション設定（トークン、パス、DB パス、環境 / ログレベル、各種閾値、Paper Trading 設定など）をプロパティとして安全に取得可能。
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の値検証を実装（不正値では ValueError を発生）。

- 設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式で .env を作成/更新するウィザードを実装。
    - デフォルト値・選択肢・シークレット入力・既存 .env の読み込み・確認プロンプト・.env 出力（二重引用符やコメント付きヘッダ）をサポート。
    - `.env` の保存確認とヒントメッセージを追加。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を実装。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）とオプション変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。PyYAML 未インストール時はスキップして警告を出力。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict オプションで警告も失敗として扱う exit(1) を返すモードを提供。

- 実行系スクリプト（プロダクション起動用）
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - Paper Trading と本番の DB 分離（paper_trading の場合は paper_sqlite_path を使用）。
    - プロセス優先度設定、PID ファイル管理、停止フラグ検出（data/stop_requested.flag）に対応。
    - DB（SQLite / DuckDB）接続・初期化（監視テーブルの冪等初期化）を実装。

  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（1 秒以上にフォールバック）。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する仕様。
    - 停止フラグ / KeyboardInterrupt のハンドリング、DB 接続のクリーンアップを実装。

- Execution エンジン本体
  - src/kabusys/execution/execution_engine.py
    - Signal Queue Pull 型の発注エンジンを実装（EngineConfig により target_date / 時刻帯を指定）。
    - シグナル処理ループ（8:50-9:10）と WebSocket push ドレインループ（9:10-15:30）を実装。
    - kill.flag の検査（起動時とループ内）と KILL_FLAG_CLEAR_ON_START 挙動のサポート。
    - PID ファイル書き込み、WebSocket スレッド（broker の stream_push を利用）および push キューの処理。
    - Gate1/2/3 による多段リスクチェック（リスクマネージャ連携）と Rate Limit リトライロジック。
    - 発注処理後に DuckDB へ position_entries を更新（発注成功/pending による分岐）。
    - 監視 DB への発注イベント記録（monitoring_db が提供される場合）。
    - Reconciliation の起動（存在する場合）と例外耐性。

- 注文管理・状態機械
  - src/kabusys/execution/order_record.py
    - OrderState 列挙型と遷移許可表を実装。
    - OrderRecord dataclass に遷移検証（transition_to）を実装し、不正遷移時は InvalidStateTransitionError を発生。
    - 更新時刻の自動更新と broker_order_id / filled_qty / avg_fill_price / error_message のキーワード更新をサポート。

  - src/kabusys/execution/order_manager.py
    - OrderRecord（純粋ロジック）と OrderRepository（SQLite）を組み合わせた公開 API を実装。
    - create_order: signal_id ベースで重複する active 注文を検出して DuplicateOrderError を発生させる。DB の部分ユニーク制約違反を DuplicateOrderError に変換。
    - send_order: クラッシュ耐性を意識した二相的永続化の流れを実装（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）。
      - OrderRejectedError は Rejected へ遷移。
      - OrderSentPendingError の扱い（broker_order_id を保存し OrderSent のまま残す）を実装し呼び出し元へ伝播。
    - sync_order: broker 側の状態を取得してローカル状態を同期。部分約定の進行では差分更新のみを行う。
    - cancel_order: キャンセル不可能な状態を判定し、可能な場合は broker cancel を呼んで Cancelled へ遷移。

- ブローカークライアント（kabu station）
  - src/kabusys/execution/kabu_client.py
    - httpx（同期）を用いた kabu station REST API クライアントを実装。
    - トークン取得と遅延初期化（_get_token）、401 時のトークン再取得とリトライを内部で処理。
    - HTTP ステータスに基づくエラー変換（401/429/5xx 等）や JSON パース失敗の変換を実装。
    - 注文状態コードから内部ステータス文字列へのマッピングを実装。
    - WebSocket push 処理は broker 側の stream_push を用いて実装可能（ExecutionEngine から利用）。

- 監視関連
  - monitoring 用 DB 初期化ユーティリティと SystemMonitor（別モジュールに分離、起動スクリプトから利用）。
  - run_monitoring/run_execution 両方で監視 DB の初期化処理を呼び出す。

- ユーティリティ
  - ロギングセットアップ、プロセス優先度設定ユーティリティの利用を各起動スクリプトで行う。

### Changed
- （初回公開のため該当なし）

### Fixed
- （初回公開のため該当なし）

### Notes / Limitations
- config/*.yaml の内容検証は PyYAML に依存。PyYAML がインストールされていない環境ではファイル存在チェックのみ実行され、パース検証はスキップされる（警告を表示）。
- KabuStationClient は同期 httpx.Client を使用しており、将来の非同期対応は httpx.AsyncClient への切り替えで対応可能。
- 一部の処理（例: DuckDB / SQLite スキーマ、OrderRepository 実装、Broker の具体実装）は本ログの対象外（別ファイル）であり、実動作はそれらに依存。

---

今後のリリースでは、テストカバレッジ、ドキュメント（使用例・運用手順）、各種エッジケースの追加検証、非同期対応などを追記予定です。