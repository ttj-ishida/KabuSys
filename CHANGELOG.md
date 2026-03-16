# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

[Unreleased]: https://example.com/kabusys/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/kabusys/releases/tag/v0.1.0

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買プラットフォームの基盤機能を提供します。

### Added
- パッケージ基盤
  - pakage metadata: `kabusys.__version__ = "0.1.0"` を設定。
  - モジュール公開 API を定義（data, strategy, execution, monitoring）。

- 環境設定 (`kabusys.config`)
  - .env ファイルおよび環境変数からの設定読み込みを実装（自動ロード機能）。
    - プロジェクトルート判定: `.git` または `pyproject.toml` を起点に探索して自動的に .env/.env.local を読み込む。
    - 自動ロード無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサを実装（コメント、`export KEY=val`、シングル/ダブルクォート、エスケープ対応、インラインコメント処理）。
  - .env ロード時の上書き制御と「保護された」OS環境変数の扱いを実装（`.env` → `.env.local` の優先度を維持）。
  - 必須設定取得ヘルパー `_require` を追加（未設定時は例外）。
  - `Settings` クラスを実装し、アプリ設定をプロパティ経由で提供:
    - J-Quants: `jquants_refresh_token`
    - kabuステーション: `kabu_api_password`, `kabu_api_base_url`
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`, `sqlite_path`
    - 実行環境判定・検証: `env`, `log_level`, `is_live`, `is_paper`, `is_dev`
    - `env` / `log_level` は有効値検証を行い不正値で例外を送出。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - ベース実装:
    - API ベース URL、レート制限（120 req/min -> 固定間隔スロットリング）を実装。
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408, 429, 5xx）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）と ID トークンのモジュールレベルキャッシュ（ページネーション間で共有）。
    - JSON デコードエラーやネットワークエラーに対する詳細な例外メッセージとログ。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes (株価日足 OHLCV)
    - fetch_financial_statements (四半期財務データ)
    - fetch_market_calendar (JPX マーケットカレンダー)
    - 取得件数ログ出力、pagination_key による継続取得
  - 認証:
    - get_id_token(refresh_token: Optional) を実装（POST `/token/auth_refresh` を呼ぶ）。
  - DuckDB への保存関数（冪等化）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE により挿入/更新。
      - fetched_at を UTC ISO8601 で記録し Look-ahead Bias のトレーサビリティに配慮。
      - PK 欠損行はスキップし警告ログ出力。
    - save_financial_statements: raw_financials へ冪等保存（PK: code, report_date, period_type）。
    - save_market_calendar: market_calendar へ冪等保存（取引日/半日/SQ 判定処理を含む）。
  - ユーティリティ:
    - 型変換ヘルパー `_to_float`, `_to_int`（安全な変換と不正値時の None 戻し、float 由来の整数処理ロジックを実装）。

- データベーススキーマ (`kabusys.data.schema`)
  - DataSchema.md に基づく多層スキーマを定義（Raw / Processed / Feature / Execution）。
  - DDL 定義（冪等 CREATE TABLE IF NOT EXISTS）:
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリに基づく）。
  - 公開 API:
    - init_schema(db_path) : ディレクトリ自動作成、全テーブルおよびインデックス作成、DuckDB 接続返却（冪等）。
    - get_connection(db_path) : 既存DBへの接続（スキーマ初期化は行わない）。

- 監査ログ（トレーサビリティ） (`kabusys.data.audit`)
  - 監査向けスキーマを実装（signal_events / order_requests / executions）。
    - トレーサビリティ設計（business_date → strategy_id → signal_id → order_request_id → broker_order_id）。
    - order_request_id を冪等キーとし、発注再送時の二重発注防止を想定。
    - 各テーブルに created_at / updated_at を保持（UTC を前提）。
    - order_requests のカラム制約（limit/stop の price 必須条件）やチェック制約を実装。
    - executions は broker_execution_id を外部（証券会社）由来の冪等キーとして保持。
  - インデックスを用意し検索性能を最適化。
  - 公開 API:
    - init_audit_schema(conn) : 既存 DuckDB 接続に監査テーブルを追加（UTC タイムゾーン設定含む）。
    - init_audit_db(db_path) : 監査専用 DB を作成して接続返却。

- データ品質チェック (`kabusys.data.quality`)
  - DataPlatform.md に基づく品質チェック群を実装。
  - チェック項目:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損検出（サンプル行と件数を返す）。
    - 重複チェック (check_duplicates): raw_prices の主キー重複検出。
    - 異常値検出 (check_spike): 前日比スパイク検出（デフォルト閾値 50%）。
    - 日付不整合検出 (check_date_consistency): 将来日付・market_calendar と整合しないデータ検出（テーブル未存在時はスキップ）。
  - 各チェックは QualityIssue データクラスを返却（check_name, table, severity, detail, rows）。
  - 全チェック実行ユーティリティ run_all_checks を提供（全チェックを集約して実行、エラー/警告集計ログ出力）。
  - 実装方針:
    - Fail-Fast ではなく全問題を収集して返す。
    - DuckDB 経由で効率的に SQL を実行、パラメータバインドを使用。

### Changed
- なし（初回公開）

### Fixed
- なし（初回公開）

### Security
- なし（初回公開）

### Notes / Design highlights
- 全てのタイムスタンプは UTC を原則とし、データ取得時刻（fetched_at）や監査ログの時刻を UTC で扱うように設計。
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE）とし、ETL の再実行に耐えるようにしている。
- ネットワーク/API 呼び出しはレート制御・リトライ・トークン自動リフレッシュを組み合わせて堅牢化。
- スキーマに多数の CHECK 制約・外部キー・インデックスを定義し、データ整合性とクエリ性能を両立。

---

今後の例（予定）
- strategy / execution 層の実装充実（リスク管理、ポートフォリオ最適化、発注送信実装）
- モニタリング/アラート（Slack 通知等）の統合
- 単体テスト・統合テストの追加、CI ワークフロー整備

（この CHANGELOG はコードベースからドキュメント化した初期リリースの要約です。必要であれば個別機能ごとに詳細な変更点や使用例を追加します。）