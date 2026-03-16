# CHANGELOG

すべての notable な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]


## [0.1.0] - 2026-03-16
初回リリース。

### Added
- パッケージ骨組みを追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（src/kabusys/__init__.py）

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む Settings クラスを実装。
  - 自動読み込みロジック:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して自動的に .env/.env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env の読み込みは OS 環境変数を保護する保護機構（protected keys）をサポート。
  - .env パーサ:
    - export KEY=val 形式に対応。
    - シングルクォート/ダブルクォート、およびバックスラッシュエスケープに対応した値パース。
    - インラインコメントの取り扱い（クォートあり/なしの違いを考慮）。
  - 必須設定取得用の _require()、環境値検証（KABUSYS_ENV, LOG_LEVEL）を提供。
  - 設定項目（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - 環境判定ユーティリティ is_live / is_paper / is_dev

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - daily quotes（株価日足）、financial statements（財務データ：四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装。
  - ページネーション対応（pagination_key を用いた自動ページ巡回）。
  - レート制限制御（RateLimiter）を実装し、デフォルトで 120 req/min を保証。
  - リトライ戦略（指数バックオフ、最大 3 回）。リトライ対象は 408/429/5xx、429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized 受信時はリフレッシュトークンを使って id_token を自動リフレッシュし1回だけリトライ。
  - id_token キャッシュをモジュールレベルで保持し、ページネーション間で共有。
  - 保存用関数 save_* を実装して DuckDB へ保存（冪等性を担保する ON CONFLICT DO UPDATE を使用）。
  - レコード保存時に fetched_at を UTC ISO8601 で記録（Look-ahead bias 対策のため取得時刻を保存）。
  - 型変換ユーティリティ _to_float / _to_int を提供（空値・不正値を安全に処理、"1.0" のような float 文字列処理に注意）。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DataPlatform に基づく 3 層（Raw / Processed / Feature）および Execution レイヤーのテーブル定義を追加。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores 等の Feature テーブル。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - 頻出クエリに対するインデックス定義を追加。
  - init_schema(db_path) でディレクトリ自動作成＋テーブル作成を行い、init_schema は冪等（既存テーブルはスキップ）。
  - get_connection(db_path) により既存 DB へ接続可能。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL を実行する run_daily_etl() を実装。
    - 処理フロー: カレンダー ETL → 株価 ETL（差分 + backfill）→ 財務 ETL（差分 + backfill）→ 品質チェック（オプション）
    - 各ステップは独立して例外処理され、1 ステップの失敗が他のステップを止めない設計。
    - デフォルトのバックフィルは 3 日、カレンダー先読みは 90 日。
    - ETLResult データクラスで処理結果（取得数・保存数・品質問題・エラー）を返却。
  - run_prices_etl, run_financials_etl, run_calendar_etl を個別に提供（差分更新ロジック、最終取得日の取得ヘルパーを含む）。
  - カレンダーを先に取得して営業日調整（非営業日の場合は直近の営業日に調整）を行うためのユーティリティを実装。

- 監査ログ（audit）（src/kabusys/data/audit.py）
  - シグナル→発注→約定の一連のトレーサビリティを保持する監査テーブル群を実装。
    - signal_events, order_requests, executions を定義。
  - order_request_id を冪等キーとして使用することで二重発注防止を設計。
  - 全 TIMESTAMP は UTC で保存（init_audit_schema で SET TimeZone='UTC' を実行）。
  - テーブルは削除を想定しない（ON DELETE RESTRICT 等で一貫性を保持）。
  - 監査用インデックスを複数定義。

- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue データクラスを定義し、チェック結果を構造化して返却。
  - 実装済チェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（必須カラムの NULL）。検出時は severity="error"。
    - check_spike: 前日比スパイク検出（LAG を用いた SQL 実装）。デフォルト閾値は 50%。
  - チェックは全件収集方式（Fail-Fast ではない）で、呼び出し側が重大度に応じて対応を決定可能。
  - DuckDB を用いた効率的な SQL ベースのチェック実装、パラメータバインドを使用して SQL インジェクションリスクを低減。

### Changed
- （なし、初回リリースのため過去変更なし）

### Fixed
- （なし、初回リリースのため修正履歴なし）

### Removed
- （なし）

### Security
- HTTP クライアントでのタイムアウト設定やリトライ制御、環境変数保護（.env 上書き除外）など基本的な堅牢性に配慮。

### Notes / Implementation details
- jquants_client の API 呼び出しは urllib を使用して実装されており、JSON デコードエラーや HTTP エラーのラップとログ出力を行う。
- DuckDB 側の INSERT 文は ON CONFLICT DO UPDATE を使用して冪等性を確保（raw レイヤの再取得でも上書きで整合性を保つ）。
- pipeline のデフォルト動作は「差分更新 + 小さなバックフィル（日次の後出し修正吸収）」を想定している。
- quality モジュールでは現時点で主に raw_prices に対するチェックが実装されている（将来的に追加チェックを想定）。

### Breaking Changes
- なし

---

今後の予定（例）
- strategy / execution / monitoring 層の具象実装とテストの追加
- quality チェックの拡充（重複チェック、日付不整合チェックなどの完全実装）
- 単体テスト、統合テスト、CI 設定の追加
- ドキュメント（DataSchema.md, DataPlatform.md 等）の整備とサンプル運用手順の追加

---
脚注:
- バージョンはパッケージ内の __version__="0.1.0" に基づいて作成しています。