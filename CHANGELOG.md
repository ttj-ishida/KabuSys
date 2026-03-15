# Changelog

すべての注目すべき変更はこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠します。

なお、コードベースから推測して記載しています（実際のコミット履歴ではありません）。

## [0.1.0] - 2026-03-15

### 追加
- 初期リリース: kabusys パッケージ v0.1.0 を公開。
  - パッケージルート: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定、公開モジュールとして ["data", "strategy", "execution", "monitoring"] を定義。

- 環境変数 / 設定管理モジュールを追加（src/kabusys/config.py）。
  - プロジェクトルート検出:
    - __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を検出してプロジェクトルートを特定。
    - プロジェクトルートが見つからない場合は自動ロードをスキップ。
  - .env 自動読み込み:
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途を想定）。
    - OS 環境変数は保護（protected）され、.env の内容で上書きされない。
  - .env パーサー (_parse_env_line) の実装:
    - コメント行や空行を無視。
    - "export KEY=val" 形式に対応。
    - クォートありの値をサポート（シングル/ダブルクォート、バックスラッシュによるエスケープに対応し、閉じクォートまでを値として扱う）。
    - クォートなしの値では、'#' が直前にスペース／タブのある場合にコメントと判定。
  - .env ファイル読み込み (_load_env_file):
    - ファイルが存在しない場合は安全にスキップ。
    - open 時のエラーは警告として扱う（warnings.warn）。
    - override フラグにより既存の環境変数を上書き可能（ただし protected キーは上書き不可）。
  - 必須環境変数チェック:
    - _require() により未設定時は ValueError を送出。
  - Settings クラス（settings インスタンスを公開）:
    - J-Quants, kabuステーション, Slack などの必須トークン／設定をプロパティで取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
    - kabu_api_base_url, duckdb_path, sqlite_path のデフォルト値を提供（パスは expanduser()）。
    - 環境（KABUSYS_ENV）のバリデーション（有効値: development, paper_trading, live）。
    - ログレベル（LOG_LEVEL）のバリデーション（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）。
  - 目的: DataSchema.md に準拠した 3 層（Raw / Processed / Feature）＋Execution 層のテーブル定義と初期化。
  - 提供関数:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定した DuckDB ファイルを初期化し、全テーブルとインデックスを作成して接続を返す。
      - db_path の親ディレクトリが存在しなければ自動生成。":memory:" をサポートしてインメモリ DB を使用可能。
      - DDL は冪等（既存テーブルはスキップ）。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB へ接続を返す（スキーマ初期化は行わない。初回は init_schema を使用）。
  - 定義されたテーブル群（主なもの）:
    - Raw Layer:
      - raw_prices (date, code, open/high/low/close, volume, turnover, fetched_at) — 主キー (date, code)、各種 CHECK 制約（非負等）。
      - raw_financials (code, report_date, period_type, revenue, operating_profit, net_income, eps, roe, fetched_at) — 主キー (code, report_date, period_type)。
      - raw_news (id, datetime, source, title, content, url, fetched_at) — id を主キー。
      - raw_executions (execution_id, order_id, datetime, code, side, price, size, fetched_at) — side は ('buy','sell')、サイズや価格のチェック、execution_id を主キー。
    - Processed Layer:
      - prices_daily (date, code, open, high, low, close, volume, turnover) — 主キー (date, code)、low <= high 等の CHECK。
      - market_calendar (date, is_trading_day, is_half_day, is_sq_day, holiday_name) — date を主キー。
      - fundamentals (code, report_date, period_type, revenue, operating_profit, net_income, eps, roe) — 主キー (code, report_date, period_type)。
      - news_articles / news_symbols — news_symbols は news_articles(id) への外部キー（ON DELETE CASCADE）。
    - Feature Layer:
      - features (date, code, momentum_20, momentum_60, volatility_20, ... , created_at) — 主キー (date, code)。
      - ai_scores (date, code, sentiment_score, regime_score, ai_score, created_at) — 主キー (date, code)。
    - Execution Layer:
      - signals (date, code, side, score, signal_rank) — side 制約あり、主キー (date, code, side)。
      - signal_queue (signal_id, date, code, side, size, order_type, price, status, created_at, processed_at)
        - status は ('pending','processing','filled','cancelled','error')、order_type は ('market','limit','stop')。
      - portfolio_targets (date, code, target_weight, target_size)。
      - orders (order_id, signal_id, datetime, code, side, size, price, status)
        - status は ('created','sent','filled','cancelled','rejected')。
        - signal_id は signal_queue(signal_id) への外部キー（ON DELETE SET NULL）。
      - trades (trade_id, order_id, datetime, code, price, size)
        - order_id -> orders(order_id) に対して ON DELETE CASCADE。
      - positions (date, code, position_size, avg_price, market_value) — 主キー (date, code)。
      - portfolio_performance (date, equity, cash, drawdown, daily_return) — date を主キー。
  - スキーマ上の制約・インデックス:
    - 各テーブルに対して適切な PRIMARY KEY、CHECK 制約（非負、列範囲、列値集合など）を付与。
    - 頻出クエリ向けに複数のインデックスを生成（例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status, idx_orders_status など）。
    - テーブル作成順は外部キー依存を考慮して管理。
  - 実装上の注意:
    - duckdb を利用して接続・DDL 実行を行う。
    - init_schema は与えられた db_path に対して親ディレクトリを自動生成する（ファイル DB の場合）。

- パッケージのサブモジュールの雛形を追加:
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py（現時点では空のパッケージ初期化ファイル）。

### 変更
- (該当なし) 初版のため変更履歴なし。

### 修正
- (該当なし) 初版のため修正履歴なし。

### 削除
- (該当なし) 初版のため削除履歴なし。

---

注:
- 上記はソースコードから推測した「注目すべき点」を CHANGELOG 形式でまとめたものです。実際のリリースノートとして使用する場合は、リリース日や変更の意図、影響範囲などを開発履歴やコミットメッセージに合わせて調整してください。