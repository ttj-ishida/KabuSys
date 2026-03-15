# Changelog

すべての注記は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  

既知の互換性方針はセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-15

初回公開リリース。以下の主要機能を実装しています。

### 追加 (Added)
- パッケージ初期構成
  - top-level パッケージ `kabusys` を追加し、公開モジュールとして `data`, `strategy`, `execution`, `monitoring` を定義。
  - パッケージバージョン: `0.1.0`（src/kabusys/__init__.py）。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定値をロードする自動ローダーを実装。
    - 読み込み順序: OS環境変数 > .env.local > .env。プロジェクトルートが検出できない場合は自動ロードをスキップ。
    - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
    - ロード時、OS側に既に存在する環境変数は保護（`.env.local` を除く）される。
  - .env パーサーの実装（`_parse_env_line`）
    - コメント行、`export KEY=VAL` 形式、クォート（シングル/ダブル）の扱い、バックスラッシュによるエスケープ処理、インラインコメント処理を考慮。
  - .env ファイル読み込み時の I/O エラーに対して警告を出す挙動を追加。
  - プロジェクトルート検出関数（`.git` または `pyproject.toml` を親ディレクトリから探索）を追加（CWD に依存しない挙動）。
  - 環境取得のユーティリティ `Settings` を追加（`settings` インスタンスを提供）。
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション: `kabu_api_password`（必須）、`kabu_api_base_url`（デフォルト: `http://localhost:18080/kabusapi`）
    - Slack: `slack_bot_token`（必須）、`slack_channel_id`（必須）
    - データベース: `duckdb_path`（デフォルト: `data/kabusys.duckdb`）、`sqlite_path`（デフォルト: `data/monitoring.db`）
    - システム設定:
      - `KABUSYS_ENV`（`development`, `paper_trading`, `live` のいずれか、デフォルト `development`）の検証
      - `LOG_LEVEL`（`DEBUG, INFO, WARNING, ERROR, CRITICAL` の検証、デフォルト `INFO`）
      - `is_live`, `is_paper`, `is_dev` のブールプロパティ

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - 投資自動売買システム向けの多層スキーマを定義（Raw / Processed / Feature / Execution レイヤー）。
  - 生データ (raw) テーブル:
    - `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
  - 加工済み (processed) テーブル:
    - `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
  - 特徴量 (feature) テーブル:
    - `features`, `ai_scores`
  - 実行 (execution) テーブル:
    - `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに対する制約（PRIMARY KEY、CHECK、FOREIGN KEY）を定義し、クエリ効率を考慮したインデックスを追加。
  - テーブル作成の順序は外部キー依存を考慮して決定。
  - 公開 API:
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 指定 DB を初期化して全テーブルとインデックスを作成。親ディレクトリがない場合は自動作成。":memory:" 対応。
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 既存の DuckDB へ接続（スキーマ初期化は行わない）。

### 変更 (Changed)
- 初回リリースにつき該当なし。

### 修正 (Fixed)
- 初回リリースにつき該当なし。

### セキュリティ (Security)
- 初回リリースにつき該当なし。

---

利用と移行メモ
- 初回セットアップ
  1. 必須環境変数（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）を設定してください。未設定の場合は `Settings` のプロパティアクセスで `ValueError` が発生します。
  2. DuckDB スキーマを作成するには:
     - Python から: 
       - from kabusys.data.schema import init_schema
       - conn = init_schema("data/kabusys.duckdb")
  3. 自動で .env を読み込みたくないテスト環境などでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env の書式
  - `KEY=VALUE`、`export KEY=VALUE`、クォート、エスケープ、インラインコメント等に対応しています。詳細は実装の挙動に従ってください。
- デフォルト値
  - Kabu API base URL: `http://localhost:18080/kabusapi`
  - DuckDB path: `data/kabusys.duckdb`
  - SQLite path (monitoring): `data/monitoring.db`
  - 環境: `development`、ログレベル: `INFO`

既知の制約 / 今後の改善予定（例）
- schema 定義は現在 DDL を直書きで管理しているため、将来的にバージョン管理（マイグレーション機構）の追加を検討。
- strategy, execution, monitoring モジュールはパッケージ雛形として存在（今後具体的機能追加予定）。

--- 

署名: kabusys コードベース（初回リリース: 0.1.0）