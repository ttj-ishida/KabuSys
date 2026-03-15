CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
次のバージョンに関するエントリはリリース済みのもののみ記載しています。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

0.1.0 - YYYY-MM-DD
------------------

初回公開リリース。日本株自動売買システムのコア基盤を実装しました。主な追加点は次の通りです。

Added
- パッケージ基礎
  - パッケージメタ情報を追加 (kabusys.__init__ に __version__ = "0.1.0"、公開モジュール定義)。
  - strategy、execution、monitoring パッケージのプレースホルダを追加。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定値を読み込む自動ロード機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索するため、CWD に依存しません。
    - 読み込み順序: OS 環境変数 > .env.local > .env。既存の OS 環境変数は保護されます。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行コメント等に対応する堅牢なパーサーを実装。
  - Settings クラスを提供し、アプリで使用する設定値をプロパティ経由で取得可能に:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを設定
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の値検証を実装
    - is_live, is_paper, is_dev ヘルパーを追加
  - 必須環境変数未設定時は ValueError を送出する保護ロジックを実装。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API クライアントを実装。以下機能を提供:
    - 株価日足（OHLCV）取得 (fetch_daily_quotes)
    - 財務データ（四半期 BS/PL）取得 (fetch_financial_statements)
    - JPX マーケットカレンダー取得 (fetch_market_calendar)
  - 設計上の特徴:
    - レート制限対応: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
    - リトライロジック: 指数バックオフ（base=2）、最大3回、408/429/5xx を対象にリトライ。
      - 429 の場合は Retry-After ヘッダを優先。
    - 401（Unauthorized）受信時はトークンを自動リフレッシュして1回リトライ（無限再帰防止）。
    - ID トークンのモジュールレベルキャッシュを導入し、ページネーション間で共有。
    - ページネーション対応（pagination_key を用いた継続取得）。
    - 取得日時（fetched_at）を UTC 形式で記録し、Look-ahead Bias に配慮したトレーサビリティを保持。
    - JSON デコード失敗時やネットワークエラーに対する明示的なエラーハンドリング。

  - DuckDB への保存関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - INSERT ... ON CONFLICT DO UPDATE により冪等性を確保。
    - PK 欠損レコードはスキップし、その件数をログ出力。
    - market_calendar では HolidayDivision を解釈して is_trading_day / is_half_day / is_sq_day を算出して保存。

  - 値変換ユーティリティ:
    - _to_float / _to_int を実装。空値や変換不能値は None を返す。
    - _to_int は "1.0" のような文字列は float 経由で変換し、小数部が 0 以外の場合は None を返す等の安全策を講じる。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataLayer（Raw / Processed / Feature / Execution）を想定したテーブル定義を追加:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY / CHECK / FOREIGN KEY）を適切に設定。
  - 頻出クエリに備えたインデックス定義を追加。
  - init_schema(db_path) で DuckDB を初期化（親ディレクトリの自動作成、冪等なテーブル作成）。
  - get_connection(db_path) を提供（既存 DB への接続、初期化は行わない）。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - 監査用テーブル群と初期化ロジックを実装:
    - signal_events（戦略が生成したシグナルのログ）
    - order_requests（発注要求、order_request_id を冪等キーとして実装）
    - executions（証券会社からの約定ログ、broker_execution_id を一意キーに）
  - order_requests に対するチェック制約（limit/stop/market 順序や価格必須条件）を実装。
  - 監査用インデックスを追加（status/日付/strategy/broker_order_id などの検索最適化）。
  - init_audit_schema(conn) は SET TimeZone='UTC' を実行し、すべての TIMESTAMP を UTCで扱うことを保証。
  - init_audit_db(db_path) を提供（監査専用 DB の初期化）。

Changed
- （初回リリースのため変更なし）

Fixed
- （初回リリースのため修正なし）

Security
- 認証トークンの自動リフレッシュを安全に行う設計（無限再帰を防止）。  

Notes / 使用上の注意
- settings.jquants_refresh_token など必須環境変数が未設定の場合、ValueError が発生します。 .env.example を参照して設定してください。
- DuckDB の初期化は init_schema() を使用してください。既存 DB に接続するだけの場合は get_connection() を利用します。
- J-Quants API のレート制限やリトライは実装されていますが、外部環境や証券会社 API への接続時の追加制御（発注レート等）は別途実装が必要です。
- strategy / execution / monitoring モジュールはプレースホルダ実装のため、具体的な戦略ロジックや発注実装は今後追加予定です。

今後の予定 (短期ロードマップ)
- strategy レイヤの特徴量生成・戦略実装テンプレートを追加
- execution レイヤのブローカー接続ラッパー（kabuステーション連携等）実装
- 監査ログの挿入ユーティリティ／抽象化レイヤ追加
- 単体テストおよび CI/CD の整備

問い合わせ・貢献
- このリポジトリへのフィードバックやプルリクエスト歓迎します。