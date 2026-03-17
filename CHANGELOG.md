KEEP A CHANGELOG形式に準拠した CHANGELOG.md（日本語）を作成しました。コードの構造・コメント・実装から推測して記載しています。

Keep a Changelog に準拠
======================

Unreleased
----------

- Bug: run_prices_etl の戻り値が仕様（(int, int)）と合わず、現在は取得件数のみを返す不具合が確認されました（ソース上で "return len(records)," としているため単要素のタプルが返ります）。呼び出し側で保存件数を期待する箇所がある場合は注意してください（修正予定: 正しく (fetched, saved) を返す）。
- Improvement (予定): pipeline.run_* 系の追加の単体テストおよび end-to-end テストを強化予定（id_token 注入・ネットワークモックを用いたテスト性向上）。

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリース。
  - パッケージ名: KabuSys（__version__ = "0.1.0"）。
  - パッケージの公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理モジュール (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に決定）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサは export プレフィックス、クォート文字列、インラインコメント、エスケープ等に対応。
  - 必須設定を取得する _require と Settings クラスを実装。主要な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出し共通処理 (_request) を実装:
    - レート制限（固定間隔スロットリング）を実装（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx 等を対象）。
    - 401 受信時はリフレッシュ (id_token) を行い1回だけ再試行。
    - JSON デコードエラーハンドリング。
  - get_id_token: リフレッシュトークンから ID トークンを取得する POST 実装。
  - データ取得関数:
    - fetch_daily_quotes (株価日足、ページネーション対応)
    - fetch_financial_statements (財務データ、ページネーション対応)
    - fetch_market_calendar (JPX マーケットカレンダー)
    - 取得時に pagination_key を用いたページネーション処理を実装。
  - DuckDB への保存関数（冪等性を考慮、ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - データ型変換ユーティリティ: _to_float / _to_int（堅牢なパースと不正値処理）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集と DB 保存の実装:
    - fetch_rss: RSS 取得と XML パース（defusedxml を使用）。
    - セキュリティ対策:
      - URL スキーム検証（http/https のみ許可）。
      - SSRF 対策: リダイレクト先のスキーム・ホスト検証（内部アドレスへの到達を防止）。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB、gzip 解凍後も検査）。
      - 受信ハンドラには _SSRFBlockRedirectHandler を使用。
    - URL 正規化と記事ID生成:
      - _normalize_url によるトラッキングパラメータ除去（utm_ 等）・ソート・フラグメント除去。
      - _make_article_id は正規化 URL の SHA-256 先頭32文字を採用。
    - テキスト前処理: URL 除去、空白正規化。
  - DB 保存:
    - save_raw_news: チャンク化とトランザクションを使い INSERT ... ON CONFLICT DO NOTHING RETURNING id で新規挿入IDを返す（バルク処理、チャンクサイズ制限）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを INSERT ... ON CONFLICT DO NOTHING RETURNING で保存（トランザクション単位）。
  - 銘柄抽出:
    - extract_stock_codes: 正規表現で 4 桁の数字を抽出し、既知銘柄セットでフィルタ（重複除去）。
  - run_news_collection: 複数 RSS ソースを順次処理し、例外をソース単位で捕捉して他ソースへ影響を与えない設計。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataPlatform.md に基づく 3 層 + 実行レイヤのスキーマを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）とインデックスを定義。
  - init_schema(db_path) でファイルパスの親ディレクトリ作成と全DDLの実行（冪等）。
  - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass: ETL 実行結果の構造化（品質問題の集約、エラー一覧、has_errors 判定など）。
  - 差分更新ヘルパー:
    - _table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date
  - 市場カレンダー補正: _adjust_to_trading_day（非営業日を直近の営業日に調整）。
  - run_prices_etl: 差分取得ロジック（DBの最終取得日から backfill_days を考慮した date_from 自動算出）、jquants_client を用いた取得・保存フローの実装。
    - デフォルト backfill_days = 3、最小データ開始日 _MIN_DATA_DATE = 2017-01-01。
    - カレンダーの先読み設定 (_CALENDAR_LOOKAHEAD_DAYS = 90)。

Changed
- N/A（初回リリースのため該当なし）。

Fixed
- N/A（初回リリースのため該当なし）。

Security
- ニュース収集で defusedxml を利用して XML 関連攻撃（XML bomb 等）対策を実装。
- RSS フェッチで SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト先検証）を導入。
- .env ロードで OS 環境変数を保護する protected 機構。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを止められる。

Database / Migration Notes
- 初回利用時は必ず init_schema(db_path) を呼び、スキーマを作成してください。既存スキーマがある場合は冪等でスキップされます。
- デフォルトの DuckDB パスは data/kabusys.duckdb（Settings.duckdb_path）。
- raw_* テーブルは jquants_client の save_* 関数で ON CONFLICT により上書きされる設計のため、再実行は安全です（冪等性）。

API（主な公開関数）
- kabusys.config.settings (Settings インスタンス)
- kabusys.data.jquants_client:
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int
- kabusys.data.news_collector:
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list[str]
  - save_news_symbols(conn, news_id, codes) -> int
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30) -> dict[str, int]
  - extract_stock_codes(text, known_codes) -> list[str]
- kabusys.data.schema:
  - init_schema(db_path) -> duckdb.DuckDBPyConnection
  - get_connection(db_path) -> duckdb.DuckDBPyConnection
- kabusys.data.pipeline:
  - ETLResult dataclass
  - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - run_prices_etl(conn, target_date, ...)

Known issues / Notes
- run_prices_etl の戻り値バグ（上記 Unreleased に記載）。ETLResult などを返す上位集約の実装・利用時に影響する可能性あり。呼び出し側で保存件数を使う場合は注意／修正を待つこと。
- pipeline モジュールの追加 ETL ジョブ（financials, calendar の差分 ETL 等）は今後実装が予想される（現在は prices_etl のみが明確に実装されている）。
- ネットワーク関連のリトライやレート制御は実装済みだが、本番環境での負荷や TLS 証明書・プロキシ設定等の運用確認を推奨。

開発者向け補足
- テスト性確保のため、news_collector._urlopen や jquants_client の id_token 注入を行える設計になっており、HTTP 呼び出しのモックが可能です。
- .env パーサは shell 風の書式をある程度サポートします（export, クォート, コメント等）。
- DuckDB への大量挿入はチャンク化しており、SQL のプレースホルダ数上限やメモリを考慮した安全設計になっています。

お問い合わせ
- 実装の詳細や不明点はコード内 docstring／コメントを参照してください。バグ修正依頼・機能追加提案があればリポジトリの issue/ticket システムへご登録ください。