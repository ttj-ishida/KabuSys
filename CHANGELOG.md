CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-16
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの骨組みを追加。
  - パッケージ情報
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - エクスポート: data, strategy, execution, monitoring を公開（__all__）。
  - 環境設定管理 (src/kabusys/config.py)
    - .env ファイルおよび環境変数から設定を自動読み込み（優先順位: OS環境変数 > .env.local > .env）。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の行パーサーは以下をサポート:
      - 空行・コメント行の無視、export KEY=val 形式の対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理
      - 非クォート値におけるインラインコメント判定（直前が空白／タブの場合）
    - _load_env_file の override / protected 引数により OS 環境変数の保護と上書き制御が可能。
    - Settings クラスを提供（settings インスタンスをエクスポート）:
      - J-Quants: jquants_refresh_token（必須）
      - kabuステーション API: kabu_api_password, kabu_api_base_url（デフォルト http://localhost:18080/kabusapi）
      - Slack: slack_bot_token, slack_channel_id（必須）
      - DB パス: duckdb_path（data/kabusys.duckdb）、sqlite_path（data/monitoring.db）
      - システム設定: env (development|paper_trading|live)、log_level（DEBUG/INFO/...）と判定ヘルパー is_live / is_paper / is_dev
  - J-Quants クライアント (src/kabusys/data/jquants_client.py)
    - API 呼び出しのための HTTP ユーティリティを実装。
    - レート制限対応: 固定間隔スロットリングで 120 req/min を順守（内部 RateLimiter）。
    - リトライ機構: 指数バックオフ（最大 3 回）、対象は 408/429/5xx、429 の Retry-After を優先。
    - 401 応答時にリフレッシュトークンで自動的に ID トークンを更新して 1 回だけリトライ。
    - モジュールレベルで ID トークンをキャッシュ（ページネーション間で共有可能）。
    - ページネーション対応のデータ取得関数:
      - fetch_daily_quotes (株価日足 / OHLCV)
      - fetch_financial_statements (四半期 BS/PL 等)
      - fetch_market_calendar (JPX カレンダー: 祝日・半日・SQ)
    - DuckDB へ保存する冪等関数（ON CONFLICT DO UPDATE）:
      - save_daily_quotes -> raw_prices
      - save_financial_statements -> raw_financials
      - save_market_calendar -> market_calendar
    - 型変換ユーティリティ: _to_float, _to_int（入力の頑健なパース）
  - スキーマ管理 (src/kabusys/data/schema.py)
    - DuckDB のスキーマ定義を追加（Raw / Processed / Feature / Execution 層のテーブルを網羅）:
      - Raw: raw_prices, raw_financials, raw_news, raw_executions
      - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature: features, ai_scores
      - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - インデックス定義を追加（典型的なクエリパターン対応: 銘柄×日付、ステータス検索など）。
    - init_schema(db_path) でディレクトリ自動作成後に全 DDL を実行して接続を返す（冪等）。
    - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない点に注意）。
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - 日次 ETL のエントリ: run_daily_etl を実装。処理フロー:
      1. 市場カレンダー ETL（先読み lookahead days）
      2. 株価日足 ETL（差分 + backfill）
      3. 財務データ ETL（差分 + backfill）
      4. 品質チェック（オプション）
    - 差分更新ロジック:
      - DB の最終取得日を元に date_from を自動算出（存在しない場合は 2017-01-01 から）
      - デフォルトの backfill_days = 3 により最終取得日の数日前から再取得して API の後出し修正に対応
      - 市場カレンダーはデフォルト lookahead_days = 90 日先まで取得
    - 各ステップは独立してエラーハンドリングされ、1ステップ失敗でも他のステップは継続（エラーは ETLResult.errors に蓄積）。
    - ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラー等を集約）。
    - run_prices_etl / run_financials_etl / run_calendar_etl を個別に実行可能。
  - 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
    - 監査テーブルを定義: signal_events, order_requests, executions（UUID によるトレーサビリティ階層を意識）。
    - order_request_id を冪等キーとして実装。注文種別ごとのチェック制約（limit/stop/market）を追加。
    - 約定は broker_execution_id をユニーク鍵として冪等保存。
    - init_audit_schema(conn) / init_audit_db(db_path) を提供。全 TIMESTAMP を UTC で保存するために SET TimeZone='UTC' を実行。
    - 関連インデックスを作成（status スキャン、signal_id / order_request_id の結合パフォーマンス向上等）。
  - データ品質チェック (src/kabusys/data/quality.py)
    - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
    - 実装済みチェック（SQL ベース、DuckDB に対して効率的に動作）:
      - check_missing_data: raw_prices の OHLC 欠損検出（volume は対象外）。検出時は severity="error"。
      - check_spike: 前日比での急騰・急落（デフォルト閾値 50%）を検出しサンプルを返す。
    - 仕様: 各チェックは全件収集方式（Fail-Fast ではなく問題を一覧化）、SQL にパラメタバインドを使用している。
  - その他
    - data パッケージのモジュール構成を整備（jquants_client, schema, pipeline, audit, quality 等）。
    - strategy, execution, monitoring のパッケージ初期化ファイルを追加（将来実装のエントリポイント）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 注意事項
- DuckDB の初期化は init_schema を用いること（get_connection は既存 DB への単純接続のみ）。
- 環境変数の必須項目（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）は Settings 経由で参照すると ValueError を投げて明示的に通知されます。
- jquants_client の HTTP 層は urllib を使用しており、タイムアウトや HTTPError を明示的にハンドリングしています。実運用時はネットワーク/認証周りのログを確認してください。
- audit モジュールはトレーサビリティのために監査ログを削除しない前提（ON DELETE RESTRICT）で設計されています。運用時のデータ保持ポリシーに留意してください。

-----------

（今後のリリースでは Unreleased セクションに変更を記載し、リリース時にバージョンと日付を追加してください。）