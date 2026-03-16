# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-16

### Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョンを `__version__ = "0.1.0"` として導入。
  - パッケージ公開API (`__all__`) に data, strategy, execution, monitoring を追加。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定値を自動読み込みする仕組みを実装。
    - 読み込み順序: OS環境変数 > .env.local > .env
    - OS 環境変数を保護するため、既存の環境変数を保護セットとして扱い上書きを制御。
    - プロジェクトルートは現在ファイル位置から上位を探索し、`.git` または `pyproject.toml` を基準に判定（CWD 非依存）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト向け）。
  - .env パーサーに以下の対応を実装:
    - 空行・コメント行（#始まり）を無視。
    - `export KEY=val` 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理を考慮した値抽出。
    - クォート無しの場合は、インラインコメント（`#`）の判定をスペース/タブ直前のみとする挙動。
  - Settings クラスを導入し、環境変数からアプリケーション設定を取得するプロパティを提供:
    - J-Quants / kabu API / Slack / DB パス等を取得するプロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - デフォルト値: KABU_API_BASE_URL -> "http://localhost:18080/kabusapi"、DUCKDB_PATH -> "data/kabusys.duckdb"、SQLITE_PATH -> "data/monitoring.db"。
    - 環境名（KABUSYS_ENV）とログレベル（LOG_LEVEL）に対するバリデーションを実装（有効値リストで検証）。
    - is_live / is_paper / is_dev のブールプロパティを提供。
    - 必須環境変数未設定時には ValueError を送出する `_require()` を実装。

- データ取得クライアント: J-Quants (`kabusys.data.jquants_client`)
  - J-Quants API クライアント実装（価格日足 / 財務データ / JPX マーケットカレンダー 取得）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライロジック:
    - 指数バックオフ（base=2.0 秒）、最大 3 回リトライ。
    - 再試行対象ステータス: 408, 429, および 5xx。
    - 429 の場合は `Retry-After` ヘッダを優先して待機。
    - ネットワークエラー（URLError, OSError）に対してもリトライ。
  - 認証トークン管理:
    - リフレッシュトークンから ID トークンを取得する `get_id_token()`（POST）。
    - モジュールレベルでの ID トークンキャッシュを導入し、ページネーション間でトークンを共有。
    - 401 応答時に自動でトークンを 1 回リフレッシュして再試行（無限再帰を防ぐため allow_refresh フラグを利用）。
  - API 呼び出し共通関数 `_request()` を実装。JSON デコードエラーや再試行ロジックを統一。
  - ページネーション対応の取得関数を実装:
    - fetch_daily_quotes(code / date_from / date_to 指定可)
    - fetch_financial_statements(code / date_from / date_to 指定可)
    - fetch_market_calendar(holiday_division 指定可)
  - DuckDB への保存関数（冪等）を実装:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - 保存時に取得時刻（fetched_at）を UTC で記録（ISO 8601, "Z" 表記）。
    - INSERT ... ON CONFLICT DO UPDATE によるアップサートで重複を排除。
    - PK 欠損行はスキップし、スキップ件数をログ出力。
  - 型変換ユーティリティ `_to_float` / `_to_int` を実装:
    - 空値や変換失敗は None を返す。
    - `_to_int` は "1.0" のような小数表現を許容して int に変換するが、小数部が 0 以外の場合は None を返す（切り捨てを防止）。

- データベーススキーマ (`kabusys.data.schema`)
  - DuckDB 用スキーマを定義し、初期化ユーティリティ `init_schema(db_path)` を提供。
  - レイヤー構成を明確化: Raw / Processed / Feature / Execution。
  - 多数のテーブル定義を追加（主要テーブルの一部）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK）、外部キー、カラム型を設定。
  - 頻出クエリ向けのインデックスを作成（例: code/date、status、signal_id 等）。
  - DB ファイルの親ディレクトリが存在しない場合は自動作成。":memory:" をサポート。
  - 既存テーブルへの接続のみを返す `get_connection(db_path)` を追加。

- 監査ログ（Audit）モジュール (`kabusys.data.audit`)
  - シグナル→発注→約定のトレーサビリティを完全に残す監査スキーマを実装。
  - トレーサビリティ階層（business_date / strategy_id / signal_id / order_request_id / broker_order_id）を明示。
  - テーブル定義:
    - signal_events（戦略が生成したシグナルのログ）
    - order_requests（発注要求、order_request_id を冪等キーとして機能）
    - executions（証券会社からの約定情報、broker_execution_id をユニークキー）
  - 複数の整合性制約（チェック制約、外部キー、idempotency のための制約）を設計。
  - すべての TIMESTAMP は UTC 保存を強制（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 監査用インデックス群を追加（status / signal_id / broker_order_id / executed_at 等）。
  - `init_audit_schema(conn)` と独立DB初期化 `init_audit_db(db_path)` を提供。

- データ品質チェック (`kabusys.data.quality`)
  - DataPlatform に基づいた品質チェック機能を実装。
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 実装されたチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は許容）。
    - check_spike: 前日比スパイク検出（LAG を用いた前日比算出、デフォルト閾値 50%）。
    - check_duplicates: raw_prices の主キー重複検出（ON CONFLICT では通常排除されるが念のため）。
    - check_date_consistency: 将来日付検出および market_calendar と整合しない非営業日データ検出（market_calendar が存在しない場合はスキップ）。
  - run_all_checks(conn, target_date, reference_date, spike_threshold) で一括実行し、検出された QualityIssue のリストを返す。すべてのチェックは Fail-Fast ではなく全問題を収集して返す設計。
  - 各チェックはサンプル行（最大 10 件）を返却し、重大度に応じて呼び出し元が ETL 停止や警告出力を判断可能。

- その他モジュール作成
  - 空のパッケージ初期化ファイルを追加: execution, strategy, monitoring（将来的な拡張ポイントとして公開APIに含める構成）。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Security
- 初期リリースのため該当なし。

注記:
- 本リリースは初期実装を中心とした機能追加（データ取得・保存・スキーマ定義・監査・品質チェック・環境設定）を含みます。各モジュールはユニットテスト・運用テストを通じての検証が推奨されます。