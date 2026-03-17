CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[0.1.0] - 2026-03-17
--------------------

Added
- 初回リリース (0.1.0)
  - パッケージ構成を追加:
    - kabusys パッケージのルート定義（__version__ と __all__）。
    - サブパッケージ: data, strategy, execution, monitoring（空の __init__ を含むプレースホルダ）。
  - 環境設定モジュール (kabusys.config)
    - .env/.env.local と OS 環境変数からの設定自動読み込みを実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を導入し、CWD に依存しない読み込みを実現。
    - .env パーサーを実装（コメント行、export プレフィックス、クォート、エスケープ対応、インラインコメント処理を含む）。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル判定などのプロパティ）。
    - 環境変数必須チェック（_require）と値検証（KABUSYS_ENV, LOG_LEVEL）。
  - J-Quants クライアント (kabusys.data.jquants_client)
    - API 呼び出しユーティリティを実装（_request）。
    - レート制御（120 req/min 固定間隔スロットリング）を実装する RateLimiter。
    - 冪等性・ページネーション対応の取得関数を実装:
      - fetch_daily_quotes (日足)
      - fetch_financial_statements (財務・四半期)
      - fetch_market_calendar (JPX カレンダー)
    - HTTP リトライロジックを実装（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）と ID トークンキャッシュ共有機構を導入。
    - DuckDB への保存関数（冪等）を実装:
      - save_daily_quotes (raw_prices に ON CONFLICT DO UPDATE)
      - save_financial_statements (raw_financials に ON CONFLICT DO UPDATE)
      - save_market_calendar (market_calendar に ON CONFLICT DO UPDATE)
    - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正値や空文字に対する安全処理を提供。
    - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias の追跡を可能に。
  - ニュース収集モジュール (kabusys.data.news_collector)
    - RSS フィードからのニュース収集と前処理を実装:
      - fetch_rss: RSS 取得・XML パース・記事リスト作成（content:encoded 優先、pubDate パース、タイトル/本文の前処理）。
      - preprocess_text: URL 除去と空白正規化。
      - _normalize_url / _make_article_id: URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と SHA-256 ベースの ID 生成（先頭32文字）で冪等性を確保。
    - セキュリティ対策と堅牢性:
      - defusedxml を使用して XML Bomb 等を防止。
      - SSRF 対策: http/https スキーム検証、ホストのプライベートアドレス判定、リダイレクト時の事前検査（_SSRFBlockRedirectHandler）。
      - レスポンスサイズ制限 (MAX_RESPONSE_BYTES=10MB)、gzip 解凍時のサイズチェック（Gzip bomb 対策）。
      - URL スキームや不正なリンクを検出してスキップ。
    - DuckDB 保存関数:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用いて新規挿入された記事 ID を正確に返却。チャンク分割および単一トランザクションで実行。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括保存。ON CONFLICT を使い重複を排除し、挿入数を正確に返す。
    - 銘柄抽出:
      - extract_stock_codes: テキストから4桁銘柄コード候補を抽出し、既知銘柄セットでフィルタリング。重複除去。
    - 統合収集ジョブ:
      - run_news_collection: 複数 RSS ソースを順次取得し DB に保存、既知銘柄があれば紐付けを実行。ソース単位でエラーを隔離（1 ソース失敗しても他を継続）。
    - デフォルト RSS ソースに Yahoo Finance を登録。
  - DuckDB スキーマ定義 (kabusys.data.schema)
    - DataSchema.md に基づく 3 層 + Execution 層のスキーマを実装（DDL を定義）:
      - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
      - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature 層: features, ai_scores
      - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
    - 頻出クエリ向けインデックスを定義。
    - init_schema(db_path) によりディレクトリ作成 → DuckDB 接続 → 全DDL とインデックスを実行する初期化を提供。get_connection は既存接続を返す（初期化は行わない）。
  - ETL パイプライン (kabusys.data.pipeline)
    - ETL 結果を表す ETLResult データクラスを追加（品質問題・エラー収集・シリアライズ機能を含む）。
    - 差分更新ヘルパー:
      - テーブル存在チェック、最大日付取得ユーティリティ (_table_exists, _get_max_date)。
      - 市場カレンダーに基づく営業日調整 (_adjust_to_trading_day)。
      - raw_prices/raw_financials/market_calendar の最終取得日取得関数。
    - run_prices_etl の骨格を実装（差分計算、backfill_days による再取得、jq.fetch_daily_quotes + jq.save_daily_quotes を使用して取得・保存）。
    - 設計方針: 差分更新、backfill による後出し修正吸収、品質チェックの並行実行（quality モジュールと連携予定）。

Security
- ニュース収集に関して以下のセキュリティ対策を実装:
  - defusedxml による XML パースの安全化。
  - SSRF 防止のためのスキーム検証・プライベートアドレス検査・リダイレクト時の検証。
  - レスポンスサイズ制限と gzip 解凍後の追加チェック（DoS / Gzip bomb 対策）。
  - 外部 URL のスキーム制限（http/https のみ）。

Notes
- 各 API クライアント/ETL はログ出力を備え、処理状況や警告を記録します。
- DuckDB に対する INSERT は可能な限り冪等（ON CONFLICT）を採用しており、繰り返し実行しても重複を抑制します。
- 設定値は Settings を通してアクセスすることを想定しています。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化できます。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

未解決 / 既知の注意点
- pipeline.run_prices_etl など ETL のいくつかの処理は骨格実装（品質チェック連携やその他 ETL ジョブの統合は今後実装予定）。
- strategy / execution / monitoring のサブパッケージはプレースホルダとして存在しており、具体的なアルゴリズムや発注ロジックは未実装。

[[0.1.0]: https://example.com/release/0.1.0]