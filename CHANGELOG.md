CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

フォーマット:
- 変更は逆順（新しいリリースを上に）で記載
- セクションは Added / Changed / Fixed / Security / Deprecated / Removed を使用

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-17
--------------------

Added
- 初回リリース。パッケージ名: kabusys（日本株自動売買システムの骨格）。
- パッケージメタ:
  - バージョン: 0.1.0
  - パッケージ公開用 __all__ に data, strategy, execution, monitoring を定義。

- 環境設定管理 (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
  - export KEY=val 形式やクォート／エスケープ、行内コメント等に対応した .env パーサ実装。
  - 環境変数取得ヘルパー（Settings クラス）を提供:
    - 必須トークンの取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - DB パス既定値（DUCKDB_PATH, SQLITE_PATH）
    - 環境種別検証（KABUSYS_ENV: development, paper_trading, live）
    - ログレベル検証（LOG_LEVEL）

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、市場カレンダー取得用の API クライアントを実装。
  - レート制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
  - 再試行ロジック: 指数バックオフ（最大3回）、対象ステータス 408, 429, 5xx。
  - 401 Unauthorized 受信時は自動でリフレッシュして1回リトライ（get_id_token を用いた id_token リフレッシュ）。モジュールレベルで id_token キャッシュを保持してページネーション間で共有。
  - ページネーション対応で fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を提供。
  - DuckDB へ冪等保存する save_* 関数を実装（raw_prices, raw_financials, market_calendar）。INSERT ... ON CONFLICT DO UPDATE を使用して重複や後出し修正に対応。
  - データ変換ユーティリティ (_to_float, _to_int) を用意し、空値や不正値を安全に扱うロジックを提供。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからのニュース収集処理を実装（デフォルトソースに Yahoo Finance のビジネス RSS を設定）。
  - セキュリティおよび堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - HTTP/HTTPS 以外のスキーム拒否、SSRF 対策のためリダイレクト先のスキームとホストの事前検証。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、Gzip 解凍後も検査（Gzip bomb 対策）。
    - 受信バイト上限を超える場合はスキップして安全性を確保。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）を実施し、正規化 URL の SHA-256（先頭32文字）から記事IDを生成。これにより冪等性を保証。
  - テキスト前処理（URL除去、空白正規化）と pubDate の堅牢なパース（UTC で正規化、失敗時は現在時刻で代替）。
  - RSS のパースと記事抽出処理（fetch_rss）を提供。非標準レイアウトや名前空間にもフォールバック対応。
  - DuckDB への保存機能:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING と RETURNING を使い、新規挿入された記事IDを返す。チャンク化して単一トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING）し、実際に挿入された件数を返す。
  - 銘柄コード抽出ユーティリティ (extract_stock_codes): テキスト中の 4 桁数値候補を known_codes と照合して抽出（重複除去）。

- DuckDB スキーマ定義 & 初期化 (kabusys.data.schema)
  - DataSchema.md に基づく多層（Raw / Processed / Feature / Execution）スキーマを実装。
  - 生データテーブル（raw_prices, raw_financials, raw_news, raw_executions）から、加工層（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）、特徴量層（features, ai_scores）、実行層（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）までの DDL を定義。
  - 各種制約（PK, CHECK, FOREIGN KEY）やインデックスを設定。
  - init_schema(db_path) でディレクトリ自動作成・DDL 実行を行い初期化済み DuckDB 接続を返す（冪等）。get_connection(db_path) で接続のみ取得可。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新（incremental）を想定した ETL パイプライン補助機能を実装。
  - ETLResult dataclass により ETL 実行結果（取得数 / 保存数 / 品質問題 / エラー）を集約可能。
  - 差分判定用ユーティリティ: テーブル存在チェック、最大日付取得（_get_max_date を基にした get_last_price_date 等）。
  - 市場カレンダー補助: 非営業日の場合は直近営業日に調整する _adjust_to_trading_day。
  - run_prices_etl の実装（差分範囲自動算出、backfill_days デフォルト 3 日、取得→保存の流れ）。J-Quants 側の最小データ日付は 2017-01-01 に設定。
  - カレンダーの先読みデフォルトは 90 日（_CALENDAR_LOOKAHEAD_DAYS）。

Security
- news_collector にて SSRF 対策、受信サイズ制限、defusedxml による XML 攻撃対策を実装。
- jquants_client の HTTP リトライ・バックオフ実装により過剰リクエストや一時的障害に耐性を持たせる。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / 補足
- DuckDB への保存ロジックは冪等性（ON CONFLICT）を前提として設計しているため、ETL を何度実行しても重複を起こさないようになっています。
- NewsCollector の記事IDは URL の正規化ルールに依存します。URL 正規化の振る舞い（トラッキングパラメータ除去やクエリソート）を変更すると ID が変わる可能性があります。
- 環境変数の自動ロードはプロジェクトルートの判定に __file__ からの親ディレクトリ探索を用いており、CWD に依存しない設計です。CI/テスト等で自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。