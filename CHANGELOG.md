Changelog
=========
すべての変更は Keep a Changelog 規約に準拠しています。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------

（なし）

[0.1.0] - 2026-03-16
-------------------

初回リリース。日本株自動売買システム "KabuSys" のコア基盤を追加しました。主な追加・設計方針は以下の通りです。

Added
- パッケージ初期化
  - パッケージのエントリポイントを追加（kabusys.__init__、__version__ = "0.1.0"）。
  - サブパッケージ候補を公開（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: __file__ を基点に .git または pyproject.toml を探索してルートを特定。
  - .env パーサ実装:
    - コメント行、export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - override フラグと protected キーセットをサポートし、OS 環境変数を保護して .env.local による上書きを実現。
  - 自動読み込みの無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスを公開（settings）:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティ（必須値は未設定時にエラー）。
    - env（development/paper_trading/live）や log_level のバリデーション。
    - duckdb/sqlite パスの取り扱い（~ 展開）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本機能:
    - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得。
    - ページネーション対応。
    - 取得時刻（fetched_at）を UTC ISO8601 フォーマットで記録（Look-ahead Bias の追跡用）。
  - 信頼性/スロットリング:
    - 固定間隔スロットリング: 120 req/min を守る RateLimiter（_MIN_INTERVAL_SEC）。
    - リトライ: 指数バックオフ最大 3 回（対象 408/429/5xx、429 は Retry-After 優先）。
    - 401 時の自動トークンリフレッシュを 1 回行い再試行（無限再帰防止のため allow_refresh 制御）。
    - モジュールレベルの id_token キャッシュ（ページネーション間で共有）。
  - DuckDB への保存関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - 保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で重複を排除。
    - PK 欠損行はスキップし、ログで警告。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - 3層（Raw / Processed / Feature）＋Execution レイヤーのテーブル定義を追加。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 型・CHECK 制約・PRIMARY KEY を明示的に指定。
  - クエリパターンに基づくインデックスを作成（頻出スキャンやステータス検索向け）。
  - init_schema(db_path) によりディレクトリ自動作成とテーブル作成（冪等）を提供。
  - get_connection(db_path) で接続を返すヘルパ。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の実装（run_daily_etl）:
    - 処理順: カレンダー ETL → 株価 ETL（差分 + backfill）→ 財務 ETL → 品質チェック（オプション）
    - カレンダー先読みデフォルト 90 日（_CALENDAR_LOOKAHEAD_DAYS）。
    - バックフィルデフォルト 3 日（_DEFAULT_BACKFILL_DAYS）で API 後出し修正を吸収。
    - 差分更新: DB の最終取得日を基に自動で date_from を算出（初回ロード時は 2017-01-01 から）。
    - 各ステップは独立して例外処理され、1 ステップ失敗でも他は継続（エラーは ETLResult に収集）。
  - ETLResult データクラス:
    - 取得数・保存数・品質問題・エラー一覧などを保持し、has_errors / has_quality_errors / to_dict を提供。
  - 市場カレンダーに基づく営業日調整 (_adjust_to_trading_day)。

- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定のトレーサビリティを担保する監査用テーブル群を追加。
    - signal_events, order_requests, executions
  - 設計方針:
    - order_request_id を冪等キーとして採用（同一キーの再送で重複防止）。
    - すべての TIMESTAMP は UTC 保存（init_audit_schema で SET TimeZone='UTC'）。
    - FK は ON DELETE RESTRICT（監査ログは原則削除しない）。
    - order_requests の注文タイプ制約（market/limit/stop）と価格チェックを実装。
    - 状態遷移を想定した status 列（pending, sent, filled, ... 等）。
  - 監査用インデックスを追加して検索性能を確保（signal_id、status、broker_order_id 等）。

- データ品質チェック（kabusys.data.quality）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 実装したチェック:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欄の欠損を検出（volume は許容）。
    - スパイク検出 (check_spike): LAG ウィンドウを用いて前日比の急騰/急落（デフォルト閾値 50%）を検出。
    - （設計上）重複チェック、日付不整合チェックも仕様として明記（SQL ベースで拡張可能）。
  - 各チェックは問題をすべて収集して QualityIssue リストを返す（Fail-Fast ではない）。

- ユーティリティ
  - 型変換ユーティリティ: _to_float / _to_int（不正値を安全に None にする）。
  - DuckDB 保存のための行整形・PK チェックログ出力等。

Security
- 認証情報や重要設定は環境変数から読み込む設計（.env の自動ロードを採用するが無効化可能）。
- SQL 実行はパラメータバインド（?）を意識した作りを想定。

Notes / Migration
- 初回実行時は init_schema() を呼び出して DuckDB スキーマを作成してください。
- 監査ログを別 DB に分離する場合は init_audit_db() を使用できます。
- J-Quants の認証には JQUANTS_REFRESH_TOKEN 環境変数が必須です。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければ例外が発生します。
- 自動 .env 読み込みを行いたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Removed
- （なし）

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）