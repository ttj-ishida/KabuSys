Keep a Changelog 準拠の変更履歴

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

Unreleased
---------

- なし

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージ初期リリース。kabusys の基本モジュール群を追加。
  - src/kabusys/__init__.py
    - パッケージメタ情報（__version__ = "0.1.0"）とエクスポート対象を定義。
- 環境変数 / 設定管理を実装。
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）自動ロード機能（プロジェクトルートは .git または pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を使った自動ロード無効化。
    - .env パーサー（コメント、export プレフィックス、クォート、エスケープ処理に対応）。
    - 設定ラッパークラス Settings（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル 等）。
    - 必須環境変数未設定時に ValueError を送出する _require 関数。
    - KABUSYS_ENV / LOG_LEVEL のバリデーションを実装（有効値制約）。
- J-Quants API クライアントを実装。
  - src/kabusys/data/jquants_client.py
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得関数を実装（ページネーション対応）。
    - API レート制御（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行）。
    - 401 を受信した場合はトークン自動リフレッシュを一回だけ行う仕組みを実装（トークンキャッシュ共有）。
    - JSON デコードエラーやネットワークエラーのハンドリング、Retry-After ヘッダ考慮。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等化。
    - 取得時刻（fetched_at）を UTC で記録し look-ahead bias のトレースを容易にする設計。
    - 型変換ユーティリティ _to_float / _to_int（不正値・空値は None）。
- ニュース収集モジュールを実装。
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を取得・前処理し DuckDB に保存するワークフローを提供。
    - 既定の RSS ソース（Yahoo Finance）を定義（DEFAULT_RSS_SOURCES）。
    - セキュリティ対策実装:
      - defusedxml による XML パース（XML Bomb 等対策）。
      - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベート/ループバック/リンクローカル判定、リダイレクト時の検査ハンドラ（_SSRFBlockRedirectHandler）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および Gzip 解凍後サイズ検査（Gzip bomb 対策）。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url, _TRACKING_PARAM_PREFIXES）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）から生成する _make_article_id により冪等性を保証。
    - テキスト前処理（URL 除去・空白正規化）の preprocess_text。
    - RSS 取得関数 fetch_rss（XML パースエラーを安全に扱い、各ソースは独立してエラー処理）。
    - DB 保存関数:
      - save_raw_news: チャンク挿入、トランザクション、INSERT ... RETURNING で実際に挿入された記事IDを返却。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを ON CONFLICT DO NOTHING で冪等保存（チャンク & トランザクション）。
    - 銘柄コード抽出ロジック extract_stock_codes（4桁数字、known_codes によるフィルタ、重複除去）。
    - 統合収集ジョブ run_news_collection（複数ソースの個別エラーハンドリング、既知銘柄の紐付けを一括で実行）。
- DuckDB スキーマ定義と初期化機能を実装。
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution 層に対応したテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
    - 各テーブルに制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を付与。
    - インデックス定義（頻出クエリ向け）を追加。
    - init_schema(db_path) により必要な親ディレクトリの自動作成・DDL 実行を行い接続を返す（冪等）。
    - get_connection(db_path) で単純接続取得。
- ETL パイプラインの基礎を実装。
  - src/kabusys/data/pipeline.py
    - ETLResult データクラス（取得件数、保存件数、品質問題、エラー一覧等）を提供。
    - テーブル存在確認、最大日付取得ユーティリティ（_table_exists, _get_max_date）。
    - 市場カレンダーに基づく営業日調整ヘルパー _adjust_to_trading_day。
    - 差分更新ヘルパー関数（get_last_price_date/get_last_financial_date/get_last_calendar_date）。
    - run_prices_etl の骨格を実装（差分取得ロジック、backfill_days、_MIN_DATA_DATE など）。※実装途中（ファイル末尾で切れているため完全実装は次リリース想定）。
- パッケージ構成ファイル（空の __init__.py など）を追加してモジュール群を整理。
  - src/kabusys/data/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py

Security
- ニュース収集で複数の安全対策を導入（defusedxml、SSRF ブロック、レスポンスサイズ制限、gzip 解凍後サイズ検査、URL スキーム検証）。
- J-Quants API クライアントでタイムアウトやリトライ、429 の Retry-After を考慮した実装を採用。

Notes / Known limitations
- run_prices_etl の末尾が現時点のスナップショットで切れており、戻り値の組み立てやその他 ETL ジョブ群（財務・カレンダーの ETL）は次のリリースで完成予定。
- データベース操作は DuckDB を前提としており、実行環境に duckdb パッケージと適切なファイルパス権限が必要。
- .env の自動読み込みはプロジェクトルート検出に依存（.git または pyproject.toml）。パッケージ配布後に振る舞いを変えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。

References
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照。