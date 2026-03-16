Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-16
--------------------

Added
- パッケージ基盤を実装（初期リリース）
  - パッケージ情報
    - kabusys.__version__ = 0.1.0
    - パッケージ公開モジュール: data, strategy, execution, monitoring（空の __init__ を含む構成）
- 環境変数 / 設定管理（kabusys.config）
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により .env 自動読み込みを実装
  - .env / .env.local を OS 環境変数を保護しつつ読み込む仕組み（.env.local は上書き可能）
  - .env のパースで export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメント等に対応
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - 必須設定取得用の _require() と Settings クラスを提供（J-Quants / kabu API / Slack / DB パス 等）
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーション
  - デフォルトのデータベースパス（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）を提供
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、四半期財務、JPX マーケットカレンダーを取得する関数を実装（ページネーション対応）
  - レートリミッタ（固定間隔スロットリング）で 120 req/min を遵守
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）
  - 401 発生時の自動トークンリフレッシュ（1 回のみ）と id_token キャッシュ共有（ページネーション間）
  - JSON デコードエラーやタイムアウト等の例外処理とログ出力
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
    - 冪等性を考慮して ON CONFLICT DO UPDATE を使用
    - fetched_at を UTC ISO 形式で記録（Z 表記）
    - PK 欠損行のスキップとログ
  - 値変換ユーティリティ（_to_float / _to_int）で型安全に変換し、不正な変換は None を返す
- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを定義
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, CHECK 等）と推奨されるインデックスを定義
  - init_schema(db_path) によりディレクトリ作成 → テーブル・インデックス作成（冪等）
  - get_connection(db_path) を提供（初期化済み接続が不要な場合に使用）
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL のフロー実装（run_daily_etl）
    - 市場カレンダー ETL（先読み lookahead あり）
    - 株価日足 ETL（差分更新 + backfill）
    - 財務データ ETL（差分更新 + backfill）
    - 品質チェック（quality モジュール）実行（オプション）
  - 差分更新ヘルパー（最終取得日の取得、営業日調整、backfill のロジック）
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別ジョブ
  - ETL 実行結果を表す ETLResult データクラス（品質問題・エラー一覧、has_errors 等のヘルパ）
  - 各ステップは独立したエラーハンドリングで、1 ステップ失敗でも残りを継続
- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブルを実装
    - signal_events（戦略生成シグナルログ）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社約定ログ、broker_execution_id を一意キーとして冪等性を担保）
  - テーブル作成順、インデックス、UTC タイムゾーン（SET TimeZone='UTC'）設定を実装
  - init_audit_schema(conn) / init_audit_db(db_path) を提供
- データ品質チェック（kabusys.data.quality）
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）
  - チェック実装（DuckDB SQL ベース）
    - 欠損データ検出（raw_prices の OHLC 欄の NULL 検出、サンプル取得）
    - スパイク検出（前日比の変化率が閾値を超える株価の検出、LAG ウィンドウ利用）
    - （設計上）重複チェックや日付不整合チェックも想定（実装拡張可能）
  - 各チェックは全件収集型（Fail-Fast ではない）で呼び出し側で重大度に応じて判断可能

Notes / Migration
- 初期化
  - DuckDB スキーマは kabusys.data.schema.init_schema(db_path) で作成してください。
  - 監査ログのみを別 DB に分けたい場合は kabusys.data.audit.init_audit_db(db_path) を使用可能。
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings から必須取得するため設定が必要です。
  - 自動 .env 読み込みを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用等）。
- 時刻・タイムゾーン
  - 監査ログテーブルは UTC に固定して保存します（init_audit_schema は SET TimeZone='UTC' を実行）。
  - jquants_client の fetched_at は UTC ISO 形式（Z）で保存します。
- API 利用に関する注意
  - J-Quants へのリクエストは内部でレート制御・リトライ・トークンリフレッシュを行いますが、運用側でも過剰な同時実行は避けてください。
- 品質チェック
  - quality モジュールはチェックごとに severity を持ちます。ETL 実行結果 ETLResult.has_quality_errors を参照して運用ルールを決めてください。

Deprecated
- なし

Removed
- なし

Fixed
- なし

その他
- この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時はコミット履歴・リリース計画に基づいた調整を推奨します。