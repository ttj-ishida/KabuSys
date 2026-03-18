CHANGELOG
=========

すべての重要な変更をここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

なし

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージ初期リリース: kabusys (version 0.1.0)
  - パッケージトップに __version__ と __all__ を定義。
- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みする仕組みを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護（protected）され、.env.local により上書き可能。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - Settings クラスを追加し、J-Quants / kabu ステーション / Slack / DB パス 等のプロパティを提供。値検証（KABUSYS_ENV, LOG_LEVEL の許容値）を実装。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - 認証: リフレッシュトークンから id_token を取得する get_id_token を実装。モジュールレベルのトークンキャッシュを保持。
  - レート制御: 固定間隔スロットリングで 120 req/min を制限する RateLimiter を実装。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx をリトライ対象。429 時は Retry-After ヘッダを優先。
  - 401 Unauthorized 受信時は id_token を自動リフレッシュして 1 回のみリトライ（無限再帰を防止）。
  - データ保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - DuckDB への保存を冪等に行うため ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC ISO 形式で記録（Look-ahead bias 防止のためデータを取得した時刻を保持）。
    - PK 欠損行はスキップしてログ警告を出力。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存するフローを実装。
  - セキュリティ・堅牢性:
    - defusedxml を使用して XML Bomb 等の脆弱性対策。
    - SSRF 対策: URL スキーマ検証（http/https のみ）、リダイレクト先の事前検証、プライベート/ループバック/リンクローカルの排除。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - 許可されないスキームやプライベートホストへのアクセスは拒否/スキップ。
  - URL 正規化と記事 ID 生成:
    - トラッキングパラメータ（utm_*, fbclid 等）を除去し、クエリをソートして正規化。
    - 記事IDは正規化 URL の SHA-256 の先頭32文字（ハッシュ）を使用して冪等性を保証。
  - テキスト前処理（URL除去・空白正規化）を実装。
  - RSS の pubDate をパースして UTC naive datetime に変換（パース失敗時は警告を出して現在時刻で代替）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて、実際に新規挿入された記事IDのリストを返却。チャンク単位挿入・トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けテーブル(news_symbols)へ一括挿入。重複除去、チャンク挿入、INSERT ... RETURNING で実際に挿入された数を返却。トランザクション保護とロールバック実装。
  - 銘柄抽出:
    - 4桁数字パターンから候補を抽出し、known_codes に存在するもののみを返す extract_stock_codes を実装。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加。
- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の 3 層（＋実行層）に対応するテーブル DDL を網羅的に定義。
  - テーブル例: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など。
  - インデックス定義（頻出スキャンやステータス検索のため）を追加。
  - init_schema(db_path) によりディレクトリ自動作成・全DDL実行で初期化するユーティリティを提供。get_connection() で既存 DB に接続可能。
- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新を行う ETL 実装
    - 最終取得日を確認し、backfill_days（デフォルト 3 日）分の再取得を行う差分ロジック。
    - 市場カレンダーの先読み設定（_CALENDAR_LOOKAHEAD_DAYS = 90）。
    - ETLResult データクラスを提供（取得件数・保存件数・品質問題・エラーリストなどを保持）。品質問題は quality.QualityIssue を想定して統合。
    - DB 存在チェック・最大日付取得ユーティリティを実装。
  - run_prices_etl を実装（fetch + save の差分フロー）。（注: ファイル末尾で関数は途中まで実装されている構成を示唆）

Security
- ニュース収集における SSRF 対策、XML 解析時の defusedxml 使用、最大応答サイズチェック等を実装。
- J-Quants クライアントは認証トークンの自動リフレッシュを 1 回のリトライに限定し、無限再帰を防止。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / 実装上の注意
- .env の自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後に CWD に依存せず動作する設計。ただしプロジェクトルートが検出できない場合は自動ロードをスキップする。
- jquants_client の _request は内部でモジュールレベルのトークンキャッシュを更新するため、テストでは allow_refresh フラグや get_id_token への id_token 注入を使用して副作用を抑えることが推奨される。
- news_collector.fetch_rss は外部ネットワーク依存のため、ユニットテストでは _urlopen をモックして動作を検証可能。
- schema.init_schema は ":memory:" を渡せばインメモリ DB を使用可能。

今後の予定（想定）
- pipeline のさらなる ETL ジョブ（財務データ・カレンダーの差分ETL 完全実装）や quality モジュールとの統合強化。
- execution/strategy/monitoring パッケージの具体実装（現在はパッケージ空ディレクトリあり）。