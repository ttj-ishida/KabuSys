# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-16
初回リリース — 日本株自動売買システムの基盤機能を実装。

### Added
- パッケージ初期化
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - メインサブパッケージとして data, strategy, execution, monitoring をエクスポート。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local を自動読み込みする仕組みを実装。プロジェクトルートは .git または pyproject.toml を基準に探索するため、CWD に依存しない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パーサーは以下をサポート:
    - コメント行・空行スキップ、`export KEY=val` 形式、
    - シングル／ダブルクォートの中のバックスラッシュエスケープ処理、
    - クォートなし値のインラインコメント扱いルール（直前にスペース/タブがある `#` をコメントとして扱う）など。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / データベースパス 等のプロパティを提供。
  - 環境（KABUSYS_ENV）は "development"/"paper_trading"/"live" のみ許容。LOG_LEVEL は事前定義のレベルのみ許容。検証失敗時は ValueError を送出。
  - データベースパスは Path 型で取得（デフォルト: duckdb -> data/kabusys.duckdb, sqlite -> data/monitoring.db）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 通信の基本機能を実装（ベースURL, タイムアウト, JSON デコード）。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter を実装。
  - 再試行戦略: 指数バックオフ、最大 3 回リトライ（ネットワークエラー、HTTP 408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
  - 認証トークン処理:
    - リフレッシュトークンからの id_token 取得（get_id_token）。
    - 401 受信時は id_token を自動リフレッシュして 1 回リトライ（無限再帰を防止）。
    - モジュールレベルの id_token キャッシュを保持し、ページネーション間で共有。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar: ON CONFLICT DO UPDATE を用いた upsert 実装。fetched_at を UTC ISO8601 文字列で記録。
    - PK 欠損行をスキップし、スキップ件数を警告ログ出力。
  - 型変換ユーティリティ _to_float / _to_int を実装（安全な変換・空値処理・小数切捨て回避等）。
  - ログ出力を適切に行い、エラー内容を詳細に記録。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - 3層＋実行層アーキテクチャに基づくテーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに型制約・CHECK 制約・主キーを設定（数値の非負チェック等）。
  - 典型的クエリに対するインデックスを定義（コード×日付スキャン、ステータス検索など）。
  - init_schema(db_path) で親ディレクトリ自動作成、DDL 実行による初期化（冪等）。get_connection() で既存 DB へ接続。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL のエントリ run_daily_etl を実装。処理フロー:
    1. 市場カレンダー ETL（先読み lookahead、デフォルト 90 日）
    2. 株価日足 ETL（差分更新 + backfill、デフォルト backfill_days = 3）
    3. 財務データ ETL（差分更新 + backfill）
    4. 品質チェック（オプション）
  - 差分更新ロジック: DB の最終取得日から未取得分のみを取得。初回は J-Quants の最小データ日（2017-01-01）から取得。
  - backfill により最終取得日から数日前を再取得して API の後出し修正を吸収。
  - ETLResult データクラス: 各ステップの取得数／保存数、品質問題、エラー概要を保持。has_errors / has_quality_errors / to_dict を提供。
  - _adjust_to_trading_day による非営業日の調整（market_calendar を参照し最大 30 日遡る）。
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl を実装。各ジョブは失敗しても他ジョブは継続する堅牢なエラーハンドリング。

- 監査ログ（トレーサビリティ）（src/kabusys/data/audit.py）
  - シグナル→発注→約定のトレーサビリティを担保する監査テーブルを追加:
    - signal_events（戦略が生成したシグナルログ）
    - order_requests（発注要求：冪等キー order_request_id を持つ）
    - executions（証券会社からの約定ログ、broker_execution_id をユニークに保存）
  - 監査用インデックスを用意し、UTC タイムゾーン保存（init_audit_schema は SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。

- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue データクラスを追加（check_name, table, severity, detail, rows）。
  - 実装済チェック:
    - check_missing_data: raw_prices の必須カラム（open/high/low/close）欠損検出（重大度: error）。サンプル行取得と件数集計。
    - check_spike: 前日比による株価スパイク検出（LAG ウィンドウで前日 close を取得、閾値デフォルト 50%）。サンプル行取得と件数集計。
  - チェックは SQL（パラメータバインド）で実行し、Fail-Fast ではなく全問題を収集して返す設計。
  - pipeline.run_daily_etl から品質チェック (quality.run_all_checks) を呼び出す想定（品質問題は ETLResult に格納）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- （該当なし）

Notes
- 主要な設計方針: API レート制限厳守、再試行とトークン自動リフレッシュ、DuckDB への冪等な保存、ETL の差分更新とバックフィル、監査ログによる完全なトレーサビリティ、品質チェックによるデータ品質管理。
- 今後の作業候補:
  - strategy / execution / monitoring モジュールの実装（現在はパッケージ構造のみ準備）。
  - quality モジュールの追加チェック（重複検出、日付不整合等）の実装と run_all_checks の明示的提示。
  - 単体テスト・統合テストの追加と CI パイプライン整備。

---
バージョン番号は src/kabusys/__init__.py の __version__ と一致します。