CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

[0.1.0] - 2026-03-16
-------------------

初回リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主要なコンポーネントはデータ取得・格納、ETLパイプライン、監査ログ、品質チェック、環境設定ユーティリティです。

Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring（将来の拡張用プレースホルダ）。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを追加。
  - 自動 .env 読み込み機構:
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索して行う（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
    - OS 環境変数を保護するため protected キー集合を導入。
  - .env パーサを強化:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理に対応。
  - 必須環境変数取得用の _require ユーティリティ。
  - 主要設定プロパティを提供（例: jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id 等）。
  - デフォルト値: KABUSYS_ENV (development), LOG_LEVEL (INFO)、データベースパスのデフォルト（DUCKDB_PATH / SQLITE_PATH）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 通信用のクライアント実装を追加。
  - 特徴:
    - ベースURL: https://api.jquants.com/v1（設定可能）。
    - レート制御: 固定間隔スロットリングで 120 req/min を厳守（_RateLimiter）。
    - リトライロジック: 指数バックオフ、最大 3 回。対象は 408/429/5xx とネットワークエラー。
    - 429 の場合は Retry-After ヘッダを優先。
    - 401 受信時は ID トークンを自動リフレッシュして1回再試行（無限再帰防止）。
    - ID トークンのモジュールレベルキャッシュを導入（ページネーションや複数呼び出しで共有可能）。
    - JSON パース例外の扱い（デバッグ用に先頭部分を含むエラー）。
  - データフェッチ関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務四半期データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
    - 各関数は id_token を注入可能でテスト容易性を確保。
  - DuckDB 保存関数（冪等設計）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 全て ON CONFLICT DO UPDATE を使用して重複を排除
    - fetched_at を UTC ISO フォーマットで記録（Look-ahead Bias を抑制）
  - 値変換ユーティリティ:
    - _to_float, _to_int（文字列・数値の安全な変換、意図しない切り捨てを回避）

- DuckDB スキーマ（kabusys.data.schema）
  - DataPlatform に基づく 3 層 + 実行層のスキーマ定義を追加。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルには適切な型チェック、PRIMARY KEY、FOREIGN KEY 制約を付与。
  - インデックス群を用意（頻出クエリ向け）。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成、DDL 実行、接続を返す（冪等）。
  - get_connection(db_path) を追加（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の実装を追加。
  - 機能:
    - 差分更新（最終取得日からの差分を自動算出）。
    - backfill_days による再取得（デフォルト 3 日）で API の後出し修正を吸収。
    - 市場カレンダーの先読み（デフォルト 90 日）。
    - 取得 → 保存（jquants_client の冪等保存）→ 品質チェック の一連処理。
    - 品質チェックは Fail-Fast ではなく全件収集。重大度に応じて呼び出し元が判断可能。
    - id_token の注入可能設計でテストしやすい。
  - 公開関数:
    - run_prices_etl, run_financials_etl, run_calendar_etl（個別ジョブ）
    - run_daily_etl（統合ジョブ、各ステップは独立して例外捕捉。処理継続を保証）
  - ETLResult データクラスを追加（各ステップの取得数・保存数、品質問題、エラー概要などを保持）。
  - 営業日に調整するヘルパー（_adjust_to_trading_day）を実装。

- 監査ログ（kabusys.data.audit）
  - シグナルから約定までのトレーサビリティを確保する監査用スキーマを追加。
  - トレーサビリティ階層と冪等キー（order_request_id）設計を採用。
  - テーブル:
    - signal_events（戦略が生成した全シグナルを記録）
    - order_requests（発注要求、order_request_id が冪等キー。各種チェック制約あり）
    - executions（証券会社からの約定ログ、broker_execution_id を冪等キーとして管理）
  - 全 TIMESTAMP を UTC 保存（init_audit_schema は SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn)（既存接続へ追加）と init_audit_db(db_path)（監査専用 DB 初期化）を提供。
  - インデックスを整備（検索・キュー処理を想定）。

- データ品質チェック（kabusys.data.quality）
  - DataPlatform に基づく品質チェックモジュールを追加。
  - 実装済みチェック:
    - 欠損データ検出（raw_prices の OHLC 欄）
    - スパイク検出（前日比の絶対変動 > threshold、デフォルト 50%）
    - （設計に重複チェック・日付不整合検出が盛り込まれているが、今回のコードでは主要なチェックを実装）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - DuckDB 上で SQL（パラメータバインド）により効率的に実行。サンプル行を最大 10 件返す。

- ロギングとエラーハンドリング
  - 各処理で logger を使用して情報・警告・例外ログを出力。
  - ETL の各ステップは独立例外処理され、1 ステップの失敗が他を止めない設計。

Security
- ID トークンの自動リフレッシュは 401 の場合に限定して一度のみ行い、無限再帰を防止。
- OS 環境変数はデフォルトで保護され、.env で上書きされない（override の挙動により制御）。
- SQL 実行はパラメータバインド（?）を使用する箇所を想定した設計でインジェクションリスクを低減。

Notes for users / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings._require により必須化。
- DuckDB を利用するため、実行環境に duckdb パッケージが必要。
- デフォルトのデータベースパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- ETL を初回実行する際は schema を init_schema() で初期化してから run_daily_etl() を実行してください。監査ログを別途利用する場合は init_audit_schema() を呼ぶか init_audit_db() を使用してください。
- run_daily_etl はデフォルトで品質チェックを実行し、結果を ETLResult として返します。品質問題はリストで収集され、呼び出し側で対処を行ってください。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）