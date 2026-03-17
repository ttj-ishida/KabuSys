# Changelog

すべての重要な変更をここに記録します。  
このファイルは「Keep a Changelog」フォーマットに従います。  
リリース日はコードベースの snapshot に基づき設定しています。

## [0.1.0] - 2026-03-17

### Added
- 新規パッケージ「KabuSys」初期リリース。
  - パッケージメタ情報:
    - version = 0.1.0
    - パッケージ公開モジュール: data, strategy, execution, monitoring（__all__ に定義）

- 設定管理モジュール（kabusys.config）
  - .env / .env.local ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート検出：.git または pyproject.toml 基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装（export プレフィックス対応、引用符のエスケープ処理、インラインコメントの扱い等）。
  - 必須環境変数取得ヘルパーと Settings クラスを提供。主要な設定プロパティ：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）
    - 環境判定ユーティリティ: is_live / is_paper / is_dev

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API レート制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
  - リトライロジック: 指数バックオフ、最大 3 回。リトライ対象ステータス（408、429、5xx）に対応。429 の場合は Retry-After ヘッダ優先。
  - 認証トークン管理: refresh token から id_token を取得する get_id_token、モジュールレベルのトークンキャッシュと自動リフレッシュ（401 受信時に1回リフレッシュしてリトライ）。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes（OHLCV 日足）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 挿入は ON CONFLICT DO UPDATE を用いた冪等性を保証
    - 各レコードに fetched_at を UTC ISO8601 で付与して取得時刻をトレース可能に

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得・前処理・DuckDB への保存ワークフローを実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の防御）
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホスト/IP のプライベートアドレス判定（DNS 解決も実施）、リダイレクト時の検査（_SSRFBlockRedirectHandler）
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズチェック（Gzip bomb 対策）
  - 正規化と重複対策:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリをキーでソート）
    - 記事 ID = 正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保
  - テキスト前処理（URL 除去、空白正規化）
  - DB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を使い、実際に挿入された記事IDを返す（チャンクと単一トランザクション）
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けを一括挿入（ON CONFLICT で重複排除、INSERT RETURNING で実挿入数を把握）
  - 銘柄コード抽出ユーティリティ（4桁数字、既知銘柄セットでフィルタ）

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataPlatform の三層（Raw / Processed / Feature / Execution）に基づくテーブル群を定義。
  - 主なテーブル（抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）と頻出クエリ向けインデックスを定義。
  - init_schema(db_path) により親ディレクトリ作成 → DuckDB 接続 → 全 DDL/INDEX を実行（冪等）。
  - get_connection(db_path)：既存 DB への接続取得（スキーマ初期化は行わない）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新に基づく ETL の設計と実装（差分取得、保存、品質チェックの呼び出し方針を含む）。
  - ETLResult データクラスを導入（取得数/保存数/品質問題/エラーの集約、辞書化ユーティリティ）。
  - 差分取得ヘルパー:
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
    - _adjust_to_trading_day（非営業日の補正）
  - run_prices_etl（株価日足 ETL）を実装（差分/バックフィル処理、デフォルト backfill_days = 3、初回ロード日付 = 2017-01-01 等）
  - 定数:
    - _MIN_DATA_DATE = 2017-01-01
    - _CALENDAR_LOOKAHEAD_DAYS = 90
    - _DEFAULT_BACKFILL_DAYS = 3

### Security
- 外部入力（RSS / URL）に対する複数の防御を実装：
  - defusedxml による XML パース、防御的な例外ハンドリング
  - SSRF 対策（スキーム制限、プライベート IP/ホスト判定、リダイレクト検査）
  - レスポンスサイズ・gzip 解凍後のサイズ制限（DoS 緩和）
  - ニュース収集・API クライアントにおける適切なタイムアウトと例外ハンドリング

### Notes / Migration
- 初期セットアップ:
  - 必要な環境変数（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
  - データベース初期化は必ず init_schema() を実行してください（初回のみ）。
- 自動 .env 読み込みはプロジェクトルートの検出に依存するため、配布後に .env を正しく読み込ませたい場合は .git または pyproject.toml を配置してください。テスト等で自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート・リトライ挙動に依存しているため、大量取得時はリクエスト間隔に注意してください（120 req/min 制限）。

### Known limitations / TODO
- strategy, execution, monitoring パッケージの具体的な実装は未包含（パッケージは空の __init__ として存在）。
- pipeline.run_prices_etl の末尾が不完全（戻り値タプルの構築が途中で終わっているなどの痕跡あり）。（将来的に run_prices_etl の return 値整備が必要）
- 一部のユーティリティ関数やエラーメッセージの国際化（i18n）やロギング強化は未検討事項。

---

（将来のリリースでは Changed / Fixed / Removed セクションを追加予定）