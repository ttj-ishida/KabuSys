CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" のフォーマットに準拠しています。  
リリースの概要はコードベースから推測して作成しています。

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-03-16
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージエントリポイントを定義（src/kabusys/__init__.py）。
    - 公開モジュール: data, strategy, execution, monitoring。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート検出は .git / pyproject.toml を基準に行い、CWD に依存しない実装。
  - .env パーサーは export プレフィックス、引用符付き文字列、インラインコメント等に対応。
  - Settings クラスを提供（settings インスタンスをモジュールレベル公開）。
    - 必須環境変数の検証: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値: KABUSYS_API_BASE_URL、DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db
    - KABUSYS_ENV の許容値検証: development / paper_trading / live
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev

- データクライアント: J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得機能を実装。
  - 設計上の特徴:
    - API レート制限を守る固定間隔スロットリング（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx をリトライ対象）。
    - 401 Unauthorized 受信時にリフレッシュトークンで自動的に id_token を取得して 1 回リトライ。
    - id_token のモジュールレベルキャッシュを導入（ページネーション間で共有）。
    - データ取得時に fetched_at を UTC タイムスタンプで付与し、Look-ahead Bias を防止するトレーサビリティを担保。
  - DuckDB への保存関数を実装（冪等性: INSERT ... ON CONFLICT DO UPDATE）。
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型変換ユーティリティ: _to_float / _to_int（堅牢な変換ルール実装）

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - 3層データレイヤ（Raw / Processed / Feature）と実行層のテーブル定義を実装。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - パフォーマンスを考慮したインデックスを複数定義。
  - init_schema(db_path) でデータベースと全テーブルを初期化（冪等、親ディレクトリの自動作成対応）。
  - get_connection(db_path) を提供（既存 DB への接続用）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL のエントリポイント run_daily_etl を実装（市場カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック）。
  - 差分更新ロジック:
    - DB 側の最終取得日から未取得分のみを差分取得する。
    - backfill_days により後出し修正を吸収（デフォルト 3 日）。
    - 市場カレンダーは先読み（lookahead_days デフォルト 90 日）して営業日調整に利用。
  - 各ジョブは独立したエラーハンドリングを行い、1 ステップ失敗でも他を継続する設計（Fail-Fast ではない）。
  - ETL 実行結果を格納するデータクラス ETLResult を提供（品質問題やエラーの収集を構造化）。
  - jquants_client の save_* を使った冪等保存を利用。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - ビジネス日付→戦略→シグナル→発注要求→約定 に至るトレーサビリティ用テーブルを定義。
    - signal_events, order_requests, executions
  - order_request_id を冪等キーとして設計（再送による二重発注防止）。
  - 全 TIMESTAMP を UTC で扱うことを明示（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 監査用インデックスを複数定義。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。

- データ品質チェック (src/kabusys/data/quality.py)
  - 欠損データ検出、スパイク（前日比）検出、重複チェック、日付不整合検出の設計に基づくモジュール。
  - QualityIssue データクラスで問題を表現（check_name, table, severity, detail, rows）。
  - check_missing_data（OHLC 欠損検出）を実装。
  - check_spike（前日比スパイク検出）を実装（デフォルト閾値 50%）。
  - DuckDB への SQL 実行はパラメータバインドを使用してインジェクションリスクを排除。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 認証トークン取り扱いにおいて自動リフレッシュとキャッシュを導入し、無限再帰を避ける設計（allow_refresh フラグ）。
- .env の読み込みで OS 環境変数を保護する protected 引数を導入（.env.local 等で OS 変数を不用意に上書きしない）。

Notes / Implementation details
- J-Quants API のレート制限は 120 req/min。内部で最小間隔を導入してスロットリングを実現。
- HTTP 429 (Too Many Requests) の場合、Retry-After ヘッダーを優先して再試行待機時間を決定。
- DuckDB 側は主キーおよび CHECK 制約を広範に使用してデータ整合性を保つ。
- 日時は可能な限り UTC で保存し、fetched_at / created_at フィールドを利用してデータの取得時点を記録する。
- SQL の実行はパラメータバインド（?）を使うことで安全なクエリを実現。
- コードはモジュール単位で単純な公開 API を提供しており、テスト容易性を考慮して id_token の注入などが可能。

Breaking Changes
- 初回公開のため該当なし。

References
- 各モジュール内の docstring に設計・使用方針が記載されています（例: DataPlatform.md, DataSchema.md を参照する旨のコメント）。

今後の予定（想定）
- strategy / execution / monitoring モジュールの具体実装（現時点では __init__.py のみ存在）。
- 追加の品質チェック（重複・日付不整合チェック等）・監視・アラート通知（Slack 統合など）。
- 単体テスト、CI パイプラインの整備、パッケージング／ドキュメントの充実。