# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。

## [0.1.0] - 2026-03-17

初期リリース。日本株自動売買システムの基盤機能を提供します。

### 追加
- パッケージ公開
  - パッケージ名: kabusys、バージョン 0.1.0
  - エントリポイント: src/kabusys/__init__.py（サブパッケージ data, strategy, execution, monitoring を公開）

- 環境設定（src/kabusys/config.py）
  - Settings クラスを実装し、環境変数経由で各種設定を取得可能に。
  - .env/.env.local ファイル自動ロード機能（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env の行パーサ（クォート、export プレフィックス、インラインコメント処理に対応）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須変数取得ヘルパ（_require）と各種プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等
    - DBパスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 環境モード検証（development / paper_trading / live）と log level 検証

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - APIアクセスのための共通リクエスト実装（_request）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライロジック（最大 3 回、指数バックオフ、408/429/5xx を対象）。
  - 401 発生時の ID トークン自動リフレッシュ（1 回のみ）、モジュールレベルのトークンキャッシュ実装。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes（OHLCV 日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ冪等に保存する関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 数値変換ユーティリティ: _to_float, _to_int
  - ロギングを含む詳細なエラーハンドリング

- RSS ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード取得と記事保存のパイプラインを実装:
    - fetch_rss: RSS 取得・XMLパース・前処理・記事抽出
    - save_raw_news: raw_news テーブルへトランザクション・チャンク挿入（INSERT ... RETURNING を使用し新規挿入IDを取得）
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への銘柄紐付けをバルク挿入
    - run_news_collection: 複数ソースの統合収集ジョブ（ソース単位で失敗を分離）
  - セキュリティ・堅牢化:
    - defusedxml を用いた安全な XML パース（XML Bomb 対策）
    - SSRF 対策: _SSRFBlockRedirectHandler、_is_private_host によるプライベートアドレス検査、HTTP/HTTPS スキーム制限
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズ検査
    - URL 正規化とトラッキングパラメータ削除、SHA-256 ベースの記事ID生成（先頭32文字）
  - 既定RSSソース: Yahoo Finance のビジネスカテゴリを登録（DEFAULT_RSS_SOURCES）

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層の DDL を実装
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw 層
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層
  - features, ai_scores 等の Feature 層
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層
  - インデックス定義と依存順を考慮したテーブル作成
  - DB 初期化ユーティリティ:
    - init_schema(db_path) — 必要なディレクトリ作成と全DDL適用（冪等）
    - get_connection(db_path)

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult データクラスで ETL 実行結果を表現（品質問題・エラー情報を含む）
  - 差分更新の補助関数:
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
    - _adjust_to_trading_day（非営業日調整）
  - run_prices_etl: 差分更新ロジックを実装（最終取得日から backfill_days の再取得、デフォルト backfill_days=3）
    - J-Quants から差分取得して save_daily_quotes に保存する処理を実装
  - 市場カレンダーの先読み（_LOOKAHEAD_DAYS = 90）や最小データ日（_MIN_DATA_DATE = 2017-01-01）などの設計パラメータを定義
  - 品質チェックフレームワーク（quality モジュール連携を想定）

- テスト容易性向上のための設計
  - news_collector._urlopen の差し替え（モック可能）
  - jquants_client の id_token を外部注入可能

### 変更
-（初回リリースのためなし）

### 修正（既知の問題・注意点）
- ETL の run_prices_etl に関する実装上の不整合:
  - run_prices_etl の docstring とシグネチャは (取得数, 保存数) のタプルを返すことを想定しているが、実装ファイル末尾で return 文が単一の要素だけを返すようになっており（末尾のコンマにより 1 要素タプルになっているか、戻り値が不完全になる可能性あり）、保存件数を正しく返していない可能性があります。利用時は戻り値の確認を推奨します（修正予定）。
- pipeline.run_prices_etl の末尾が途中で切れているように見える（ファイル末尾の抜け等）。実運用時は関数の戻り値と例外処理を検証してください。

### セキュリティ
- RSS 取得での SSRF 対策、XML パースの安全化（defusedxml）、受信サイズ制限、URL 正規化によるトラッキング除去など多数の防御を実装。
- J-Quants クライアントはトークン管理と再試行ロジックを実装し、非公開トークンの自動更新を安全に行う設計。

### パフォーマンス / 運用
- DuckDB へのバルク挿入はチャンク化（_INSERT_CHUNK_SIZE）とトランザクションで実行し、INSERT ... RETURNING により実際に挿入された行のみを検出。
- J-Quants API は固定間隔スロットリングでレート制限を順守（120 req/min）。
- run_news_collection はソース単位で失敗を分離し、1ソースの失敗がジョブ全体を停止しない設計。

### 既知の改善予定（次期リリース候補）
- pipeline の戻り値とエラー集約ロジックの修正（run_prices_etl の戻り値不整合の修正を優先）。
- quality モジュールによる自動品質修正・通知フローの統合（ETL 実行後の自動アクション）。
- strategy / execution / monitoring サブパッケージの実装強化（現在は公開されているが具体実装は限定的）。

---

今後の変更はこのファイルに逐次追記します。リリースノートの参照・リンク等が必要な場合はお知らせください。