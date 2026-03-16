# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システムのコアライブラリを追加しました。以下は主要な追加点・設計方針の要約です。

### Added
- パッケージのメタ情報
  - kabusys.__version__ = "0.1.0"
  - パッケージ公開モジュール: data, strategy, execution, monitoring（strategy/execution は初期は空パッケージ）。

- 環境設定管理 (kabusys.config)
  - Settings クラスにより環境変数から設定値を取得する API を提供（settings インスタンス経由）。
  - 必須環境変数の取得を行う _require() を実装。
  - 提供される設定項目（プロパティ）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (既定: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (既定: data/kabusys.duckdb), SQLITE_PATH (既定: data/monitoring.db)
    - KABUSYS_ENV (development | paper_trading | live)、LOG_LEVEL（DEBUG/INFO/...）の検証
    - ヘルパー: is_live / is_paper / is_dev
  - .env 自動読み込み機能を実装
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境 > .env.local > .env
    - OS 環境変数は保護され、.env.local の上書きから除外可能
    - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - .env のパースは export 形式、クォート、インラインコメント、エスケープに対応

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API ベース実装: 認証、ページネーション、HTTP リクエスト/レスポンス処理、JSON デコード
  - レート制限: 120 req/min を守る固定間隔スロットリング (_RateLimiter)
  - 再試行ロジック:
    - 最大試行回数: 3 回
    - 指数バックオフ (base=2.0 秒)
    - リトライ対象: HTTP 408/429 および 5xx
    - 429 の場合は Retry-After ヘッダを優先
  - トークン管理:
    - get_id_token(refresh_token=None) による ID トークン取得（POST /token/auth_refresh）
    - モジュールレベルの ID トークンキャッシュを導入（ページネーション間で共有）
    - 401 受信時はトークンを自動リフレッシュして一度だけリトライ（無限再帰防止）
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes(date_from/ date_to / code)
    - fetch_financial_statements(date_from/ date_to / code)
    - fetch_market_calendar(holiday_division)
    - 各関数は取得件数のログ出力
  - DuckDB 保存関数（冪等: ON CONFLICT DO UPDATE）:
    - save_daily_quotes(conn, records): raw_prices へ保存、fetched_at を UTC ISO8601 で記録
    - save_financial_statements(conn, records): raw_financials へ保存
    - save_market_calendar(conn, records): market_calendar へ保存（取引日／半日／SQ 日判定）
  - 型変換ユーティリティ: _to_float, _to_int（安全な変換、空値は None）

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataPlatform 構成に準拠した多層スキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム制約（CHECK、PRIMARY KEY、FOREIGN KEY）を多数導入してデータ整合性を担保
  - インデックスを頻出クエリに合わせて作成
  - init_schema(db_path) でディレクトリ自動作成 & テーブル作成（冪等）
  - get_connection(db_path) を提供（既存 DB への接続）

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計方針および実装:
    - 差分更新（最終取得日からの差分取得）、デフォルトのバックフィル（3 日）で後出し修正を吸収
    - 市場カレンダーは先読み（デフォルト 90 日）して営業日判断に使用
    - 品質チェックを実行（オプション）し、問題を収集して呼び出し元が判断可能
    - id_token を引数で注入可能（テスト容易性）
  - 主な API:
    - run_prices_etl(conn, target_date, id_token=None, date_from=None, backfill_days=3)
    - run_financials_etl(conn, target_date, ...)
    - run_calendar_etl(conn, target_date, ...)
    - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
  - ETLResult データクラスを導入（取得/保存件数、品質問題、エラーの集約）
  - 各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他ステップは継続

- 監査ログ（トレーサビリティ）機能 (kabusys.data.audit)
  - 戦略→シグナル→発注リクエスト→証券会社の約定まで追跡できる監査テーブルを追加
  - テーブル:
    - signal_events (戦略が生成した全シグナル／棄却やエラーも記録)
    - order_requests (冪等キー order_request_id を持つ発注要求)
    - executions (証券会社の約定ログ、broker_execution_id を冪等キーとして保持)
  - created_at / updated_at を持ち、INIT 時に SET TimeZone='UTC' を実行（すべて UTC で保存）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供
  - ステータス列や複数の制約 (CHECK、FOREIGN KEY) により監査データの一貫性を確保
  - 監査用のインデックスを作成（検索・結合を高速化）

- データ品質チェック (kabusys.data.quality)
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）
  - 実装済みチェック:
    - check_missing_data(conn, target_date=None): raw_prices の OHLC 欠損検出（volume は対象外）
    - check_spike(conn, target_date=None, threshold=0.5): 前日比スパイク検出（LAG による比較）
  - 各チェックは Fail-Fast ではなく問題を全件収集してリストで返す（呼び出し元が重大度に応じて対応）
  - SQL はパラメータバインドを使用

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Notes / ドキュメント的注意事項
- デフォルトのデータベースファイル: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可能）
- ログレベルや環境設定は Settings による検証があるため、不正値は起動時に例外が発生します。
- J-Quants の API レート制限・リトライ・ページネーション・トークンリフレッシュなどの挙動は実運用を想定して設計されていますが、証券会社 API と接続する execution 層の実装は本バージョンでは含まれていません（execution/strategy パッケージは準備済み）。
- ETL 実行中に品質チェックがエラーを返しても ETL 自体は可能な限り継続し、ETLResult に問題を集約します。呼び出し側で処理を停止するか通知するか判断してください。

もしリリースノートに追加したい詳細（例: 実際の動作ログ例、互換性や今後の予定、マイグレーション手順など）があれば教えてください。必要に応じてセクションを追記します。