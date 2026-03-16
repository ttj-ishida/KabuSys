CHANGELOG
=========

すべての注目すべき変更点を記録します。本ドキュメントは「Keep a Changelog」規約に準拠しています。

フォーマット:
- 変更は大分類（Added, Changed, Fixed, Removed, Security 等）で記述します。
- 各リリースはバージョンと日付を付与します。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-16
-------------------

初回公開リリース。日本株自動売買システムの基盤機能群を実装しました。主な追加点は以下の通りです。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開サブパッケージ定義: data, strategy, execution, monitoring）。
  - 空のモジュールプレースホルダ: kabusys.execution, kabusys.strategy, kabusys.monitoring を追加（将来の拡張用）。

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動ロード機能を実装。
    - プロジェクトルート自動検出: 現在ファイル位置から .git または pyproject.toml を探索してプロジェクトルートを特定。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - OS 環境変数を保護する protected 機能（既存の OS 環境変数を上書きしない）。
  - .env パーサーの拡張:
    - export KEY=val 形式のサポート。
    - シングル／ダブルクォートのエスケープ処理に対応。
    - インラインコメント取り扱いルール（クォート無しの場合の # の扱い）を実装。
  - Settings クラスを導入し、アプリ設定をプロパティ経由で提供:
    - J-Quants / kabuステーション / Slack / DBパス（DuckDB, SQLite）などの必須/任意設定。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
    - is_live / is_paper / is_dev のヘルパー。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装（_request）。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - 冪等なトークンキャッシュと自動リフレッシュ（401 受信時に1回リフレッシュして再試行）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。429 の場合は Retry-After を優先。
    - ページネーション対応（pagination_key を利用して全件取得）。
    - JSON デコードエラーやネットワークエラーの扱いを明確化。
  - データ取得関数を実装:
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等）を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を用いて重複を排除し更新する実装。
    - fetched_at を UTC ISO8601 で記録し、Look-ahead バイアス対策を意識したトレーサビリティ確保。
  - 型変換ユーティリティ:
    - _to_float / _to_int: 安全な変換ロジック（空値や不正フォーマットは None、"1.0" 等の float 文字列対応、非整数の切り捨て回避など）。

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - DataPlatform 構成に基づく 3 層（Raw / Processed / Feature）+ Execution 層のテーブル群を DDL で定義。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 多数の CHECK 制約・PRIMARY KEY を付与し、データ整合性を確保。
  - インデックス定義（頻出クエリに合わせたインデックス）を追加。
  - init_schema(db_path) によりディレクトリ自動作成→DDL 実行→DuckDB 接続返却。get_connection() も提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ベースの ETL（run_prices_etl, run_financials_etl, run_calendar_etl）を実装。
    - DB の最終取得日を基に date_from を自動算出（backfill_days による再取得対応）。
    - calendar は lookahead（デフォルト 90 日）で先読みして営業日判定に利用。
    - 各 ETL は取得→save_*（冪等保存）を行う。
  - 日次統合エントリ run_daily_etl を実装:
    - カレンダー→価格→財務→オプションで品質チェックの順で実行。
    - 各ステップは独立してエラーハンドリング（1ステップ失敗でも残り継続）。
    - 結果を ETLResult dataclass に集約（取得数/保存数、品質問題、エラー一覧など）。
  - DB 存在確認 / 最大日付取得ユーティリティ（_table_exists, _get_max_date, get_last_price_date 等）。
  - 営業日調整ヘルパー（_adjust_to_trading_day）: 非営業日の場合に直前の営業日に調整。

- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定 のトレーサビリティを保持する監査スキーマを追加。
    - signal_events（戦略が生成するすべてのシグナルの記録）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社からの約定ログ、broker_execution_id を冪等キーとして扱う）
  - 各種チェック制約（注文タイプに応じた価格必須チェック等）、FK、UTC タイムゾーン設定（SET TimeZone='UTC'）を実装。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。
  - 監査用インデックス群を追加（signal や order の検索高速化）。

- データ品質チェック（kabusys.data.quality）
  - QualityIssue dataclass を導入（check_name, table, severity, detail, rows）。
  - 以下のチェックを実装（DuckDB SQL による実装）:
    - check_missing_data: raw_prices の OHLC 欄の欠損検出（サンプル行取得、件数カウント、severity=error）
    - check_spike: 前日比スパイク検出（LAG を用いた前日比の絶対値が閾値を超えるものを検出）
  - 各チェックはサンプル行（最大 10 行）を返し、Fail-Fast ではなく問題を集めて戻す設計。

Changed
- （該当なし — 初回リリース）

Fixed
- （該当なし — 初回リリース）

Removed
- （該当なし — 初回リリース）

Security
- J-Quants トークンを取り扱う実装:
  - トークンはモジュールレベルでキャッシュし、401 でのみ自動リフレッシュ（無限再帰防止のため allow_refresh フラグを使用）。
  - .env 読み込みで OS 環境変数を保護する仕組みを用意（意図せぬ上書きを防止）。

Notes / 実装上の注意
- DuckDB の DDL/インデックスは初期化時に実行されるため、既存データは基本的に保持される想定（冪等 DDL を使用）。
- save_* 関数は ON CONFLICT DO UPDATE を利用して重複を防止するが、PK 欠損行はスキップされる（ログに警告を出す）。
- 日付取り扱いは概ね date / TIMESTAMP を使用し、監査関連では明示的に UTC をセットしている。
- quality.check_spike の閾値デフォルトは 50%（_SPIKE_THRESHOLD = 0.5）。

今後の TODO / 予定（例）
- strategy / execution 層の具体的実装（シグナル生成ロジック、発注ブローカー連携）。
- monitoring（Slack 通知等）や運用監視の実装。
- 追加の品質チェック（重複チェック、将来日付チェック等）の実装拡充。

以上。