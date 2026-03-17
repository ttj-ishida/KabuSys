KEEP A CHANGELOG
すべての変更はセマンティックバージョニング（https://semver.org/）に従って管理しています。

v0.1.0 - 2026-03-17
==================

Added
-----
- 新規パッケージ "kabusys" を初期リリース。
  - パッケージ概要説明（src/kabusys/__init__.py）。
  - バージョン: 0.1.0。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動読み込みルール:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装 (_parse_env_line):
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートのエスケープ処理に対応。
    - クォート無しのインラインコメント取り扱い（# の前が空白/タブの場合はコメント扱い）。
  - .env 読み込み関数で既存OS環境変数を保護する protected オプションを実装。
  - 必須環境変数取得ヘルパ (_require) と各種プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を参照。
    - デフォルト値: KABUS_API_BASE_URL, DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db)。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）。
    - LOG_LEVEL のバリデーション（DEBUG/INFO/...）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 基本機能:
    - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装。
    - ページネーション対応（pagination_key を用いた取得ループ）。
  - レート制御とリトライ:
    - 固定間隔スロットリングで 120 req/min（_RateLimiter）。
    - 最大 3 回のリトライ、指数バックオフ、HTTP 408/429 や 5xx を再試行対象に設定。
    - 429 の場合は Retry-After ヘッダを優先。
  - 認証:
    - リフレッシュトークンから ID トークンを取得する get_id_token（POST）。
    - 401 受信時は自動でトークンを1回リフレッシュしてリトライする仕組み。
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間でトークン共有）。
  - DuckDB 保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を追加。
    - 冪等性を確保するため INSERT ... ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC ISO8601 形式で記録（Z 表記）。
  - データ変換ユーティリティ:
    - _to_float / _to_int: 入力の堅牢な数値変換ロジック（空文字や不正値は None、"1.0" を int に変換する処理など）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news / news_symbols に保存する機能を実装。
  - セキュリティ対策:
    - defusedxml を利用して XML Bomb 等を緩和。
    - SSRF 対策: URL スキーム検証 (http/https 限定)、ホスト/IP のプライベート判定 (_is_private_host)、リダイレクト先検査用ハンドラ (_SSRFBlockRedirectHandler)。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10 MB) を設け、読み込み超過で中止。
    - gzip 解凍時にもサイズ検査を行う（Gzip bomb 対策）。
  - URL 正規化と記事ID:
    - トラッキングパラメータ（utm_*, fbclid, gclid, ref_*, _ga）を除去してクエリをソートする _normalize_url。
    - 正規化後の SHA-256 ハッシュ先頭32文字を記事IDとして生成 (_make_article_id)。
  - テキスト前処理:
    - URL 除去、連続空白を単一スペース化する preprocess_text。
  - DB 保存:
    - save_raw_news はチャンク分割（_INSERT_CHUNK_SIZE=1000）＆トランザクション内で INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて新規挿入IDを返す実装。
    - save_news_symbols / _save_news_symbols_bulk は記事と銘柄コードの紐付けをチャンク挿入で行い、実際に挿入された件数を返す。
  - 銘柄抽出:
    - 4桁数字（日本株銘柄）を抽出する extract_stock_codes を実装。known_codes によるフィルタリングで有効なコードのみ返す。
  - 統合ジョブ:
    - run_news_collection で複数ソースを順次処理。各ソースは独立して例外処理を行い、1ソースの失敗が他へ影響しないように実装。

- DuckDB スキーマと初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層＋実行層のテーブル群を定義（Raw / Processed / Feature / Execution）。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY / CHECK / FOREIGN KEY）を追加。
  - よく使う検索のためのインデックスを定義。
  - init_schema(db_path) でディレクトリ作成→接続→テーブル作成→インデックス作成を行う（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計方針と差分更新ロジックを実装。
  - ETLResult dataclass を導入（各種取得数・保存数・品質問題・エラーを保持、辞書化メソッド付き）。
  - テーブル存在確認や最大日付取得ユーティリティ (_table_exists, _get_max_date) を提供。
  - market_calendar を用いた営業日調整ヘルパ (_adjust_to_trading_day) を実装（最大30日遡り）。
  - 差分更新ヘルパ get_last_price_date / get_last_financial_date / get_last_calendar_date を追加。
  - run_prices_etl を実装（差分算出、backfill のデフォルト 3 日、jq.fetch_daily_quotes → jq.save_daily_quotes の流れ）。
  - ETL は品質チェック（quality モジュール）と分離して動作する設計（品質問題を検出しても収集は継続）。

Changed
-------
- （初期リリースのため該当なし）

Fixed
-----
- （初期リリースのため該当なし）

Security
--------
- RSS や外部URL取り扱いに関して複数のセキュリティ対策を導入（defusedxml, SSRF チェック、レスポンスサイズ制限、gzip 検査、許可スキーム制限）。
- .env 読み込み時に OS 環境変数保護用の protected オプションを導入し、環境上書きの安全性を向上。

Deprecated
----------
- （初期リリースのため該当なし）

注意点 / 既知の問題
------------------
- run_prices_etl の戻り値に関して: 関数シグネチャは (取得数, 保存数) のタプルを返す想定ですが、実装末尾が "return len(records), " のように途中で終わっており意図した保存数を返していない可能性があります。リリース後の修正が必要です。
- pipeline モジュールは run_prices_etl のほかの ETL ジョブ（financials, calendar 等）も想定されていますが、本リリースでは一部のみ実装済みです。拡張と品質チェックモジュール連携は今後の作業対象です。
- ユニットテストや統合テスト用のテストスイートはこのリリースに含まれていません。外部API呼び出しやネットワーク処理はモック可能（例: news_collector._urlopen の差し替え）に設計されていますが、実利用前にテストの追加を推奨します。

開発者向け備考
--------------
- 設定は settings = Settings() から参照可能。自動 .env ロードをテスト時に抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート/認証/ページネーションロジックは jquants_client に集中しています。テスト時は get_id_token や _urlopen 等をモックしてトークンや HTTP レスポンスを制御してください。
- DuckDB のスキーマ初期化は init_schema を呼ぶことで行えます。既存DBに対しては get_connection を使用してください。

--- End of changelog for v0.1.0 ---