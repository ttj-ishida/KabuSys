# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
現在のパッケージバージョン: 0.1.0

## [0.1.0] - 2026-03-15
初回リリース。以下の主要機能とスキーマを追加しました。

### 追加
- パッケージ構成
  - パッケージルート: kabusys（__version__ = 0.1.0）
  - サブパッケージ: data, strategy, execution, monitoring（各サブパッケージの初期化ファイルを含む）

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを提供。
  - 自動ロード:
    - プロジェクトルートは __file__ を基準に `.git` または `pyproject.toml` を探索して特定。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能（テスト用）。
  - .env 解析機能:
    - 空行・コメント行（先頭の `#`）を無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - クォートなしの値では、スペースまたはタブで区切られた `#` をインラインコメントとして扱う。
  - 設定プロパティ（必須・任意）:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - DBパス: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - システム: KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - 利便性プロパティ:
    - settings.is_live / is_paper / is_dev

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本方針に基づくクライアントを実装:
    - レート制限遵守（120 req/min -> 最小間隔 60/120 秒）
    - 再試行ロジック（最大 3 回、指数バックオフ、対象ステータス: 408, 429, >=500, およびネットワークエラー）
    - 401 応答時はリフレッシュトークンから id_token を再取得して 1 回リトライ
    - ページネーション対応（pagination_key を用いた連続取得）
    - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）
    - fetch_* 関数が取得日時（fetched_at）を UTC で記録し、Look-ahead Bias の防止を容易にする
  - 提供 API:
    - get_id_token(refresh_token: str | None) -> str
    - fetch_daily_quotes(id_token, code, date_from, date_to) -> list[dict]
    - fetch_financial_statements(id_token, code, date_from, date_to) -> list[dict]
    - fetch_market_calendar(id_token, holiday_division) -> list[dict]
  - DuckDB への保存関数（冪等 / ON CONFLICT DO UPDATE）:
    - save_daily_quotes(conn, records) -> int
      - raw_prices テーブルへ保存。PK (date, code) の欠損行はスキップしログ出力。
      - fetched_at は UTC ISO8601（Z）で保存。
    - save_financial_statements(conn, records) -> int
      - raw_financials テーブルへ保存。PK 欠損行をスキップ。
    - save_market_calendar(conn, records) -> int
      - market_calendar テーブルへ保存。HolidayDivision を基に is_trading_day / is_half_day / is_sq_day を決定。
  - ユーティリティ:
    - _to_float, _to_int: 変換に失敗した場合は None を返す安全な変換ロジック（"1.0" 等の float 文字列処理や小数切り捨て回避を考慮）

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層＋実行層のスキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・チェック制約・PRIMARY KEY を設定。
  - 頻出クエリ向けのインデックス群を定義（例: code×date、status 検索等）。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定パスに DB ファイルを作成（親ディレクトリ自動作成）。すべての DDL とインデックスを実行（冪等）。
      - ":memory:" によるインメモリ DB に対応。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続（スキーマ初期化は行わない）。初回は init_schema を推奨。

- 監査ログ / トレーサビリティ (kabusys.data.audit)
  - シグナルから約定までの追跡を行う監査テーブル群を定義:
    - signal_events（戦略が出した全シグナルを記録。棄却やエラーも含む）
    - order_requests（内部発注要求。order_request_id を冪等キーとして採用。注文種別に応じた価格チェック制約を設定）
    - executions（証券会社からの約定情報。broker_execution_id を一意の冪等キーとして記録）
  - 設計原則の反映:
    - すべての TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）
    - 削除しない前提（FK は ON DELETE RESTRICT）
    - updated_at カラムはアプリ側が更新時に current_timestamp をセットする想定
  - インデックスを定義（signal の日付・銘柄検索、status スキャン、broker_order_id／broker_execution_id 紐付けなど）
  - 公開 API:
    - init_audit_schema(conn: duckdb.DuckDBPyConnection) -> None
      - 既存接続に監査テーブルを追加（冪等）。
    - init_audit_db(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 監査専用の DB を作成し、監査スキーマを初期化して接続を返す。

### 変更
- 該当なし（初回リリース）

### 修正
- 該当なし（初回リリース）

### 既知の注意点 / 破壊的変更
- 設定チェック:
  - KABUSYS_ENV, LOG_LEVEL の値検証が厳格です。無効な値を設定すると ValueError を送出します。
- .env 自動ロード:
  - 自動ロードはデフォルトで有効です。テスト時や意図的に環境変数のみを使用したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB 初期化:
  - init_schema は親ディレクトリを自動生成します。既存データの扱いには注意してください（DDL は IF NOT EXISTS を使用しているため一般的には安全です）。

--- 

この CHANGELOG はコードベースの現状から推測できる機能と設計方針を元に作成しています。実際のリリースノート作成時は、差分コミットや変更履歴（Git log）に基づく追記・修正を推奨します。