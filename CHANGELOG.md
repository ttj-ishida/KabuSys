# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

※初期リリースはコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-17

Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基盤機能を実装。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
  - エクスポートモジュール: data, strategy, execution, monitoring

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local および OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env パーサ実装: コメント、export プレフィックス、クォート・エスケープ対応、インラインコメント処理をサポート。
  - Settings クラス提供: J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルなどの取得・検証用プロパティを実装。
  - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを定義（data/ 以下）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得用 API ラッパーを実装。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を遵守（内部 RateLimiter）。
  - リトライ戦略: 指数バックオフ、最大リトライ 3 回、HTTP 408/429 および 5xx に対する再試行。
  - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライ（無限再帰防止）。
  - ページネーション対応（pagination_key を追跡）。
  - データ保存用関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - DuckDB への冪等保存を実現（INSERT ... ON CONFLICT DO UPDATE）。
    - fetched_at を UTC で記録し Look-ahead Bias のトレーサビリティを確保。
    - PK 欠損レコードはスキップしてログ出力。
  - ユーティリティ変換関数: 安全な _to_float / _to_int（文字列 float からの int 変換時の安全処理含む）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得と raw_news 保存パイプラインを実装。
  - セキュリティ対策:
    - defusedxml を利用した XML パース（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム制限（http/https のみ）、ホストのプライベートアドレス検査（IP 直接判定および DNS 解決して A/AAAA を確認）、リダイレクト時の事前検査ハンドラ実装。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後もサイズ検査（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ削除（utm_* 等）、SHA-256 ハッシュ（先頭32文字）で記事IDを生成し冪等性を確保。
  - テキスト前処理: URL 除去、空白正規化。
  - DB 保存:
    - INSERT ... RETURNING を利用し、実際に挿入された記事 ID を返却（チャンク分割・1 トランザクション）。
    - news_symbols（記事と銘柄の紐付け）を一括保存する内部関数（重複除去・チャンク挿入・トランザクション）。
  - 銘柄抽出: 正規表現で 4 桁数字を抽出し、known_codes によるフィルタリングで有効銘柄のみ返す。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを登録。

- DuckDB スキーマ定義 & 初期化（src/kabusys/data/schema.py）
  - DataPlatform 設計に基づくスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）とカラム型を定義。
  - パフォーマンス向けのインデックス群を作成。
  - init_schema(db_path)：親ディレクトリ自動作成、DDL をすべて実行して DuckDB 接続を返す（冪等）。
  - get_connection(db_path)：既存 DB への接続を返す（初期化は行わない）。

- ETL パイプラインの基礎（src/kabusys/data/pipeline.py）
  - 差分更新（差分 ETL）の仕組みを実装するためのヘルパー群と結果クラス:
    - ETLResult dataclass（取得数、保存数、品質問題、エラー一覧などを保持）。
    - テーブル存在チェック、最大日付取得ユーティリティ。
    - 市場カレンダーに基づく営業日調整関数（_adjust_to_trading_day）。
    - raw_prices / raw_financials / market_calendar の最終取得日取得関数。
  - run_prices_etl の骨組み:
    - 差分取得ロジック（最終取得日から backfill_days 分を再取得するデフォルト挙動）。
    - jq.fetch_daily_quotes を用いた取得 → jq.save_daily_quotes による保存。
    - （設計方針）品質チェックモジュールと組み合わせる想定（quality モジュール参照）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- ニュース収集での SSRF / XML Bomb / Gzip Bomb 対策を実装。
- .env 読み込み時に OS 環境変数を保護するための protected キー機構。

Notes / Migration
- 初回データベース初期化は schema.init_schema(db_path) を呼び出してください（":memory:" も可）。
- .env の自動読み込みをテスト中に無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API の認証には JQUANTS_REFRESH_TOKEN が必須です（Settings.jquants_refresh_token が取得・検証を行う）。
- NewsCollector の既知銘柄抽出には known_codes を渡すことで正確な紐付けが可能です（run_news_collection の引数）。

Acknowledgements / Design
- API クライアントではレート制限順守、リトライ・トークンリフレッシュ、取得時刻の記録により再現性と堅牢性を重視。
- DB 保存では冪等性（ON CONFLICT）とトランザクション（bulk insert）により安全な再実行・高効率化を図っています。

--- 

（必要に応じてリリース日や詳細を実際の履歴に合わせて調整してください。）