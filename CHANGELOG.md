# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このプロジェクトではセマンティックバージョニングを採用しています。

フォーマット要約: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-15
初回公開リリース。

### Added
- パッケージ基本構成を追加
  - パッケージ名: `kabusys`
  - エクスポート: `data`, `strategy`, `execution`, `monitoring`
  - バージョン: `0.1.0`（src/kabusys/__init__.py）

- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に親ディレクトリから探索する `_find_project_root()` を実装。カレントワーキングディレクトリに依存しない自動 .env ロードを実現。
  - `.env` 行パーサー `_parse_env_line()` を実装
    - コメント行、空行、`export KEY=val` 形式に対応
    - シングル/ダブルクォート内のエスケープ処理を考慮
    - クォートなしの値では `#` の前がスペース/タブならコメントとして扱う挙動を実装
  - .env ファイル読み込みロジック `_load_env_file()` を実装
    - `override` と `protected`（OS 環境変数保護）の仕組みを提供
    - 読み込み失敗時は警告を発行（例外は投げず処理継続）
  - 自動読み込みの優先順位を実装
    - OS 環境変数 > .env.local > .env
    - 自動ロード無効化環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
    - プロジェクトルートが見つからない場合は自動ロードをスキップ
  - 必須環境変数取得ヘルパー `_require()` を実装（未設定時は ValueError を送出）
  - 設定クラス `Settings` を公開（インスタンス: `settings`）
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション API: `kabu_api_password`（必須）、`kabu_api_base_url`（デフォルト: `http://localhost:18080/kabusapi`）
    - Slack: `slack_bot_token`（必須）、`slack_channel_id`（必須）
    - データベースパス: `duckdb_path`（デフォルト: `data/kabusys.duckdb`）、`sqlite_path`（デフォルト: `data/monitoring.db`）
    - 実行環境判別: `env`（許可値: `development`, `paper_trading`, `live`; 不正値は ValueError）
    - ログレベル検証: `log_level`（許可値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）
    - 環境フラグ: `is_live`, `is_paper`, `is_dev`

- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）
  - 3層（Raw / Processed / Feature）＋Execution 層に基づくテーブル群を定義
    - Raw layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature layer: `features`, `ai_scores`
    - Execution layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに対して適切な型、CHECK 制約、PRIMARY KEY、外部キーを定義
    - 例: `raw_prices` と `prices_daily` の主キーは `(date, code)`、`orders` の `signal_id` に対する外部キーは `ON DELETE SET NULL` 等
  - 頻出クエリへ対応するためのインデックスを定義
    - 例: `idx_prices_daily_code_date`, `idx_signal_queue_status`, `idx_orders_status` など
  - スキーマ初期化 API を提供
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 指定したパスに対してテーブルとインデックスを作成（冪等）
      - `:memory:` をサポート（インメモリ DB）
      - ファイル DB の場合は親ディレクトリを自動作成
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 既存 DB への接続を返す（スキーマ初期化は行わない）
  - スキーマ作成順は外部キー依存を考慮して設定済み

- 空のパッケージ・プレースホルダを追加
  - `src/kabusys/data/__init__.py`, `src/kabusys/execution/__init__.py`, `src/kabusys/strategy/__init__.py`, `src/kabusys/monitoring/__init__.py`
  - 今後の機能実装のためのエントリポイントを確保

### Changed
- （初版のため無し）

### Fixed
- （初版のため無し）

### Deprecated
- （初版のため無し）

### Removed
- （初版のため無し）

### Security
- 環境変数の取り扱いにおいて、OS 環境変数を保護するための `protected` 機構を導入。自動読み込み時に既存 OS 環境変数が不意に上書きされないように配慮。

---

注意:
- 必須の環境変数（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）が設定されていない場合、`settings` のプロパティアクセス時に `ValueError` が発生します。`.env.example` を参考に `.env` を準備してください。
- 自動 .env ロードをテスト等で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のスキーマは初回に `init_schema()` を呼ぶことで作成されます。既存 DB に接続するだけの場合は `get_connection()` を使用してください。