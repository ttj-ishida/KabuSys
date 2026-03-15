# Change Log

すべての注目すべき変更はこのファイルに記録されます。  
形式は "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

現在のバージョン: 0.1.0

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-15

初回リリース。日本株自動売買システムのコア基盤を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - `kabusys` パッケージの基本構成を追加。バージョンは `__version__ = "0.1.0"`。
  - パッケージ公開モジュールとして `data`, `strategy`, `execution`, `monitoring` を定義（サブパッケージは初期化ファイルを用意）。

- 環境設定管理モジュール (`src/kabusys/config.py`)
  - .env ファイルおよびOS環境変数から設定を読み込む自動ローダーを実装。
    - 読込優先順位: OS 環境変数 > `.env.local` > `.env`
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用途）。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を基準に行い、CWDに依存しない探索を実装。
    - .env 読み込み時に読み込み失敗が発生した場合は警告を出力して安全に続行。
    - `.env` 読み込み時の上書き制御: `override` フラグと OS 環境変数を保護する `protected` セットを採用。
  - 強化された .env パーサーを実装:
    - 空行・コメント行（先頭が `#`）を無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のエスケープ処理を考慮して正しく値をパース。
    - クォートなし値でのインラインコメント（`#`）の解釈ルールを実装。
  - 設定取得用 `Settings` クラスを提供（モジュールレベルで `settings = Settings()`）。
    - J-Quants, kabuステーション API, Slack, データベースパスなど主要設定のプロパティを提供。
    - 必須環境変数未設定時は `_require()` により明示的に `ValueError` を送出。
    - `KABUSYS_ENV` の許容値検証（`development`, `paper_trading`, `live`）と `LOG_LEVEL` の検証（`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）を実装。
    - DB パス (`DUCKDB_PATH`, `SQLITE_PATH`) は `Path` 型で返し、`~` の展開を行う。

- DuckDB スキーマ定義・初期化モジュール (`src/kabusys/data/schema.py`)
  - データレイヤ構成（Raw / Processed / Feature / Execution）に基づくテーブル DDL を実装。
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 多数の制約（PRIMARY KEY / FOREIGN KEY / CHECK）を定義し、データ整合性を担保。
    - 例: price/volume の非負制約、side/status/order_type の列挙制約、外部キー依存関係など。
  - 頻出クエリに対するインデックスを用意（銘柄×日付検索、ステータス検索、FK参照向けなど）。
  - 公開 API:
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 指定の DuckDB ファイルを作成（親ディレクトリ自動生成）し、上記テーブル・インデックスを冪等に作成して接続を返す。
      - `":memory:"` を渡すことでインメモリ DB を利用可能。
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 既存 DB への接続を返す（スキーマ初期化は行わない）。初回は `init_schema` を推奨。

- 監査ログ（トレーサビリティ）モジュール (`src/kabusys/data/audit.py`)
  - シグナルから約定に至るトレーサビリティを確保する監査用テーブル群を実装。
    - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を想定。
  - テーブル:
    - `signal_events`（戦略が生成した全シグナルのログ。棄却やエラーも記録）
    - `order_requests`（冪等性を持つ発注要求ログ、`order_request_id` を冪等キーとして実装。limit/stop の価格チェックなど制約を実装）
    - `executions`（証券会社からの約定ログ。`broker_execution_id` をユニーク制約として扱う）
  - すべての TIMESTAMP を UTC で保存する方針を反映。初期化時に `SET TimeZone='UTC'` を実行。
  - 監査用インデックス群を用意（シグナル検索、ステータス検索、broker_order_id/ordering の紐付けなど）。
  - 公開 API:
    - `init_audit_schema(conn: duckdb.DuckDBPyConnection) -> None`
      - 既存の DuckDB 接続に監査テーブル・インデックスを追加（冪等）。
    - `init_audit_db(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 監査専用 DB を作成して初期化済み接続を返す（親ディレクトリ自動生成、UTC 設定）。

### Changed
- 初回リリースにつき該当なし。

### Fixed
- 初回リリースにつき該当なし。

### Notes / 実装上の注意
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる（配布後や非リポジトリ環境で安全に動作）。
- `.env` の読み込みで OS 環境変数を上書きしたくない場合はデフォルト動作により保護される。`.env.local` は明示的に上書き（override=True）されるが、既存の OS 環境変数は保護される。
- DuckDB ファイルパス（`init_schema`/`init_audit_db`）は親ディレクトリが存在しない場合に自動作成するため、初期化時のファイル作成が容易。
- 監査ログは削除しない前提で設計されており、外部キーは基本的に `ON DELETE RESTRICT` を採用している。

---

今後のリリースでは戦略実装、実行エンジン（kabuステーション連携）、監視/通知（Slack 等）、テストケースと例示データの追加を予定しています。