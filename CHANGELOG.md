# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-16
初回リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。__version__ = 0.1.0。
  - サブパッケージ骨組み: data, strategy, execution, monitoring（strategy/execution は初期状態では __init__ のみ）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード機能:
    - プロジェクトルートを .git または pyproject.toml を起点に探索して .env / .env.local を読み込む（CWD 非依存）。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - 行内コメント（#）の適切な解釈（クォート外かつ直前が空白/タブの場合など）。
  - 必須項目取得 helper (_require) と環境値検証:
    - KABUSYS_ENV に対する検証 (development, paper_trading, live)。
    - LOG_LEVEL に対する検証 (DEBUG/INFO/WARNING/ERROR/CRITICAL)。
  - 代表的な Settings プロパティを提供:
    - J-Quants / kabu API のトークン・URL、Slack トークン/チャンネル、DB（DuckDB/SQLite）パス等。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装:
    - ベース URL、タイムアウト等を備えた _request()。
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装 (_RateLimiter)。
    - リトライロジック（指数バックオフ、最大 3 回）。対象ステータス: 408/429/5xx。
    - 401 発生時はトークンを自動リフレッシュして1回再試行（無限再帰を防ぐ仕組み）。
    - ページネーション対応（pagination_key を追跡して全ページ取得）。
    - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
    - レスポンス JSON デコードエラー時の明瞭な例外化。
  - 認証補助:
    - get_id_token(refresh_token=None)：リフレッシュトークンから idToken を取得（POST）。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
    - 取得結果は fetched_at を付きで記録可能にする方針（Look-ahead bias 防止のため UTC での時刻付与を設計方針に明記）。
  - DuckDB への保存関数（冪等性を確保）
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT DO UPDATE を用いて重複を排除し、fetched_at を更新。
    - 型変換ユーティリティ _to_float / _to_int を実装（空値や不正値処理、"1.0" のような文字列 float からの安全な int 変換等）。

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく多層（Raw / Processed / Feature / Execution）スキーマ定義を実装。
  - 主なテーブル（抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK 等）と索引（頻出クエリに対する INDEX）を定義。
  - init_schema(db_path)：DB を初期化し全テーブル/インデックスを作成（冪等）。
  - get_connection(db_path)：既存 DB への接続取得。初期化は行わない（初回は init_schema を推奨）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計方針と実装:
    - 差分更新（DB の最終取得日に基づき未取得分のみ取得）。
    - デフォルトのバックフィル単位は営業日ベースで 1 日、backfill_days デフォルト 3 日。
    - 市場カレンダーは先読み（lookahead_days=90 日デフォルト）。
    - 品質チェックは収集型（Fail-Fast ではなく問題一覧を返す）。
    - id_token の注入を可能にしてテスト容易性を確保。
  - ETL の公開 API:
    - run_prices_etl / run_financials_etl / run_calendar_etl：各種差分ETL を実行し (fetched, saved) を返却。
    - run_daily_etl：日次 ETL の統合エントリポイント（カレンダー取得→営業日調整→株価・財務の差分ETL→品質チェック）。
  - ETLResult dataclass を導入:
    - ETL 実行結果（取得数・保存数・品質問題リスト・エラー一覧等）を集約。
    - has_errors / has_quality_errors / to_dict 等のユーティリティを提供。
  - 市場カレンダーに依存した営業日調整ロジック（_adjust_to_trading_day）を実装。
  - DB 存在チェックや最大日付取得のヘルパーを提供。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - 信号→発注→約定のトレースを可能にする監査スキーマを追加。
  - トレーサビリティ設計（business_date → strategy_id → signal_id → order_request_id → broker_order_id）。
  - 主なテーブル:
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求、order_request_id を冪等キーとして実装）
    - executions（約定ログ、broker_execution_id をユニークキーとして冪等性確保）
  - 発注・約定の状態遷移と制約（チェック制約、外部キー）を定義。
  - init_audit_schema(conn) / init_audit_db(db_path)：監査テーブル初期化（UTC タイムゾーン強制）を提供。
  - 監査用インデックスを多数定義（status / signal_id / broker_order_id 等での高速検索を意識）。

- データ品質チェック (src/kabusys/data/quality.py)
  - DataPlatform.md に基づく品質チェックを実装。
  - QualityIssue データクラス（check_name, table, severity, detail, rows）を定義。
  - 実装済みチェック（少なくとも下記を実装）:
    - check_missing_data: raw_prices の OHLC 欠損検出（重大度: error）
    - check_spike: 前日比スパイク検出（LAG を使った SQL 実装、デフォルト閾値 50%）
  - 各チェックは DuckDB 上で SQL を用いて実行し、サンプル行（最大 10 件）を返却。
  - チェックは全件収集アプローチで、呼び出し元（ETL）側で重大度に応じた判断を行える設計。

### 修正 (Changed)
- 初版につき該当なし。

### 削除 (Removed)
- 初版につき該当なし。

### 破壊的変更 (Breaking Changes)
- 初版につき該当なし。

### 備考 (Notes)
- 現状 strategy および execution パッケージはプレースホルダ（将来的な戦略・発注ロジック実装を想定）。
- jquants_client の HTTP 実装は urllib を使用。環境や運用に応じてリトライ・レート制御は設定可能。
- DuckDB スキーマは多くの CHECK 制約・外部キー・インデックスを含むため、既存データベースとのマイグレーション時は注意。
- すべてのタイムスタンプは監査テーブル初期化時に UTC を強制する方針（init_audit_schema 内で SET TimeZone='UTC' を実行）。

--- 
今後のリリースでは、strategy 層の実装、発注エンジン（kabu ステーション連携）、監視（monitoring）や通知（Slack 連携）の具体化、追加の品質チェック・メトリクス出力等を予定しています。