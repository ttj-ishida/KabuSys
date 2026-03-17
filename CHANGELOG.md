CHANGELOG
=========

すべての注目すべき変更はこのファイルで管理します。フォーマットは "Keep a Changelog" に準拠します。
リリースはセマンティックバージョニングに従います。

[Unreleased]
-------------

v0.1.0 - 2026-03-17
-------------------

Added
- パッケージ初期公開: kabusys 0.1.0
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ に追加。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロードを実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込む（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env 読み込みにおいて export プレフィックス、クォート文字列、インラインコメント処理をサポート。
    - OS 環境変数を保護する protected 上書きロジック（.env.local は上書き、.env は未設定のみ設定）。
  - Settings クラスを提供し、必須項目は取得時に検証:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須チェック。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルト値。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証を実装。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - v1 API から株価（OHLCV）・財務（四半期BS/PL）・マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - 認証トークン取得（get_id_token）とモジュールレベルのトークンキャッシュを実装。401 受信時の自動リフレッシュを1回保証。
  - API レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx 等の再試行対象に対応。429 の Retry-After ヘッダ優先。
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装:
    - fetched_at を UTC で記録（Look-ahead Bias 対策）。
    - 冪等性を確保するため INSERT ... ON CONFLICT DO UPDATE を使用。
    - PK 欠損行のスキップとログ出力、変換ユーティリティ（_to_float / _to_int）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news に保存する機能を実装。
    - デフォルトソース（Yahoo Finance のビジネス RSS）を定義。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）を採用し冪等性を確保。
    - defusedxml を利用し XML Bomb 等の攻撃を防御。
    - SSRF 対策:
      - fetch 前にスキーム検証（http/https のみ許可）。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないことを判定（IP 直接判定および DNS 解決）。
      - リダイレクト時にも検証を行うカスタム HTTPRedirectHandler を導入。
    - 応答サイズ上限（MAX_RESPONSE_BYTES=10MB）を導入し、gzip 解凍後もサイズチェック（Gzip bomb 対策）。
    - テキスト前処理（URL除去・空白正規化）。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使って新規挿入IDを正確に取得。チャンク・トランザクションで実行。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへ記事と銘柄コードの紐付け（チャンク挿入、ON CONFLICT DO NOTHING、トランザクション）。
    - 銘柄コード抽出: 4桁数字を抽出し、既知コードセットでフィルタリング（extract_stock_codes）。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature / Execution）をカバーする DDL を実装。
    - raw_prices, raw_financials, raw_news, raw_executions など Raw Layer。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed Layer。
    - features, ai_scores など Feature Layer。
    - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution Layer。
  - 各種制約・CHECK・PRIMARY KEY・FOREIGN KEY を定義。
  - 頻出クエリに対するインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status）。
  - init_schema(db_path) でディレクトリ作成（必要なら）→ 全テーブル・インデックスを作成して接続を返す。get_connection() で既存 DB に接続可能。

- ETL パイプライン骨組み (src/kabusys/data/pipeline.py)
  - 差分更新方針の実装を開始（最終取得日算出、backfill_days による再取得、calendar の先読み等）。
  - ETLResult dataclass を導入し、取得数・保存数・品質問題・エラー一覧等を集約して返却可能に。
  - テーブル存在チェック、最大日付取得ユーティリティ (_table_exists, _get_max_date) を実装。
  - 市場カレンダーを考慮した営業日調整ヘルパー (_adjust_to_trading_day) を提供。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を追加。
  - run_prices_etl を実装（差分計算、backfill を考慮した date_from 決定、jq.fetch_daily_quotes → jq.save_daily_quotes の呼び出し）。
    - ※ 現状 run_prices_etl の返却値の実装箇所が途中で終わっているため、最新版では保存数の返却などに注視が必要（実装継続予定）。

- パッケージ構成
  - data パッケージ内に jquants_client, news_collector, schema, pipeline を実装。strategy, execution, monitoring のプレースホルダパッケージを作成。

Security
- ニュース収集における SSRF 対策、defusedxml 使用、受信最大バイト数制限、gzip 解凍後の検査などを導入。
- .env 読み込みにおける OS 環境変数保護（protected set）を実装し、テスト / 実行時の誤上書きを防止。

Changed
- 初回公開のため該当なし。

Deprecated
- 初回公開のため該当なし。

Removed
- 初回公開のため該当なし。

Fixed
- 初回公開のため該当なし。

Notes / Known issues
- run_prices_etl の最後の return が途中で切れている（コード末尾が未完のため、戻り値の整備が必要）。ETL の一部実装は継続中。
- strategy/ execution / monitoring パッケージは現時点では空のプレースホルダ（拡張予定）。
- DuckDB の型や制約は設計段階で決定されているが、実運用に合わせたチューニング（インデックス追加・パーティショニング等）が今後必要になる可能性あり。

Referenced files
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/data/schema.py
- src/kabusys/data/pipeline.py
- その他パッケージ初期化ファイル

以上。