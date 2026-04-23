# Changelog

すべての注目すべき変更履歴はここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

全てのバージョン表記は Semantic Versioning に従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

初回リリース。主な追加点・実装内容は以下の通りです。

### Added
- パッケージ初期化
  - パッケージバージョンを __version__ = "0.1.0" として設定。

- 環境設定管理
  - kabusys.config: 環境変数・.env ファイルの読み込み・管理モジュールを実装。
    - プロジェクトルートを .git または pyproject.toml から自動検出し、.env / .env.local を自動読み込み（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
    - .env のパース実装を強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等）。
    - Settings クラスで型付きプロパティを提供（トークンやパス、閾値、環境/ログレベル等）。不正値は明示的に ValueError を送出。
    - Paper Trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）や PAPER_FILL_MODE の検証ロジックを実装。

- 対話式設定ウィザード
  - kabusys.config_setup: .env を対話的に生成・更新する CLI ウィザードを実装。
    - 多数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE 通知関連など）を用意。
    - 既存 .env の読み込みと Enter による既存値再利用、シークレットのマスク表示、選択肢サポート等。
    - .env をフォーマット付きで出力（※ .env を Git にコミットしないよう注意書き）。

- 設定検証ツール
  - kabusys.validate_config: 起動前に .env および config/*.yaml を検証する CLI を実装。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - プレースホルダ値（*_here / your_value）を警告。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、KABUSYS_ENV=live の際の注意喚起。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と（PyYAML が存在する場合の）パース検証。PyYAML 未インストール時はスキップして警告。
    - --strict フラグで警告も失敗扱い（exit code 1）にできる。

- 実行スクリプト群
  - run_execution: ExecutionEngine を起動するスクリプトを実装。
    - paper_trading 環境時は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用し、本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ（stop_requested.flag）検出機構を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - Monitoring は環境に関わらず本番 sqlite_path を使用。

- 発注関連コアロジック
  - execution/order_record.py: OrderRecord（状態遷移ロジック）を実装。
    - OrderState 列挙、許容遷移テーブル、transition_to による安全な遷移とタイムスタンプ更新、InvalidStateTransitionError。
  - execution/order_manager.py: OrderManager による外向き API を実装。
    - create_order（signal_id の重複チェック、DB 保存、DuplicateOrderError）、send_order（2相永続化の流れを明示）、sync_order（broker 状態との同期）、cancel_order（キャンセル可否判定）。
    - OrderSentPendingError, OrderRejectedError 等の扱いを考慮したエラーハンドリング。
    - send_order の実装では、OrderSent を永続化後に broker に送信し、broker_order_id を先に保存してから OrderAccepted へ遷移することでクラッシュ耐性を向上。
  - execution/execution_engine.py: Signal Queue Pull 型発注エンジンを実装。
    - シグナル処理（8:50-9:10）、WebSocket push ドレイン（9:10-15:30）、kill.flag の取り扱い、PID 書き込み、Reconciliation 実行（任意）、WebSocket スレッド、push 処理での同期（sync_order）と Gate チェック（Gate1: シグナル、Gate2: 実行/レート制限、Gate3: ドローダウン監視）。
    - Gate 2 のレート制限で最大リトライ（3回）やサーキットブレーカー時の挙動を実装。
    - 発注後の position_entries 更新（約定日を翌営業日にするため next_trading_day を使用）と監視 DB へのイベント記録（存在する場合）。
    - kill_switch による全 active 注文のキャンセル処理。

- ブローカークライアント（kabu station）
  - execution/kabu_client.py: KabuStationClient を実装（httpx を使用した同期クライアント）。
    - トークン管理（遅延初期化・401 再取得とリトライ）、共通リクエスト処理、タイムアウト・ネットワークエラーの BrokerAPIError 変換。
    - レスポンス JSON パースのエラーハンドリング、HTTP 429 の RateLimitError、サーバーエラーのハンドリング。
    - kabu station の状態コードを内部ステータス文字列へマップする定義を追加。

- その他ユーティリティ
  - config の各種デフォルトや閾値（CPU/MEM/DISK/ログレベルなど）プロパティを Settings 経由で提供。
  - run_monitoring/run_execution で duckdb, sqlite の接続初期化や監視テーブル初期化を実装。

### Changed
-（初回リリースのため該当なし）

### Fixed
-（初回リリースのため該当なし）

### Removed
-（初回リリースのため該当なし）

### Security
- .env を生成する際に「絶対に Git にコミットしないこと」という注意書きを出力。

---

注記:
- 本 CHANGELOG はコードベースから推測して作成したものであり、実際のコミット履歴や外部仕様書と差異がある可能性があります。用途に応じて追記・修正してください。