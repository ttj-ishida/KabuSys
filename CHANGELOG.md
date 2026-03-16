Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

[Unreleased]
------------


[0.1.0] - 2026-03-16
-------------------

Added
- 初回リリース: kabusys パッケージ（日本株自動売買システム）の基盤実装を追加。
  - パッケージメタ:
    - バージョン: 0.1.0（src/kabusys/__init__.py にて定義）。
    - サブパッケージ公開: data, strategy, execution, monitoring。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）。
  - 読み込み順序: OS 環境 > .env.local（上書き） > .env（未設定時にセット）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パーサを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応）。
  - Settings クラスでアプリ設定をプロパティとして提供（必須キー取得で未設定時に ValueError を送出）。
  - 必須設定（プロパティ）例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルトと検証:
    - KABUSYS_ENV の許可値: development, paper_trading, live（不正値は ValueError）。
    - LOG_LEVEL の許可値: DEBUG, INFO, WARNING, ERROR, CRITICAL（不正値は ValueError）。
    - デフォルトの DB パス（DUCKDB_PATH、SQLITE_PATH）は data/ 配下に配置されるよう設定。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装:
    - レート制限: 120 req/min を厳守する固定間隔スロットリング（_RateLimiter）。
    - リトライ: 指数バックオフ付きリトライ（最大 3 回、対象ステータス: 408, 429, 5xx）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有（ページネーション間）。
    - JSON デコードエラーやネットワークエラーのハンドリング。
  - 認証: get_id_token(refresh_token=None) で refresh_token から idToken を取得（POST）。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes: 株価日足（OHLCV）
    - fetch_financial_statements: 四半期財務（BS/PL）
    - fetch_market_calendar: JPX マーケットカレンダー
  - DuckDB への保存関数（冪等設計、fetched_at を UTC で記録）:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE で保存
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE で保存
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE で保存（HolidayDivision を is_trading_day/is_half_day/is_sq_day にマッピング）
  - 型変換ユーティリティ:
    - _to_float: 空値/不正値は None を返す
    - _to_int: "1.0" のような整数表現の文字列は許容するが、小数部がある場合は None を返す（意図しない切り捨て防止）

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - 3 層データモデルに基づくテーブル定義を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 主要インデックスを定義（頻出クエリ向けに code × date や status 等のインデックスを作成）。
  - init_schema(db_path) で DB ファイル（または ":memory:"）を初期化し接続を返す。get_connection(db_path) で既存 DB へ接続。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL の実装:
    - run_prices_etl, run_financials_etl, run_calendar_etl: 差分取得ロジック（最終取得日から backfill 日数分を再取得）と保存を実装。
    - run_daily_etl: 市場カレンダー取得 → 営業日調整 → 株価・財務 ETL → 品質チェック、を順に実行。各ステップは独立してエラーハンドリング（1ステップ失敗でも他ステップ継続）。
  - デフォルト動作:
    - backfill_days = 3（後出し修正の吸収用）
    - calendar_lookahead_days = 90（市場カレンダーを先読み）
  - ETLResult データクラス（処理結果/品質問題/エラー集計）を追加。has_errors / has_quality_errors 等のプロパティを提供。
  - 市場カレンダーに基づく営業日調整 helper（_adjust_to_trading_day）を実装（最大 30 日遡る）。

- 監査ログ（src/kabusys/data/audit.py）
  - シグナル→発注→約定のトレーサビリティ用テーブルを追加:
    - signal_events, order_requests（冪等キー order_request_id）, executions（broker_execution_id を一意に扱う）
  - すべての TIMESTAMP を UTC で保存する方針を反映（init_audit_schema で SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn), init_audit_db(db_path) を提供。

- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の必須カラム（open/high/low/close）欠損を検出（重大度: error）。
    - check_spike: 前日比スパイク検出（LAG を使った前日比、デフォルト閾値 50%）。
  - 各チェックは問題のサンプル行（最大 10 件）を返し、呼び出し元が重大度に応じて対応を決定する設計。

Other
- 各モジュールに詳細なドキュメンテーション文字列と設計方針を追加（API レート制御、リトライ、冪等性、監査/トレーサビリティ、UTC 保存など）。
- ログ出力と warning の利用により運用時の可観測性を強化。

Notes / 今後の想定
- strategy/ execution/ monitoring サブパッケージはエントリポイントを用意済み（__init__.py）が、戦略ロジックや実際のブローカー連携実装は別途実装することを想定。
- 実運用では J-Quants / 証券会社の資格情報 (refresh token / API password 等) を適切に管理してください（.env 例の整備を推奨）。
- テスト時に自動 .env ロードを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD を利用できます。

[0.1.0]: https://example.com/release/0.1.0