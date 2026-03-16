# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-16

### Added
- パッケージ初版を追加（kabusys 0.1.0）。
  - パッケージルート: src/kabusys/__init__.py（__version__ = "0.1.0"、公開モジュール指定）

- 環境設定／ロード機能（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env のパース強化:
    - "export KEY=val" 形式対応。
    - シングル/ダブルクォート対応（バックスラッシュのエスケープ処理を考慮）。
    - コメント処理（クォート有無での取り扱い差分を配慮）。
  - .env 上書き制御:
    - .env -> .env.local の優先順位。
    - OS 環境変数を保護（protected set）して誤上書きを防止。
  - Settings クラスを提供（settings インスタンス）:
    - J-Quants / kabuステーション / Slack / DB パスなどのプロパティを経由して取得。
    - デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）を提供。
    - env / log_level の入力検証（許容値集合チェック）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティ（_request）:
    - 固定間隔のレートリミッタ実装（120 req/min、スロットリング）。
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx 等を対象）。
    - 429 の場合は Retry-After ヘッダを尊重。
    - HTTP 401 受信時はトークンを自動リフレッシュして一度だけリトライ（無限再帰防止の allow_refresh フラグ）。
    - JSON デコードエラーの明示的なエラー化。
  - get_id_token(refresh_token=None): リフレッシュトークンから ID トークンを取得（POST）。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes: 株価日足（OHLCV）の取得（pagination_key 処理）。
    - fetch_financial_statements: 四半期財務データの取得（pagination_key 処理）。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
  - DuckDB への保存関数（冪等処理: ON CONFLICT DO UPDATE）:
    - save_daily_quotes: raw_prices テーブルへ保存（fetched_at を UTC ISO8601 で記録）。
    - save_financial_statements: raw_financials テーブルへ保存。
    - save_market_calendar: market_calendar テーブルへ保存（HolidayDivision を基に is_trading_day / is_half_day / is_sq_day を算出）。
  - ユーティリティ変換関数:
    - _to_float, _to_int（空値や不正値に対して安全に None を返す。_to_int は "1.0" などを float 経由で変換し、小数部が非ゼロの場合は None を返す）。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - 3 層データモデルの DDL を定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK など）を網羅。
  - クエリパフォーマンスを考慮したインデックス定義群を提供。
  - init_schema(db_path) によりディレクトリ自動作成・テーブル作成を冪等に実行。
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない旨を明記）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL の設計と実装:
    - 差分更新（DB の最終取得日を基に未取得分のみ取得）。
    - backfill_days による後出し修正吸収（デフォルト 3 日）。
    - カレンダー先読み（デフォルト 90 日）。
    - 各ステップは独立してエラーハンドリング（1 ステップ失敗でも他は継続）。
  - ETLResult dataclass を導入（取得数、保存数、品質問題、エラー一覧などを保持）。
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別ジョブ実装（差分計算・API 呼び出し・保存）。
  - run_daily_etl: メインエントリポイント（カレンダー取得 → 営業日調整 → 株価/財務 ETL → 品質チェック）。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date ヘルパーを提供。

- 監査ログ（Audit）機能（src/kabusys/data/audit.py）
  - シグナル〜発注〜約定までを UUID 連鎖で完全にトレースする監査テーブルを定義。
  - テーブル: signal_events, order_requests, executions（各テーブルに厳密な CHECK / FK / 制約を設置）。
  - order_request_id を冪等キーとして扱う設計（重複送信防止）。
  - 全 TIMESTAMP を UTC で保存する（init_audit_schema は SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn)／init_audit_db(db_path) による初期化 API とインデックス群を提供。

- データ品質チェックモジュール（src/kabusys/data/quality.py）
  - QualityIssue dataclass による問題表現（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は対象外）。検出は error として報告。
    - check_spike: 前日比スパイク検出（LAG ウィンドウ関数使用、デフォルト閾値 50%）。
  - 各チェックは問題を全件収集して返す（Fail-Fast ではない）。
  - DuckDB のパラメータバインド（?）を使用した安全な SQL 実行。

- モジュール構成の足がかり
  - src/kabusys/data, src/kabusys/strategy, src/kabusys/execution, src/kabusys/monitoring 等のパッケージをエクスポート（空の __init__ モジュールを含む箇所あり）。将来的な拡張用に名前空間を用意。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- HTTPS 経由で J-Quants API を呼び出す設計。認証トークンは環境変数から取得し、ID トークンはメモリ内キャッシュで共有（必要時に自動更新）して安全性と効率を考慮。

注記
- 本バージョンはライブラリ骨格と主要機能（外部 API 連携、ETL、DB スキーマ、監査、品質チェック）を実装した初版です。ユニットテストや運用向けの補完（リトライポリシーの調整、監視／アラート統合、より詳細なエラーハンドリングなど）は今後の改善項目です。