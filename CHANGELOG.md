# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはまだ初期リリースの段階です。

全般的な注意
- バージョンはパッケージ定義 (kabusys.__version__) に合わせています。
- 多くの API/DB 操作は依存注入（conn / id_token 引数）に対応しており、テスト容易性を考慮して設計されています。

## [0.1.0] - 2026-03-16

### Added
- パッケージの初期構成を追加
  - モジュール: kabusys (パッケージルート)、data、strategy、execution、monitoring を公開。
  - バージョン: 0.1.0 を設定。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）。
  - 自動読み込みの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - .env パース機能の強化:
    - コメント行、`export KEY=val` 形式に対応。
    - シングル／ダブルクォート内でのバックスラッシュエスケープ処理をサポート。
    - インラインコメントの取り扱い（クォート無しの際は直前に空白／タブがあればコメントと判断）。
  - 環境変数読み込みの上書き/保護ロジック（OS 環境変数を保護する protected set）。
  - Settings クラスを追加し、必須設定の取得・検証を簡便化:
    - J-Quants / kabu API / Slack / DB パスなどのプロパティを提供。
    - `KABUSYS_ENV`（development/paper_trading/live）と `LOG_LEVEL` の値検証を実装。
    - DB パスのデフォルト (`data/kabusys.duckdb`, `data/monitoring.db`) を提供。

- J-Quants クライアント (`kabusys.data.jquants_client`)
  - API クライアント実装を追加（/v1 ベース URL）。
  - スロットリングによるレート制御: 固定間隔スロットリングで 120 req/min を保証する _RateLimiter。
  - 冪等なトークンキャッシュ（モジュールレベルの ID トークンキャッシュ）とトークン自動リフレッシュ機能。
  - リトライロジックを実装:
    - 最大 3 回リトライ、指数バックオフ、対象ステータスコード（408, 429, 5xx）に対応。
    - 401 受信時は一度トークンをリフレッシュして再試行。
    - 429 の場合は Retry-After ヘッダを優先。
  - ページネーション対応の取得関数を提供:
    - fetch_daily_quotes (株価日足, OHLCV)
    - fetch_financial_statements (四半期財務)
    - fetch_market_calendar (JPX カレンダー)
    - 各取得は取得件数ログを出力し、pagination_key を用いて続き取得。
  - DuckDB への保存関数（冪等）を提供:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT DO UPDATE を利用して重複・差分更新に対応。
    - fetched_at を UTC タイムスタンプで記録（Look-ahead Bias のトレースに有用）。
  - 値変換ユーティリティ: _to_float, _to_int（入力の堅牢なパース、"1.0" 等の扱いに注意）。

- DB スキーマ初期化モジュール (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution の 3 層＋監査向けテーブルを定義。
  - テーブル定義には CHECK 制約・PRIMARY KEY を豊富に付与してデータ整合性を強化。
    - 例: raw_prices の主キー (date, code)、prices_daily の low <= high チェックなど。
  - インデックスを定義し、頻出クエリパターンに対する高速化を考慮。
  - init_schema(db_path) によりディレクトリ自動作成とテーブル初期化（冪等）を実行。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分更新（差分取得 + backfill）を行う ETL 実装。
    - デフォルトの差分単位は営業日1日分、backfill_days=3 を採用して API の後出し修正を吸収。
    - カレンダーは先読み（lookahead_days=90 日）して営業日調整に利用。
  - 個別ジョブ:
    - run_prices_etl, run_financials_etl, run_calendar_etl（それぞれ差分ロジック・保存を実行）。
  - メイン: run_daily_etl
    - 処理順: カレンダー取得 → 営業日調整 → 株価ETL → 財務ETL → 品質チェック（オプション）。
    - 各ステップは独立して例外処理され、1 ステップの失敗で他が停止しない設計（Fail-Fast ではない）。
    - ETLResult データクラスを返却し、取得件数・保存件数・品質課題・エラーメッセージを集約。
    - ロギングで処理サマリを出力。

- 監査ログ（トレーサビリティ）モジュール (`kabusys.data.audit`)
  - シグナル→発注要求→約定の階層的トレーサビリティを記録するためのスキーマを追加。
  - テーブル:
    - signal_events（戦略が生成したシグナルをすべて記録）
    - order_requests（冪等キー order_request_id を持つ発注要求）
    - executions（証券会社由来の約定ログ、broker_execution_id をユニークキーとして冪等性を確保）
  - すべての TIMESTAMP を UTC で保存するように初期化時に SET TimeZone='UTC' を実行。
  - ステータス列と updated_at / created_at を持ち、監査ログは削除しない設計（ON DELETE RESTRICT）。
  - init_audit_schema(conn), init_audit_db(db_path) を提供。

- データ品質チェックモジュール (`kabusys.data.quality`)
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損（open/high/low/close）を検出（欠損は error）。
    - check_spike: 前日比の急騰・急落（スパイク）を検出（デフォルト閾値 50%）。
    - 実装方針: 全件収集（Fail-Fast ではない）、サンプル行取得、SQL のパラメータバインドを使用して安全に実行。
  - pipeline.run_daily_etl から呼び出せる品質チェックの統合。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- 現時点で公開 API キーやトークンの取り扱いに関する特別なセキュリティ修正は無し。
- 設定は環境変数 / .env に依存。`.env` 読み込みの上書き制御や OS 環境変数保護を実装している。

補足・設計上の注意
- J-Quants API 呼び出しは同期ブロッキング（urllib）で実装されているため、大量並列呼び出しが必要な場合は別途非同期化を検討してください。
- DuckDB の SQL 実行は文字列 DDL をそのまま実行するため、テーブル名等は固定で利用する想定です（ユーザー入力等を直接 DDL に流すことは避けてください）。
- audit テーブルは削除しない想定（監査用途）。更新はアプリ側で updated_at を current_timestamp にセットする運用を想定しています。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装強化（現状はパッケージ初期化のみ）。
- 非同期対応やより詳細なエラーメトリクスの追加。
- テストスイート、CI の整備、ドキュメント（DataSchema.md / DataPlatform.md 参照）を公開。

---  

（本 CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。）