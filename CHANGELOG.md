# Keep a Changelog

すべての注目すべき変更を時系列で記載します。  
このファイルは Keep a Changelog の慣例に従っています。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムの基盤を実装しました。

### Added
- パッケージ基盤
  - パッケージルート: `kabusys`、バージョン `0.1.0` を定義（src/kabusys/__init__.py）。
  - public モジュール群をエクスポート: `data`, `strategy`, `execution`, `monitoring`（将来的な拡張ポイントとして空の __init__ を配置）。

- 環境変数／設定管理（src/kabusys/config.py）
  - プロジェクトルート自動検出: `.git` または `pyproject.toml` を基準に探索する `_find_project_root()` を実装。CWD に依存しない自動 .env ロード。
  - .env 読み込み: `.env` と `.env.local` の読み込み順序を採用（OS 環境変数が優先）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - .env パーサー `_parse_env_line()` は `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理（クォートありでは行末のコメント無視）に対応。
  - `Settings` クラスを公開（settings インスタンス）。以下のプロパティを提供:
    - J-Quants: `jquants_refresh_token`
    - kabuステーション: `kabu_api_password`, `kabu_api_base_url`（デフォルト: `http://localhost:18080/kabusapi`）
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`（デフォルト `data/kabusys.duckdb`）、`sqlite_path`（デフォルト `data/monitoring.db`）
    - 環境判定・検証: `env`（有効値: `development`, `paper_trading`, `live`）、`log_level`（`DEBUG` 等の検証）、便宜的に `is_live`, `is_paper`, `is_dev`

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本設計:
    - API レート制限遵守（120 req/min）。固定間隔スロットリング `_RateLimiter` を提供。
    - リトライロジック（指数バックオフ、最大 3 回）。リトライ対象ステータス: 408, 429, 5xx。429 の場合は `Retry-After` ヘッダを優先。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）と再試行。無限再帰防止のため `allow_refresh` フラグを利用。
    - Look-ahead bias 対策として取得時刻を UTC で `fetched_at` に保存。
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除。
  - HTTP ユーティリティ `_request()` 実装（JSON デコードエラーや各例外処理を含む）。
  - トークン管理: モジュールレベルキャッシュ `_ID_TOKEN_CACHE`、`get_id_token()`（リフレッシュトークンから取得）。
  - データ取得関数（ページネーション対応）:
    - `fetch_daily_quotes(...)` — 日足（OHLCV）
    - `fetch_financial_statements(...)` — 四半期財務データ
    - `fetch_market_calendar(...)` — JPX マーケットカレンダー
  - DuckDB への保存関数（冪等）:
    - `save_daily_quotes(conn, records)`
    - `save_financial_statements(conn, records)`
    - `save_market_calendar(conn, records)`
    - 保存時に必須 PK 欠損行はスキップしてログ警告（件数）を出力
  - 型変換ユーティリティ: `_to_float()`、`_to_int()`（文字列や浮動小数点文字列の扱いを明確化）

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - 3層データレイヤ設計: Raw, Processed, Feature（+ Execution 層）
  - Raw レイヤ:
    - `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
  - Processed レイヤ:
    - `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
  - Feature レイヤ:
    - `features`, `ai_scores`
  - Execution レイヤ:
    - `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに型チェックや CHECK 制約（例: 非負、列チェック等）を付与。主キー・外部キーを設定。
  - 利用頻度に応じたインデックスを複数定義（銘柄×日付スキャン、ステータス検索等）。
  - `init_schema(db_path)` により DB ファイルの親ディレクトリを自動作成し、すべての DDL とインデックスを作成（冪等）。`:memory:` サポートあり。
  - `get_connection(db_path)` で既存 DB へ接続（初期化は行わない点を明記）。

- 監査（Audit）モジュール（src/kabusys/data/audit.py）
  - 監査ログ用テーブルの実装: `signal_events`, `order_requests`, `executions`
  - 設計方針:
    - UUID ベースのトレーサビリティ（signal_id → order_request_id → broker_order_id → executions）
    - order_request_id を冪等キーとして二重発注防止
    - すべての TIMESTAMP を UTC で保存（`init_audit_schema()` は `SET TimeZone='UTC'` を実行）
    - エラーや棄却も必ず永続化
    - FK は削除制約（ON DELETE RESTRICT）とし、監査ログは削除しない前提
  - `init_audit_schema(conn)` で既存の DuckDB 接続に対して監査関連テーブルを追加
  - `init_audit_db(db_path)` で監査専用 DB を初期化して接続を返す
  - 監査用のインデックスを多数定義（status 検索、signal_id/日付/銘柄検索、broker_order_id など）

- ロギング/警告
  - 各処理で logging を利用（取得件数、リトライ警告、PK 欠損スキップなど）
  - .env 読み込み失敗時は warnings.warn を発行

### Changed
- （なし：初回リリース）

### Fixed
- （なし：初回リリース）

### Security
- （なし：初回リリース）

### Notes / 設計上の重要点
- Look-ahead Bias の防止のため、外部データの取得タイミングを `fetched_at` に UTC で保存しており、いつシステムがそのデータを入手したかをトレース可能です。
- API レート制限（120 req/min）を守るため固定間隔スロットリングを採用。短時間に多数のリクエストを送るバッチ処理は注意が必要です。
- J-Quants API 呼び出しは自動リトライとトークン自動リフレッシュ（401 → 1回リフレッシュ）を備えていますが、極端なエラー時には最終的に例外を投げます。
- DuckDB のテーブル設計ではデータ整合性を重視した CHECK 制約や外部キーを多数追加しています。既存 DB への適用時は互換性に注意してください。
- デフォルトの DuckDB ファイルパスは `data/kabusys.duckdb`。環境変数 `DUCKDB_PATH` で変更可能。

---

（将来的には Unreleased セクションに変更を記載し、バージョンを切っていってください。）