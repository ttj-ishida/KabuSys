CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog のフォーマットに準拠し、セマンティック バージョニングを使用します。

[unreleased]: https://example.com/compare/v0.1.0...HEAD

v0.1.0 - 2026-03-16
-------------------

Added
- 初回リリース。パッケージ名: kabusys（__version__ = 0.1.0）
- パッケージ構成を追加:
  - kabusys.config: 環境変数／設定管理
    - .env/.env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化
    - .env パーサーの улучшения:
      - export KEY=val 形式対応
      - シングル/ダブルクォートの解釈（バックスラッシュエスケープ対応）
      - インラインコメントの扱い（クォート外での # を考慮）
    - 環境変数取得ヘルパー（必須値チェックを行い未設定時に ValueError を投げる）
    - 設定プロパティ群: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL,
      SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（検証あり）, LOG_LEVEL（検証あり）
    - env（development / paper_trading / live）とそれに基づく is_live/is_paper/is_dev 判定

  - kabusys.data.jquants_client: J-Quants API クライアント
    - API レート制限対応（固定間隔スロットリングで 120 req/min を守る RateLimiter）
    - 汎用 HTTP リクエストラッパー（JSON デコード、タイムアウト、エラーハンドリング）
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408, 429, 5xx）
    - 401 時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ
    - ページネーション対応の取得関数:
      - fetch_daily_quotes（株価日足: OHLCV）
      - fetch_financial_statements（四半期財務）
      - fetch_market_calendar（JPX マーケットカレンダー）
    - DuckDB への保存関数（冪等性確保: ON CONFLICT DO UPDATE）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - データ整合用ユーティリティ: _to_float, _to_int
    - 取得時刻（fetched_at）は UTC で記録（Look-ahead Bias 対策）

  - kabusys.data.schema: DuckDB スキーマ管理・初期化
    - 3 層＋実行層を想定したテーブル定義（Raw / Processed / Feature / Execution）
    - 主要テーブル（抜粋）:
      - raw_prices, raw_financials, raw_news, raw_executions
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - features, ai_scores
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - パフォーマンス向けインデックス群を定義
    - init_schema(db_path) によりディレクトリ生成→テーブル作成→接続を返す（冪等）
    - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）

  - kabusys.data.audit: 監査ログ（トレーサビリティ）
    - シグナル→発注要求→約定までの監査テーブル群とインデックスを定義
      - signal_events（戦略シグナルの永続化）
      - order_requests（order_request_id を冪等キーとする発注要求）
      - executions（約定ログ、broker_execution_id を冪等キーとして扱う）
    - init_audit_schema(conn) と init_audit_db(db_path) による初期化
    - すべての TIMESTAMP は UTC を前提（init で SET TimeZone='UTC' を実行）

  - kabusys.data.quality: データ品質チェック
    - QualityIssue データクラス（check_name, table, severity, detail, rows）
    - 主なチェック実装:
      - check_missing_data: raw_prices の OHLC 欄欠損検出（volume は除外）
      - check_spike: 前日比でのスパイク検出（デフォルト閾値 50%）
      - check_duplicates: raw_prices の主キー重複検出
      - check_date_consistency: 将来日付・market_calendar と矛盾する非営業日データ検出
    - run_all_checks で全チェックをまとめて実行、error/warning をログ出力
    - 各チェックは問題を全件収集（Fail-Fast しない）し、呼び出し元で扱いを決められる設計

  - パッケージ空のプレースホルダモジュールを追加:
    - kabusys.execution.__init__.py
    - kabusys.strategy.__init__.py
    - kabusys.monitoring.__init__.py

Notes / Usage
- 初回の DB 初期化:
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
- 監査ログの初期化（既存接続に追加）:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn)
- 環境変数の自動ロードが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 時刻関連:
  - 監査テーブルや fetched_at は UTC で記録します。DB 初期化時にタイムゾーンを UTC に設定します。

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Deprecated
- 初回リリースのため該当なし

Breaking Changes
- 初回リリースのため該当なし

Contributors
- このリリースの変更はコードベースから推測して作成しました（自動生成ドキュメント）。