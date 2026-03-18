# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」規約に準拠しています。  
バージョン番号は semantic versioning に従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-18

初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。モジュール公開 (__all__) とバージョン情報を設定。
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートの .git または pyproject.toml を基準に検出）。
  - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数をサポート。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応）。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / ログレベル等の設定プロパティを提供。
  - KABUSYS_ENV, LOG_LEVEL の妥当性チェックと便利な is_live/is_paper/is_dev プロパティを追加。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API から株価日足、財務データ（四半期 BS/PL）、マーケットカレンダーを取得するクライアントを実装。
  - レート制御（120 req/min、固定間隔スロットリング）を実装。
  - 再試行ロジック（指数バックオフ、最大3回）と HTTP ステータス別のハンドリング（408, 429, 5xx）。
  - 401 応答時の自動トークンリフレッシュ（1回のみ）を実装し、トークン取得ロジックを提供（get_id_token）。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
  - DuckDB への冪等保存メソッドを提供（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT で更新することで重複を排除。
  - 取得日時（fetched_at）を UTC で記録することでデータをいつシステムが知り得たかをトレース可能に。
  - データ変換ユーティリティ (_to_float, _to_int) を追加し、文字列→数値変換の堅牢化を行った。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news テーブルに保存するモジュールを実装。
  - セキュリティ対策:
    - defusedxml による XML パースで XML Bomb 等を防御。
    - リダイレクト時にスキーム/ホストを検査する専用ハンドラ (_SSRFBlockRedirectHandler) を実装し、SSRF と内部ネットワークアクセスを防止。
    - URL スキームを http/https に限定し、プライベートアドレスへのアクセスを拒否する検査を実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェックでメモリDoS を緩和。
    - 受信ヘッダの Content-Length を事前チェックし大きすぎるレスポンスはスキップ。
  - 安全で正規化された記事 ID を生成（URL を正規化して SHA-256 の先頭32文字を使用）。トラッキングパラメータ（utm_* など）を除去。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - DuckDB への保存はトランザクションとチャンク単位のバルクINSERTを行い、INSERT ... RETURNING を用いて実際に挿入された件数を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄抽出ロジック（4桁数字の抽出と既知銘柄フィルタ）を実装し、run_news_collection で収集→保存→銘柄紐付けの統合処理を提供。
  - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを登録。
- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataPlatform 設計に基づく DuckDB スキーマを定義・初期化するモジュールを追加。
  - レイヤー毎にテーブルを定義（Raw / Processed / Feature / Execution）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な型チェック・制約（CHECK, PRIMARY KEY, FOREIGN KEY）を定義。
  - 検索効率向上のためのインデックスも定義。
  - init_schema(db_path) によりディレクトリ作成含めてスキーマ初期化を行う関数を提供。get_connection() で既存 DB へ接続可能。
- ETL パイプライン (kabusys.data.pipeline)
  - ETL 実行のための枠組みを実装（差分更新、バックフィル、品質チェックフック、結果レポート）。
  - ETLResult dataclass を追加し、処理結果（取得数、保存数、品質問題、エラー一覧）を構造化して返却可能。
  - 差分更新のヘルパ（テーブル存在チェック、テーブルの最終取得日取得、営業日調整）を実装。
  - run_prices_etl をはじめとした差分ETLの骨組みを実装（バックフィルロジック、_MIN_DATA_DATE による初回ロード対応、J-Quants クライアント経由の取得と保存）。品質チェックモジュールとの連携を想定した設計。

### Changed
- （初回リリースのため対象なし）

### Fixed
- （初回リリースのため対象なし）

### Security
- news_collector にて以下のセキュリティ対策を導入:
  - defusedxml を用いた安全な XML パース
  - リダイレクト時のスキーム・ホスト検査およびプライベートアドレス拒否（SSRF 対策）
  - レスポンスサイズ制限と gzip 解凍後サイズ検査（Zip/Gzip bomb 対策）
  - URL スキーム制限（http/https のみ）

### Notes / Migration
- 環境変数:
  - 自動で .env / .env.local を読み込む動作はデフォルトで有効です。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト時に便利）。
  - 必須の設定（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は Settings 経由で取得され、未設定時は ValueError を送出します。
- DuckDB:
  - デフォルトの DuckDB ファイルパスは data/kabusys.duckdb、監視用 SQLite は data/monitoring.db です。必要に応じて DUCKDB_PATH / SQLITE_PATH を設定してください。
  - 初回利用時は init_schema() を呼び出してスキーマを作成してください。既存テーブルがある場合は冪等にスキーマ作成をスキップします。
- J-Quants:
  - API レート制限や再試行、トークンの自動リフレッシュなどを実装しています。id_token を外部から注入してテストしやすい設計です。

---

今後の改善予定（例）
- 品質チェックモジュール（kabusys.data.quality）の実装と pipeline との統合テスト強化
- strategy / execution / monitoring モジュールの実装（現時点ではパッケージ構造のみ）
- 単体テスト、統合テスト、CI/CD の追加

（以上）