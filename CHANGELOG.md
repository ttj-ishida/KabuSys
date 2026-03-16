CHANGELOG
=========

すべての重要な変更点はここに記載します。  
フォーマットは Keep a Changelog に準拠しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-16
------------------

Added
- パッケージ初版リリース (kabusys v0.1.0)
  - パッケージ情報
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - パブリック API: data, strategy, execution, monitoring

  - 設定 / 環境管理 (kabusys.config)
    - .env ファイルまたは環境変数からの設定読み込みを実装。
      - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して判定。配布後も動作するよう CWD に依存しない実装。
      - 読み込み順序: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
      - export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応するパーサを実装。
    - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト含む)
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH / SQLITE_PATH（Path 型）
      - KABUSYS_ENV のバリデーション（development, paper_trading, live）
      - LOG_LEVEL のバリデーション（DEBUG, INFO, WARNING, ERROR, CRITICAL）
      - is_live / is_paper / is_dev のヘルパー

  - J-Quants API クライアント (kabusys.data.jquants_client)
    - API 呼び出しユーティリティを実装:
      - レート制限（固定間隔スロットリング）: 120 req/min を遵守する RateLimiter を実装。
      - リトライロジック: 指数バックオフ (最大 3 回)、対象ステータス 408/429/5xx を再試行。
      - 401 応答時はリフレッシュトークンで自動的に id_token を更新し 1 回リトライ（無限再帰防止の仕組みあり）。
      - ページネーション対応（pagination_key を利用して全件取得）。
      - JSON デコードエラー・ネットワーク例外のハンドリング。
      - id_token のモジュールレベルキャッシュを提供（ページネーション間で共有）。
    - データ取得関数:
      - fetch_daily_quotes: 株価日足（OHLCV）のページネーション取得。
      - fetch_financial_statements: 四半期財務データのページネーション取得。
      - fetch_market_calendar: JPX マーケットカレンダー取得（祝日・半日・SQ 等）。
      - 取得時に fetched_at を UTC タイムスタンプで付与して Look-ahead bias を防止する考慮。
    - DuckDB への永続化（冪等）関数:
      - save_daily_quotes / save_financial_statements / save_market_calendar
      - INSERT ... ON CONFLICT DO UPDATE を用いて冪等性を確保。
      - PK 欠損行のスキップとログ出力、型安全な変換ユーティリティ (_to_float/_to_int) を提供。

  - DuckDB スキーマ定義・初期化 (kabusys.data.schema)
    - DataSchema.md に基づく多層スキーマを提供（Raw / Processed / Feature / Execution 層）。
    - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル定義。
    - prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等を含む処理層・実行層のDDL定義。
    - 適切な制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）とインデックスを定義。
    - init_schema(db_path) により DB 作成（親ディレクトリ自動作成）とテーブル初期化を行う。init_schema は冪等。
    - get_connection(db_path) を提供（スキーマ初期化は行わない）。

  - ETL パイプライン (kabusys.data.pipeline)
    - 日次 ETL の実装:
      - 差分更新戦略: DB の最終取得日を見て差分のみ取得。デフォルトのバックフィルは backfill_days=3（API 後出し修正を吸収）。
      - 市場カレンダーを先読み（lookahead デフォルト 90 日）して営業日調整に使用。
      - run_prices_etl / run_financials_etl / run_calendar_etl を提供（各関数は差分判定・取得・保存を行う）。
      - run_daily_etl: カレンダー→株価→財務→品質チェックの順で実行。各ステップは独立したエラーハンドリングにより、1 ステップ失敗でも他ステップは継続。
      - ETLResult データクラスを導入し、取得数・保存数・品質問題・エラー一覧などを返却・ログ可能。
      - id_token 注入によりテスト容易性を確保。

  - 品質チェック (kabusys.data.quality)
    - DataPlatform.md に基づく品質チェック機能を提供。
      - チェック項目: 欠損データ検出、スパイク（前日比）検出、主キー重複、日付不整合 等。
      - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
      - check_missing_data: raw_prices の OHLC 欠損を検出（volume は許容）。
      - check_spike: LAG を使って前日比の変動率が閾値（デフォルト 50%）を超えるレコードを検出。
      - 各チェックは Fail-Fast とせず、問題をリストで返す（呼び出し元が重大度に応じた対応を決定）。

  - 監査ログ / トレーサビリティ (kabusys.data.audit)
    - シグナルから約定に至るフローを UUID 連鎖でトレースする監査スキーマを実装。
      - signal_events, order_requests, executions のテーブル定義。
      - order_request_id を冪等キーとして扱う設計。FK は ON DELETE RESTRICT、監査ログは削除しない前提。
      - すべての TIMESTAMP を UTC で保存するため init_audit_schema で SET TimeZone='UTC' を実行。
      - インデックスを含む初期化関数 init_audit_schema(conn) と専用 DB 初期化 init_audit_db(db_path) を提供。
      - 発注ステータス遷移や制約（limit/stop の price 必須チェックなど）を DDL レベルで表現。

  - パッケージ構成
    - data サブパッケージを中心に、strategy, execution, monitoring のプレースホルダ __init__ を用意。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- 新規リリースのため該当なし。

Notes / 備考
- DuckDB をデータ層に採用しており、ファイルパスのデフォルトは settings.duckdb_path = data/kabusys.duckdb。
- J-Quants API のレート制限・リトライ・トークン更新の挙動は実運用を想定した堅牢な実装になっていますが、外部ネットワーク環境や証券会社 API については別途接続・例外ハンドリングのテスト推奨。
- 品質チェックは ETL を停止させない設計（問題の収集を優先）なので、重大な品質問題を検出した場合は呼び出し元で運用ルールに従って対応してください。