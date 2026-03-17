CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは "Keep a Changelog" の慣習に従います。
履歴は semver に基づきバージョン毎に管理します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージのメタ情報およびエクスポート:
    - src/kabusys/__init__.py にて __version__="0.1.0"、主要サブパッケージを __all__ で公開 (data, strategy, execution, monitoring)。
- 環境設定管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
  - .env の堅牢なパース:
    - export 付き行、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 必須環境変数取得ヘルパー (_require) と Settings クラスを提供。主な設定項目:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL 検証
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 主要機能:
    - 株価日足（OHLCV）取得 fetch_daily_quotes（ページネーション対応）
    - 財務データ取得 fetch_financial_statements（ページネーション対応）
    - JPX マーケットカレンダー取得 fetch_market_calendar
    - リフレッシュトークンからの id_token 取得 get_id_token（POST）
  - 設計上の耐障害/運用機能:
    - 固定間隔スロットリングによるレート制御（120 req/min）を実装する内部 RateLimiter。
    - 再試行ロジック（指数バックオフ、最大3回）を導入。408/429/5xx をリトライ対象。
    - 401 受信時は id_token を自動リフレッシュして 1 回のみリトライ（再帰防止の allow_refresh 制御）。
    - id_token キャッシュをモジュールレベルで保持し、ページネーション間で共有。
  - DuckDB への保存関数（冪等設計）:
    - save_daily_quotes, save_financial_statements, save_market_calendar: ON CONFLICT DO UPDATE により重複排除／上書き。
    - fetched_at を UTC ISO8601 形式で保存し、データの取得時点をトレース可能に。
  - データ変換ユーティリティ: _to_float, _to_int（文字列数値の安全な変換ルールを定義）
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード収集と DuckDB への保存機能一式を実装:
    - fetch_rss: RSS フィード取得、XML パース、記事リスト生成（title, content, datetime, url, source）
    - save_raw_news: INSERT ... RETURNING による新規記事IDリストの取得（チャンク & 単一トランザクション）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け保存（ON CONFLICT DO NOTHING, RETURNING）
    - run_news_collection: 複数ソースの統合収集ジョブ、各ソース独立エラーハンドリング
  - セキュリティ／頑健性の設計:
    - defusedxml を使用して XML Bomb 等の攻撃を軽減。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - リダイレクト先のスキームとホストを検査するカスタムリダイレクトハンドラ (_SSRFBlockRedirectHandler)
      - ホスト名を DNS 解決してプライベート/ループバック/リンクローカル/マルチキャストを拒否
    - レスポンス受信上限（MAX_RESPONSE_BYTES = 10 MB）や gzip 解凍後のサイズチェックを実装しメモリDoSを防止。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）および記事ID の SHA-256（先頭32文字）での生成（_make_article_id）により冪等性を保証。
  - テキスト前処理と銘柄抽出:
    - preprocess_text: URL除去、空白正規化
    - extract_stock_codes: 正規表現で4桁銘柄コードを抽出し既知コードセットでフィルタ（重複除去）
  - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを用意（DEFAULT_RSS_SOURCES）
- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DataSchema.md に基づいたテーブル群を定義（Raw / Processed / Feature / Execution 層）
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック・外部キーを含む DDL を用意（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY 等）。
  - よく使うクエリ用のインデックスを作成。
  - init_schema(db_path) により親ディレクトリ自動作成、全DDLとインデックスを冪等に適用して接続を返す。
  - get_connection(db_path) で既存DBへの接続を取得（スキーマ初期化は行わない）。
- ETL パイプライン基本（src/kabusys/data/pipeline.py）
  - 差分更新・保存・品質チェックのための基礎機能:
    - ETLResult データクラス（品質問題やエラーの集約、辞書化メソッド to_dict を提供）
    - _table_exists / _get_max_date のユーティリティ
    - 市場カレンダー調整ヘルパー (_adjust_to_trading_day)
    - 差分取得用ヘルパー get_last_price_date / get_last_financial_date / get_last_calendar_date
    - run_prices_etl の骨組み（date_from 自動算出、backfill_days のサポート、fetch→save の流れ）
  - 設計上の方針をコード内に明記（backfill_days デフォルト3日、カレンダー先読み日数 90 日等）

Security
- XML パースに defusedxml を採用。
- RSS フェッチでの SSRF 対策（スキーム制限、プライベートホスト検出、リダイレクト検査）。
- HTTP レスポンスの読み込み上限と gzip 解凍後サイズ検証でリソース攻撃を軽減。
- .env パーサはクォート内のエスケープを処理し、コメント判定を慎重に実施。

Performance & Reliability
- J-Quants API クライアントに固定間隔レートリミッタと指数バックオフ付きリトライを導入。
- id_token の自動リフレッシュとキャッシュでページネーションや大量取得を効率化。
- DuckDB への保存は冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING）。
- ニュース保存はチャンク & トランザクションで高速化／整合性確保。INSERT ... RETURNING を利用して実挿入数を正確に報告。

Configuration / Requirements
- 必須環境変数（未設定時は Settings プロパティで ValueError を送出）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 既定の DB パス:
  - DUCKDB_PATH = data/kabusys.duckdb
  - SQLITE_PATH = data/monitoring.db
- 自動 .env ロードの無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化。

Notes / Known limitations
- strategy/ execution/ monitoring サブパッケージはパッケージ階層で用意されているが（__init__.py が存在）各機能の実装は初期段階であり、本リリースでは主にデータ収集・保存・スキーマ・ETL の基盤を提供。
- ETL の品質チェック（quality モジュール）は pipeline から参照される設計となっているが、品質チェックの実装詳細は別途（quality モジュールの実装を参照）。
- run_prices_etl の戻り値や処理の続き（financials/calendar の ETL 実行など）は今後拡張予定（このリリースでは run_prices_etl の取得→保存までの骨組みを提供）。

Contributing
- バグ報告・機能要望は issue へお願いします。セキュリティ関連の脆弱性を報告する場合は公開前にプライベートに連絡してください。

----