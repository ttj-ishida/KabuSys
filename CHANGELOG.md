# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- 変更はセクションごとに分類（Added / Changed / Fixed / Security / Note 等）
- バージョンごとにリリース日を記載

## [Unreleased]

（現在のリポジトリの最新状態は v0.1.0 としてリリース済みのため、Unreleased に特段の差分はありません）

---

## [0.1.0] - 2026-03-17

最初の公開リリース。日本株自動売買システムのコアライブラリを実装しました。以下の主要機能・設計方針を含みます。

### Added
- パッケージ初期化
  - kabusys パッケージを追加（__version__ = 0.1.0）。
  - モジュールの公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を検出。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルパーサを実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - コメント処理（#）の扱いを細かく実装。
  - .env/.env.local の読み込み優先度を実装（OS 環境変数を保護しつつ .env.local は上書き）。
  - Settings クラスを提供し、以下のプロパティで環境変数を安全に取得:
    - J-Quants / kabu API / Slack トークン類（必須のキーは未設定時に ValueError を送出）
    - DUCKDB_PATH, SQLITE_PATH のデフォルトパス
    - KABUSYS_ENV の検証（development, paper_trading, live のみ許可）
    - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - is_live / is_paper / is_dev のヘルパー

- J-Quants API クライアント (kabusys.data.jquants_client)
  - ベースURL と API 呼び出しユーティリティを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
  - リトライロジック（最大3回、指数バックオフ、対象: 408/429/5xx）を実装。
  - 429 の Retry-After ヘッダ優先対応。ネットワークエラー（URLError/OSError）も再試行。
  - 401 受信時は自動でリフレッシュトークンから id_token を取得して 1 回だけリトライ（無限再帰回避）。
  - モジュールレベルの id_token キャッシュを共有（ページネーション対応）。
  - 以下のデータ取得関数を実装（ページネーション対応）:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (四半期 BS/PL 等)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB へ冪等に保存する保存関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes (raw_prices)
    - save_financial_statements (raw_financials)
    - save_market_calendar (market_calendar)
  - データ整形ユーティリティを実装:
    - _to_float / _to_int（空値・変換失敗時は None、_to_int は小数非ゼロ部を検出して None を返す等の安全な変換）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を取得し raw_news テーブルに保存するパイプラインを実装。
  - セキュリティ・耐障害設計:
    - defusedxml を用いた XML パース（XML Bomb 等への防御）。
    - SSRF 対策: URL スキーム検証（http/https のみ）とプライベート IP/ホストの検査。リダイレクト時にも検証を行う専用ハンドラを実装。
    - レスポンス最大サイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入し、読み取り量を制限。
    - gzip 圧縮レスポンスの安全な解凍（解凍後もサイズチェック）。
    - URL 正規化でトラッキングパラメータを除去（utm_*, fbclid, gclid など）して記事の冪等性を高める。
    - 記事IDは正規化 URL の SHA-256 の先頭32文字で生成。
  - RSS 取得・解析機能:
    - fetch_rss: RSS 取得 → XML パース → アイテム抽出 → 前処理（URL 除去・空白正規化） → NewsArticle リスト返却。
    - preprocess_text: URL 除去・空白正規化のユーティリティ。
    - _parse_rss_datetime: pubDate のパース（RFC 2822 対応）、失敗時は現在時刻で代替。
  - DB 保存機能:
    - save_raw_news: チャンク分割（最大 _INSERT_CHUNK_SIZE）して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、新規挿入された記事IDのみを返す。挿入は単一トランザクションで行い、失敗時にロールバック。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け保存（重複除去、チャンク INSERT、トランザクション管理）。
  - 銘柄コード抽出:
    - extract_stock_codes: テキストから 4 桁の数字を抽出し、与えられた known_codes のみを返す（重複除去）。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataSchema.md に基づいた三層（Raw / Processed / Feature）＋Execution 層の包括的スキーマを実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切なチェック制約（NOT NULL / CHECK）や PRIMARY KEY を付与。
  - 外部キーと ON DELETE 動作を設定（例: news_symbols.news_id → news_articles(id) ON DELETE CASCADE）。
  - 頻出クエリ向けにインデックス群を定義（code×date、ステータス検索等）。
  - init_schema(db_path) 関数を提供し、必要な親ディレクトリの自動作成とすべての DDL・インデックスを冪等に適用して DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETL の設計方針と差分更新ロジックを実装:
    - 差分更新のための最終取得日取得ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダー未取得時のフォールバックや、非営業日を直近営業日に調整する _adjust_to_trading_day。
    - ETLResult dataclass を導入し、取得数・保存数・品質チェック結果・エラーを収集。has_errors / has_quality_errors / to_dict を提供。
    - run_prices_etl を実装（差分計算、backfill_days デフォルト 3 日、最小データ開始日 _MIN_DATA_DATE = 2017-01-01 を考慮）。J-Quants の取得と保存（jq.fetch_daily_quotes / jq.save_daily_quotes）を呼び出す。
  - 市場カレンダーの先読み日数や品質チェックの設計値（_CALENDAR_LOOKAHEAD_DAYS = 90 等）を設定。

### Changed
- 初回リリースにつき特筆すべき「変更」はなし。設計上のデフォルト値や挙動（.env のロード順、backfill の既定値等）は上記 Added に記載のとおり。

### Fixed
- 初回リリースにつき特筆すべき「修正」はなし。

### Security
- ニュース収集で SSRF 対策、defusedxml 使用、レスポンスサイズ制限、URL スキーム検証等のセーフガードを実装。
- 環境変数の上書きに関して OS 環境変数を保護する設計（protected set）を採用。

### Notes / Migration
- DuckDB のスキーマを利用する前に必ず init_schema(db_path) を呼び出してテーブルを作成してください。get_connection() は既存 DB へ接続するのみでスキーマを作成しません。
- 必須環境変数（未設定時は ValueError）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- オプションの環境変数:
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)
- 環境設定: KABUSYS_ENV は development/paper_trading/live のいずれか、LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれかに制限されています。
- id_token のリフレッシュは内部で自動化されていますが、テストや限定的な呼び出しのために get_id_token() に refresh_token を注入可能です。

---

過去のリリース/将来の変更はこのファイルに追記していきます。問題の報告や機能要求は issue を通じてお願いします。