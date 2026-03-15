# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

- リリース方針: 公開 API やストレージスキーマの仕様、環境設定の振る舞いといった利用者に影響する箇所を重点的に記載します。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムのコア基盤を提供します。

### Added
- パッケージ初期化
  - `kabusys` パッケージを追加。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に設定（strategy/execution/monitoring は現時点でパッケージスケルトン）。
  - バージョン情報: `kabusys.__version__ = "0.1.0"`。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
    - ロード順序: OS 環境変数 > .env.local > .env
    - 環境変数の自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト用）。
    - プロジェクトルート判定は `src/kabusys/config.py` の実装により、`.git` または `pyproject.toml` の存在を基に決定（__file__ を起点とした探索で CWD に依存しない）。
    - OS 環境変数を保護するため、既存の環境変数キーは保護セットとして扱い `.env.local` の override 時に誤って OS 変数を上書きしない。
  - 柔軟な .env パーサ実装:
    - 空行・コメントアウト行 (`#`)、`export KEY=val` 形式に対応。
    - シングル/ダブルクォート値のサポート、バックスラッシュによるエスケープ処理。
    - クォートなし値では `#` の直前がスペース/タブの場合にのみインラインコメントとして扱う（コメント誤認を低減）。
  - 設定ラッパー `Settings` を追加（インスタンス: `settings`）。
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供:
      - jquants_refresh_token (必須)
      - kabu_api_password (必須)
      - kabu_api_base_url (デフォルト "http://localhost:18080/kabusapi")
      - slack_bot_token, slack_channel_id (必須)
      - duckdb_path (デフォルト "data/kabusys.duckdb")
      - sqlite_path (デフォルト "data/monitoring.db")
      - env: `KABUSYS_ENV` を検証（有効値: development, paper_trading, live）
      - log_level: `LOG_LEVEL` を検証（有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - ヘルパー: is_live / is_paper / is_dev
    - 必須環境変数未設定時は `ValueError` を送出する `_require` を採用。

- データベーススキーマ（DuckDB） (`kabusys.data.schema`)
  - 3層構造のテーブル群を定義（Raw / Processed / Feature / Execution）。
  - 主なテーブル:
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに対して適切な制約を設定:
    - PRIMARY KEY、CHECK 制約（負値や範囲チェック）、外部キー制約（必要箇所に ON DELETE 動作を指定）を導入。
  - パフォーマンス向上のためのインデックスを定義（例: 銘柄×日付、status 検索、orders/trades の結合用等）。
  - スキーマ初期化 API:
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 指定 DB ファイルの親ディレクトリを自動作成し、すべてのテーブルとインデックスを作成（冪等）。
      - ":memory:" 指定でインメモリ DB をサポート。
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 既存 DB へ接続を返す（スキーマの初期化はしない。初回は init_schema を推奨）。

- 監査ログ（Audit）スキーマ (`kabusys.data.audit`)
  - シグナル → 発注 → 約定のトレーサビリティを保証する監査用テーブルを提供:
    - `signal_events`（戦略層が生成するすべてのシグナルを記録、棄却やエラー含む）
    - `order_requests`（冪等キーである order_request_id を持つ発注要求ログ）
    - `executions`（証券会社からの約定ログ、broker_execution_id をユニークキーとして冪等性を確保）
  - 設計方針・特徴:
    - すべての TIMESTAMP は UTC 保存（初期化時に `SET TimeZone='UTC'` を実行）。
    - `order_requests` のステータス遷移・エラー情報を格納するフィールドを用意（pending/sent/filled/partially_filled/cancelled/rejected/error 等）。
    - 外部キーは ON DELETE RESTRICT（監査ログは削除しない前提）。
    - 監査用インデックスを多数定義（signal 日付検索、戦略別検索、status 検索、broker_order_id 検索等）。
  - 監査スキーマ初期化 API:
    - `init_audit_schema(conn: duckdb.DuckDBPyConnection) -> None`
      - 既存の DuckDB 接続に監査用テーブルとインデックスを追加（冪等）。
    - `init_audit_db(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 監査専用 DuckDB を初期化し接続を返す（親ディレクトリ自動作成、UTC 設定）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- DB 初期化関数は冪等設計のため、繰り返し呼び出しても既存オブジェクトを上書きしない。
- `.env` パースの実装により、クォート中のエスケープやインラインコメントの扱いが慎重に設計されているため、既存の環境変数の誤読み取りリスクを低減。
- `kabusys.data` 以下はデータ格納と監査のスキーマ実装に注力しており、実際のデータ取得や戦略ロジック、発注実装は別モジュール（strategy, execution, monitoring）での実装を想定する。

---

（今後のリリースでは、strategy と execution の具象実装、監視/アラート機能、より細かなマイグレーション手順・ユニットテストを追記予定）