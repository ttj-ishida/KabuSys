# Changelog

すべての変更点は Keep a Changelog の形式に従って記載しています。  
このプロジェクトでは、公開 API や挙動に影響する変更を明確に記録します。

## [0.1.0] - 2026-03-17

初回リリース — 日本株自動売買システム "KabuSys" の基盤機能を実装しました。

### 追加 (Added)
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - エクスポートモジュール: data, strategy, execution, monitoring
  - バージョン: 0.1.0

- 環境設定モジュール (kabusys.config)
  - .env ファイルまたは環境変数から自動で設定を読み込む機能を実装
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）
    - .env と .env.local を読み込み（.env.local は上書き）、OS 環境変数は保護
  - .env パーサーの強化
    - export KEY=val 形式、クォート（シングル/ダブル）内のエスケープ、インラインコメントの扱い等に対応
  - 設定アクセス用 Settings クラスを提供
    - 必須変数取得時は未設定で ValueError を送出 (_require)
    - J-Quants / kabuAPI / Slack / DB パス等のプロパティを提供
    - KABUSYS_ENV と LOG_LEVEL の値検証（allowed 値チェック）
    - ヘルパー: is_live / is_paper / is_dev

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本 API クエリ機能を実装
    - get_id_token (リフレッシュトークンから ID トークン取得)
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - 考慮した設計点
    - レート制限（デフォルト 120 req/min）を守る固定間隔スロットリング実装 (_RateLimiter)
    - リトライロジック（最大 3 回、指数バックオフ、408/429/5xx を再試行）
    - 401 受信時は自動でトークンをリフレッシュして 1 回リトライ
    - ページネーションでのトークン共有のためのモジュールレベルキャッシュ
    - レスポンス JSON のデコード失敗時に分かりやすいエラーを送出
  - DuckDB への永続化ユーティリティ
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装
    - 各保存は冪等性を確保（ON CONFLICT DO UPDATE）
    - レコードに fetched_at (UTC) を付与して取得時点をトレース可能に
  - 型変換ユーティリティ: _to_float / _to_int（入力値の堅牢な変換）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS 収集および DB 保存ワークフローを実装
    - fetch_rss: RSS フィード取得と記事抽出（content:encoded 対応）
    - preprocess_text: URL 除去・空白正規化
    - _normalize_url / _make_article_id: トラッキングパラメータ除去と SHA-256 による冪等 ID 生成
    - 抽出した記事の DuckDB へのバルク保存: save_raw_news（INSERT ... RETURNING を使用）
    - 記事と銘柄コードの紐付け保存: save_news_symbols / _save_news_symbols_bulk
    - 銘柄コード抽出: extract_stock_codes（4桁数字、known_codes フィルタ）
    - 統合ジョブ: run_news_collection（複数ソースを順次処理、各ソースは独立してエラーハンドリング）
  - セキュリティ・堅牢性機能
    - defusedxml を使用して XML Bomb 等を防御
    - SSRF 対策: リダイレクト時のスキーム検証とホストがプライベート IP でないか検査する専用ハンドラ
    - URL スキームは http/https のみ許可
    - レスポンスの最大サイズ制限 (MAX_RESPONSE_BYTES = 10 MB)、gzip 解凍後もサイズ確認（Gzip bomb 対策）
    - リダイレクト先の事前検証で内部アドレス到達を防止
  - デフォルト RSS ソース
    - yahoo_finance: https://news.yahoo.co.jp/rss/categories/business.xml
  - 大量挿入対策: チャンクサイズでの分割挿入（_INSERT_CHUNK_SIZE）

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataPlatform 指向の多層スキーマを定義（Raw / Processed / Feature / Execution 層）
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルにチェック制約・主キー・外部キーを定義
  - 頻出クエリ用のインデックスを作成
  - init_schema(db_path) でディレクトリ作成からテーブル作成・インデックス作成までを実行（冪等）
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult データクラス（実行メタ情報・品質問題・エラー保持）
  - 差分更新・最終日判定ユーティリティ
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - 市場カレンダーを用いた営業日調整ヘルパー (_adjust_to_trading_day)
  - run_prices_etl の骨組みを実装
    - 差分取得ロジック（最終取得日から backfill して再取得）
    - J-Quants クライアントを使った取得・保存フロー
    - デフォルトのバックフィル日数: 3 日
  - 品質チェック (quality モジュール) と連携するためのフック（品質問題は収集するが ETL を止めない設計）

### セキュリティ (Security)
- RSS パーサーに defusedxml を採用して XML 関連の脆弱性を軽減
- RSS/HTTP 取得時に SSRF 対策を実装（リダイレクト先のスキーム・プライベート IP 検査）
- レスポンスサイズ上限・gzip 解凍後のサイズチェックでメモリ DoS 対策

### 既知の問題 (Known issues)
- pipeline.run_prices_etl の戻り値に関する実装不整合
  - ドキュメント（関数の docstring）は (取得レコード数, 保存レコード数) を返すと記載していますが、現状のコード末尾は "return len(records)," のように単一要素のタプル（保存件数を返していない）になっている箇所が存在します。これは意図した戻り値タプルを返せていないため修正が必要です。
- 一部モジュール（execution, strategy, monitoring 等）はパッケージ構造に存在しますが、機能実装は今後の追加を予定しています。
- pipeline は quality モジュール等の外部/未掲モジュールと連携する前提があり、外部依存の準備が必要です。

### 注意事項 / マイグレーション
- 初期設定には下記の環境変数が必要です（未設定時は ValueError を送出するものあり）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB / SQLite のデフォルトパス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- テストや CI 等で自動的な .env 読み込みを抑制する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

今後の予定としては、execution/strategy/monitoring モジュールの実装、品質チェックの詳細実装、ETL のエンドツーエンドテスト整備を予定しています。バグ修正や API の追加は適宜この CHANGELOG に追記します。