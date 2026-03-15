# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」仕様に準拠しています。

全てのリリースは semver に従います。

## [0.1.0] - 2026-03-15

初回公開リリース。

### 追加
- パッケージ初期化
  - `kabusys` パッケージの基本構造を追加。`__version__ = "0.1.0"` を設定し、モジュール公開リストとして `["data", "strategy", "execution", "monitoring"]` を定義。

- 環境設定管理 (`src/kabusys/config.py`)
  - `.env` ファイルおよび環境変数から設定を読み込む自動ローダーを実装。自動ロードはプロジェクトルート（`.git` または `pyproject.toml`）を基準に行われるため、CWD に依存しない挙動を実現。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をサポート。
  - `.env` / `.env.local` の読み込み順序および上書きルールを実装（OS 環境変数は保護）。
  - `.env` パーサーの実装：
    - `export KEY=val` 形式に対応。
    - シングル／ダブルクォート内でのバックスラッシュエスケープ処理をサポート（クォートで囲まれた値はその閉じクォートまでを値として扱い、それ以降のインラインコメントを無視）。
    - クォート無し値での `#` をコメント扱いとする条件（`#` の直前がスペースまたはタブの場合にコメント）を導入。
  - `.env` 読み込み失敗時は警告を出す実装。
  - 必須環境変数が未設定のときに例外を投げるヘルパー `_require()` を提供。
  - 設定ラッパー `Settings` クラスを追加。主なプロパティ：
    - J-Quants: `jquants_refresh_token`（必須）
    - kabu API: `kabu_api_password`（必須）、`kabu_api_base_url`（デフォルト: `http://localhost:18080/kabusapi`）
    - Slack: `slack_bot_token`（必須）、`slack_channel_id`（必須）
    - DB パス: `duckdb_path`（デフォルト `data/kabusys.duckdb`）、`sqlite_path`（デフォルト `data/monitoring.db`）
    - 実行環境: `env`（`development` / `paper_trading` / `live` の検証を含む）、`log_level`（ログレベル検証）、および `is_live` / `is_paper` / `is_dev` 補助プロパティ

- データスキーマと初期化 (`src/kabusys/data/schema.py`)
  - DuckDB ベースのデータスキーマを定義。設計は DataSchema.md に基づく3層構造を想定：
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルのカラム型・制約（CHECK、PRIMARY KEY、FOREIGN KEY）を定義。例: 価格・出来高に対する非負チェック、注文サイドやステータスに対する列挙チェックなど。
  - インデックス群を定義（頻出クエリ想定に基づく）。例: `idx_prices_daily_code_date`, `idx_signal_queue_status`, `idx_orders_status` など。
  - テーブル作成の順序付け（外部キー依存を考慮）。
  - 公開 API:
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 指定した DuckDB ファイルを初期化し（必要なら親ディレクトリ作成）、全テーブルとインデックスを作成。冪等性あり。`:memory:` をサポート。
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 既存 DB へ接続（スキーマ初期化は行わない）。

- 空ディレクトリプレースホルダ
  - `src/kabusys/execution/__init__.py`, `src/kabusys/strategy/__init__.py`, `src/kabusys/data/__init__.py`, `src/kabusys/monitoring/__init__.py` を追加してパッケージ構造を確立（将来的な実装ポイント）。

- ドキュメント文字列（docstring）を各モジュールに追加。主要な関数・クラスに説明を付与。

### 変更
- 初回リリースのため該当なし。

### 修正
- 初回リリースのため該当なし。

### 破壊的変更
- 初回リリースのため該当なし。

### セキュリティ
- 初回リリースのため該当なし。

---

注:
- この CHANGELOG はソースコードから推測して作成しています。実装や仕様の詳細は当該ファイルの docstring やコード本体を参照してください。