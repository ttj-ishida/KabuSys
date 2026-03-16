# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。  
過去の変更点はコードベースから推測して記載しています。

全般注記
- 初期リリース v0.1.0 はデータ収集（J-Quants）、DuckDB によるスキーマ定義・永続化、日次 ETL パイプライン、監査ログ（発注→約定のトレーサビリティ）、および基本的なデータ品質チェックを含みます。
- DuckDB をデータストアとして利用する設計です。スキーマ初期化関数（init_schema / init_audit_schema）で必要なテーブルとインデックスを作成します。
- 環境変数管理・自動ロード機構を備え、.env/.env.local をプロジェクトルートから自動読み込みします（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-16
### Added
- パッケージ初期化
  - kabusys パッケージの初期バージョンを追加。__version__ = "0.1.0" を設定。

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを追加。OS 環境変数を保護するための上書き制御（override / protected）を実装。
  - .env のパースは export 句、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなど多様なケースに対応。
  - 必須環境変数を取得する _require()、および Settings クラスを提供。以下の主要な設定プロパティを実装:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/... のバリデーション）
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング (_RateLimiter) を実装。
  - 再試行ロジック（指数バックオフ、最大3回）を追加。HTTP 408/429/5xx をリトライ対象。
  - 401 Unauthorized 受信時は自動的にリフレッシュトークンから id_token を再取得して一度だけリトライ。
  - ページネーション対応（pagination_key を用いて継続取得）を実装。
  - 取得データに fetched_at（UTC）を付与して Look-ahead Bias のトレースを可能にする方針。
  - DuckDB へ保存する冪等的な save_* 関数を提供（INSERT ... ON CONFLICT DO UPDATE を利用）:
    - save_daily_quotes: raw_prices へ保存（PK: date, code）
    - save_financial_statements: raw_financials へ保存（PK: code, report_date, period_type）
    - save_market_calendar: market_calendar へ保存（PK: date）
  - データ型変換ユーティリティ (_to_float, _to_int) を実装（不正値に寛容に None を返す等の挙動を明示）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など多数）。
  - テーブル作成用 DDL をまとめ、init_schema(db_path) でディレクトリ作成→テーブル・インデックス作成→接続返却を行うユーティリティを実装。
  - get_connection(db_path) を提供（既存 DB への接続）。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の実装:
    - 差分更新ロジック（DB の最終取得日を参照し、デフォルトで backfill_days=3 を用いた再取得を行う）。
    - 市場カレンダー（lookahead で先読み）、株価日足、財務データの順に差分取得→保存を行う run_daily_etl() を提供。
    - 各ステップは独立して例外をハンドルし、他ステップの継続を保証（Fail-Fast ではない設計）。
    - ETL 実行結果を ETLResult データクラスで返却（取得件数、保存件数、品質問題、エラーメッセージなどを集約）。
    - 市場カレンダー取得後に対象日を営業日に調整する _adjust_to_trading_day を実装。

- 監査ログ / トレーサビリティ（kabusys.data.audit）
  - シグナル→発注要求→約定までの監査テーブルを別モジュールで定義:
    - signal_events（戦略が生成したシグナルのログ）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（約定ログ。broker_execution_id をユニークに保持）
  - すべての TIMESTAMP を UTC で運用する方針（init_audit_schema で SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供し、既存の DuckDB 接続へ監査テーブルを追加可能。
  - インデックスを用意して検索・キュー処理のパフォーマンスを考慮。

- データ品質チェック（kabusys.data.quality）
  - 品質チェックフレームワークを実装。QualityIssue データクラスで問題を表現（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は除外）。問題があれば severity="error"。
    - check_spike: 前日終値比によるスパイク検出（デフォルト閾値 50%）。
  - DuckDB に対する SQL ベースの効率的なチェックを実行。全件収集（Fail-Fast ではない）設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の必須チェックを Settings._require で行い、機密情報が不足している場合に明確にエラーを出すことで誤設定を早期発見できるようにした。

### Notes / Migration
- 初回使用時は以下を確認してください:
  - 必須環境変数を設定すること:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DuckDB の初期化:
    - data.schema.init_schema(settings.duckdb_path) を呼び出してテーブルを作成してください。
    - 監査ログを別 DB に分ける場合は data.audit.init_audit_db() を使用できます。
  - 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト環境等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### Known limitations / TODO（推測）
- ロギング/メトリクスの集中管理やリトライ/バックオフの可観測性向上は今後の改善候補。
- Kabu ステーション（実際の発注・約定連携）の実装はこのスナップショットでは未実装（kabusys.execution パッケージが空のまま）。
- Slack 通知やモニタリング統合は設定項目はあるが、具体的な通知モジュールは未確認。

---

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/tag/v0.1.0