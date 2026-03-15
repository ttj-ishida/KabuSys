CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に概ね準拠しています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-15
-----------------

Added
- 初期リリース。パッケージ名: kabusys
  - パッケージエントリポイントにバージョンを設定 (kabusys.__version__ = "0.1.0")。
  - 主要サブパッケージを公開: data, strategy, execution, monitoring（strategy/execution/monitoring の __init__ はプレースホルダ）。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルート検出: .git または pyproject.toml を上位ディレクトリから検索して特定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - OS の既存環境変数は保護され、.env.local の override は保護キーを除き有効。
  - .env の柔軟なパーサ実装:
    - 空行・コメント行（#）を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート（対応する閉じクォート以降は無視）。
    - クォートなしの場合のインラインコメント認識は直前が空白またはタブのときのみコメント扱い。
  - Settings クラスでアプリ設定を公開:
    - J-Quants / kabuステーション / Slack / データベースパス等の必須・任意設定をプロパティ化。
    - 必須キーの未設定時は ValueError を送出（helpful message を含む）。
    - KABUSYS_ENV の値検証 (development, paper_trading, live) と補助プロパティ is_dev/is_paper/is_live。
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - デフォルト値: KABUSYS_API_BASE_URL のデフォルト値、データベースファイルパスの既定値等。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しの設計原則を実装:
    - レート制限 (120 req/min) を固定間隔スロットリングで順守する RateLimiter を実装。
    - 冪等性・ページネーション対応。
    - リトライ機構: 指数バックオフ、最大リトライ回数 3、対象ステータス: 408/429 および 5xx、ネットワークエラーもリトライ対象。
    - 401 Unauthorized 受信時は ID トークンを自動リフレッシュして最大 1 回リトライ（無限再帰を防止）。
    - ページネーション間で共有されるモジュールレベルの ID トークンキャッシュを実装。
    - JSON デコード失敗時は明示的に RuntimeError を送出。
  - 高レベル API:
    - get_id_token(refresh_token: Optional[str]) : リフレッシュトークンから idToken を取得（/token/auth_refresh へ POST）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar : ページネーション対応でデータを取得。
      - 取得レコード数のログ出力あり。
  - DuckDB への保存関数（冪等性を担保）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
      - fetched_at は UTC の ISO8601（末尾 Z）で記録。
      - 主キー欠損行はスキップして警告ログを出す。
      - INSERT ... ON CONFLICT DO UPDATE を用いて重複時に更新（冪等）。
      - market_calendar では HolidayDivision に基づき is_trading_day / is_half_day / is_sq_day を安全に判定。
  - ユーティリティ:
    - _to_float: None/空/変換失敗で None を返す安全な float 変換。
    - _to_int: 整数化の厳密ルール（"1.0" は変換可能、"1.9" のように小数部がある場合は None）を実装。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataPlatform/3層構造に基づく包括的なスキーマ定義を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions（主キー制約、型チェック）。
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
    - Feature Layer: features, ai_scores。
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 各テーブルに適切な型、CHECK 制約、PRIMARY / FOREIGN KEY を付与。
  - 頻出クエリ向けのインデックスを定義（code/date, status, signal_id など）。
  - init_schema(db_path) : ディレクトリを自動作成し、すべてのテーブルとインデックスを冪等に作成して DuckDB 接続を返す。
  - get_connection(db_path) : 既存 DB への接続を返す（初回は init_schema を推奨）。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - シグナルから約定までのフローを UUID 連鎖で追跡する監査用テーブルを実装:
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求、order_request_id を冪等キーとして扱う。limit/stop のチェック制約を実装）
    - executions（証券会社からの約定ログ、broker_execution_id をユニークに扱う）
  - すべての TIMESTAMP を UTC に固定（init_audit_schema は SET TimeZone='UTC' を実行）。
  - ON DELETE RESTRICT で監査ログは原則削除しない設計。
  - init_audit_schema(conn) : 既存の DuckDB 接続に監査テーブルとインデックスを冪等に追加。
  - init_audit_db(db_path) : 監査専用の DuckDB を初期化して接続を返す（ディレクトリ自動作成）。

Other notes
- ロギング: 主要な操作（取得レコード数、保存件数、リトライ・警告など）で logger.info / logger.warning を利用している。
- 設計上の配慮: Look-ahead bias 防止のためにデータ取得時刻を記録、冪等性を意識した DB 操作、リトライ/レート制御、監査ログによる完全トレーサビリティ。

Changed
- （なし）

Fixed
- （なし）

Removed
- （なし）

Security
- （なし）

---