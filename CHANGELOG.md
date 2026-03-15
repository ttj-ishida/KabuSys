# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはリポジトリ内の現在のコードベースから推測して作成しています。

## [0.1.0] - 2026-03-15

### Added
- 初回公開（ベース実装）。
- パッケージメタ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として定義。
  - パッケージの公開モジュールを `__all__ = ["data", "strategy", "execution", "monitoring"]` で明示。

- 環境設定管理モジュール（src/kabusys/config.py）
  - `.env` ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
    - 読み込み優先順位は OS 環境変数 > .env.local > .env。
    - プロジェクトルートは `__file__` を起点に `.git` または `pyproject.toml` を探索して特定（CWD に依存しない）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - OS 環境変数は保護（protected keys）され、`.env.local` の上書き時に保護キーは上書きされない。
  - .env 解析の詳細：
    - コメント行（先頭の `#`）と空行を無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォートされた値のバックスラッシュエスケープ対応（クォート内のインラインコメントは無視）。
    - クォート無しの値では、`#` の直前が空白またはタブの場合にコメントとして扱う挙動を採用。
  - `Settings` クラスを提供し、環境変数からアプリ設定を取得するプロパティを公開（インスタンス `settings` をエクスポート）。
    - J-Quants / kabuステーション / Slack / データベースパスなどの必須・任意設定を取得。
    - 必須値が未設定の場合は `_require()` により `ValueError` を送出。
    - `duckdb_path` / `sqlite_path` は Path オブジェクトとして返す（`expanduser()` を適用）。
    - `env`（`KABUSYS_ENV`）は `development` / `paper_trading` / `live` のみ許可し、不正値で例外を送出。
    - `log_level`（`LOG_LEVEL`）は `DEBUG/INFO/WARNING/ERROR/CRITICAL` のみ許可。
    - `is_live` / `is_paper` / `is_dev` の便宜プロパティを実装。

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - 3 層構造（Raw / Processed / Feature）および Execution 層を含む包括的なテーブル定義を実装。
    - Raw layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature layer: `features`, `ai_scores`
    - Execution layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに対して主キー、CHECK 制約、外部キー、NOT NULL などの厳密なスキーマ制約を付与（データ整合性を重視）。
  - 頻出クエリに基づくインデックスを複数定義（例: 銘柄×日付検索、ステータス検索、order_id/ signal_id 参照用など）。
  - スキーマ初期化 API を提供：
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 指定した DuckDB ファイルを初期化し、全テーブルとインデックスを作成する（冪等）。
      - `:memory:` を指定した場合はインメモリ DB を使用。
      - DB ファイル格納ディレクトリが存在しない場合は自動作成。
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 既存 DB への接続を返す（スキーマ初期化は行わない）。
  - テーブル作成順は外部キー依存を考慮して決定。

- 監査ログ（トレーサビリティ）モジュール（src/kabusys/data/audit.py）
  - シグナルから約定までのトレーサビリティを保証する監査テーブル群を実装。
    - `signal_events`（戦略が生成したシグナル。棄却されたものやエラーも含めて永続化）
    - `order_requests`（発注要求、`order_request_id` を冪等キーとして扱う。status と updated_at を持つ）
    - `executions`（実際の約定ログ。`broker_execution_id` は証券会社提供の約定 ID としてユニーク）
  - 監査テーブル初期化 API：
    - `init_audit_schema(conn: duckdb.DuckDBPyConnection) -> None`
      - 既存接続に監査テーブルを追加（冪等）。
      - `SET TimeZone='UTC'` を実行し、すべての TIMESTAMP を UTC で扱うポリシーを適用。
    - `init_audit_db(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 監査ログ専用 DB を初期化して接続を返す（ディレクトリ自動作成、UTC を適用）。
  - 監査テーブルは削除を前提とせず（FK は ON DELETE RESTRICT）、完全な監査証跡を保持する設計。
  - インデックスを複数定義（signal_events の日付/銘柄検索、order_requests の status・signal_id 検索、executions の broker_order_id 検索など）。

- モジュール構成
  - サブパッケージのプレースホルダファイルを追加（空の __init__）:
    - `src/kabusys/execution/__init__.py`
    - `src/kabusys/strategy/__init__.py`
    - `src/kabusys/monitoring/__init__.py`
  - データ関連モジュール群を `src/kabusys/data/` 内に収録（schema, audit, audit 初期化ロジック等）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- 環境変数の取り扱いについて、OS 環境変数を保護する仕組み（`protected` keys）を導入。自動ロード時の上書き制御が可能。

----

備考・実装上の注意（コードからの想定）
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされるため、パッケージ配布後やテスト環境でも安全に動作する設計となっている。
- `Settings` の必須設定が未設定だと起動時に即時例外を投げるため、運用時は `.env` や環境変数の整備が必要。
- DuckDB 初期化関数は冪等であるため複数回呼んでも安全だが、スキーマ変更やマイグレーションは別途考慮が必要（本コードではマイグレーションフレームワークは含まれていない）。
- 監査テーブルは削除しない前提で設計されているため、永続化ポリシーとストレージ管理に注意が必要。

もし追加のリリース履歴（Unreleased の機能や次版の予定）や、各テーブル・環境変数についての詳しい説明を追記したい場合は指示してください。