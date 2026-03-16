CHANGELOG
=========

すべての主要な変更はこのファイルに記録されます。フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

- （なし）

0.1.0 - 2026-03-16
------------------

Added
- 初回リリースを追加。
- パッケージ構成を追加:
  - kabusys (トップレベルパッケージ)
  - サブパッケージ: data, strategy, execution, monitoring（strategy/execution の __init__ はプレースホルダ）
- バージョン情報:
  - __version__ = "0.1.0"
- 環境設定管理:
  - env/.env.local 自動読込機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読込を無効化可能。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - Settings クラスで主要設定をプロパティとして取得可能（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH 等）。
  - KABUSYS_ENV と LOG_LEVEL の入力検証を実装（許容値チェック、無効値は ValueError）。
  - settings インスタンスを公開。

- J-Quants API クライアント (kabusys.data.jquants_client):
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - ページネーション対応（pagination_key の継続取得）。
  - レートリミッタ実装（固定間隔スロットリング, デフォルト 120 req/min）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象、429 の場合は Retry-After を優先）。
  - 401 応答時にリフレッシュトークンで自動的にトークン再取得して 1 回リトライ。
  - id_token のモジュールレベルキャッシュを実装（ページネーション間でトークン共有）。
  - get_id_token() 実装（refresh token から id token を取得）。
  - API レスポンスの JSON デコード失敗時に明瞭なエラーを発生させる。
  - 取得時刻（fetched_at）を UTC で付与する設計（Look-ahead Bias 防止、トレーサビリティ）。

- DuckDB スキーマ管理 (kabusys.data.schema):
  - DataPlatform に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のスキーマ定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを定義。
  - features, ai_scores 等の Feature テーブルを定義。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等の Execution テーブルを定義。
  - 頻出クエリに対するインデックスを複数定義。
  - init_schema(db_path) によりディレクトリ自動作成と DDL 実行（冪等）を行い、DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB へ接続可能。

- データ保存の冪等性:
  - jquants_client 側で DuckDB にデータ保存する際、ON CONFLICT DO UPDATE を使用して冪等性を確保（save_daily_quotes, save_financial_statements, save_market_calendar）。
  - PK 欠損行はスキップし、スキップ件数をログ警告。

- ETL パイプライン (kabusys.data.pipeline):
  - 日次 ETL のエントリポイント run_daily_etl() を実装（市場カレンダー → 株価 → 財務 → 品質チェック）。
  - 差分更新ロジック: DB の最終取得日を元に自動的に取得範囲を算出。バックフィル（日数指定で後出し修正を吸収）対応（デフォルト 3 日）。
  - カレンダーは先読みを行い（デフォルト 90 日）、取得後に営業日調整を行う。
  - 個別 ETL ジョブ run_prices_etl, run_financials_etl, run_calendar_etl を提供。
  - 各ステップは独立してエラーハンドリングし、1 ステップ失敗でも他ステップは継続（エラー情報を ETLResult に集約）。
  - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー一覧などを含む。to_dict() で品質問題をシリアライズ可能）。

- データ品質チェック (kabusys.data.quality):
  - QualityIssue データクラスを実装（check_name, table, severity, detail, rows）。
  - 欠損データ検出（check_missing_data: raw_prices の OHLC 欄の欠損を検出、サンプル出力 & 件数カウント、重大度 'error'）。
  - スパイク検出（check_spike: 前日比の変動率を LAG ウィンドウで評価、閾値デフォルト 50%）。サンプル・カウントを返す。
  - チェック群は Fail-Fast ではなく全件収集する設計。呼び出し側が重大度に応じて判断可能。

- 監査ログ（トレーサビリティ）(kabusys.data.audit):
  - シグナル → 発注要求 → 約定のトレーサビリティを保持する監査テーブルを実装（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとして使用する設計。
  - すべての TIMESTAMP を UTC で保存するように init_audit_schema() が TimeZone='UTC' を設定。
  - 監査テーブル初期化用の init_audit_schema(conn) / init_audit_db(db_path) を提供。
  - 状態遷移や制約（order_type 別チェック、FK、ステータス列など）を詳細に定義。

- ユーティリティ:
  - jquants_client 内で安全な _to_float / _to_int を実装（空値や変換エラーは None、"1.0" のような float 文字列は int 変換を試すが小数部がある場合は None）。
  - pipeline 内でのテーブル存在確認・最大日付取得ユーティリティを実装。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Deprecated
- なし。

Notes / 制約
- 一部モジュール（strategy, execution, monitoring）はまだ具象実装がないため、戦略ロジックや実際の発注実装は今後の追加予定。
- quality モジュールはドキュメントに記載される他のチェック（重複、日付不整合等）を想定しているが、実装状況はモジュール内の実装に依存します（今回提供されたコードには欠損・スパイク検出が明示的に実装されています）。
- DuckDB の SQL 実行はパラメータバインドを使用する設計。大量データや並列処理時の運用は今後の検証が必要。

今後の予定（例）
- strategy / execution の実装（シグナル生成 → 監査ログ → ブローカー発注を結ぶフロー）。
- 追加品質チェック（重複検出、未来日・非営業日データ検出等）の実装とルール化。
- 詳細ドキュメント（DataSchema.md, DataPlatform.md 等）と利用ガイドの整備。