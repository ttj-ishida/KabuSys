# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初期リリースに関する変更履歴を以下に示します。

## [Unreleased]

## [0.1.0] - 2026-03-16

初期リリース — 日本株自動売買システムの基盤モジュール群を実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基礎
  - kabusys パッケージの初期化（__version__ = 0.1.0、公開モジュール定義）。
  - 空のサブパッケージプレースホルダ: execution, strategy。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数の自動ロード機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない実装）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーは export KEY=val 形式、クォート文字列（エスケープ処理含む）、およびインラインコメント（適切な条件下での '#' 扱い）に対応。
  - 環境変数上書き時に OS 環境変数を保護する仕組み（protected set）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を必須チェック。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
    - ヘルパー bool プロパティ: is_live / is_paper / is_dev。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ (_request) を実装。
    - ベース URL: https://api.jquants.com/v1。
    - レート制限遵守: 固定間隔スロットリングで 120 req/min（最小間隔 0.5s）。
    - 再試行ロジック: 最大 3 回、指数バックオフ（base=2.0 秒）、対象ステータス 408/429 および 5xx。
    - 429 の場合は Retry-After ヘッダを優先して待機。
    - 401 受信時はトークンを自動リフレッシュして一度リトライ（無限再帰防止フラグ allow_refresh）。
    - JSON デコードエラーを明示的に報告。
  - ID トークン管理:
    - モジュールレベルのキャッシュを持ち、ページャや複数呼び出しで共有。
    - get_id_token(refresh_token=None) によりリフレッシュトークンから idToken を取得。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes（株価日足、OHLCV）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX マーケットカレンダー）
    - ページネーションは pagination_key を使って重複検出を行い終了判定。
    - 取得時刻（fetched_at）を UTC で記録する設計思想を反映。
  - DuckDB への保存関数（冪等性を確保）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT DO UPDATE による上書きで重複を排除（冪等）。
    - PK 欠損レコードのスキップとログ出力。
    - 型変換ユーティリティ _to_float / _to_int を実装（変換ルールを厳密に扱う）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層＋監査向けテーブルを含む広範なスキーマを実装。
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤー: features, ai_scores
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルにチェック制約、主キー、外部キーを設定（データ整合性を重視）。
  - 頻出クエリ向けのインデックス群を定義。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成とテーブル作成（冪等）を行う。
  - get_connection(db_path) で既存 DB に接続するユーティリティを提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の主要フローを実装:
    1. 市場カレンダー ETL（デフォルト先読み 90 日）
    2. 株価日足 ETL（差分取得 + backfill、デフォルト backfill_days=3）
    3. 財務データ ETL（差分取得 + backfill）
    4. 品質チェック（オプションで実行）
  - 差分更新ロジック: DB の最終取得日を確認して未取得範囲のみを取得し、バックフィルで後出し修正を吸収。
  - run_prices_etl / run_financials_etl / run_calendar_etl を提供（それぞれ取得数・保存数を返す）。
  - run_daily_etl: ETLResult を返す統合エントリポイント。個々のステップは独立して例外処理され、1 ステップ失敗でも他ステップは継続（全問題の収集を優先する設計）。
  - ETLResult クラス: 取得数・保存数、品質問題リスト、エラーメッセージ等を持ちログ・監査に利用可能。

- 監査ログ（kabusys.data.audit）
  - 戦略 → シグナル → 発注 → 約定までのトレーサビリティを担保する監査テーブルを実装:
    - signal_events, order_requests, executions
  - order_request_id を冪等キーとして扱い二重発注を防止する設計。
  - 各テーブルに created_at / updated_at を持たせ監査証跡を確保。
  - init_audit_schema(conn) により既存の DuckDB 接続へ監査テーブルを追加（SET TimeZone='UTC' を実行して UTC 保存を保証）。
  - init_audit_db(db_path) で監査専用 DB の初期化が可能。
  - 監査向けのインデックス群を定義（status 検索や JOIN 最適化 等）。

- データ品質チェック（kabusys.data.quality）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損を検出（欠損はエラー扱い）。
    - check_spike: 前日比によるスパイク検出（デフォルト閾値 50%）。
  - チェックは Fail-Fast ではなく問題を全件収集して呼び出し元に返す（ETL の停止判断は呼び出し元に委ねる）。
  - DuckDB の SQL を用いた効率的な実装（パラメータバインド使用でインジェクション対策）。

### Changed
- （該当なし）初回リリースのため変更履歴はありません。

### Fixed
- （該当なし）初回リリースのため修正履歴はありません。

### Security
- 認証情報は環境変数経由で取得する設計（.env は便利だがソース管理しない運用を推奨）。
- .env 読み込み時に OS 環境変数を保護する仕組みを導入。

### Notes / Design principles（ドキュメント的補足）
- レート制限：J-Quants API の 120 req/min を守るため固定間隔スロットリングを採用。
- 再試行：ネットワーク障害や一部 HTTP ステータスに対し指数バックオフを行う（最大試行回数 3）。
- トークン管理：401 を受けた場合は id_token を自動リフレッシュして 1 回だけ再試行。
- 冪等性：DuckDB への保存は ON CONFLICT DO UPDATE を用いることで冪等に動作。
- 時刻管理：監査・fetched_at 等のタイムスタンプは UTC を前提とする（監査スキーマ初期化時に TimeZone='UTC' をセット）。
- テーブル設計：整合性のため CHECK / PK / FK を多用し、運用時のデータ品質を高める設計。

---

今後の予定（例）
- execution / strategy パッケージの実装（ブローカー連携、発注ロジック、ポジション管理）。
- モニタリング・アラート機能（Slack 連携を利用した通知）。
- テストカバレッジと CI の整備、ドキュメントの充実。