# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般方針:
- 主要リリースは semver に従います（このリポジトリはこの段階で v0.1.0）。
- 日付はリリース日を示します。

## [0.1.0] - 2026-03-15

初回リリース — 日本株自動売買システムの基盤モジュール群を追加しました。

### Added
- パッケージ初期化
  - `kabusys` パッケージを追加し、バージョンを 0.1.0 に設定。
  - サブパッケージのプレースホルダを作成：`data`, `strategy`, `execution`, `monitoring`。

- 環境設定管理
  - `kabusys.config` モジュールを追加。
  - `.env` ファイルまたは OS 環境変数から設定を自動読み込み（優先度: OS 環境 > .env.local > .env）。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト等で使用）。
  - .env パーサー実装:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート中のバックスラッシュエスケープ対応。
    - クォートなしのコメント扱いは「# の直前が空白/タブの場合」に限定。
  - `Settings` クラスを提供し、環境変数の取得と検証を一元化。
    - 必須環境変数チェック（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）。
    - デフォルト値: `KABUS_API_BASE_URL` は `http://localhost:18080/kabusapi`、`DUCKDB_PATH` は `data/kabusys.duckdb`、`SQLITE_PATH` は `data/monitoring.db`。
    - `KABUSYS_ENV` 値検証（有効値: `development`, `paper_trading`, `live`）。
    - `LOG_LEVEL` 検証（有効値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）。
    - ヘルパーで実行モード判定: `is_live`, `is_paper`, `is_dev`。

- J-Quants API クライアント
  - `kabusys.data.jquants_client` を実装。
  - 取得可能データ:
    - 株価日足（OHLCV）: `fetch_daily_quotes`
    - 財務データ（四半期 BS/PL）: `fetch_financial_statements`
    - JPX マーケットカレンダー: `fetch_market_calendar`
  - 設計上の特徴:
    - レート制限遵守: 固定間隔スロットリングで 120 req/min に対応（内部クラス `_RateLimiter`）。
    - リトライ戦略: 最大 3 回、指数バックオフ（基底 2 秒）、HTTP 408/429 と 5xx を対象に再試行。
    - 429 の場合は `Retry-After` ヘッダを優先。
    - 401 (Unauthorized) 受信時はリフレッシュトークンで自動的に ID トークンを再取得して 1 回だけリトライ（無限再帰防止）。
    - ページネーション対応: `pagination_key` を用いたループ処理、重複検出で終了。
    - モジュールレベルで ID トークンをキャッシュし、ページネーション間で共有。
    - 取得時刻（fetched_at）を UTC タイムスタンプで記録することで Look-ahead Bias を低減。
  - HTTP ユーティリティ `_request` 実装（JSON デコード時のエラーハンドリングなど）。

- DuckDB スキーマと永続化ユーティリティ
  - `kabusys.data.schema` を追加。
  - 3 層アーキテクチャに対応する DDL を定義:
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに妥当性制約（CHECK, NOT NULL, PRIMARY KEY, FOREIGN KEY）を追加。
  - 運用を想定したインデックス群を定義（例: 銘柄×日付スキャン、ステータス検索など）。
  - `init_schema(db_path)` を提供:
    - DuckDB ファイル作成（親ディレクトリ自動作成）および DDL/インデックスの適用（冪等）。
    - `:memory:` を指定してインメモリ DB を利用可能。
  - `get_connection(db_path)` を提供（既存 DB への接続。スキーマ初期化は行わない）。

- DuckDB への保存（J-Quants 連携）
  - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar` を実装。
  - 保存は冪等: INSERT ... ON CONFLICT DO UPDATE を使用して重複を更新。
  - PK 欠損行はスキップし、その数を警告ログ出力。
  - `save_*` は保存件数を返す。

- 監査ログ（トレーサビリティ）
  - `kabusys.data.audit` を追加。
  - 監査用テーブル群:
    - `signal_events`（シグナル生成ログ、decision/status を含む）
    - `order_requests`（発注要求、`order_request_id` を冪等キーとして扱う）
    - `executions`（約定ログ、証券会社提供の約定 ID を冪等キーとして扱う）
  - 監査用インデックス群を定義（status や signal_id、broker_order_id 等での検索を高速化）。
  - `init_audit_schema(conn)` を提供（既存の DuckDB 接続へ監査テーブルを追加、UTC タイムゾーンを強制）。
  - `init_audit_db(db_path)` を提供（監査専用 DB を初期化して接続を返す）。
  - 設計原則の注記（UTC 保存、削除禁止の設計、updated_at はアプリ側で更新等）。

- データ変換ユーティリティ
  - `_to_float`, `_to_int` を実装。無効値や変換失敗時は `None` を返す。
  - `_to_int` は "1.0" のような浮動小数文字列を適切に整数変換し、小数部が 0 以外の場合は None を返して誤切り捨てを防止。

### Notes
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN（J-Quants リフレッシュトークン）
  - KABU_API_PASSWORD（kabuステーション API パスワード）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知用）
- デフォルトやオプションについては `kabusys.config.Settings` を参照してください。
- 現時点では `strategy`, `execution`, `monitoring` の実装はプレースホルダ（空）です。戦略ロジックや発注実行・監視の実装は今後追加予定です。
- 監査ログは削除しない前提で設計されているため、消去操作は現行実装で行わないでください。

### Known limitations / TODO
- J-Quants API クライアントは urllib を使用する低レベル実装です。将来的に requests / httpx 等への移行検討。
- トークンキャッシュはモジュールレベルの単純キャッシュ。マルチプロセスや分散環境では追加の考慮が必要。
- テスト用フック（モック可能な HTTP 層、DB の DI 等）を拡充する予定。
- monitoring / execution の実装（発注送信、ステータス管理、Slack 通知等）は未実装。

---

（以降のリリース履歴はここに追加してください）