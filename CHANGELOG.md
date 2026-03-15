# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測した初期リリースの変更点を日本語でまとめたものです。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムの基盤となるモジュール群とデータプラットフォームの初期実装を追加。

### 追加 (Added)
- パッケージとバージョン
  - パッケージ名: kabusys、バージョン 0.1.0 を追加。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - Settings クラスを導入し、環境変数をラップして取得する API を提供。
  - 必須環境変数チェック (例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID) を実装。
  - デフォルト設定:
    - KABUSYS_ENV の既定値は "development"、有効値は {"development", "paper_trading", "live"}。
    - LOG_LEVEL の既定値は "INFO"、有効値は {"DEBUG","INFO","WARNING","ERROR","CRITICAL"}。
    - DUCKDB_PATH の既定値は "data/kabusys.duckdb"、SQLITE_PATH の既定値は "data/monitoring.db"。
  - .env 自動読み込み機能を実装:
    - プロジェクトルートを .git または pyproject.toml から探索して決定。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パーサ:
      - export KEY=val 形式に対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
      - コメント処理（クォート外での '#' の扱いなど）を実装。
    - .env 読み込み時の保護機構（OS 環境変数の上書き防止）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からのデータ取得機能を実装:
    - 日足（OHLCV）取得: fetch_daily_quotes (ページネーション対応)
    - 財務データ（四半期 BS/PL）取得: fetch_financial_statements (ページネーション対応)
    - JPX マーケットカレンダー取得: fetch_market_calendar
  - 認証: リフレッシュトークンから ID トークンを取得する get_id_token を実装。
  - 信頼性・運用機能:
    - レート制限の実装 (_RateLimiter): 固定間隔で 120 req/min（デフォルト）を遵守。
    - リトライロジック: 指数バックオフ、最大 3 回、対象は 408/429 と 5xx、ネットワークエラー対応。
    - 401 応答時の自動トークンリフレッシュ（1 回のみ）と再試行。
    - ID トークンのモジュールレベルキャッシュ（ページネーション間で共有）。
    - JSON デコード例外の明示的エラー化。
    - 取得データに対して fetched_at を UTC タイムスタンプで付与（Look-ahead Bias 防止の注記）。
  - DuckDB への永続化ユーティリティ:
    - save_daily_quotes: raw_prices へ保存（ON CONFLICT DO UPDATE による冪等処理）。
    - save_financial_statements: raw_financials へ保存（冪等）。
    - save_market_calendar: market_calendar へ保存（冪等）。HolidayDivision の解釈（取引日/半日/SQ）を実装。
  - ヘルパー関数: _to_float, _to_int（安全な型変換ロジック）。

- DuckDB スキーマ定義・初期化モジュール (src/kabusys/data/schema.py)
  - Data Lake / Data Warehouse 用のスキーマ（3 層 + 実行層）を定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対する列型・CHECK 制約・PRIMARY KEY を整備。
  - パフォーマンスを考慮したインデックス定義を追加（銘柄×日付検索、ステータス検索等）。
  - init_schema(db_path) を提供。親ディレクトリ自動作成、冪等的にテーブル作成を実行。
  - get_connection(db_path) を提供（既存 DB へのコネクション取得）。
  - ":memory:" によるインメモリ DuckDB のサポート。

- 監査ログ・トレーサビリティモジュール (src/kabusys/data/audit.py)
  - 監査用スキーマを追加（signal_events, order_requests, executions）。
  - トレーサビリティ階層/設計原則をコードに反映:
    - signal_id / order_request_id / broker_order_id による連鎖と永続化。
    - order_request_id を冪等キーとして定義。
    - order_requests の複雑な CHECK 制約（limit/stop/market の条件）を実装。
    - EXECUTIONS に broker_execution_id（証券会社約定ID）をユニークキーとして保持。
    - すべての TIMESTAMP を UTC で保存するため init_audit_schema() 内で SET TimeZone='UTC' を実行。
  - init_audit_schema(conn) と監査専用 DB を初期化する init_audit_db(db_path) を提供。
  - 監査テーブル用の索引を多数追加（ステータス検索、signal_id での結合、broker_order_id 紐付けなど）。

- パッケージ骨子
  - strategy/, execution/, monitoring/ モジュール（パッケージ初期化ファイル）は存在するが、実装は最小限のスケルトンとして追加。

### 変更 (Changed)
- 初版のため該当なし。

### 修正 (Fixed)
- 初版のため該当なし。

### 非推奨 (Deprecated)
- 初版のため該当なし。

### 削除 (Removed)
- 初版のため該当なし。

### セキュリティ (Security)
- 初版のため特記事項なし。認証トークンの取り扱いや自動読み込みの挙動に注意（機密情報は適切に管理すること）。

---

注記:
- strategy, execution, monitoring パッケージは将来的な戦略実装・発注ロジック・監視機能の拡張ポイントとして残されています（現時点では未実装の箇所あり）。
- 実運用前に .env の取り扱い、DB マイグレーション、外部 API の認証情報管理（シークレット管理）を検討してください。