CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
リリース日はパッケージ内のバージョン情報に基づき付与しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-17
--------------------

Added
- 初回公開リリース。
- パッケージ構成
  - kabusys モジュール（src/kabusys）を提供。サブパッケージとして data, strategy, execution, monitoring を公開。
  - パッケージバージョンは 0.1.0 に設定（src/kabusys/__init__.py）。
- 環境設定（src/kabusys/config.py）
  - .env / .env.local / OS 環境変数からの設定自動読み込み機能を実装。プロジェクトルート検出は .git または pyproject.toml を参照して行うため、CWD 非依存で動作。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export プレフィックス、クォートあり/なし、行内コメント（スペース直前の '#'）などに対応。
  - 必須設定取得用 _require() と Settings クラス提供。主な設定項目（プロパティ）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
  - Settings による環境判定ユーティリティ is_live / is_paper / is_dev を提供。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得用 API クライアントを実装。
  - レート制限対応（120 req/min）として固定間隔スロットリング RateLimiter を導入。
  - リトライロジック：指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象。
  - 401 Unauthorized 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰回避のため allow_refresh 制御あり）。
  - ページネーション対応（pagination_key を用いた取得ループ実装）。
  - DuckDB へ保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等化（ON CONFLICT DO UPDATE）を実装。
  - データ整形ユーティリティ（_to_float, _to_int）を実装し、空値や不正値に寛容に対応。
  - ログ出力を適切に行い取得数・保存数を記録。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news テーブルに保存する一連の処理を実装。
  - セキュリティと堅牢性:
    - defusedxml を利用した XML パース（XML Bomb 等対策）。
    - SSRF 対策：URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカル/IP の場合アクセス拒否。リダイレクト時にも検証を実施。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入し、読み込み超過時はスキップ。
    - gzip 圧縮レスポンスの解凍時にもサイズチェックを実施（Gzip bomb 対策）。
  - 記事IDの冗長性回避：URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去、スキーム/ホスト小文字化）後、SHA-256 の先頭32文字を ID として生成。
  - 記事テキストの前処理（URL 除去、空白正規化）。
  - DB 保存はトランザクション・チャンク分割で実施し、INSERT ... RETURNING により実際に挿入された記事 ID を返す（save_raw_news）。
  - 銘柄コード抽出（4桁数字）と news_symbols への紐付け機能（重複除去、チャンク挿入）。
  - デフォルト RSS ソースとして Yahoo Finance のビジネス RSS を定義。
- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の4層スキーマを定義。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw レイヤーと、prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等を含む。
  - features, ai_scores 等の Feature レイヤー、signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤーを定義。
  - 各テーブルの制約（PRIMARY KEY、CHECK、FOREIGN KEY）や型を明示。
  - 頻出クエリを想定したインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status）。
  - init_schema(db_path) によりディレクトリ作成→全DDLとインデックスを実行して接続を返す。get_connection() で既存 DB に接続可能。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新方針に基づく ETL 処理用ユーティリティを実装。
  - 最小データ開始日、カレンダー先読み、バックフィル日数（デフォルト 3 日）等の定数を導入。
  - ETLResult dataclass を導入し、取得数・保存数・品質問題・エラー等を集約。品質問題は quality モジュールの QualityIssue を扱う想定。
  - テーブル存在チェック、最大日付取得ヘルパー、営業日補正（市場カレンダー参照）等のユーティリティを実装。
  - run_prices_etl 等の個別 ETL ジョブ（差分計算→fetch→save）を実装（差分更新ロジック、backfill による再取得）。
- 型アノテーションと型安全性の強化
  - 各関数に typing を付与し、戻り値や引数の型を明示。
  - NewsArticle TypedDict 等を用いた静的型情報の提供。
- ロギング
  - 各モジュールで logger を使用して情報・警告・例外ログを出力。

Changed
- 初期リリースのため、既存プロジェクトからの変更履歴はなし。

Fixed
- 初回公開のため、過去の不具合修正履歴はなし。

Security
- RSS パーサに defusedxml の導入、SSRF 対策（スキーム検証・プライベートIPブロック・リダイレクト検査）、レスポンスサイズ上限、gzip 解凍後のサイズ検査などの対策を実装。
- API クライアントにおけるリトライ/バックオフやトークン自動リフレッシュで認証エラーに対処。

Notes
- 環境変数に重要なシークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN など）を使用するため、.env ファイルの管理には注意してください。.env.example を参考に設定してください。
- DuckDB スキーマは init_schema() が作成するため、初回は init_schema(settings.duckdb_path) の呼び出しを推奨します。既存 DB に接続する場合は get_connection() を使用してください。
- news_collector のネットワークアクセスは外部 RSS に対して行われます。社内ネットワークやプロキシの要件がある場合は _urlopen のモック/差し替えや環境に応じた設定の検討を推奨します。
- ETL の品質チェック（quality モジュール）は別モジュールとして想定されています。品質チェックの扱いは ETLResult を参照して呼び出し元で判断してください。

BREAKING CHANGES
- なし（初回リリースのため）。

Authors
- コードベースから生成された初回リリースの変更ログ。

License
- リポジトリ内の LICENSE 等を参照してください。