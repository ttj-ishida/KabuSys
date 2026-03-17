# Changelog

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-17

### Added
- パッケージの初期リリース: kabusys (バージョン 0.1.0)
  - パッケージトップ: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
  - パッケージ構成: data, strategy, execution, monitoring モジュールを公開。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - export KEY=val 形式やクォート、インラインコメントを考慮した .env パース実装。
  - 必須設定取得用 _require() と Settings クラスを提供。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須取得。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルトと展開処理。
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）と LOG_LEVEL の検証。
    - is_live / is_paper / is_dev ヘルパー。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - 安全で信頼性の高い HTTP 実装:
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装する RateLimiter。
    - 指数バックオフを用いたリトライ（最大 3 回、対象ステータス: 408, 429, 5xx）。
    - 401 を検出した場合はトークンを自動リフレッシュして1回だけ再試行（無限再帰防止）。
    - id_token のモジュールレベルキャッシュを共有し、ページネーション間で再利用。
    - JSON デコード失敗時のエラー報告。
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - PK 欠損行のスキップとログ出力、fetched_at の UTC 記録。
  - 型変換ユーティリティ: _to_float, _to_int（厳密な int 変換ロジック）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからのニュース収集と DuckDB への永続化処理を実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を用いた安全な XML パース（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホスト/IP のプライベート判定、リダイレクト時の事前検査用ハンドラ。
    - 最大応答サイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後の再チェック（Gzip Bomb 対策）。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証（utm_* 等のトラッキングパラメータを除去）。
  - テキスト前処理: URL 除去、空白正規化（preprocess_text）。
  - fetch_rss: RSS 取得→パース→NewsArticle 型で返却。非標準レイアウトへのフォールバック処理。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事IDを返却。チャンク/トランザクション処理で効率化。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク/トランザクションで保存し、INSERT RETURNING で挿入件数を正確に取得。
  - 銘柄コード抽出: 4桁数字パターンを known_codes と照合して抽出する extract_stock_codes。
  - 高レベルジョブ run_news_collection を提供。ソースごとに独立してエラーハンドリングし、既知銘柄と新規記事に対して一括で銘柄紐付けを実行。

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく3層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）とインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成→DDL 実行→インデックス作成を行い、DuckDB 接続を返す（冪等）。
  - get_connection(db_path) により既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計に基づく差分更新パターンを実装。
  - ETLResult データクラス: 実行結果・品質問題・エラーログを集約して返却可能（to_dict を提供）。
  - テーブル存在チェック、最大日付取得ユーティリティ (_table_exists, _get_max_date)。
  - 市場カレンダー参照による営業日調整ヘルパー (_adjust_to_trading_day)。
  - 差分更新向けヘルパー: get_last_price_date, get_last_financial_date, get_last_calendar_date。
  - 個別 ETL ジョブ例: run_prices_etl を実装（差分計算、backfill 対応、fetch→save の連携）。（注意: ファイル上での実装は一部まで。）

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- RSS 処理における SSRF、XML Bomb、Gzip Bomb、過大レスポンス対策を実装。
- .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。

### Notes / Usage Highlights
- .env 自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化推奨。
- J-Quants の API レートは 120 req/min に設定。RateLimiter でスロットリングしています。
- jquants_client の id_token はモジュールキャッシュで再利用され、401 受信時は1回だけ自動リフレッシュして再試行します。
- DuckDB への保存は基本的に冪等（ON CONFLICT）で実装。初回 DB 構築には init_schema() を実行してください。
- run_news_collection は既知銘柄セット（known_codes）を与えることで記事→銘柄の紐付けを行います。

---

今後のリリースでは、strategy / execution / monitoring の実装拡張、品質チェックモジュール（quality）の統合、ETL のエンドツーエンド実行結果報告やモニタリング通知等を予定しています。