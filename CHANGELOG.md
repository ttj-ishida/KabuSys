# Changelog

すべての注目に値する変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従って管理しています。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-16
初回リリース

### Added
- パッケージ基盤
  - パッケージルートとバージョン管理を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を追加。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を基準に探索）。
  - .env/.env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプション）。
  - Bash 形式の export KEY=val、シングル/ダブルクォート内でのエスケープ、インラインコメント取り扱い等に対応した堅牢なパーサを実装。
  - 必須環境変数取得ヘルパー _require() と Settings クラスを提供。
    - J-Quants / kabu / Slack / DB パス等のプロパティ（例: jquants_refresh_token, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH など）。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証ロジックを実装（有効値チェック、エラー報告）。
  - Path を返す DB 設定（duckdb, sqlite）の展開処理を提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）, 財務データ（四半期 BS/PL）, JPX マーケットカレンダーを取得するクライアントを実装。
  - レート制限を守る固定間隔スロットリング実装（デフォルト 120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）を実装。429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized を検出した場合、リフレッシュトークンで id_token を自動再取得して 1 回リトライする機構。
  - ページネーション対応（pagination_key を用いた続き取得）をサポート。
  - 取得時刻（fetched_at）を UTC ISO 形式で記録し、look-ahead bias を防止するトレーサビリティを確保。
  - DuckDB への保存関数を提供（idempotent に ON CONFLICT DO UPDATE を使用）。
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
  - 型変換ユーティリティ _to_float, _to_int を実装（不正値・空値に対して安全に None を返す）。

- DuckDB スキーマ（kabusys.data.schema）
  - DataSchema に基づく多層テーブル定義（Raw / Processed / Feature / Execution）を実装。
  - raw_prices, raw_financials, raw_news, raw_executions など Raw 層のテーブル定義。
  - prices_daily, market_calendar, fundamentals, features, ai_scores 等の Processed/Feature 層定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層定義。
  - パフォーマンスを考慮したインデックス群を定義（頻出クエリパターンに合わせたインデックス）。
  - init_schema(db_path) により冪等的にテーブルとインデックスを作成する初期化処理を提供。
  - get_connection(db_path) で既存 DB への接続を取得するユーティリティを提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL のエントリポイント run_daily_etl を実装。
    - 処理フロー: カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック。
    - 各ステップは独立したエラーハンドリング（1 ステップ失敗でも他ステップは継続）。
  - 差分更新サポート:
    - DB の最終取得日を基に差分のみを取得するロジック（最小データ開始日 _MIN_DATA_DATE）。
    - backfill_days による後出し修正吸収（デフォルト 3 日）。
    - 市場カレンダーを先読みして営業日調整を行う（lookahead デフォルト 90 日）。
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl を提供（取得数・保存数を返す）。
  - ETLResult データクラスにより実行結果（取得数、保存数、品質問題、エラー）を構造化して返す。
  - 品質チェックの実行フラグ run_quality_checks をサポート。

- 監査ログ（kabusys.data.audit）
  - シグナルから約定に至るトレーサビリティを担保する監査テーブルを追加。
    - signal_events（戦略生成ログ）、order_requests（冪等キー付き発注要求）、executions（約定ログ）。
  - ステータス遷移や制約（limit/stop の価格必須チェック等）を含めた堅牢な DDL を実装。
  - init_audit_schema(conn) / init_audit_db(db_path) により監査テーブルとインデックスを初期化。
  - すべての TIMESTAMP を UTC で保存するために SET TimeZone='UTC' を実行。

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比による急騰・急落）、重複、日付不整合等のチェック機能を実装方針で定義。
  - QualityIssue データクラスを導入し、チェック名・テーブル・重大度・サンプル行等を返却。
  - check_missing_data: raw_prices の OHLC 欠損検出（サンプル最大 10 件）。
  - check_spike: LAG を使った前日比スパイク検出（閾値デフォルト 50%）。
  - 品質チェックは Fail-Fast ではなく全件収集し、呼び出し元が重大度に応じて判断できる設計。

### Changed
- （初回リリースのため履歴なし）

### Fixed
- （初回リリースのため履歴なし）

### Security
- （初回リリースのため履歴なし）

備考
- J-Quants API のレート制御・リトライ・自動トークンリフレッシュは実運用を想定した設計となっていますが、実際のプロダクション運用時はさらに監視やメトリクス、テストでの実検証を推奨します。
- DuckDB のスキーマは冪等に作成されるため、既存 DB との互換性を壊さないよう配慮しています。