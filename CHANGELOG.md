# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。形式は "Keep a Changelog" に準拠しています。

## [Unreleased]


## [0.1.0] - 2026-03-16

初回リリース。日本株の自動売買プラットフォームの基盤機能を実装しました。主にデータ取得・保存（DuckDB）・ETL・品質チェック・監査ログに関するモジュールを含みます。

### Added
- パッケージ初期化
  - `kabusys.__init__` を追加。バージョン番号 `0.1.0` と、公開サブパッケージ (`data`, `strategy`, `execution`, `monitoring`) を定義。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む `Settings` を実装。
  - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml を探索）を基に `.env` → `.env.local` の順でロード。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - `.env` パーサ実装: `export KEY=val`、シングル/ダブルクォート、エスケープ、行内コメントなどに対応。
  - OS 環境変数の保護（既存キーを上書きしない／override 時に保護キーを尊重）。
  - 必須キー取得用ヘルパー `_require`（未設定時は ValueError）。
  - 設定プロパティ: J-Quants トークン、kabuAPI 設定、Slack トークン・チャンネル、DuckDB/SQLite パス、環境（development/paper_trading/live）・ログレベルの検証と便利判定プロパティ（is_live/is_paper/is_dev）。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 日足（OHLCV）、四半期財務、JPX マーケットカレンダーを取得する関数を実装（ページネーション対応）。
  - レート制限を厳守する固定間隔スロットリング（120 req/min の `_RateLimiter`）。
  - 再試行（指数バックオフ、最大 3 回）を組み込んだ HTTP 汎用 `_request`。対象ステータス（408/429/5xx）でリトライ、429 の場合は `Retry-After` を優先。
  - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh 制御）。
  - モジュールレベルで ID トークンをキャッシュし、ページネーション間で共有。
  - 取得データを DuckDB に保存する `save_daily_quotes` / `save_financial_statements` / `save_market_calendar` を実装。保存は冪等（ON CONFLICT DO UPDATE）で、`fetched_at` は UTC タイムスタンプで記録。
  - 型変換ユーティリティ（`_to_float`, `_to_int`）により不正値・空値に対処。
  - ロギングを強化（取得件数・保存件数・リトライ情報・警告等）。

- DuckDB スキーマ定義と初期化 (`kabusys.data.schema`)
  - 3層構造（Raw / Processed / Feature）と Execution 層を含む包括的なテーブル定義を実装。
  - Raw: raw_prices / raw_financials / raw_news / raw_executions
  - Processed: prices_daily / market_calendar / fundamentals / news_articles / news_symbols
  - Feature: features / ai_scores
  - Execution: signals / signal_queue / portfolio_targets / orders / trades / positions / portfolio_performance
  - 各テーブルに適切な制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を付与。
  - パフォーマンスを考慮したインデックス群を定義。
  - `init_schema(db_path)`：親ディレクトリ自動作成、DDL を実行してスキーマを初期化（冪等）。
  - `get_connection(db_path)`：既存 DB への接続を返す（初回は init_schema を推奨）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - 日次 ETL のエントリポイント `run_daily_etl` を実装。処理流れ:
    1. 市場カレンダーの先読み取得（デフォルト 90 日の lookahead）
    2. 株価日足の差分取得（最終取得日から backfill 日数分を再取得、デフォルト backfill_days=3）
    3. 財務データの差分取得（同上）
    4. 品質チェック（`kabusys.data.quality` を利用）
  - 差分更新用ヘルパー（最終取得日の取得、営業日調整 `_adjust_to_trading_day` 等）。
  - 各 ETL ステップは独立してエラーハンドリングされ、1 つの失敗が他を止めない設計（エラーは収集して戻り値に格納）。
  - `ETLResult` データクラス: 実行結果・メタ情報（取得数・保存数・品質問題・エラーメッセージ）を一元化。品質問題を辞書化して出力可能。

- 監査ログ（監査トレーサビリティ） (`kabusys.data.audit`)
  - 戦略→シグナル→発注要求→約定のトレースを可能にする監査テーブル群を実装。
  - テーブル: signal_events / order_requests / executions（各テーブルに UUID ベースの主キーや冪等キー、ステータス、created_at/updated_at を含む）。
  - 発注要求には冪等キー（order_request_id）と、order_type に応じた価格チェック制約を追加。
  - すべての TIMESTAMP を UTC で保存すべく、初期化時に `SET TimeZone='UTC'` を実行。
  - インデックス群を追加（ステータススキャンや JOIN を意識）。
  - `init_audit_schema(conn)` / `init_audit_db(db_path)` を提供。

- データ品質チェック (`kabusys.data.quality`)
  - `QualityIssue` データクラスを実装（チェック名・テーブル・重大度・詳細・問題レコードのサンプル）。
  - 実装済みチェック:
    - 欠損データ検出 (`check_missing_data`): raw_prices の OHLC 欠損を検出（volume は除外）。発見時はサンプル最大 10 行と件数を返す。重大度は "error"。
    - スパイク検出 (`check_spike`): 前日比での変動（LAG ウィンドウ関数）を用いて、閾値（デフォルト 50%）を超える急騰/急落を検出。
  - 各チェックは DuckDB 上で SQL により実行し、Fail-Fast ではなく全件収集して戻す設計。
  - 将来日付・重複検出など追加チェックのための設計が整備済み。

- その他
  - コードベースに Strategy / Execution / Monitoring 用のパッケージ（空 __init__ モジュール）を配置し、今後の拡張に備える。
  - ロギングを広範に使用し、ETL の各段階で情報・警告・例外ログを出力。

### Notable design decisions / implementation notes
- J-Quants クライアントは API レート制限（120 req/min）を厳守するための固定間隔スロットリングを採用。短時間のバースト要求には適さない点に注意。
- HTTP のリトライは指数バックオフを採用。429 の場合は `Retry-After` ヘッダを尊重。
- 401 の場合はトークンの自動リフレッシュを行うが、無限ループを避けるためリフレッシュは最大 1 回/呼び出しに制限。
- DuckDB に保存する際は各テーブルで冪等性（ON CONFLICT DO UPDATE）を確保しており、再取得による上書きを許容する設計。
- 監査ログは削除を想定せず（ON DELETE RESTRICT）、完全なトレーサビリティを保持する方針。
- 全ての TIMESTAMP は UTC を基本に扱う（監査ログ初期化で TimeZone を UTC に設定）。

### Fixed
- 初回リリースのため該当なし。

### Changed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---
注: 本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートを作成する際は変更者やコミットログ、PR の説明に基づいて追記・修正してください。