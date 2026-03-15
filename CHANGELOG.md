# Changelog

すべての変更は Keep a Changelog のガイドラインに従っています。  
このファイルでは、利用者に影響のある機能追加・変更・修正を日本語でまとめています。

## [0.1.0] - 2026-03-15

### 追加
- 初回リリース。KabuSys パッケージの基本機能を提供します。
  - パッケージメタ情報
    - バージョン: `__version__ = "0.1.0"`
    - パッケージ公開 API: `__all__ = ["data", "strategy", "execution", "monitoring"]`
  - 環境変数・設定管理モジュール (kabusys.config)
    - .env ファイルまたは環境変数から設定を読み込む仕組みを実装。
    - 自動ロードの挙動:
      - プロジェクトルートを `.git` または `pyproject.toml` を基準に探索して判定（CWD に依存しない）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - OS 環境変数は保護され、.env(.local) による上書きを制御。
      - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途など）。
    - .env パーサーの詳細:
      - 空行・コメント行（先頭が `#`）を無視。
      - `export KEY=val` 形式に対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープを考慮して値を正しく復元。
      - クォート外の `#` は、直前がスペース/タブであればコメント扱い。
    - Settings クラスによるプロパティアクセスを提供（要求される/任意の設定を明確化）。
      - 必須環境変数取得関数 `_require()` により未設定時は `ValueError` を送出。
      - 必須 (例):
        - `JQUANTS_REFRESH_TOKEN`
        - `KABU_API_PASSWORD`
        - `SLACK_BOT_TOKEN`
        - `SLACK_CHANNEL_ID`
      - データベースパスのデフォルト:
        - DuckDB: `data/kabusys.duckdb`（`DUCKDB_PATH` で上書き可）
        - SQLite: `data/monitoring.db`（`SQLITE_PATH` で上書き可）
      - 環境/ログレベルの検証:
        - KABUSYS_ENV の有効値: `development`, `paper_trading`, `live`
        - LOG_LEVEL の有効値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
      - 利便性プロパティ:
        - `is_live`, `is_paper`, `is_dev`
  - DuckDB スキーマ定義・初期化モジュール (kabusys.data.schema)
    - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution レイヤーのテーブル定義を実装。
    - 生データ（Raw Layer）テーブル:
      - `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - 整形済み（Processed Layer）テーブル:
      - `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
      - `news_symbols` は `news_articles(id)` への外部キー（ON DELETE CASCADE）
    - 特徴量（Feature Layer）テーブル:
      - `features`, `ai_scores`
    - 実行（Execution Layer）テーブル:
      - `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
      - 外部キー関係の整備（例: `orders.signal_id` → `signal_queue(signal_id)`、`trades.order_id` → `orders(order_id)` など）
    - 各カラムに対する型・チェック制約（非負・範囲・列組み合わせの PRIMARY KEY 等）を定義。
    - 頻出クエリを想定したインデックスを複数作成:
      - 例: `idx_prices_daily_code_date`, `idx_features_code_date`, `idx_signal_queue_status`, `idx_orders_status` など
    - 公開 API:
      - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
        - 指定した DuckDB ファイルの親ディレクトリを自動作成し、全テーブル・インデックスを作成（冪等）。
        - `":memory:"` を指定するとインメモリ DB を使用。
      - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
        - 既存 DB へ接続を返す（スキーマ初期化は行わない。初回は `init_schema()` を使用すること）。
  - パッケージ構造の雛形
    - サブパッケージの初期化ファイルを配置（空の __init__ を配置）:
      - `kabusys.execution`, `kabusys.strategy`, `kabusys.data`, `kabusys.monitoring`（今後の実装拡張用）

### 変更
- 初回リリースのため該当なし。

### 修正
- 初回リリースのため該当なし。

### 既知の注意点 / マイグレーション
- DuckDB スキーマの初期化は `init_schema()` を明示的に呼び出すことを推奨。`get_connection()` はスキーマを作成しないため、初回実行時にテーブルが無いといった事象が発生します。
- .env 自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後や特殊な実行環境で挙動を制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。

--- 

今後のリリースでは、戦略実装（strategy）、発注・実行エンジン（execution）、監視・アラート（monitoring）などの機能追加を予定しています。必要であれば CHANGELOG を英語版やより詳細な移行手順付きで作成します。