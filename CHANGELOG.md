# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従っています。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-16

初回公開リリース。日本株自動売買システムの基盤となる以下の機能を追加しました。

### 追加 (Added)
- パッケージ初期化
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - サブパッケージ公開: data, strategy, execution, monitoring（各 __init__ を用意）。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local または OS 環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - OS 環境変数は protected され、.env.local の上書きを制御。
  - .env パーサー実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行中コメントの扱いに対応）。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得。
    - 必須項目の取得時は未設定だと ValueError を送出。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許可値セットに対するバリデーション）。
    - データベースパスのデフォルト（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）を Path 型で返却。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API からのデータ取得機能を実装:
    - 株価日足 (fetch_daily_quotes)
    - 財務データ（四半期 BS/PL）(fetch_financial_statements)
    - JPX マーケットカレンダー (fetch_market_calendar)
  - 認証: リフレッシュトークンから ID トークンを取得する get_id_token を実装。
  - HTTP ユーティリティ:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装 (_RateLimiter)。
    - リトライロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx）の実装。
    - 401 Unauthorized 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止の allow_refresh フラグ）。
    - ページネーション対応（pagination_key を継続取得）。
    - JSON デコード失敗時の明示的エラー。
  - 取得日時の記録（look-ahead bias 防止のため、fetched_at を UTC タイムスタンプで付与）。
  - DuckDB への保存用関数（冪等性を担保）:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE を用いて保存。
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE を用いて保存。
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE を用いて保存。
  - 型変換ユーティリティ (_to_float, _to_int) を用意（安全な数値変換と空値処理、"1.0" のような文字列処理の仕様を明記）。

- DuckDB スキーマ定義 & 初期化 (src/kabusys/data/schema.py)
  - DataPlatform の三層（Raw / Processed / Feature）＋Execution 層に基づくテーブル定義を追加。
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤー: features, ai_scores
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各列に対する型と CHECK 制約を充実（価格・数量の非負チェック、列の NOT NULL、列間ロジック等）。
  - 頻出クエリのためのインデックスを作成（銘柄×日付、ステータス検索等）。
  - init_schema(db_path) で親ディレクトリ自動作成・DDL 実行して接続を返すユーティリティを追加。
  - get_connection() で既存 DB への接続を返す関数を追加。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL のエントリ run_daily_etl を実装:
    - 処理順: 市場カレンダー ETL → 株価日足 ETL → 財務 ETL → 品質チェック（オプション）
    - 各ステップは独立してエラーハンドリング（1 ステップの失敗が他を停止させない）。
    - backfill_days（デフォルト 3 日）により最終取得日の数日前から再取得し、API 後出し修正を吸収。
    - calendar_lookahead_days（デフォルト 90 日）でカレンダーを先読みし営業日調整に利用。
    - ETLResult データクラスを返し、取得件数・保存件数・品質問題・エラー概要を保持。
  - 個別ジョブのヘルパー:
    - run_prices_etl, run_financials_etl, run_calendar_etl
    - 差分取得のための最終日取得ヘルパー（get_last_price_date 等）。
    - 市場カレンダー未取得時のフォールバックおよび営業日調整機能 (_adjust_to_trading_day)。

- 監査ログ / トレーサビリティ (src/kabusys/data/audit.py)
  - シグナル → 発注要求 → 約定 を UUID で連鎖して完全トレースする監査テーブル定義を追加。
    - signal_events, order_requests (冪等キー: order_request_id), executions
  - order_requests の詳細な制約（limit/stop/market による価格列の必須チェック）やステータス遷移を設計。
  - init_audit_schema(conn) で UTC タイムゾーン設定を行い監査テーブル・インデックスを初期化。
  - init_audit_db(db_path) で専用 DB を作成して初期化するユーティリティを追加。

- データ品質チェック (src/kabusys/data/quality.py)
  - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損を検出。サンプル行と件数を返却。
  - 異常値検出 (check_spike): 前日比の急騰・急落（スパイク）を LAG ウィンドウで検出。デフォルト閾値 50%。
  - 重複・日付不整合等のチェック（設計に基づく実装の土台）。
  - QualityIssue データクラスで検出結果を統一的に表現（check_name, table, severity, detail, rows）。
  - 各チェックは全件収集方式（Fail-Fast ではなく、呼び出し元が重大度に応じて判断）。

### 変更 (Changed)
- （初回リリースにつき、既存機能の変更はなし）

### 修正 (Fixed)
- （初回リリースにつき、バグ修正はなし）

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- J-Quants リクエストのリトライとトークン自動リフレッシュにより、認証周りと再試行を堅牢化。
- .env 読み込み時に OS 環境変数を保護（上書き防止）の配慮。

---

注記:
- 本リリースは「フレームワーク」としての基盤実装に重点を置いています。戦略ロジック（strategy）や実際の証券会社連携（execution）、監視（monitoring）の具象実装は別途実装する想定です。
- ユーザーはまず init_schema() / init_audit_schema() を用いて DuckDB スキーマを初期化し、Settings クラスで必要な環境変数を設定してから ETL/run_daily_etl 等を実行してください。