# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは「Keep a Changelog」スタイルに準拠しています。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買プラットフォーム KabuSys のコア機能を実装しました。

### 追加
- パッケージ基盤
  - パッケージ初期化（kabusys.__version__ = 0.1.0、公開モジュールの __all__ 指定）。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - OS 環境変数を保護するロード順序（OS > .env.local > .env）と上書き制御（protected set）。
  - .env 読み込みの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - .env 行パーサー（export 形式、クォート・エスケープ、インラインコメント対応）。
  - 必須環境変数取得ヘルパー _require() と Settings クラス：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev の利便性プロパティ

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しのレート制御（_RateLimiter: 120 req/min 固定間隔スロットリング）。
  - 汎用 HTTP リクエストユーティリティ _request():
    - ページネーション対応
    - 指数バックオフを伴うリトライ（最大 3 回、408/429/5xx を対象、Retry-After 対応）
    - 401 受信時の ID トークン自動リフレッシュ（1 回のみ）
    - JSON デコード失敗時のエラーハンドリング
  - 認証ヘルパー get_id_token()（リフレッシュトークンから idToken を取得）。
  - データ取得関数（ページネーション対応）：
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）：
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 保存時に fetched_at を UTC ISO 形式で記録
  - データ変換ユーティリティ：_to_float, _to_int（安全な型変換）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードの取得・パースと raw_news への保存フローを実装。
  - セキュリティ強化：
    - defusedxml を用いた XML パース（XML Bomb 等の対策）
    - SSRF 対策（URL スキーム検証、プライベートアドレス判定、リダイレクト時の検査）
    - リスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と Gzip 解凍後チェック（Gzip bomb 対策）
    - 許可スキームは http/https のみ
  - URL 正規化（トラッキングパラメータ除去、フラグメント除去、クエリソート）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）
  - テキスト前処理（URL 除去、空白正規化）と RSS pubDate の堅牢なパース（UTC 正規化）
  - DB 保存（DuckDB）：
    - save_raw_news：チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用、新規挿入 ID を返す
    - save_news_symbols / _save_news_symbols_bulk：ニュースと銘柄コードの紐付けをトランザクションで保存、RETURNING で実際の挿入数を返却
  - 銘柄抽出ユーティリティ extract_stock_codes（4桁数字を抽出し既知銘柄セットでフィルタ）

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを定義
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）や推奨インデックスを定義
  - init_schema(db_path) により冪等的にテーブルとインデックスを作成し DuckDB 接続を返す
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult Dataclass により ETL 実行結果を構造化（品質問題・エラー一覧を保持、辞書化メソッドを提供）
  - 差分更新のためのヘルパー：
    - _table_exists, _get_max_date（汎用）
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
    - _adjust_to_trading_day（非営業日の補正）
  - run_prices_etl: 日次株価差分 ETL（差分算出、backfill_days による再取得、jquants_client を使った取得と保存）

### セキュリティ / 信頼性強化
- RSS パーサーに defusedxml を使用して XML 関連の脆弱性に対処。
- RSS ダウンロードで SSRF や内部ネットワークアクセスを防止する検証を導入。
- Gzip 圧縮レスポンスに対するサイズ検査（展開後も含む）を実装。
- .env パーサーはクォートやエスケープを正しく扱い、コメント処理も強化。

### ドキュメント（コード内）
- 各モジュールに詳細な docstring を付与（設計方針、処理フロー、仕様・注意点、戻り値説明など）。
- 実装の設計原則や想定シナリオ（例: Look-ahead Bias 回避、冪等性）を明記。

### 既知の問題 / 注意点
- run_prices_etl の戻り値が不完全（コード末尾で `return len(records), ` のように 2 要素のタプルを期待するところで片方だけになっている箇所が存在）。ETL 呼び出し元では (fetched, saved) を期待するため、修正が必要。
- 初期化手順：
  - DuckDB を使用する前に init_schema() を呼んでスキーマを作成すること。
- 必須環境変数が未設定だと Settings のプロパティで ValueError が発生するため、CI/デプロイ時に環境変数管理が必要。
- news_collector の RSS ソースは DEFAULT_RSS_SOURCES により初期化されるが、運用では独自ソースの追加が必要。

### 互換性
- 初回リリースのため互換性保証は初期状態。今後のリリースで API（関数名・戻り値）やスキーマ変更が入る可能性があります。

---

今後の予定（想定・設計上の TODO）
- jquants_client のロギングやメトリクス収集強化（レート・エラー統計）。
- pipeline モジュールにおける品質チェック（quality モジュール呼び出し）の具体実装と自動レポート。
- strategy / execution / monitoring 各モジュールの実装（現時点ではパッケージエントリのみ）。
- 単体テスト、統合テストの整備（ネットワーク呼び出しはモック化）。
- run_prices_etl の戻り値修正および他 ETL ジョブの追加（財務データ・カレンダーの差分ETL 等）。

（以上）