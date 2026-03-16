CHANGELOG
=========

すべての重要な変更は Keep a Changelog に準拠して記載します。  
セマンティックバージョニングを採用します。  

0.1.0 - 2026-03-16
------------------

初回リリース。日本株自動売買システムの骨格となるコア機能（設定管理、データ取得・保存、ETLパイプライン、品質チェック、監査ログ、DBスキーマなど）を実装しました。

Added
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0 を src/kabusys/__init__.py に定義。
  - モジュール公開: data, strategy, execution, monitoring を __all__ に追加（strategy, execution は空パッケージとして準備）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定値を自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト用）。
  - .env のパースを独自実装（コメント、export プレフィックス、クォート／エスケープ対応、インラインコメントの扱い等）。
  - 必須環境変数取得用の _require 関数および Settings クラスを提供。
  - Settings に主要設定プロパティを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト localhost）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL の検証、および is_live/is_paper/is_dev ヘルパー。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本設計: レート制限遵守、リトライ、トークン自動リフレッシュ、ページネーション対応、fetched_at によるトレーサビリティ、DuckDB への冪等保存。
  - レート制御: _RateLimiter による固定間隔スロットリング（デフォルト 120 req/min 相当）。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx を考慮。429 の場合は Retry-After を尊重。
  - 401 受信時は id_token を自動でリフレッシュして 1 回だけ再試行（無限再帰防止）。
  - ページネーション対応のフェッチ関数:
    - fetch_daily_quotes (OHLCV 日次)
    - fetch_financial_statements (四半期 BS/PL 等)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE で保存、fetched_at を記録
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE
  - 型変換ユーティリティ: _to_float, _to_int（不正値は安全に None を返す）。
  - モジュールレベルの ID トークンキャッシュを保持（ページネーション間で共有）。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataPlatform 構想に基づく 3 層（Raw / Processed / Feature）と Execution 層の DDL を定義。
  - テーブル群（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）を実装。
  - 制約、CHECK、PRIMARY KEY、外部キーなどを定義してデータ整合性を確保。
  - よく使うクエリパターンに対応したインデックスを作成。
  - init_schema(db_path) により親ディレクトリ自動作成も含めて DB を初期化（冪等）。
  - get_connection(db_path) を提供（初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL の実装: run_daily_etl をエントリポイントに(calendar → prices → financials → 品質チェックの順)。
  - 差分更新ロジック:
    - DB の最終取得日からの差分取得
    - デフォルトのバックフィル (backfill_days=3) による後出し修正吸収
    - 価格取得は最小取得日 _MIN_DATA_DATE を考慮
  - 市場カレンダーは先読み（lookahead_days=90）で取得し、営業日判定に使用。
  - ページネーション付きの API 呼び出しを利用して全件取得。
  - 各 ETL ステップは独立して例外を捕捉し、1 ステップ失敗でも他は継続する（エラーは結果に集約）。
  - ETLResult データクラスを導入（target_date、fetched/saved カウンタ、品質問題リスト、errors リスト、シリアライズ用 to_dict）。
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別ジョブを実装。

- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 実装済みチェック（SQL ベース、DuckDB 接続を受け取る）:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は許容）。サンプル行を最大 10 件返す。検出時は severity="error"。
    - check_spike: 前日比スパイク検出（デフォルト閾値 50%）。LAG を用いたウィンドウで差分を計算。サンプル行を最大 10 件返す。
  - 設計方針として Fail-Fast ではなく全件収集方式を採用。呼び出し側が重大度（error/warning）に応じて判断する。
  - （パイプラインから run_all_checks を呼ぶ設計を採用。実装はモジュール内に存在する想定）

- 監査ログ（src/kabusys/data/audit.py）
  - シグナル → 発注 → 約定までをトレースする監査スキーマを実装。
  - テーブル:
    - signal_events (戦略が生成したシグナルのロギング)
    - order_requests (発注要求ログ、order_request_id を冪等キーに設定、価格チェック用制約あり)
    - executions (証券会社からの約定ログ、broker_execution_id をユニーク・冪等キーとして保持)
  - ステータス列・エラーメッセージ・created_at/updated_at を整備。
  - 全ての TIMESTAMP は UTC で保存することを保証（init 関数で SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。インデックスもセットアップ。

Changed
- N/A（初回リリースのため履歴なし）

Fixed
- N/A（初回リリースのため履歴なし）

Notes / マイグレーション
- DuckDB 初期化:
  - data.schema.init_schema(settings.duckdb_path) を呼ぶことでスキーマを作成できます。
  - 監査専用 DB を利用する場合は data.audit.init_audit_db() / init_audit_schema() を使用してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID はアプリケーション動作に必須です（Settings._require により未設定時は例外）。
- .env パース注意:
  - export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント（直前が空白/タブの場合）に対応しています。
- API 使用制限:
  - J-Quants API はレート制限 (120 req/min) を守る設計です。カスタムの HTTP クライアント設定が必要な場合は jquants_client を拡張してください。
- 冪等性:
  - データ保存は ON CONFLICT DO UPDATE を利用して冪等化しています。既存レコードの更新ロジックに注意してください。

今後の予定（短め）
- strategy / execution 層の実装拡充（発注ロジック、ブローカー接続）
- 追加の品質チェック（重複検出、将来日付・営業日外の検出等）の実装完了
- CI テスト（API クライアント、ETL パイプライン、品質チェック）の充実
- ドキュメント（DataSchema.md, DataPlatform.md 等）の公開

-----------

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートやユーザー向けドキュメントを作成する際は、追加の設計意図や既知の制限事項を追記してください。