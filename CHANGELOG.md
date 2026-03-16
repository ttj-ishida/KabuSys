# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog のフォーマットに準拠しています。  
初期リリース（0.1.0）として、パッケージのコア機能（設定管理、データ取得・保存、スキーマ初期化、監査ログ、データ品質チェックなど）を実装しています。

## [Unreleased]

## [0.1.0] - 2026-03-16
### 追加 (Added)
- パッケージ初期公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に ["data", "strategy", "execution", "monitoring"] を公開。

- 環境変数 / 設定管理モジュール（kabusys.config）
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートを .git または pyproject.toml から検出し、CWD に依存しない探索を実現。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト用途）。
    - OS 環境変数を保護するための protected キーセットを導入し、.env.local の上書き挙動を制御。
  - .env パーサーの実装:
    - 空行・コメント行（#）を無視。
    - export KEY=val 形式を許可。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく解釈。
    - クォートなしの値でのインラインコメント判定（直前が空白/タブの場合のみ）に対応。
  - Settings クラスを提供し、環境変数の取得・検証をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須値の取得（未設定時は ValueError 発生）。
    - DUCKDB_PATH / SQLITE_PATH の Path 型返却。
    - KABUSYS_ENV（development, paper_trading, live）の検証。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev の補助プロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 主な設計方針: レート制限遵守、リトライ、トークン自動リフレッシュ、Look-ahead バイアス防止のための fetched_at 記録、DuckDB への冪等保存。
  - 機能:
    - ID トークン取得 (get_id_token)：リフレッシュトークンから idToken を POST で取得。
    - 汎用リクエスト実装 (_request):
      - 120 req/min を守る固定間隔スロットリング（_RateLimiter）。
      - リトライ（指数バックオフ、最大 3 回）および 408/429/5xx に対するリトライロジック。
      - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ（allow_refresh により再帰防止）。
      - 429 の Retry-After ヘッダを優先。
      - JSON デコード失敗時は詳細を含む RuntimeError を送出。
    - ページネーション対応のデータ取得:
      - fetch_daily_quotes（株価日足 OHLCV）
      - fetch_financial_statements（四半期 BS/PL）
      - fetch_market_calendar（JPX マーケットカレンダー）
    - モジュールレベルの ID トークンキャッシュを導入し、ページネーション間でトークンを共有。
  - データ保存:
    - DuckDB 接続を受け取り、raw レイヤーのテーブルへ冪等的に保存する関数を提供:
      - save_daily_quotes（raw_prices）
      - save_financial_statements（raw_financials）
      - save_market_calendar（market_calendar）
    - 保存時に fetched_at を UTC タイムスタンプ（ISO 8601 Z 表記）で付与。
    - PRIMARY KEY に対して ON CONFLICT DO UPDATE を利用して重複上書き（冪等性）を確保。
    - PK 欠損行はスキップし、スキップ数をログ出力。

- DuckDB スキーマ定義・初期化モジュール（kabusys.data.schema）
  - DataPlatform の層構造に基づくテーブル定義と初期化機能を実装:
    - Raw Layer（raw_prices, raw_financials, raw_news, raw_executions）
    - Processed Layer（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）
    - Feature Layer（features, ai_scores）
    - Execution Layer（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）
  - 各テーブルに適切な型チェック・制約（CHECK、PRIMARY KEY、FOREIGN KEY）を付与。
  - 頻出クエリに備えたインデックス群を定義。
  - init_schema(db_path) でデータベースファイル（:memory: 対応）を初期化して接続を返す。親ディレクトリ自動作成。
  - get_connection(db_path) で既存 DB への接続（スキーマ初期化は行わない）。

- 監査ログ / トレーサビリティ（kabusys.data.audit）
  - シグナル→発注→約定の完全トレースを目的とした監査テーブル群を実装:
    - signal_events（戦略が生成した全シグナルを記録、棄却・エラーも含む）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社からの約定ログ、broker_execution_id をユニークとして冪等管理）
  - 外部キーは ON DELETE RESTRICT を基本とし、監査ログの削除を防止する設計。
  - 全 TIMESTAMP を UTC で保存するため、init_audit_schema は SET TimeZone='UTC' を実行。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（既存接続への追加と専用 DB 初期化）。

- データ品質チェック（kabusys.data.quality）
  - DataPlatform.md に基づく品質チェック実装:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は対象外）
    - check_spike: 前日比スパイク検出（LAG ウィンドウ、デフォルト閾値 = 50%）
    - check_duplicates: raw_prices の主キー重複検出
    - check_date_consistency: 将来日付チェック、market_calendar と矛盾する非営業日データ検出（market_calendar があれば実行）
  - QualityIssue データクラスを定義し、各チェックは問題をリストで返す（詳細メッセージと最大 10 件のサンプル行を含む）。
  - run_all_checks で全チェックをまとめて実行し、検出された issue を返す。
  - SQL は DuckDB 上で実行され、パラメータバインド（?）を使用しているためインジェクションリスクを低減。

- ユーティリティ関数
  - 型変換補助:
    - _to_float: None/空文字/変換失敗で None を返す安全な float 変換。
    - _to_int: int 変換を試行、失敗時は float 経由で小数部が 0 の場合のみ変換、それ以外は None を返す。
  - 内部 RateLimiter クラス: 固定間隔スロットリングを実装。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 破壊的変更 (Removed / Breaking Changes)
- 初回リリースのため該当なし。

### 注記 (Notes)
- DuckDB のテーブル定義や制約は初期設計に基づくもので、今後の運用やクエリパフォーマンスに応じて調整が想定されます。
- J-Quants API クライアントはネットワーク・HTTP エラーに対して堅牢化されているが、実際の API レスポンスの変更やスキーマ変更があった場合は追加対応が必要です。
- 環境変数の自動読み込みは便利だが、CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して副作用を抑えることを推奨します。

---

参照:
- パッケージの主要モジュール: kabusys.config, kabusys.data (jquants_client, schema, audit, quality), kabusys.strategy, kabusys.execution, kabusys.monitoring (空の __init__ を含む)
- 初期リリース日: 2026-03-16 (この CHANGELOG 作成日)