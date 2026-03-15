# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠し、セマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムのコア構成と基盤機能を追加。

### Added
- パッケージ初期化
  - `kabusys` パッケージの基本構成を追加。公開モジュールとして `data`, `strategy`, `execution`, `monitoring` をエクスポート（`src/kabusys/__init__.py`）。
  - バージョン情報を `__version__ = "0.1.0"` として定義。

- 環境設定管理
  - 環境変数・設定管理モジュールを追加（`src/kabusys/config.py`）。
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの検出は `.git` または `pyproject.toml` を基準として行い、CWD に依存しない実装（`_find_project_root`）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途など）。
    - OS 環境変数は保護（上書き禁止）される仕組みを導入。
  - `.env` ファイルパーサー（`_parse_env_line`）を実装：
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート文字列のバックスラッシュエスケープ対応
    - クォート無しの場合の行末コメント（`#`）の扱いを細かく実装
  - `.env` ファイル読み込み時にファイルオープンに失敗した場合は警告を出す（安全なフェイルフォワード）。
  - アプリ設定を取得する `Settings` クラスを追加（`settings` インスタンスを公開）。
    - J-Quants, kabuステーション, Slack, データベースパスなどのプロパティを提供（例: `jquants_refresh_token`, `kabu_api_password`, `slack_bot_token`, `duckdb_path`, `sqlite_path`）。
    - 環境 (`KABUSYS_ENV`) とログレベル (`LOG_LEVEL`) の検証ロジックを実装。許可値は `{"development","paper_trading","live"}` と `{"DEBUG","INFO","WARNING","ERROR","CRITICAL"}`。
    - `is_live`, `is_paper`, `is_dev` の補助プロパティを追加。

- DuckDB スキーマと初期化 API
  - データ層（Raw / Processed / Feature / Execution）を考慮した DuckDB 用スキーマ定義を追加（`src/kabusys/data/schema.py`）。
    - Raw レイヤー: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed レイヤー: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature レイヤー: `features`, `ai_scores`
    - Execution レイヤー: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - テーブル定義にはデータ整合性のための CHECK 制約、PRIMARY KEY、外部キー制約を適用（可能な範囲での整合性確保）。
  - 頻出クエリを想定したインデックス定義を追加（例: 銘柄×日付、ステータス検索など）。
  - `init_schema(db_path)` を実装:
    - 指定した DuckDB ファイルを初期化し、全テーブル・インデックスを作成（冪等）。
    - db の親ディレクトリが存在しない場合は自動作成。
    - `":memory:"` を受け入れ、インメモリ DB の使用に対応。
  - `get_connection(db_path)` を実装: 既存 DB への接続を返す（スキーマ初期化は行わない）。

- モジュール雛形
  - 空のパッケージモジュールを追加（`src/kabusys/data/__init__.py`, `src/kabusys/execution/__init__.py`, `src/kabusys/strategy/__init__.py`, `src/kabusys/monitoring/__init__.py`） — 今後の拡張ポイントとして確保。

### Changed
- （初回リリースのため適用なし）

### Fixed
- （初回リリースのため適用なし）

### Notes / Migration
- 初回リリースのため特別なマイグレーションは不要。  
- 初回起動時に DuckDB スキーマを作成するには、まず `init_schema(settings.duckdb_path)` を呼んでください。
- 環境変数の自動ロードを望まない場合は起動前に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト環境での競合回避等に有用）。
- 必須環境変数（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）が未設定の場合、`Settings` の該当プロパティアクセスで `ValueError` が発生します。`.env.example` を参考に設定してください。

---

今後、各サブパッケージ（data/strategy/execution/monitoring）に具体的なデータ取得、特徴量生成、シグナル発行、発注実行、監視・通知のロジックを追加していく予定です。