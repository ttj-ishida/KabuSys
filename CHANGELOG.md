# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、コードベース（src/kabusys/*）の内容から推測して作成した変更履歴です。

フォーマット:
- Unreleased: 現在の作業ツリー（HEAD 相当）の主な機能／改善点
- 各リリース: そのリリースで導入された主要な変更点（Added / Changed / Fixed 等）

## [Unreleased]

### Added
- 設定検証用 CLI を追加（src/kabusys/validate_config.py）
  - .env と config/*.yaml の存在・基本的妥当性検査を実行。
  - 必須 / 任意環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性判定、DB パスの親ディレクトリ存在チェック、PyYAML があれば config/*.yaml のパース検証を実施。
  - --strict オプションで警告を失敗として扱うモードを追加。
- 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）
  - 対話式で .env の初期作成・更新を支援。
  - 複数の設定項目（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、ログレベルなど）を定義し、既存値の再利用／デフォルトの挿入が可能。
  - .env の読み書きロジックを実装（secret のマスク表示、保存確認、テンプレート出力など）。
- 設定管理モジュールを拡充（src/kabusys/config.py）
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みする仕組みを追加。
  - .env の高度なパーサ（クォート、エスケープ、インラインコメント、export KEY=val 形式対応）を実装。
  - Settings クラスを導入して型付きプロパティ経由で設定値を取得（duckdb/sqlite パス、pid/kill flag パス、閾値、env/log level の検証など）。
  - PAPER_FILL_MODE の妥当性チェックと paper_trading 用 sqlite パスの分離を実装。
- 実行用スクリプトを追加
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - paper_trading 環境では専用の SQLite を使用して本番 DB と分離。
    - プロセス優先度設定、監視 DB 初期化、duckdb 接続、停止フラグ検出処理を統合。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
- 発注関連コアコンポーネントを追加（src/kabusys/execution/*）
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態を enum で定義し、許容される状態遷移テーブルを実装。
    - 不正遷移時に InvalidStateTransitionError を送出。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - DB（OrderRepository）と OrderRecord を組み合わせ、発注作成→送信→同期→取消 のフローを実装。
    - DuplicateOrderError を導入（同一 signal_id の重複検出）。
    - send_order において二相永続化（OrderSent 保存 → ブローカー呼び出し → broker_order_id 保存 → OrderAccepted へ遷移）を採用し、クラッシュ後のリカバリを考慮。
    - broker の様々な例外（OrderRejectedError, OrderSentPendingError 等）を扱うロジックを実装。
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - シグナル読み出し → Gate1/2 のリスクチェック → 発注 → push ドレインのループ構成を実装。
    - kill_switch の実装（全アクティブ注文取消と停止イベント設定）。
    - WebSocket プッシュ受信スレッドを持ち、push からの同期と Gate3（ドローダウン監視）を実行。
    - 発注時の監視 DB への書き込み（遅延計測、status ログ）に対応（MonitoringDB を注入可能）。
    - position_entries の更新（次営業日を fill_date として記録）を実装（duckdb 利用）。
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - kabu ステーション REST API クライアントを実装（httpx 使用）。
    - トークン取得・キャッシュ・401 時の再取得とリトライの実装。
    - レスポンス JSON パース失敗や HTTP ステータス毎の例外変換（RateLimitError, BrokerAPIError）を実装。
    - kabu station の状態コード → 内部状態へのマッピングを導入。
- 監視周りコンポーネント
  - monitoring_db 初期化を各スクリプトで呼び出すようにし、監視 DB の存在を保証。
- ユーティリティ
  - ロギングセットアップ、プロセス優先度設定ユーティリティを利用するよう統一。

### Changed
- 設定読み込みの優先順位を明確化
  - OS 環境変数 > .env.local > .env の順で読み込む実装。
  - OS 環境変数キーは保護（protected）され、.env.local の override でも上書きされない。
- Execution / Monitoring の DB 接続ルール整理
  - monitoring は常に本番 sqlite_path を使用、execution は paper_trading 時に専用 SQLite を使用するよう明確化。
- ロギングレベル・環境名の妥当性検証を Settings 内で厳格化（ValueError を送出）。

### Fixed
- .env 読み込み時のクォート・エスケープ・コメント処理を強化し、実際の .env での誤解釈を低減。
- send_order のクラッシュ・部分永続化シナリオに対するリカバリ性を向上（broker_order_id を先に永続化することで Reconciliation の改善）。
- ExecutionEngine の kill.flag 周辺の競合／残留による誤起動を防ぐため、起動時の挙動（KILL_FLAG_CLEAR_ON_START によるクリア挙動）を導入。

---

## [0.1.0] - Initial release

※ パッケージバージョン __version__ = "0.1.0" に対応。

### Added
- プロジェクトの初期実装（自動売買システムのコア機能群）。
  - 環境設定管理（src/kabusys/config.py）
  - .env ウィザード（src/kabusys/config_setup.py）
  - 設定検証 CLI（src/kabusys/validate_config.py）
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
  - 発注関連モジュール（order_record, order_manager, execution_engine, reconciler, risk_manager 等の基礎）
  - kabu station REST クライアント（kabu_client）
  - DuckDB / SQLite を用いたデータ管理の基盤
  - 監視 DB 初期化ユーティリティおよび監視イベントロギングの骨組み
  - プロセス優先度設定、ログ設定ユーティリティ

### Changed
- N/A（初期リリース）

### Fixed
- N/A（初期リリース）

---

注記:
- 本 Changelog はコードリポジトリの現行ソース（src/kabusys 以下）から機能や仕様を読み取り、推測を交えて作成したものです。実際のコミット履歴やリリースノートと相違する場合があります。必要であれば、差分やコミットログに基づいて正確な履歴へ更新してください。