Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトのリリースは、Keep a Changelog の慣習に従って管理されています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

[Unreleased]


[0.1.0] - 2026-03-15
--------------------

Added
- 初期リリースを追加（kabusys v0.1.0）。
- パッケージ構成の追加:
  - kabusys.__init__ にバージョン情報と公開モジュールリストを追加。
  - 空のパッケージ初期化ファイルを追加（execution, strategy, monitoring, data パッケージのプレースホルダ）。
- 設定管理モジュールを追加（kabusys.config）:
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途を想定）。
  - プロジェクトルート検出: __file__ から上位ディレクトリを探索し .git または pyproject.toml を基準にルートを特定（CWD に依存しない）。
  - .env のパースロジックを実装（コメント行、export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応）。
  - _load_env_file による保護付き上書きロジック（OS 環境変数を protected として上書きを制御）。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須（未設定時は ValueError を送出）。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KABUSYS_ENV などにデフォルト値と検証を実装。
    - env 値（development / paper_trading / live）と log_level の妥当性検査。
    - is_live / is_paper / is_dev の便利プロパティ。
- J-Quants API クライアントを追加（kabusys.data.jquants_client）:
  - API ベース URL、レート制限、リトライ、認証まわりの実装。
  - レート制限: 固定間隔スロットリング (120 req/min) を _RateLimiter で実装。
  - 冪等・リトライ設計:
    - ネットワークや 408/429/5xx に対して指数バックオフで最大 3 回リトライ。
    - 429 の場合は Retry-After ヘッダを優先。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止のため allow_refresh 制御）。
    - モジュールレベルで ID トークンをキャッシュし、ページネーション間で共有。
  - JSON レスポンスのパースとエラー処理、タイムアウトの設定。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes: 株価日足（OHLCV）取得。
    - fetch_financial_statements: 財務（四半期 BS/PL）取得。
    - fetch_market_calendar: JPX マーケットカレンダー取得（祝日・半日・SQ）。
    - 取得数ログ記録（logger.info）。
  - DuckDB への保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で実装。
    - fetched_at（UTC ISO8601）を記録して Look‑ahead Bias を防止する設計。
    - PK 欠損レコードはスキップし、スキップ数を警告ログ出力。
  - 型変換ユーティリティ:
    - _to_float / _to_int を実装。_to_int は "1.0" のような文字列を float 経由で整数に変換するが、小数部が 0 以外の場合は None を返して誤った切り捨てを防止。
- DuckDB スキーマ定義と初期化を追加（kabusys.data.schema）:
  - 3 層（Raw / Processed / Feature）+ Execution Layer に基づくテーブル群を定義。
  - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions。
  - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
  - Feature Layer: features, ai_scores。
  - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）および適切なデータ型を定義。
  - インデックスを実装し、典型的なクエリパターン（銘柄×日付スキャン、ステータス検索、JOIN 等）を考慮。
  - init_schema(db_path) により DuckDB を初期化して全テーブル・インデックスを作成（冪等）。親ディレクトリの自動作成対応。:memory: サポート。
  - get_connection(db_path) による既存 DB 接続取得（スキーマ初期化は行わない）。
- 監査ログ／トレーサビリティモジュールを追加（kabusys.data.audit）:
  - signal_events（シグナル生成ログ）、order_requests（発注要求ログ、order_request_id を冪等キーとする）、executions（証券会社からの約定ログ）を定義。
  - order_requests のチェック制約（limit/stop/market の価格必須／禁止ルール）を実装。
  - ステータス列と詳細な決定値（rejected_by_* 等）を持ち、エラーや棄却も永続化する設計。
  - すべての TIMESTAMP を UTC で保存するため init_audit_schema は "SET TimeZone='UTC'" を実行。
  - インデックスを追加（signal_events の date/code、order_requests の status、broker_order_id など）。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（既存接続への追加初期化、専用監査 DB の初期化両対応）。
- ロギングや警告を適宜追加（読み込み失敗、スキップ件数、リトライログ等）。

Changed
- n/a（初回リリースのため既存変更なし）

Fixed
- n/a

Deprecated
- n/a

Removed
- n/a

Security
- 認証トークン・機密情報は環境変数で管理する設計。自動 .env ロードでも OS 環境変数を protected として上書き防止を行うことで誤った上書きを避ける配慮あり。

Notes / 備考
- 多くの機能（execution / strategy / monitoring の実装）はまだ空のモジュールとして置かれており、今後の実装で発注ロジックや戦略本体、監視機能が追加される想定です。
- DuckDB スキーマ・監査ログともに冪等性と監査可能性に重点を置いて設計しています。初期化は init_schema → init_audit_schema の順で、またはそれぞれ単独で利用できます。
- J-Quants クライアントはレート制限と自動リフレッシュを備えていますが、実運用時は J-Quants API の最新仕様・利用規約に従ってください。

---