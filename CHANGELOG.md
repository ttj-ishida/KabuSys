# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトのバージョンはパッケージ定義 (src/kabusys/__init__.py) に従い v0.1.0 です。

## [Unreleased]
（現時点ではなし）

## [0.1.0] - 2026-03-17

初期リリース。日本株自動売買システムの基盤ライブラリを実装しました。主要な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。公開モジュール: data, strategy, execution, monitoring。
  - バージョン: 0.1.0 を定義。

- 環境設定 / ロード (.env)
  - robust な .env 読み込みモジュールを実装（src/kabusys/config.py）。
    - .env ファイルをプロジェクトルート（.git または pyproject.toml を基準）から自動検出して読み込み。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - export KEY=val、引用符付き値、インラインコメントなどの細かなパースをサポート。
    - 読み込み時に既存 OS 環境変数の保護（protected）を行うオプションをサポート。
  - Settings クラスを提供（settings オブジェクト経由でアクセス可能）。
    - J-Quants / kabu / Slack / DB パス等の設定プロパティを用意。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL のバリデーション実装。
    - デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）を用意。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務データ、JPX マーケットカレンダーを取得する関数を実装:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
  - 認証補助: get_id_token（リフレッシュトークンから idToken を取得）。
  - HTTP 層の設計:
    - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大3回）を実装。HTTP 408/429/5xx を再試行対象に含める。
    - 401 受信時は id_token を自動リフレッシュして1回リトライする仕組み（無限再帰を回避）。
    - JSON デコード失敗時の明示的エラー。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - いずれも PK に対して ON CONFLICT DO UPDATE を利用し冪等性を維持。
    - fetched_at を UTC で記録し Look-ahead Bias を抑制。
    - 型変換ユーティリティ (_to_float, _to_int) を実装。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事取得と DuckDB への保存機能を実装:
    - fetch_rss: RSS 取得・XML パース・記事整形（preprocess_text）・記事ID生成。
      - 記事ID は正規化した URL の SHA-256 の先頭32文字で一意化。
      - URL 正規化ではトラッキングパラメータ（utm_* 等）を削除、クエリをソート、フラグメント削除。
      - content:encoded に対応。title/description の前処理で URL 削除・空白正規化を行う。
    - セキュリティ対策:
      - defusedxml を使用して XML Bomb 等に対処。
      - SSRF 対策: リダイレクト毎にスキーム・ホスト検査を行うハンドラを導入。http/https 以外のスキーム拒否。
      - ホストがプライベート/ループバック/リンクローカルであれば拒否。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を超える場合は拒否。gzip 解凍後も検査。
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING を用い、実際に挿入された記事IDを返す。トランザクションをまとめて実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入し、RETURNING により挿入数を正確に返す。重複除去とトランザクション管理を行う。
    - extract_stock_codes: テキスト中から 4桁の銘柄コード候補を抽出し、既知のコードセットでフィルタして重複除去して返す。
    - run_news_collection: 複数 RSS ソースから収集し DB に保存、銘柄紐付けまで一括で実行。各ソースは独立してエラーハンドリング。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の多層スキーマを定義。
  - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance などを定義。
  - 各テーブルに適切な型・CHECK 制約・PRIMARY/FOREIGN KEY を設定。
  - 検索用インデックス定義を追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) でディレクトリ自動作成とスキーマ作成を行い、get_connection で既存 DB に接続可能。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分取得・保存・品質チェックのための基盤実装。
    - ETLResult: ETL 実行結果を表す dataclass（品質問題とエラーを収集）。
    - 差分更新ヘルパー: テーブル存在チェック、最大日付取得ユーティリティ（_get_max_date）。
    - 市場カレンダー補助: 非営業日の調整ロジック（_adjust_to_trading_day）。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
    - run_prices_etl の骨格を実装（差分算出、バックフィル日数のデフォルト = 3、_MIN_DATA_DATE = 2017-01-01 を使用、取得 → 保存の流れ）。（注: ファイル末尾が切れているため一部実装が継続されます）

### Security
- ニュース収集側で多数のセキュリティ対策を追加:
  - defusedxml による XML パース保護。
  - SSRF 防止（スキームチェック、ホストのプライベートアドレス判定、リダイレクト時の検査）。
  - レスポンスサイズ制限および Gzip 関連の検査（Gzip bomb 対策）。

### Internal / Implementation notes
- 各所で冪等性を重視（DB 保存は ON CONFLICT を利用）。
- API クライアントはページネーション対応と id_token キャッシュ（モジュールレベル）を実装し、ページ間でトークンを共有して効率化。
- ロギングを随所に挿入し監査・デバッグを容易に。
- テストしやすさを考慮して、_urlopen や id_token 注入等の差し替えポイントを用意。

### Fixed
- （初期リリースにつき該当なし）

### Deprecated
- （初期リリースにつき該当なし）

### Removed
- （初期リリースにつき該当なし）

### Breaking Changes
- （初期リリースにつき該当なし）

---

注: 本 CHANGELOG は与えられたコードベースから実装意図・主要機能を推測して作成しています。実際の変更履歴やコミットメッセージが存在する場合はそれに基づいて更新してください。