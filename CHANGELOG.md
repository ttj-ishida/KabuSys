Keep a Changelog準拠 — CHANGELOG.md

すべての変更は「Keep a Changelog」規約に従って記載しています。  
このファイルはコードベース（src/kabusys 配下）の現状から推測して作成した初期リリースの変更履歴です。

Unreleased
----------
- Known issues / TODO:
  - run_prices_etl の戻り値がソース内で不完全（末尾が切れており saved 値を返していない可能性がある）。修正が必要。
  - data.pipeline で参照される quality モジュールの実装／公開場所に注意（本コードスニペットでは定義が見えないため、プロジェクト内で提供されていることを確認する必要あり）。
  - ユニットテスト、統合テスト、CI ワークフローの追加。
  - ドキュメント（API 使用例、運用手順、マイグレーション手順）の拡充。

[0.1.0] - 2026-03-17
--------------------
Added
- 基本パッケージ構成を追加
  - kabusys パッケージの骨格（__init__.py）を追加。__version__ = "0.1.0" を定義し、公開サブパッケージを列挙。
  - 空のサブパッケージモジュールを配置: kabusys.execution, kabusys.strategy, kabusys.data（入口モジュールあり）。

- 環境設定管理（kabusys.config）を実装
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを提供（プロジェクトルート検出: .git または pyproject.toml）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env と .env.local の読み込み順序および override/保護（protected）挙動の実装。
  - .env 行パーサー（export 構文、クォート処理、コメント取り扱い）を実装。
  - Settings クラスを提供し、以下の設定をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパー: is_live, is_paper, is_dev

- J-Quants クライアント（kabusys.data.jquants_client）を実装
  - API のベースURLやレート制限に基づくクライアントを実装（_BASE_URL, レート制限 120 req/min）。
  - 固定間隔スロットリングを行う _RateLimiter 実装。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を再試行対象）。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（get_id_token を呼び 1 回リトライ）。
  - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）。
  - JSON デコード検査と詳細なエラーロギング。
  - データ取得関数:
    - fetch_daily_quotes: 日次株価（ページネーションサポート）
    - fetch_financial_statements: 四半期財務（ページネーションサポート）
    - fetch_market_calendar: JPX カレンダー取得
  - DuckDB への冪等的保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - データ整形ユーティリティ: _to_float, _to_int（安全な変換ルール）

- ニュース収集モジュール（kabusys.data.news_collector）を実装
  - RSS フィードから記事を収集し DuckDB に保存する ETL ロジック。
  - 設計上の主な機能:
    - トラッキングパラメータ除去（utm_* 等）を含む URL 正規化と記事 ID（SHA-256 の先頭32文字）生成。
    - defusedxml による XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証、プライベートIP/ループバック/リンクローカル判定、リダイレクト時の事前検査（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - テキスト前処理（URL 除去、空白正規化）。
    - DuckDB へのバルク挿入で冪等性を担保（INSERT ... ON CONFLICT DO NOTHING）し、INSERT ... RETURNING を用いて挿入された ID を取得。
    - news_symbols（記事 ↔ 銘柄コード）紐付けのバルク保存機能（チャンク化、トランザクションまとめ）。
    - 銘柄抽出: 正規表現で 4 桁銘柄コードを抽出し、known_codes でフィルタリング。
  - デフォルトRSSソースとして Yahoo Finance のカテゴリフィードを登録（DEFAULT_RSS_SOURCES）。

- DuckDB スキーマ定義（kabusys.data.schema）を実装
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を追加:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を含む DDL を提供。
  - よく使われるクエリに対するインデックスを定義（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成と DDL 実行（冪等）、get_connection(db_path) で接続取得。

- ETL パイプラインの骨子（kabusys.data.pipeline）を実装
  - ETLResult dataclass による実行結果の構造化（品質問題・エラー・取得/保存件数等を保持）。
  - テーブル存在確認、最大日付取得の汎用ユーティリティ実装（_table_exists, _get_max_date）。
  - market_calendar を利用した営業日に調整するヘルパー（_adjust_to_trading_day）。
  - 差分更新用ユーティリティ: get_last_price_date, get_last_financial_date, get_last_calendar_date。
  - run_prices_etl の設計:
    - 差分更新ロジック（最終取得日から backfill_days を使って再取得）
    - J-Quants クライアント呼び出しと save の利用
    - （注: ソースの末尾で戻り値が不完全に見える箇所あり。要修正/確認）

Security
- セキュリティ対策を複数実装/考慮:
  - defusedxml による XML パース（XML エクスプロージョン対策）。
  - RSS フェッチ時の SSRF 対策: スキームフィルタ、プライベートIP検出、リダイレクト先検証。
  - .env ローダーは OS 環境変数を保護（protected set）し、必要に応じて上書きを制御。
  - HTTP リクエスト時のタイムアウト設定とレスポンスサイズ上限。

Performance & Reliability
- API コールのレート制御（120 req/min 固定）を _RateLimiter で実装。
- ネットワーク障害や HTTP レート制限（429）のためのリトライと指数バックオフ実装。
- ページネーション対応（pagination_key）でのデータ取得を実装。
- DuckDB へのバルク挿入をチャンク化しトランザクションでまとめて処理（挿入オーバーヘッドを削減）。
- fetch/save 間で fetched_at（UTC）を記録し、Look-ahead Bias を防ぐ設計。

Changed
- 初回リリースにつき該当なし。

Fixed
- 初回リリースにつき該当なし。

Removed / Deprecated
- 初回リリースにつき該当なし。

Notes（運用/導入時の注意）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルトの DuckDB パスは data/kabusys.duckdb。init_schema() は親ディレクトリを自動作成します。
- KABUSYS_ENV の値は development / paper_trading / live のいずれかにする必要があります。
- run_news_collection の銘柄抽出は known_codes を与えた場合のみ実行される（known_codes に存在しない 4 桁数値は無視される）。
- ニュース収集では記事IDを URL 正規化 → SHA256 ハッシュで作成するため、同一の論理記事はデータベースで冪等に扱われます。

開発者向けメモ
- run_prices_etl の戻り値や pipeline の続きのロジックを確認・修正してください（現状ソースが途中で切れているように見えます）。
- quality モジュールの API と重大度定義（QualityIssue）を確認して pipeline と整合させてください。
- ユニットテスト、外部依存（ネットワーク／DB）を分離したモック群の整備を推奨します。

ライセンス / 著作権
- 本 CHANGELOG はコードスニペットから推測して作成したものであり、実際のリポジトリ履歴（コミットログ）ではありません。実際のリリース履歴を作成する際はコミット単位・タグを元に差分を精査してください。