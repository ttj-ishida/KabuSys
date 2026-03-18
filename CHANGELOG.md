Keep a Changelog 準拠の CHANGELOG.md（日本語）

すべての変更は semver に従います。初版リリース v0.1.0 を記録しています。

Unreleased
----------
- （なし）

0.1.0 - 2026-03-18
------------------
Added
- パッケージ初期化
  - kabusys パッケージの初期バージョンを追加。__version__ = "0.1.0"。
  - パッケージ公開 API（data, strategy, execution, monitoring）のプレースホルダを準備。

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする機能を実装。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパースは export プレフィックス、シングル/ダブルクォート、インラインコメントを適切に扱うロバストな実装。
  - OS 環境変数を保護する protected オプション（.env.local による上書き時に保護）をサポート。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パスなどの設定をプロパティ経由で取得。必須項目未設定時に ValueError を送出。
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証ロジックを追加。is_live / is_paper / is_dev の便利プロパティを提供。
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）の既定値を設定。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しの共通ロジックを実装（_request）。JSON デコード失敗時のエラー処理、HTTP エラーとネットワークエラーに対するリトライ（指数バックオフ）を実装。
  - レート制限（120 req/min）を固定間隔スロットリングで制御する _RateLimiter を実装。
  - 認証周り: get_id_token によるリフレッシュトークン→IDトークン取得、モジュールレベルのトークンキャッシュ、401 発生時の自動リフレッシュ（最大1回）をサポート。
  - データ取得関数を追加:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数を追加（冪等性を重視: ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 取得時刻（fetched_at）を UTC ISO 形式で記録する設計。型変換ユーティリティ（_to_float/_to_int）を実装。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集パイプラインを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - セキュリティ対策:
    - defusedxml を使用した XML パースで XML Bomb 等を緩和。
    - SSRF 対策: リダイレクト時のスキーム検証とホスト/IP のプライベートアドレス検査（_SSRFBlockRedirectHandler, _is_private_host）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ再チェック。
  - コンテンツ処理:
    - URL 正規化（トラッキングパラメータ除去、クエリソート）と SHA-256 による記事ID生成（先頭32文字）。
    - テキスト前処理（URL除去、空白正規化）。
    - 銘柄コード抽出（4桁数字候補を known_codes でフィルタ）。
  - DB 保存はチャンク単位でのバルク INSERT を行い、トランザクションと INSERT ... RETURNING を使って新規挿入された記事ID・件数を正確に返す設計。
  - デフォルトの RSS ソースとして Yahoo Finance を登録。

- DuckDB スキーマ（kabusys.data.schema）
  - DataPlatform 設計に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw 層。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を含む Processed 層。
  - features, ai_scores を含む Feature 層。
  - signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層。
  - 頻出クエリ向けのインデックス定義を追加。
  - init_schema(db_path) でディレクトリ作成（必要時）と全DDL/インデックスの作成を行い、接続を返す。get_connection() も提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL 実行結果を表す ETLResult dataclass を導入（品質問題・エラーメッセージの集約、辞書化メソッドを含む）。
  - DB の最終取得日を取得するユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーを考慮した営業日調整ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl の骨組みを実装（差分取得、backfill_days による遡り、J-Quants からの取得→保存）。差分更新のロジックとデフォルト振る舞いを定義。
  - 品質チェックフレームワーク（quality モジュール呼び出し想定）を想定した設計（品質問題は ETL を中断せずに集約して返す方針）。

Security
- defusedxml, SSRF 向けホスト/IP 検証、URL スキーム検証、受信バイト数の上限など複数の防御層を導入。
- .env 読み込みで OS 環境変数が意図せず上書きされないよう protected set を導入。

Performance / Reliability
- API レート制御（120 req/min）、指数バックオフ付きリトライ、429 の Retry-After 優先採用。
- DuckDB へのバッチ/チャンク挿入、トランザクションまとめにより DB 書き込みオーバーヘッドを軽減。
- ページネーション対応で大量データ取得を安全に処理。

Known Issues
- run_prices_etl の実装は現状途中（ソース末尾が return len(records), となっており、期待する (fetched_count, saved_count) のタプルを完全に返していない／処理が未完の箇所があります。ETL の統合実行や戻り値の仕様は次版で確定・修正予定です。
- strategy / execution / monitoring パッケージは __init__.py がプレースホルダのまま（具体的実装は未提供）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

BREAKING CHANGES
- なし（初回リリース）。

Migration notes
- 初回導入時は init_schema(settings.duckdb_path) を呼んで DB スキーマを作成してください。
- テストや CI 環境で自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants / Slack 等の必須環境変数を未設定の場合、Settings のプロパティ呼び出しで ValueError が発生します。.env.example を参照して設定してください。

今後の予定（一例）
- run_prices_etl 等 ETL ジョブの完成と品質チェック（quality モジュール）統合。
- strategy / execution ロジックの実装（シグナル生成→発注→ポジション管理のワークフロー）。
- テストコードの充実、CI パイプライン導入、ドキュメント整備。