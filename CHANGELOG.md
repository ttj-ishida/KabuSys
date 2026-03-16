# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の慣習に従っています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買システムの基礎モジュール群を導入します。主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__）。バージョンは `0.1.0`。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを追加。
  - 自動ロードの優先順位は OS 環境変数 > .env.local > .env。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動 .env ロード無効化をサポート（テスト用）。
  - .env パーサーは以下をサポート／考慮:
    - 空行・コメント行の無視、`export KEY=val` 形式のサポート。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなしの場合の行内コメント扱い（`#` の前が空白/タブの場合をコメントと判定）。
  - 必須環境変数の取得時に未設定だと ValueError を送出する `_require()` を実装。
  - 設定値（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）をプロパティとして提供。
  - DB パスのデフォルト値（DuckDB: `data/kabusys.duckdb`, SQLite: `data/monitoring.db`）を設定。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値チェック）を実装。`is_live` / `is_paper` / `is_dev` ヘルパーを追加。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API クライアントを実装（`_BASE_URL = https://api.jquants.com/v1`）。
  - レート制御: 固定間隔スロットリング `_RateLimiter`（120 req/min をデフォルト）を導入。
  - リトライロジック: 指数バックオフ（最大 3 回）、対象ステータスは 408/429/5xx。429 の場合は Retry-After ヘッダを優先。
  - 401 応答時の自動トークンリフレッシュ（1 回まで）と ID トークンのモジュールレベルキャッシュ。
  - JSON レスポンスのエラーハンドリングと適切な例外発生。
  - ページネーション対応の取得関数を提供:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (四半期財務)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB へ冪等に保存する save_* 関数を追加（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes → raw_prices テーブルへ保存（fetched_at を UTC タイムスタンプで記録）
    - save_financial_statements → raw_financials
    - save_market_calendar → market_calendar
  - 数値変換ユーティリティ `_to_float`, `_to_int` を実装（安全な変換・空値処理・小数の意図的切り捨て回避など）。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層を想定したスキーマを定義（多数のテーブル DDL を含む）。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリ向け）を含む。
  - init_schema(db_path) による初期化関数（親ディレクトリ自動作成、冪等）と既存接続向け get_connection を提供。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL の実装（差分取得、保存、品質チェックを統合）:
    - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェックの順で実行。各ステップは独立してエラーハンドリング。
    - 個別ジョブ: run_calendar_etl（先読みデフォルト 90 日）、run_prices_etl（バックフィルデフォルト 3 日）、run_financials_etl。
  - 差分取得ヘルパー: DB の最終取得日を基に自動で date_from を算出（初回は 2017-01-01 から取得）。
  - 営業日調整機能 `_adjust_to_trading_day`（market_calendar を参照して非営業日は直近の営業日に調整）。
  - ETL 結果を表す ETLResult データクラス（取得件数、保存件数、品質問題リスト、エラー一覧など）を追加。
  - 品質チェックモジュールを呼び出し、結果を ETLResult に格納。品質の重大度に応じた判定が可能。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - シグナルから約定までのトレースを行う監査テーブル群を定義:
    - signal_events（戦略が生成したシグナルログ）
    - order_requests（冪等キー order_request_id を含む発注要求ログ）
    - executions（証券会社からの約定ログ）
  - すべての TIMESTAMP を UTC で保存するために init_audit_schema は `SET TimeZone='UTC'` を実行。
  - 制約（外部キー、CHECK）やステータス遷移、インデックスを含む。init_audit_db による専用 DB 初期化も提供。

- 品質チェック (kabusys.data.quality)
  - データ品質チェック機能を実装（DuckDB 上の SQL による高速検査）:
    - 欠損データ検出（raw_prices の OHLC 欄）
    - スパイク検出（前日比の変動率が閾値を超えるもの、デフォルト閾値 50%）
    - （重複・将来日付・営業日外等のチェックはモジュール設計で言及）
  - QualityIssue データクラスで検出事項を表現（check_name, table, severity, detail, rows）。
  - 各チェックは fail-fast とせず、問題をリストで返す設計。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Notes / Migration
- 初回利用時はまず data.schema.init_schema(settings.duckdb_path) で DuckDB スキーマを作成してください。監査ログは init_audit_schema(conn) で追加可能です。
- J-Quants API の認証には `JQUANTS_REFRESH_TOKEN`（環境変数）が必須です。その他 Slack 連携等も環境変数を参照します（未設定時は起動時にエラーを送出）。
- ETL の差分取得や backfill の挙動は pipeline の引数（backfill_days, calendar_lookahead_days）でカスタマイズできます。
- 全ての TIMESTAMP は UTC で扱うことを前提に設計されています。

### Known issues
- なし（初版としての注意点: 実運用前に API レートや DB マイグレーション、外部ブローカー API の接続周りの追加実装・検証が必要）。

---------------------------------------------------------------------
この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時は動作確認・追加ドキュメントを元に文面を調整してください。