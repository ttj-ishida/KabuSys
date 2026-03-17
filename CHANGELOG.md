CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  

注: 以下は提示されたコードベースの実装内容から推測して作成した初期リリースの変更履歴です。

[Unreleased]
------------

（なし）

0.1.0 - 2026-03-17
------------------

Added
- 全体
  - プロジェクト初期リリース。パッケージ名を kabusys として公開。バージョンは 0.1.0 に設定。
  - モジュール構成（主要パッケージ）:
    - kabusys.config: 環境変数／設定管理
    - kabusys.data: データ取得・保存・スキーマ・パイプライン
    - kabusys.data.jquants_client: J-Quants API クライアント実装
    - kabusys.data.news_collector: RSS ニュース収集器
    - kabusys.data.schema: DuckDB スキーマ定義・初期化
    - kabusys.data.pipeline: ETL パイプライン（差分取得・保存・品質チェックの枠組み）
    - 空のパッケージプレースホルダ: kabusys.execution, kabusys.strategy

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定を安全に読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - テスト等で自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグに対応。
  - .env パーサーの改善:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートされた値内のバックスラッシュエスケープ対応。
    - コメント（#）の扱いを文脈に応じて適切に無視。
  - 既存 OS 環境変数を保護する protected キーの概念を導入（.env.local が上書きする際の保護等に利用）。
  - Settings クラスを提供し、必須値取得用 _require、各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL）を実装。
  - KABUSYS_ENV と LOG_LEVEL 値のバリデーション（許容値チェック）を実装。環境判定用のヘルパープロパティ（is_live/is_paper/is_dev）を提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しラッパー _request を実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter 実装。
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）。
    - 401 Unauthorized 受信時はリフレッシュトークンから id_token を自動更新して 1 回だけリトライ（無限再帰防止フラグあり）。
    - JSON デコード失敗時の明確なエラーメッセージ。
  - get_id_token: リフレッシュトークンから ID トークンを取得する POST 呼び出しを実装（settings から既定のトークン取得）。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes: 日次株価（OHLCV）のページネーション取得。
    - fetch_financial_statements: 四半期財務データのページネーション取得。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）を実装:
    - save_daily_quotes: raw_prices テーブルに日次株価を保存。fetched_at を UTC ISO8601 で記録。
    - save_financial_statements: raw_financials テーブルに財務データを保存。
    - save_market_calendar: market_calendar テーブルにカレンダーデータを保存。HolidayDivision をもとに is_trading_day/is_half_day/is_sq_day を判定。
  - データ変換ユーティリティ:
    - _to_float / _to_int：安全に float/int に変換（不正入力や小数切り捨ての誤りを防止）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集パイプラインの実装。
    - デフォルトソース（例: Yahoo Finance のビジネス RSS）を設定。
    - XML パースに defusedxml を利用し XML Bomb 等の脆弱性対策。
    - SSL/HTTP リダイレクトや SSRF を防ぐための検証:
      - URL スキームは http/https のみ許可。
      - 事前にホストがプライベート／ループバック等でないかチェックし、リダイレクト先も検査。
      - リダイレクトハンドラ _SSRFBlockRedirectHandler による安全なリダイレクト検査。
    - 大容量レスポンス対策:
      - MAX_RESPONSE_BYTES（デフォルト 10MB）を超えるレスポンスは破棄。
      - gzip 圧縮レスポンスの検査と解凍後サイズチェック（Gzip bomb 対策）。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）を実装。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存処理（DuckDB）:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を利用し、実際に挿入された記事ID一覧を返す。チャンク挿入（_INSERT_CHUNK_SIZE）とトランザクション管理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で安全に保存。ON CONFLICT で重複除去、TRANSACTION の扱いを実装。
  - 銘柄抽出:
    - extract_stock_codes: テキスト中の 4 桁数字候補を known_codes でフィルタリングして抽出（重複除去）。
  - 統合ジョブ run_news_collection: 複数ソースから収集→保存→（既知銘柄が与えられれば）紐付けを実行。ソース単位で独立してエラー処理。

- DuckDB スキーマ（kabusys.data.schema）
  - DataPlatform 設計に基づくスキーマ定義と init_schema を提供。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム制約（CHECK, NOT NULL, PRIMARY KEY, FOREIGN KEY）を定義しデータ整合性を強化。
  - 頻出クエリ向けのインデックスを複数定義（code/date ベース、status 検索など）。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成＆DDL 実行（冪等）。get_connection() で既存 DB へ接続。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass を導入し ETL の結果（取得数、保存数、品質問題、エラー）を構造化して返す仕組みを実装。
  - 差分取得ユーティリティ:
    - _table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date を実装。
    - _adjust_to_trading_day: 非営業日を直近の営業日に調整するロジック（market_calendar 利用）。
  - run_prices_etl: 差分更新の考え方を実装（最終取得日から backfill_days 前を date_from にする等）、fetch と save の呼び出しを組み合わせる。デフォルトの backfill_days=3、最小取得日 _MIN_DATA_DATE を考慮。

Security
- 脆弱性対策を多数導入:
  - defusedxml による XML パース（XML Bomb 対策）。
  - SSRF 対策: ホストのプライベートアドレス検査、リダイレクト前検査、スキーム制限。
  - レスポンスサイズ上限と gzip 解凍後サイズチェックによるメモリ DoS 対策。
  - .env 値の取り扱いで OS 環境変数の保護をサポート。

Compatibility
- DuckDB を利用するため、動作環境に duckdb パッケージが必要。
- defusedxml を XML パースに使用。
- jquants API の認証フロー（リフレッシュトークン→idToken）に依存する。

Known issues / Notes
- run_prices_etl の末尾での return 文が不完全（コード断片では `return len(records),` のように見える）。意図としては (fetched_count, saved_count) を返すべきだが、現在のコードではタプルの欠落や戻り値の不整合が発生する可能性があるため修正が必要。
- pipeline モジュールは品質チェック（quality モジュール）に依存しているが、quality の実装の有無はコード一覧からは確認できないため、実行時に品質チェック機能の提供状況を確認する必要あり。
- kabusys.execution / kabusys.strategy の初期化モジュールはプレースホルダ（空）として存在。実際の売買戦略・発注ロジックは別途実装が必要。
- 一部の SQL 実行で直接文字列連結を用いている箇所があり（プレースホルダ数に応じた VALUES の構築等）、将来の保守性向上のために抽象化や安全なバインドの方式を検討する余地あり。

Acknowledgements
- 本コードベースは J-Quants API、DuckDB、defusedxml 等を利用して日本株向け自動売買向けデータ基盤を構築することを目的とした初期リリースの実装を含みます。