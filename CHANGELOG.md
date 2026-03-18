Keep a Changelog に準拠した CHANGELOG.md（日本語）

すべての注目すべき変更を記録します。  
このファイルは semver に従い、"Added/Changed/Fixed/Security/..." のカテゴリで記載します。

1.0.0 未満の初期バージョンについては 0.1.0 を初回リリースとしています。

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-03-18
-------------------
Added
- パッケージ初期リリース (バージョン 0.1.0)
  - src/kabusys/__init__.py によりパッケージを公開。__version__=0.1.0、公開サブパッケージ: data, strategy, execution, monitoring。

- 設定・環境変数管理
  - src/kabusys/config.py を追加。
    - .env および .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする機能を搭載（優先順位: OS 環境 > .env.local > .env）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパース機能は export プレフィックス、クォート、インラインコメント等に対応。
    - 必須設定を取得する _require() と Settings クラスを提供。主要な設定名:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID,
        DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
    - KABUSYS_ENV の検証（development/paper_trading/live）とログレベル検証（DEBUG/INFO/...）を実装。
    - settings = Settings() をモジュールレベルで提供。

- Data 層: J-Quants クライアント
  - src/kabusys/data/jquants_client.py を追加。
    - API 呼び出しラッパー _request を実装（JSON デコード、タイムアウト、ページネーション対応）。
    - レート制限: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
    - 再試行: 指数バックオフを用いたリトライ（最大 3 回）を実装。408/429/5xx を再試行対象に含む。429 の Retry-After を考慮。
    - 401 (Unauthorized) 受信時の自動トークンリフレッシュ機能を実装（1 回のみ）。
    - id_token キャッシュ（モジュールレベル）と get_id_token(refresh_token)。
    - データ取得関数:
      - fetch_daily_quotes (ページネーション対応)
      - fetch_financial_statements (ページネーション対応)
      - fetch_market_calendar
    - DuckDB への保存関数（冪等化）:
      - save_daily_quotes -> raw_prices へ INSERT ... ON CONFLICT DO UPDATE
      - save_financial_statements -> raw_financials へ INSERT ... ON CONFLICT DO UPDATE
      - save_market_calendar -> market_calendar へ INSERT ... ON CONFLICT DO UPDATE
    - データ変換ユーティリティ: _to_float, _to_int（堅牢なパース、空値ハンドリング、"1.0" のような文字列処理含む）。
    - Look-ahead バイアス対策として fetched_at を UTC 形式で記録。

- Data 層: ニュース収集 (RSS)
  - src/kabusys/data/news_collector.py を追加。
    - RSS フィードの取得・パース・前処理・DB保存の一連処理を実装。
    - セキュリティ・堅牢性:
      - defusedxml を利用した XML パース（XML Bomb 対策）。
      - リダイレクト時にスキームとホストを検証するカスタムハンドラ（SSRF 対策）。
      - ホストがプライベート/ループバック/リンクローカルの場合は拒否。
      - URL スキームは http/https のみ許可。
      - 受信サイズを MAX_RESPONSE_BYTES (10MB) で制限し、GZIP 解凍後も検査（メモリ DoS 対策）。
      - User-Agent と Accept-Encoding の設定。
    - コンテンツ前処理: URL 除去、空白正規化。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）: _normalize_url と _make_article_id（SHA-256 の先頭32文字）。
    - pubDate パース: RFC 2822 形式を UTC naive datetime に変換（パース失敗時は警告ログと現在時刻で代替）。
    - fetch_rss(url, source, timeout) -> NewsArticle リスト（NewsArticle は TypedDict）。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDのリストを返却。チャンク分割・1トランザクションで実行。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをチャンクで挿入（ON CONFLICT DO NOTHING、INSERT ... RETURNING を利用）。
    - 銘柄コード抽出: extract_stock_codes(text, known_codes)（4桁数字パターンで known_codes フィルタ）。
    - run_news_collection: 複数ソースを順次処理し、ソースごとの挿入件数を返却。個々のソースは独立してエラーハンドリング。

- Data 層: スキーマ定義
  - src/kabusys/data/schema.py を追加。
    - DuckDB 用の DDL を定義（Raw / Processed / Feature / Execution 層の方針を明示）。
    - raw_prices, raw_financials, raw_news, raw_executions 等の CREATE TABLE 定義を含む（NOT NULL / CHECK 制約、PRIMARY KEY 指定を含む）。
    - スキーマ初期化用モジュールとして利用可能。

- Research（特徴量・ファクター計算）
  - src/kabusys/research/factor_research.py を追加。
    - StrategyModel.md に基づく定量ファクターを実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m / ma200_dev（200日移動平均乖離）を計算。過不足データ時は None を返す。
      - calc_volatility: atr_20（ATR の単純平均）、atr_pct（ATR/close）、avg_turnover（20日平均売買代金）、volume_ratio（当日/20日平均）を計算。必要行数が不足する場合は None を返す。
      - calc_value: raw_financials から最新財務データを取得し per（EPS 非ゼロ時）・roe を計算。
    - DuckDB 接続を受け取り prices_daily / raw_financials のみ参照。外部 API は呼ばない。
    - パラメータやスキャン範囲に関する定数（_MOMENTUM_SHORT_DAYS 等）を定義し、カレンダーバッファを考慮したクエリを実行。

  - src/kabusys/research/feature_exploration.py を追加。
    - calc_forward_returns: target_date の終値から指定ホライズン（営業日）後の終値を参照して forward return を計算（horizons デフォルト [1,5,21]）。ホライズン上限検査あり。
    - calc_ic: factor_records と forward_records を code で結合し、スピアマンランク相関（ランク化は同順位は平均ランク）を計算。有効レコードが 3 未満なら None を返す。
    - rank: 同順位は平均ランク処理、丸め処理（round(v,12)）で浮動小数誤差を抑制。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算（None は除外）。
    - 標準ライブラリのみで実装されており、pandas 等に依存しない設計。
  - src/kabusys/research/__init__.py で主要関数と zscore_normalize (kabusys.data.stats 由来) を公開。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集モジュールに対して複数の SSRF / XML / DoS 対策を実装（defusedxml、リダイレクト検査、プライベートIP検出、受信サイズ制限、gzip 解凍後検査等）。
- J-Quants クライアントはトークン自動リフレッシュの仕組みを導入し、不正な 401 対応を安全に実装。

Notes / Migration
- 環境変数の追加:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意/デフォルトあり: KABU_API_BASE_URL, DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db), KABUSYS_ENV (development/paper_trading/live), LOG_LEVEL
- .env の自動読み込みはプロジェクトルートを __file__ から探索するため、パッケージ配布後も動作する想定。テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に保存するテーブル名（raw_prices / raw_financials / raw_news / market_calendar / news_symbols 等）に合わせてスキーマを初期化してください（schema モジュール参照）。
- research モジュールの関数は prices_daily, raw_financials テーブルのみを参照し、本番の発注 API などにはアクセスしません。研究用途に安全に使用できます。

Acknowledgements / Implementation details
- いくつかのモジュール（strategy/, execution/, monitoring/）はパッケージ内にプレースホルダを残しています（__init__.py が存在）。将来的にエグゼキューションやモニタリング機能を追加予定です。
- jquants_client の _request は urllib を用いた実装であり、ページネーションと pagination_key に対応しています。
- news_collector は記事ID生成に URL 正規化→SHA-256 を採用して冪等性を確保しています。

ライセンスや貢献ガイドライン、さらに細かい設計文書（DataPlatform.md / StrategyModel.md / DataSchema.md 等）の参照を推奨します。