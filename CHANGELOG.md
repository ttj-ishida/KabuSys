# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」の慣例に従って管理されています。

現在のバージョン規則: SemVer

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムの基盤となる設定管理、データスキーマ、およびパッケージ構成を提供します。

### Added
- パッケージ基礎
  - `kabusys` パッケージの初期化。`__version__ = "0.1.0"`、公開モジュールとして `data`, `strategy`, `execution`, `monitoring` を定義。
  - 空のサブパッケージ初期化ファイルを追加：`kabusys/execution`, `kabusys/strategy`, `kabusys/monitoring`（今後の拡張用プレースホルダ）。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む `Settings` クラスを実装。
  - 自動ロードの仕組み:
    - プロジェクトルートを `.git` または `pyproject.toml` から検出する `_find_project_root()` を実装（CWD に依存しない探索）。
    - ルートが見つかれば `.env`（既存環境変数を上書きしない）→ `.env.local`（上書きを許可）の順で読み込み。
    - 自動ロードを無効化するために環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` に対応。
  - .env パーサー `_parse_env_line()` を実装:
    - 空行、コメント（#）や `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理と閉じクォート探索を実装。
    - クォート無しの値に対してはインラインコメントの扱いを考慮。
  - .env 読み込み関数 `_load_env_file()` を実装:
    - ファイル読込失敗時は警告を発行して続行。
    - `override` と `protected`（OS 環境変数保護）による上書き制御を実装。
  - 必須環境変数チェック `_require()` を実装し、未設定時は `ValueError` を送出。
  - `Settings` による取得可能な設定プロパティ:
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション: `kabu_api_password`（必須）、`kabu_api_base_url`（デフォルト: http://localhost:18080/kabusapi）
    - Slack: `slack_bot_token`（必須）、`slack_channel_id`（必須）
    - データベースパス: `duckdb_path`（デフォルト: data/kabusys.duckdb）、`sqlite_path`（デフォルト: data/monitoring.db）
    - システム設定: `env`（development|paper_trading|live の検証）、`log_level`（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパー: `is_live`, `is_paper`, `is_dev`

- データ層（DuckDB）スキーマ (`kabusys.data.schema`)
  - DuckDB を用いた永続化スキーマを定義。Data Lake の 3 層＋実行層を想定したテーブル群を実装。
  - Raw Layer:
    - `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
  - Processed Layer:
    - `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
  - Feature Layer:
    - `features`, `ai_scores`
  - Execution Layer:
    - `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに対して型制約、CHECK 制約、PRIMARY / FOREIGN KEY を適用し、データ整合性を強化。
  - インデックス定義を複数追加（頻出クエリパターン向け）:
    - 例: `idx_prices_daily_code_date`, `idx_features_code_date`, `idx_signal_queue_status`, `idx_orders_status` など。
  - スキーマ操作用 API:
    - `init_schema(db_path)`:
      - DuckDB データベースを初期化し、全テーブル・インデックスを作成（冪等）。
      - `db_path` の親ディレクトリを自動作成。`:memory:` のサポート。
      - 初回スキーマ作成に使用することを想定。
    - `get_connection(db_path)`:
      - 既存の DuckDB 接続を返す（スキーマ初期化は行わない）。

- ドキュメント文字列 / 型ヒント
  - 各モジュール・関数にドキュメント文字列を追加し、型ヒントを用いて可読性と静的解析性を向上。

### Changed
- （該当なし）

### Fixed
- （該当なし）

### Removed
- （該当なし）

### Security
- （該当なし）

注: 本 CHANGELOG はソースコード（初期実装）から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース検証結果を基に必要に応じて追記・修正してください。