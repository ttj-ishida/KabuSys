CHANGELOG.md
=============

すべての注目すべき変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

なお、本CHANGELOGは提供されたコードベースから機能・設計意図を推測して作成しています。

Unreleased
----------

（現在なし）

0.1.0 - 2026-03-17
------------------

Added
- 初期リリースを公開。
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = "0.1.0"、サブパッケージ公開）。
- 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト用）。
  - export 形式やクォートを含む .env 行のパースに対応。インラインコメントやエスケープ処理を考慮。
  - OS 環境変数を保護する protected モード（.env.local の上書き動作制御）。
  - Settings クラスを導入し、J-Quants / kabu API / Slack / DB パス等の設定プロパティを提供。
  - KABUSYS_ENV や LOG_LEVEL の値検証（許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。
- J-Quants クライアント（kabusys.data.jquants_client）
  - J-Quants API からのデータ取得機能を実装：
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - 認証トークン取得（get_id_token）とモジュール内トークンキャッシュ実装。401 受信時の自動リフレッシュ対応（1回のみ）。
  - レート制御（_RateLimiter）を実装し、J-Quants の 120 req/min 制限に対応。
  - リトライロジック（指数バックオフ、最大3回）と 429 の Retry-After 考慮、408/429/5xx の再試行。
  - DuckDB への保存ユーティリティ（冪等）を実装：
    - save_daily_quotes（raw_prices、ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials、ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar、ON CONFLICT DO UPDATE）
  - データ取得時の fetched_at（UTC）付与により Look-ahead バイアス追跡を可能に。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、入力の頑健性を向上。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集と前処理機能を実装：
    - fetch_rss：RSS 取得、XML パース、content:encoded 優先、pubDate パース（UTC 変換）
    - preprocess_text：URL 削除・空白正規化
    - URL 正規化と記事ID生成（_normalize_url / _make_article_id：SHA-256 の先頭32文字）
    - 記事保存（save_raw_news）：DuckDB の raw_news にチャンク挿入、INSERT ... RETURNING で実際に挿入されたIDを返す。トランザクションでまとめて挿入。
    - 銘柄紐付け（save_news_symbols, _save_news_symbols_bulk）：news_symbols テーブルへ一括挿入、INSERT ... RETURNING により挿入数を正確にカウント。
    - extract_stock_codes：本文中の4桁銘柄コード抽出（既知コードによるフィルタ、重複除去）。
    - run_news_collection：複数RSSソースの統合収集ワークフロー（個別ソースのエラーハンドリングと銘柄紐付け）。
  - セキュリティ & 堅牢性対策：
    - defusedxml を用いた XML パース（XML Bomb 等に対策）。
    - SSRF 対策：URL スキーム検証（http/https のみ許可）、リダイレクト先の事前検証（_SSRFBlockRedirectHandler）、プライベート/ループバック/リンクローカル/マルチキャストIP拒否（_is_private_host）。
    - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES、デフォルト 10MB）および gzip 解凍後のサイズ検査。
    - 不正なスキームや大きすぎるレスポンスは安全にスキップ。
- DuckDB スキーマ（kabusys.data.schema）
  - DataLayer 設計に基づくスキーマ実装（init_schema により初期化）：
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約・チェック（NOT NULL、PRIMARY KEY、CHECK 制約）を定義しデータ整合性を担保。
  - パフォーマンス向上のためのインデックス定義（頻出クエリに対する索引を作成）。
  - init_schema による親ディレクトリ自動作成、:memory: 対応。
  - get_connection ユーティリティを提供（スキーマ初期化を行わない既存 DB 接続）。
- ETL パイプライン（kabusys.data.pipeline）
  - ETL の骨組みを提供：
    - 差分更新ロジック（最終取得日を参照し backfill_days による再取得範囲を算出）
    - run_prices_etl 実装（target_date を基準に fetch -> save の流れ）
    - ETLResult データクラスによる詳細な実行結果表現（取得数・保存数・品質問題・エラー等の集約）
    - 品質チェック組み込みポイント（quality モジュールとの連携想定、品質問題は集計して呼び出し元に報告）
    - 市場カレンダーの調整ヘルパー（非営業日の調整）
  - 設計方針として Fail-Fast を避け、可能な限り全件収集して問題を報告する方針を採用。
- パッケージ構造
  - data、strategy、execution、monitoring 等のサブパッケージ骨格を作成（各 __init__.py を配置）。

Security
- RSS / HTTP 周りに対する複数の安全対策を導入（defusedxml、SSRF ブロック、応答サイズ制限、スキーム検証、プライベートIP拒否）。
- .env ファイル読み取りは OS 環境変数を保護する設計。自動読み込みは明示的に無効化可能。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Notes / Known limitations
- quality モジュールの具体的な実装はこのコードからは参照のみ（kabusys.data.quality）であり、実装詳細は別途必要。
- pipeline.run_prices_etl の戻り値のコードは提示された抜粋で途中で終わっているため、実装上の続き（完全な戻り値タプルなど）は実際のコードで確認が必要。
- 実際の運用では J-Quants の API 利用制限や Slack / kabu API の認証情報管理に注意が必要。
- NewsCollector は既定の RSS ソースとして Yahoo Finance を登録しているが、運用時は必要に応じてソース一覧を拡張してください。
- DuckDB の SQL 文は埋め込み文字列として生成されている箇所があるため、将来的に SQL インジェクションに配慮した設計（プレースホルダの徹底等）を検討してください（現状はパラメータは大部分でバインドされている）。

参考
- .env の取り扱いは環境に依存するため、本番環境での運用前に .env.example を用意して環境変数の明文化を推奨します。