# Keep a Changelog
すべての注目すべき変更を追跡します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [Unreleased]

## [0.1.0] - 2026-03-15
初期リリース。日本株自動売買システムのコアモジュール（骨組み）を実装しました。

### Added
- パッケージメタ情報
  - パッケージバージョンを定義: `kabusys.__version__ = "0.1.0"`。
  - パッケージ公開 API: `__all__ = ["data", "strategy", "execution", "monitoring"]` を設定。

- 環境変数 / 設定管理モジュール (`src/kabusys/config.py`)
  - .env ファイルおよび OS 環境変数から設定を自動ロードする機構を実装。
    - プロジェクトルートは `__file__` を基準に親ディレクトリを探索して `.git` または `pyproject.toml` を検出して特定するため、CWD に依存しない挙動を実現。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途を想定）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - OS 環境変数は保護（protected）され、`.env` / `.env.local` による上書きを制御。
  - .env パーサーの実装（`_parse_env_line`）
    - 空行・コメント行（#）の除去。
    - `export KEY=val` 形式に対応。
    - シングルクォート／ダブルクォートを考慮した値のパース（バックスラッシュによるエスケープ処理を含む）。
    - クォートなし値に対しては、インラインコメント判定（直前がスペース/タブの場合）を実装。
  - .env ファイル読み込みロジック（`_load_env_file`）
    - ファイル読み込みエラーは警告として通知。
    - `override` フラグで既存環境変数の上書き制御、`protected` セットで上書き禁止のキー指定。
  - 設定オブジェクト `Settings` を公開（`settings = Settings()`）
    - J-Quants、kabuステーション、Slack、データベース、システム設定等のプロパティを提供：
      - 必須項目は取得時に存在チェックを行い未設定時は `ValueError` を送出（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）。
      - `KABUSYS_API_BASE_URL` 相当: `kabu_api_base_url` はデフォルト `http://localhost:18080/kabusapi`。
      - DB パスのデフォルト: `duckdb_path` → `data/kabusys.duckdb`, `sqlite_path` → `data/monitoring.db`（`~` 展開あり）。
      - 環境種別 (`env`) の検証: 許容値は `development`, `paper_trading`, `live`。不正値は `ValueError`。
      - ログレベル (`log_level`) の検証: 許容値は `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`。不正値は `ValueError`。
      - ヘルパープロパティ: `is_live`, `is_paper`, `is_dev` を提供。

- DuckDB スキーマ定義 / 初期化モジュール (`src/kabusys/data/schema.py`)
  - Data Lake構成に基づく 3 層＋実行層のテーブル定義（DDL）を実装:
    - Raw Layer:
      - raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer:
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer:
      - features, ai_scores
    - Execution Layer:
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して主キー、外部キー、CHECK制約（例: 値の非負、列の値の列挙制約等）を設定。
    - 例: `raw_prices` の PRIMARY KEY は `(date, code)`、`raw_executions.side` は 'buy'/'sell' の CHECK。
    - 外部キーには削除時の挙動を定義（例: `news_symbols.news_id` は `news_articles(id)` を参照、ON DELETE CASCADE）。
    - 実行関連テーブルでは状態列（status）や注文種別（order_type）などを enumerated CHECK で表現。
  - インデックスを作成: 銘柄×日付スキャンやステータス検索など頻出クエリを想定したインデックス群を定義（`idx_prices_daily_code_date`, `idx_signal_queue_status`, `idx_orders_status` 等）。
  - スキーマ初期化関数:
    - init_schema(db_path) : DuckDB ファイルを初期化し、すべてのテーブルとインデックスを作成して接続オブジェクトを返す。
      - ":memory:" をサポート（インメモリ DB）。
      - db_path の親ディレクトリが存在しない場合は自動で作成。
      - DDL 実行は冪等（既存テーブルはスキップ）。
    - get_connection(db_path) : 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を推奨）。

- パッケージ構成（空モジュールの用意）
  - `src/kabusys/execution/__init__.py`, `src/kabusys/strategy/__init__.py`, `src/kabusys/data/__init__.py`, `src/kabusys/monitoring/__init__.py` を配置し、後続開発のための名前空間を確立。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Notes / Usage
- 環境設定の自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストや CI で便利です）。
- DuckDB スキーマは init_schema() で初期化してください。初回は必ず init_schema を呼び、以後は get_connection を使用して接続を取得することを推奨します。
- Settings プロパティは、必須環境変数が未設定の場合に例外を送出するため、アプリ起動前に .env を正しく用意してください（`.env.example` を参照する想定）。

<!--
参考:
- 主要 API:
  - settings: アプリ設定オブジェクト
  - init_schema(db_path), get_connection(db_path): DuckDB 操作
-->
