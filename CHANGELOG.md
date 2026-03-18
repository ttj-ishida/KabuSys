Keep a Changelog
=================

すべての変更は厳密に記録されます。  
このファイルは Keep a Changelog の形式に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
    - パブリック API: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースの実装:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなしでのインラインコメント扱いは直前が空白/タブの場合にのみ '#' をコメント扱いにする挙動。
  - _load_env_file にて protected（既存 OS 環境変数）を保護する上書きロジックを実装（.env と .env.local の優先度処理）。
  - Settings クラスを実装し、以下の設定を環境変数から提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)
    - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）
    - LOG_LEVEL の妥当性チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live/is_paper/is_dev

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本設計:
    - API レートリミット (120 req/min) を厳守する固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ）を導入（最大3回、HTTP 408/429 + 5xx を対象）。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して1回だけ再試行する機能。
    - ページネーション対応（pagination_key を使った継続取得）。
    - 取得時刻 fetched_at を UTC ISO8601 で記録し、Look-ahead Bias を抑制。
    - DuckDB への保存は冪等 (ON CONFLICT DO UPDATE)。
  - 公開 API:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(id_token: Optional[str], code: Optional[str], date_from: Optional[date], date_to: Optional[date]) -> list[dict]
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
    - save_daily_quotes(conn, records) -> int
    - save_financial_statements(conn, records) -> int
    - save_market_calendar(conn, records) -> int
  - ユーティリティ:
    - _to_float / _to_int による堅牢な型変換（空値・不正値ハンドリング、"1.0" のような文字列を正しく扱う等）。
    - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）。
    - HTTP 通信は urllib を使用し、JSON デコード失敗時の明確なエラーメッセージを出力。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS 取得・前処理・DB 保存パイプライン実装。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等を防御。
    - SSRF 対策: リダイレクト先のスキーム検査・プライベートIP検査（_SSRFBlockRedirectHandler / _is_private_host）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後サイズ再検査（Gzip bomb 対策）。
  - データ処理:
    - URL 正規化とトラッキングパラメータ除去（_normalize_url, _TRACKING_PARAM_PREFIXES）。
    - 記事ID を正規化 URL の SHA-256 の先頭32文字で生成（_make_article_id）し冪等性を保証。
    - テキスト前処理（URL除去、空白正規化）を行う preprocess_text。
    - pubDate のパースと UTC 換算（_parse_rss_datetime）。
  - DB 保存実装（DuckDB）:
    - save_raw_news(conn, articles) はチャンク/トランザクションで INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDを返す。
    - save_news_symbols / _save_news_symbols_bulk は (news_id, code) の紐付けをチャンクで保存し、実挿入数を返す。
    - バルク INSERT のチャンク化・トランザクションまとめによりオーバーヘッドを抑制。
  - 銘柄抽出:
    - 4桁数字を正規表現で抽出し、既知コードセット known_codes に存在するものだけを返す extract_stock_codes。
  - 統合ジョブ:
    - run_news_collection(conn, sources=None, known_codes=None, timeout=30) は複数 RSS ソースを独立して処理し、失敗したソースはスキップして収集を継続。新規保存件数を返す。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataPlatform.md に基づいた 3 層（Raw / Processed / Feature）＋ Execution レイヤのテーブル DDL を実装。
  - テーブル群（主なもの）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）とインデックス（頻出クエリ向け）を定義。
  - init_schema(db_path) によりディレクトリ作成→接続→DDL/インデックス実行（冪等）を行い DuckDB 接続を返す。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプラインヘルパ（src/kabusys/data/pipeline.py）
  - ETL の基本設計と差分更新ロジックを実装。
  - ETLResult データクラス:
    - 実行結果（取得数/保存数/品質問題/エラー）を集約し、辞書化できる to_dict を提供。
  - テーブル存在チェック・最大日付取得ユーティリティ（_table_exists / _get_max_date）。
  - 市場カレンダーを参照して非営業日を過去方向に調整する _adjust_to_trading_day。
  - 差分更新関連ユーティリティ:
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
  - run_prices_etl(...) を部分実装:
    - 最終取得日からの backfill_days による再取得（デフォルト backfill_days=3）、
    - 取得開始日の自動算出、J-Quants からの差分取得と保存の流れ（fetch_daily_quotes → save_daily_quotes）。
    - 初回ロードの下限日 _MIN_DATA_DATE = 2017-01-01 を使用。
    - カレンダー先読み用定数 _CALENDAR_LOOKAHEAD_DAYS = 90。

Security
- ニュース収集モジュールにおける SSRF, XML Bomb, Gzip Bomb, 大量応答による DoS 対策を実装。
- .env 読み込みにおける既存 OS 環境変数保護機構。

Internal
- 各モジュールは duckdb の DuckDBPyConnection を引数にとることで DB 接続注入が可能（テスト容易性）。
- HTTP/API レイヤは urllib ベースで実装され、リトライ・レート制御・トークン自動更新の組合せで堅牢性を高めている。
- 大量データ挿入はチャンク化・トランザクション制御・INSERT ... RETURNING を活用し実挿入数を正確に把握。

Notes / Breaking Changes
- 本バージョンは初期リリースのため後方互換問題はなし（以降の変更はこの CHANGELOG に追記）。

Acknowledgements
- 本リリースは DataPlatform.md / DataSchema.md 等の設計仕様に基づく実装を含みます。

--- 

（以降のリリースはこのファイルに日付と変更内容を追記してください）