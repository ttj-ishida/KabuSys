CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" と Semantic Versioning に従います。

0.1.0 - 2026-03-17
------------------

Added
- 初回リリース。パッケージメタ情報:
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring

- 環境設定管理 (kabusys.config)
  - .env / .env.local からの自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出: __file__ を基点に .git または pyproject.toml を探索して自動検出。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装: export プレフィックス対応、クォートやエスケープ処理、インラインコメント処理などをサポート。
  - protected 機能: OS 環境変数を上書きから保護して .env 読み込み可能。
  - Settings クラス: J-Quants / kabu API / Slack / DB パスなどをプロパティ経由で取得。バリデーション（KABUSYS_ENV, LOG_LEVEL の許容値）と便宜プロパティ（is_live / is_paper / is_dev）を提供。
  - デフォルト DB パス: DuckDB (data/kabusys.duckdb), SQLite (data/monitoring.db)。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ _request を実装（JSON デコード、例外ハンドリング）。
  - レート制御: 固定間隔スロットリングによる RateLimiter（120 req/min を遵守、_MIN_INTERVAL_SEC）。
  - リトライ/バックオフ: 指数バックオフ、最大 3 回リトライ、HTTP 408/429 と 5xx を対象。429 の場合は Retry-After ヘッダ優先。
  - 401 ハンドリング: 401 受信時にリフレッシュを一度実行して再試行（無限ループ防止）。
  - トークン管理: get_id_token() とモジュールレベルの ID トークンキャッシュ（ページネーション間で共有、force_refresh オプション）。
  - データ取得関数:
    - fetch_daily_quotes: 株価日足（ページネーション対応）
    - fetch_financial_statements: 財務データ（四半期 BS/PL、ページネーション対応）
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - DuckDB への保存関数（冪等/ON CONFLICT）:
    - save_daily_quotes: raw_prices へ保存（ON CONFLICT DO UPDATE）
    - save_financial_statements: raw_financials へ保存（ON CONFLICT DO UPDATE）
    - save_market_calendar: market_calendar へ保存（ON CONFLICT DO UPDATE）
  - データ整形ユーティリティ: _to_float / _to_int（厳密な変換ルール、"1.0" 等の扱いに注意）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集: fetch_rss による RSS 取得と記事パース。
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb 等対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカル/マルチキャストかをチェックしてブロック（_is_private_host）。リダイレクト時にも検査する専用 RedirectHandler を導入。
    - 受信サイズ制限: 最大 MAX_RESPONSE_BYTES = 10MB（ヘッダと実際の読み込みで二重チェック）。
    - gzip 解凍の検証（解凍失敗や解凍後サイズ超過を検出）。
  - フィードパースの堅牢化:
    - channel/item のフォールバック探索、content:encoded 名称空間対応、pubDate の RFC2822 パースと UTC 正規化（失敗時は現在時刻で代替）。
    - URL 正規化: トラッキングパラメータ（utm_ 等）除去、クエリソート、フラグメント削除。
    - 記事ID: 正規化 URL の SHA-256 先頭32文字を採用して冪等性を保証。
    - テキスト前処理: URL 除去、空白正規化、先頭末尾トリム。
  - DB 保存:
    - save_raw_news: DuckDB にチャンク単位（_INSERT_CHUNK_SIZE）で INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて新規挿入 ID を返す。トランザクションでまとめてコミット/ロールバック。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを INSERT ... ON CONFLICT DO NOTHING RETURNING で保存。チャンク化とトランザクションを使用。
  - 銘柄抽出:
    - extract_stock_codes: 4 桁数字パターンから known_codes と照合して抽出（重複排除）。
  - 統合収集ジョブ:
    - run_news_collection: 複数ソースの独立ハンドリング、新規挿入件数の集計、抽出した銘柄との一括紐付け処理。既存記事があっても他ソース継続。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - init_schema(db_path): データベース初期化関数。Raw / Processed / Feature / Execution 層のテーブル群を定義・作成（冪等）。親ディレクトリ自動作成対応。":memory:" 対応。
  - get_connection: 既存 DB への接続を返す（スキーマ初期化は行わない）。
  - 定義済みテーブル（主なもの）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・CHECK 制約・PRIMARY KEY / FOREIGN KEY を設定。
  - 実行効率のためのインデックスを複数定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass: ETL 実行結果・メタ情報の集約（品質問題リスト、エラー、has_errors / has_quality_errors プロパティ、辞書化メソッド）。
  - 差分更新ユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date: 各 raw テーブルの最終日取得（テーブル未作成や空を考慮）。
    - _adjust_to_trading_day: 非営業日を直近の営業日に調整（market_calendar 利用、最大 30 日遡る）。
  - run_prices_etl:
    - 差分更新ロジック: DB の最終取得日からの差分取得、backfill_days による後出し修正吸収（デフォルト 3 日）。
    - id_token 注入可能でテスト容易性を確保。
    - 取得 → jq.save_daily_quotes による冪等保存 → ログ出力の流れ。
  - その他:
    - 定数: _MIN_DATA_DATE（2017-01-01）、_CALENDAR_LOOKAHEAD_DAYS（90 日）などを定義。
    - 品質チェック呼び出しポイントを想定（quality モジュールとの連携を前提）。

Security
- RSS / HTTP 関連で SSRF、XML Bomb、gzip ブロート攻撃、サイズベースのメモリ DoS などへ対策を導入。
- .env 読み込みで OS 環境変数の誤上書きを防止する設計。

Notes / Implementation details
- 主要な数値・挙動:
  - J-Quants API レート上限: 120 req/min（固定間隔スロットリング）。
  - リトライ: 最大 3 回、指数バックオフ base=2 秒、429 は Retry-After を尊重。
  - RSS レスポンス上限: 10 MiB（MAX_RESPONSE_BYTES）。
  - ニュース記事 ID は normalized URL の SHA-256 の先頭32文字。
  - DuckDB 側の保存は可能な限り冪等（ON CONFLICT）かつトランザクションでまとめて実行。
  - テスト容易性のため id_token 注入や _urlopen の差し替え（モック）が可能な設計。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Contributing
- バグや改善提案は issue を立ててください。設計に関する注釈（DataPlatform.md / DataSchema.md 等）に基づいて実装されています。