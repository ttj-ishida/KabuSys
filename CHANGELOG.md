# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョンは `0.1.0` です。

## [Unreleased]
- 次回リリースに向けた作業項目や未確定の変更点はここに記載します。

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買システム「KabuSys」の基本機能（設定管理、データ取得・保存、ニュース収集、DBスキーマ、ETLパイプラインの骨格）を実装・提供します。

### Added
- パッケージ基本情報
  - src/kabusys/__init__.py にバージョン情報と公開モジュールを追加（__version__ = "0.1.0"）。
- 環境設定/ロード機能（src/kabusys/config.py）
  - .env/.env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 自動読み込み無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護（protected）され上書きされない。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント（条件付き）対応。
  - 必須環境変数取得のヘルパ `_require` と Settings クラスの提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 設定検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証、デフォルト値、パス（DUCKDB_PATH/SQLITE_PATH）展開。
  - Settings に is_live/is_paper/is_dev のユーティリティプロパティを追加。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - ベース機能: 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得用 API 呼び出しを実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を保証する RateLimiter 実装。
  - 再試行ロジック: 指数バックオフ、最大 3 回（対象ステータス: 408, 429, 5xx）。429 の場合は Retry-After ヘッダを優先。
  - 認証: リフレッシュトークンから id_token を取得する get_id_token、モジュールレベルでの id_token キャッシュと自動リフレッシュ（401 を受信した際に 1 回のみ再取得してリトライ）。
  - ページネーション対応: fetch_* 系関数で pagination_key を使った全件取得（重複検出防止）。
  - DuckDB への保存関数（冪等）: save_daily_quotes / save_financial_statements / save_market_calendar。ON CONFLICT DO UPDATE を使用して重複を排除・更新。
  - fetched_at を UTC ISO8601（Z）で記録して Look-ahead Bias のトレースを容易に。
  - 型変換ユーティリティ: _to_float / _to_int（"1.0" のような文字列処理・小数チェック等）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード収集と前処理フロー:
    - デフォルト RSS ソース (yahoo_finance) を定義。
    - RSS 取得・XML パース（defusedxml 使用で XML Bomb 等の防御）。
    - テキスト前処理: URL 除去、空白正規化（preprocess_text）。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）、正規化 URL から SHA-256 (先頭32文字) を記事IDとして生成。
    - SSRF 対策: URL スキーム検証（http/https のみ）およびプライベート/ループバック/リンクローカル/マルチキャスト判定（DNS 解決と直接 IP 判定）を実施。リダイレクト時にスキーム・ホストを検証するカスタム RedirectHandler を使用。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）チェックと gzip 解凍の安全チェック（Gzip bomb 対策）。
  - DB 書き込み:
    - save_raw_news: チャンク挿入（_INSERT_CHUNK_SIZE=1000）、トランザクションにまとめて INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用し、新規挿入された記事IDを返却。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンクで保存、RETURNING を用いて実際に挿入された件数を返却。
  - 銘柄コード抽出: 正規表現で 4 桁数字を候補とし、与えられた known_codes セットに含まれるもののみを返す。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層を含むテーブル群を DDL で定義:
    - raw_prices, raw_financials, raw_news, raw_executions 等（Raw）
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等（Processed）
    - features, ai_scores （Feature）
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance（Execution）
  - 各種制約（PK/チェック制約/外部キー）を設定し、頻出クエリを想定したインデックスを作成。
  - init_schema(db_path) によりディレクトリ自動作成とテーブル作成を実行（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult dataclass（品質チェック結果・エラー一覧を含む）を実装。
  - 差分更新用ユーティリティ:
    - テーブル存在チェック、最終取得日取得ヘルパ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - 非営業日調整ヘルパ (_adjust_to_trading_day)。
  - run_prices_etl の骨格:
    - 最終取得日に基づく差分取得ロジック（backfill_days デフォルト 3 日、最小データ日付を考慮）。
    - jq.fetch_daily_quotes -> jq.save_daily_quotes による取得と保存。
  - パイプライン設計方針として：
    - 差分更新デフォルトは営業日単位、backfill による後出し修正吸収、
    - id_token を引数注入可能にしてテスト容易性を確保、
    - 品質チェックは Fail-Fast せず呼び出し元に委譲。

### Security
- ニュース収集で SSRF 対策を実装:
  - URL スキーム制限（http/https のみ）。
  - プライベート/ループバックアドレスの拒否（直接 IP / DNS 解決による判定）。
  - リダイレクト先の検査用ハンドラを導入。
  - defusedxml を利用して XML ベースの攻撃を緩和。
  - レスポンスサイズ制限と Gzip 解凍時のサイズチェックで DoS 対策。

- .env ローダーは OS 環境変数を保護（protected set）し、テスト時に自動ロードを無効化可能。

### Internal / Design
- ロギングを適宜配置し、各処理（fetch/save/ETL）の進捗を記録。
- モジュールレベルで ID トークンをキャッシュしページネーション間で共有する実装（効率化）。
- fetch/save 系は冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING）。
- テスト容易性を考慮した設計:
  - jquants_client の id_token を注入可能。
  - news_collector の _urlopen をモック差替え可能。

### Notes / Required environment variables
- 必須環境変数（Settings で _require により必須）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- デフォルト値あり（任意で上書き可能）:
  - KABUSYS_ENV (default: "development")
  - LOG_LEVEL (default: "INFO")
  - DUCKDB_PATH (default: "data/kabusys.duckdb")
  - SQLITE_PATH (default: "data/monitoring.db")
- .env.example を参考に .env を用意してください（.env の自動読み込みはプロジェクトルートの検出に依存します）。

### Fixed
- 初回リリースのための実装に伴う基本的なエラーハンドリング・入力検証を多数追加。

### Breaking Changes
- 該当なし（初回リリースのため該当変更なし）。

### Migration notes
- 初回起動時は init_schema() を呼び出して DuckDB スキーマを作成してください。
- 既存環境からの移行は特になし（初期導入向け）。

---

今後のリリースでは、ETL の完全ワークフロー（品質チェックモジュールの統合、監視・アラート機能、実行モジュールの接続実装、戦略層の実装など）を順次追加していく予定です。必要であれば次回リリースプランの要望や優先実装項目を共有してください。