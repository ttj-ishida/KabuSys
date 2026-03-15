# CHANGELOG

すべての重要な変更をここに記録します。このファイルは「Keep a Changelog」形式に従います。

## [0.1.0] - 2026-03-15

初回リリース。日本株自動売買システムの基礎的なモジュール構成、環境設定読み込み、および DuckDB 用のスキーマ初期化機能を追加。

### 追加 (Added)
- パッケージ
  - kabusys パッケージを追加。パッケージバージョンを `0.1.0` として公開。
  - モジュールエクスポート: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定管理 (src/kabusys/config.py)
  - プロジェクトルート自動検出: .git または pyproject.toml を基準にしてパッケージ配置に依存せずプロジェクトルートを特定する `_find_project_root()` を実装。
  - .env ファイルパーサー: `_parse_env_line()` を実装。以下の形式に対応
    - 空行・コメント行の無視 (# で始まる行)
    - `export KEY=val` 形式のサポート
    - シングル/ダブルクォートで囲まれた値のバックスラッシュエスケープ処理
    - クォートなし値に対するインラインコメント判定（'#' の前の文字がスペース/タブの場合はコメント扱い）
  - .env ローダー: `_load_env_file()` を実装。以下の挙動を提供
    - ファイル存在チェックおよび読み込み時の警告出力（読み込み失敗時）
    - `override` と `protected` パラメータによる上書き制御（OS 環境変数を保護するための protected セット）
  - 自動ロードの挙動:
    - デフォルトで自動ロードを実行（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート未特定時は自動ロードをスキップ
  - 必須環境変数取得関数: `_require()` を提供し、未設定時は分かりやすい ValueError を送出。
  - Settings クラスを実装し、アプリケーション設定をプロパティで提供:
    - J-Quants: `jquants_refresh_token`
    - kabuステーション API: `kabu_api_password`, `kabu_api_base_url`（デフォルト: http://localhost:18080/kabusapi）
    - Slack: `slack_bot_token`, `slack_channel_id`
    - データベースパス: `duckdb_path`（デフォルト: data/kabusys.duckdb）、`sqlite_path`（デフォルト: data/monitoring.db）
    - システム設定: `env`（検証: development / paper_trading / live のみ許容）、`log_level`（検証: DEBUG/INFO/WARNING/ERROR/CRITICAL）、および `is_live`/`is_paper`/`is_dev` ブールプロパティ
  - settings インスタンスを公開。

- DuckDB スキーマと初期化 (src/kabusys/data/schema.py)
  - 3 層（Raw / Processed / Feature）および Execution 層に対応するテーブル定義を追加。
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤー: features, ai_scores
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対する列型・NULL 制約・チェック制約・主キー・外部キーを明示的に定義（データ整合性を想定）。
  - 頻出クエリ向けのインデックスを複数定義（例: prices_daily や features の code/date、signal_queue.status、orders.status 等）。
  - テーブル作成順序を外部キー依存を考慮して整理。
  - 公開 API:
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 指定された DuckDB ファイルの親ディレクトリを自動作成（":memory:" を除く）。
      - 全テーブルとインデックスを作成（冪等）。
      - 初期化済みの duckdb 接続を返す。
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - スキーマ初期化を行わず既存 DB に接続するユーティリティ。

- パッケージ構成
  - 空のサブパッケージ初期化ファイルを追加: src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py（将来の拡張点）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

備考:
- .env 読み込みはテストや CI 環境での妨げにならないよう `KABUSYS_DISABLE_AUTO_ENV_LOAD` により抑制可能です。
- スキーマ側はデータ整合性のため多くのチェック制約・外部キーを設けていますが、運用時に追加要件（パーティション、VACUUM、バックアップ戦略など）に応じて拡張してください。