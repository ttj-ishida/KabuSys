# CHANGELOG

すべての注目すべき変更を記載します。本ファイルは「Keep a Changelog」の方針に準拠します。

## [0.1.0] - 2026-03-18
初回リリース。

### 追加
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring
  - バージョン: 0.1.0

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を探索）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ: export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い、無効行のスキップ等。
  - 環境変数取得ユーティリティ _require と Settings クラスを追加（各種必須設定のプロパティを提供）。
  - 設定バリデーション: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
  - デフォルト設定値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）を提供。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - API レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライ/バックオフ: 指数バックオフによる自動リトライ（最大3回）、408/429/5xx を対象に再試行。429 の場合は Retry-After ヘッダを尊重。
  - 認証トークン管理: リフレッシュトークンから ID トークンを取得する get_id_token、およびモジュール内キャッシュと 401 時の自動リフレッシュ処理を実装。
  - 保存関数: DuckDB への保存処理を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。すべて冪等（ON CONFLICT DO UPDATE）で fetched_at を UTC で記録し、Look-ahead Bias 防止を考慮。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を取得して raw_news に保存する機能を実装（fetch_rss, save_raw_news 等）。
  - セキュリティ/堅牢性対策:
    - defusedxml を使用して XML Bomb 等を防ぐ。
    - リダイレクト先のスキームとホストを検証し、SSRF を防止する専用リダイレクトハンドラを実装。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) を設け、過大レスポンスを拒否（gzip 解凍後も検査）。
  - URL 正規化: トラッキングパラメータ（utm_*, fbclid, gclid など）を除去してソートされたクエリ文字列で正規化する _normalize_url を実装。
  - 記事ID生成: 正規化URLの SHA-256 の先頭32文字を用いて冪等な記事IDを生成。
  - テキスト前処理: URL除去・空白正規化を行う preprocess_text。
  - 銘柄抽出: 文章中の4桁数字から known_codes に含まれる銘柄コードを抽出する extract_stock_codes。
  - DB 操作: INSERT ... RETURNING を活用し、新規挿入された記事IDや紐付け件数を正確に返す。チャンク挿入および1トランザクション単位でのコミット/ロールバックを実装（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - デフォルト RSS ソースを定義（例: Yahoo Finance ビジネスカテゴリ）。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の多層スキーマを定義（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルの制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を定義し、インデックスを作成（頻出クエリ向け）。
  - init_schema(db_path) によりディレクトリ作成（必要時）→ DuckDB 接続 → 全DDL/INDEX を実行して初期化する API を提供。get_connection() で既存接続取得。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新を行う ETL ヘルパー群を実装（最終取得日の取得、営業日補正、差分取得ロジック）。
  - run_prices_etl を含む個別ジョブを実装（date_from 自動算出、backfill_days による再取得対応）。
  - ETLResult dataclass を導入し、取得件数・保存件数・品質問題・エラーの集約と辞書化 (to_dict) を提供。
  - 品質チェックモジュールとの連携を意図した設計（quality モジュールは別実装を想定）。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### セキュリティ
- news_collector における SSRF 対策、defusedxml の採用、サイズ上限の導入など、外部コンテンツ取り込み時の攻撃面を低減。

### 既知の制約・注意事項
- J-Quants のレート制限と認証仕様に従うため、API 呼び出しは内部で待機・リトライを行います。長時間の取得処理ではスループットに制約があります。
- DuckDB スキーマは多数の制約と外部キーを含むため、既存データベースに適用する場合は互換性に注意してください（初回は init_schema を使用することを推奨）。
- run_prices_etl の戻り値のタプル表記は実装途中の箇所があり得ます（コードベース内での実装状況に依存）。必要に応じて API を安定化させてください。

---

（今後のリリースでは、機能追加・バグ修正・互換性変更をカテゴリ別に追記します。）