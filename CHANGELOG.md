# Changelog

すべての変更は「Keep a Changelog」規約に準拠して記載しています。  
このファイルは、リポジトリ内の現行コードベースから機能・設計を推測して作成した初期の変更履歴（リリースノート）です。

## [Unreleased]

### Added
- 開発中の各モジュール骨格の追加（src/kabusys パッケージ）
  - パッケージバージョンを定義（__version__ = "0.1.0"）。
  - パッケージ公開 API に data, strategy, execution, monitoring を追加。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出：.git または pyproject.toml）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート（テストフレンドリー）。
  - .env 行パーサ（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの適切な取り扱い）。
  - Settings クラスを提供し、必要環境変数取得（必須チェック）・既定値・検証（KABUSYS_ENV, LOG_LEVEL）・便利プロパティ（is_live / is_paper / is_dev）を実装。
  - デフォルトの DB パス:
    - DUCKDB_PATH => data/kabusys.duckdb
    - SQLITE_PATH => data/monitoring.db

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants のエンドポイントから株価（日足）、財務（四半期 BS/PL）、市場カレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - レート制御（固定間隔スロットリング）を実装：120 req/min（_RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回）を実装。対象はネットワーク系・一部 HTTP ステータス（408, 429, 5xx）。
  - 401 Unauthorized 受信時はリフレッシュトークンから id_token を再取得して 1 回だけ再試行する設計（無限再帰防止の allow_refresh フラグ）。
  - id_token のモジュールレベルキャッシュを保持し、ページネーション間で共有。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を追加。いずれも冪等（ON CONFLICT DO UPDATE）で保存。
  - 取得時刻（fetched_at）を UTC ISO8601 形式で保存し、Look-ahead Bias のトレーサビリティに対応。
  - 型変換ユーティリティ（_to_float / _to_int）を実装し、変換ルール（不正値→None、"1.0" などの float 文字列処理や小数部の切り捨て防止）を明確化。
  - HTTP ユーティリティは urllib を使用、タイムアウトや JSON デコードエラーハンドリングを実装。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataPlatform 設計に基づく 3 層（Raw / Processed / Feature）＋Execution 層のテーブル定義を追加。
  - raw_prices, raw_financials, raw_news, raw_executions など Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals など Processed テーブルを定義。
  - features, ai_scores など Feature テーブルを定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution テーブルを定義。
  - 各種インデックスを作成（頻出クエリパターン向け）。
  - init_schema(db_path) による初期化（親ディレクトリ自動作成、冪等な CREATE 文）と get_connection() を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: 日次の一連 ETL ワークフローを実装（市場カレンダー → 株価 → 財務 → 品質チェック）。
  - run_prices_etl / run_financials_etl / run_calendar_etl: 差分更新ロジック（最終取得日ベース）、バックフィル（デフォルト backfill_days = 3）、カレンダー先読み（デフォルト lookahead = 90 日）を実装。
  - ETLResult dataclass により ETL のメトリクス（取得数・保存数・品質問題・エラー等）を返却。品質問題は quality モジュールの QualityIssue を格納。
  - market_calendar を先に取得して営業日調整（_adjust_to_trading_day）を行い、営業日基準で株価/財務を取得する設計。
  - 各ステップは独立してエラーハンドリングされ、1 ステップの失敗がパイプライン全体を止めない（Fail-Fast ではない）。

- 監査ログスキーマ（kabusys.data.audit）
  - signal_events, order_requests（冪等キー: order_request_id）, executions を含む監査用テーブルを実装。
  - すべての TIMESTAMP を UTC で扱うことを保障（init_audit_schema で SET TimeZone='UTC'）。
  - 発注要求・約定のトレーサビリティ（UUID 連鎖設計）を反映。
  - init_audit_schema / init_audit_db を提供。

- データ品質チェック（kabusys.data.quality）
  - QualityIssue dataclass を定義（check_name, table, severity, detail, rows）。
  - check_missing_data: raw_prices の OHLC 欠損を検出（volume は許容）。
  - check_spike: 前日比スパイク（デフォルト閾値 50%）を検出。ウィンドウ関数で LAG を取り前日 close と比較。
  - 各チェックは問題を全件収集して QualityIssue リストを返す（Fail-Fast ではない）。DuckDB 上の SQL を用いて効率的に実行。

### Changed
- （該当なし：初期リリース相当の追加）

### Fixed
- （該当なし）

### Security
- id_token リフレッシュ処理で無限再帰が発生しないよう allow_refresh フラグを導入。
- 環境変数の必須チェックを明確化し、未設定時は ValueError を投げる（誤設定の早期検出）。

---

## [0.1.0] - 2026-03-16

初回公開（推定）リリース。上記の機能を含む最小実装をリリース。

### Added
- パッケージ基盤、設定管理、J-Quants クライアント、DuckDB スキーマ定義、ETL パイプライン、監査ログスキーマ、データ品質チェックモジュールを実装。
- 各種ユーティリティ（型変換、レートリミッタ、再試行、ページネーション、冪等保存、営業日調整、品質チェック集計）を実装。

### Notes / Migration
- 初回セットアップ:
  - DuckDB スキーマは init_schema(db_path) で初期化してください（":memory:" を指定してテストも可能）。
  - 監査ログを別 DB に分ける場合は init_audit_db を使用、既存接続に追加する場合は init_audit_schema(conn) を使用。
- 必須環境変数（少なくとも次を設定する必要があります）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- KABUSYS_ENV の有効値: development, paper_trading, live（不正値は例外）。
- LOG_LEVEL の有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL（不正値は例外）。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布時は .git または pyproject.toml の存在に注意。

### Known limitations / TODO
- strategy と execution モジュールの実装は骨格のみ（実戦用戦略・発注ロジックは未実装）。
- quality モジュール内にコメントで示されているチェック項目（重複チェック、日付不整合検出など）は仕様に言及されているが、実装が一部（あるいは追加実装が必要）である可能性あり。完全なチェック実装を追加する余地あり。
- J-Quants クライアントは urllib を使用。より高度な HTTP クライアント（requests / httpx）への置換や非同期対応は今後検討。
- 大量データ・並列取得時のレート制御や効率改善（バッチ、バックオフ調整、より精緻な Retry-After 解析など）は改善の余地あり。
- DuckDB の UNIQUE / INDEX の振る舞い（NULL 扱いなど）については注記あり。各 RDBMS への移植性は限定的。

---

参考: 本 CHANGELOG は現行コード内容からの推測に基づくサマリです。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。