CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
（この CHANGELOG は与えられたコードベースの内容から推測して作成しています。）

Unreleased
----------

- なし

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
    - パッケージのエクスポート対象: data, strategy, execution, monitoring。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動ロード機能:
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env.local は .env 上に上書き適用（既存 OS 環境変数は保護）。
  - .env パース機能:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート対応（バックスラッシュエスケープを考慮）。
    - インラインコメントの扱い（クォートの有無に応じた解釈）。
  - 必須設定取得時は未設定で ValueError を発生させる _require() を提供。
  - 主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb), SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV (development|paper_trading|live) と LOG_LEVEL の検証ヘルパー
    - is_live / is_paper / is_dev の boolean プロパティ

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 基本設計:
    - API レート制限 (120 req/min) を守る固定間隔スロットリング _RateLimiter を実装。
    - リトライロジック: 指数バックオフ、最大 3 回、対象ステータス 408/429 と 5xx、429 は Retry-After を尊重。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰防止）。
    - ページネーション対応（pagination_key の検査と再帰的取得）。
    - Look-ahead bias 対策のため fetched_at を UTC で記録。
    - DuckDB 保存は冪等 (ON CONFLICT DO UPDATE)。
  - 提供 API:
    - get_id_token(refresh_token=None) - リフレッシュトークンから idToken を取得。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar - データ取得（ページネーション対応）。
    - save_daily_quotes / save_financial_statements / save_market_calendar - DuckDB への保存（冪等）。
  - データ変換ユーティリティ:
    - _to_float / _to_int：堅牢な数値変換（空値や不正値を None に変換、float->int の安全性チェック等）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news / news_symbols に保存する一連の機能を実装。
  - セキュリティと堅牢性:
    - defusedxml を使った XML パース（XML Bomb 等からの防御）。
    - SSRF 対策: リダイレクト時にスキームとホスト検査を行う _SSRFBlockRedirectHandler、初回ホストのプライベートアドレス検査、_is_private_host によるホスト/IP の私有アドレス判定。
    - URL スキーム制限（http/https のみ）、最大受信バイト数制限 (MAX_RESPONSE_BYTES = 10 MB)、gzip 解凍後のサイズ検査。
    - HTTP レスポンス取得用のラッパー _urlopen はテスト用にモック差し替え可能。
  - 機能:
    - URL 正規化とトラッキングパラメータ除去 (_normalize_url)、記事ID を SHA-256 の先頭 32 文字で生成 (_make_article_id)。
    - 前処理 preprocess_text（URL 除去、空白正規化）。
    - RSS の pubDate を UTC naive datetime に変換する _parse_rss_datetime。
    - fetch_rss(url, source, timeout) で記事の抽出（content:encoded を優先、guid の取り扱い、名前空間フォールバック）。
    - save_raw_news(conn, articles) はチャンク INSERT + トランザクション + INSERT ... RETURNING で実際に挿入された記事IDを返す（冪等: ON CONFLICT DO NOTHING）。
    - save_news_symbols / _save_news_symbols_bulk：記事と銘柄コードの紐付けを一括挿入。
    - extract_stock_codes(text, known_codes) により 4 桁数字の銘柄コード抽出（known_codes によるフィルタ、重複除去）。
  - デフォルト RSS ソース: Yahoo Finance のビジネスカテゴリを登録 (DEFAULT_RSS_SOURCES)。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく多層スキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約チェック（CHECK, PRIMARY KEY, FOREIGN KEY）を設定。
  - 頻出クエリ用インデックスを多数定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) でディレクトリ自動作成・全DDL 実行・インデックス作成を行い、DuckDB 接続を返す。get_connection は既存 DB への接続取得を提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult データクラスを導入（取得件数・保存件数・品質問題・エラーの集約、has_errors / has_quality_errors プロパティ、辞書変換 to_dict）。
  - 差分更新ユーティリティ:
    - _table_exists, _get_max_date を実装。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
    - _adjust_to_trading_day で非営業日の調整（market_calendar を参照、最大30日遡り）。
  - run_prices_etl を実装（差分更新の自動算出、backfill_days による再取得の導入、jq.fetch_daily_quotes / jq.save_daily_quotes の利用）。設計では品質チェックモジュールに連携することが想定されている（quality モジュール参照）。

Security
- ニュース収集における SSRF 対策、defusedxml 使用、最大受信サイズ制限、許可スキーム制限 (http/https) を実装。
- .env の自動ロードは OS 環境変数を保護する protected セットを使用し、環境上書きの制御を提供。

Fixed
- 初回リリースのため該当なし。

Changed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / Known issues
- run_prices_etl の最後の return が切れているように見える（コード断片の末尾に "return len(records), " のような不完全な返却が存在）。意図は (fetched_count, saved_count) を返すことと思われるため、戻り値の整合性修正が必要。
- その他、実際の運用では以下の点を確認することを推奨:
  - DuckDB のスキーマと現行データの互換性（既存 DB がある場合）。
  - settings の必須環境変数が欠如すると ValueError を投げるため、デプロイ環境での .env 設定を事前に用意すること。
  - jquants_client のリクエストで urllib に依存する実装はテスト時にモック化が必要（_get_cached_token や _rate_limiter の振る舞い確認）。
  - news_collector の _is_private_host は DNS 解決失敗時に安全側（非プライベート）扱いとする設計のため、厳格にブロックしたい場合は追加ポリシーが必要。

License
- コード中にライセンス記載はありません。配布時は適切なライセンス付与を検討してください。