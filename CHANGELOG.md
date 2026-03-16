# Changelog

すべての注目すべき変更点を記録します。本プロジェクトは Keep a Changelog のガイドラインに従っています。

## [Unreleased]

## [0.1.0] - 2026-03-16

### 追加 (Added)
- 基本パッケージ導入
  - パッケージ名: kabusys、バージョン 0.1.0。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読込する仕組みを実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメントの扱い（クォート外で # が直前に空白/タブのときはコメントとして扱うなど）。
  - 環境変数保護機能: .env を読み込む際に既存 OS 環境変数を protected として上書き抑止。
  - Settings クラスを導入し、アプリ設定をプロパティ経由で安全に取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得（未設定時は ValueError を送出）。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスと Path 型変換。
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) のバリデーション（許容値チェック）。
    - is_live / is_paper / is_dev のヘルパー。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - ベース URL と API 呼び出しユーティリティ実装。
  - レートリミッタ実装 (_RateLimiter): 固定間隔スロットリングで 120 req/min を遵守。
  - 冪等かつ堅牢なリクエスト処理:
    - 再試行ロジック（最大 3 回、指数バックオフ）。
    - ステータスコード 408/429/5xx に対するリトライ。
    - 429 の場合は Retry-After を優先。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止）。
    - タイムアウトと JSON デコード例外のハンドリング。
  - id_token キャッシュをモジュールレベルで保持し、ページネーション間で共有。
  - トークン取得関数 get_id_token (POST /token/auth_refresh)。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期 BS/PL 相当）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等設計、ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）: fetched_at を UTC ISO 形式で保存。
    - save_financial_statements（raw_financials）: PK 欠損行のスキップログ。
    - save_market_calendar（market_calendar）: HolidayDivision を解釈して is_trading_day/is_half_day/is_sq_day を算出。
  - 型変換ユーティリティ: _to_float, _to_int（エッジケースの扱いを明示）。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - 3 層データモデルを定義: Raw / Processed / Feature（＋Execution 層）。
  - Raw 層: raw_prices, raw_financials, raw_news, raw_executions。
  - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
  - Feature 層: features, ai_scores。
  - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 各テーブルに適切な型チェック・制約 (CHECK、PRIMARY KEY、FOREIGN KEY) を設定。
  - パフォーマンスを考慮したインデックス群を定義（頻出パターンに合わせた複数の INDEX）。
  - init_schema(db_path) によりディレクトリ自動作成とテーブル/インデックスの冪等作成を提供。":memory:" 対応。
  - get_connection(db_path) による既存 DB 接続取得。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL のワークフロー実装:
    1. 市場カレンダー ETL（先読み lookahead）
    2. 株価日足 ETL（差分 + backfill）
    3. 財務データ ETL（差分 + backfill）
    4. 品質チェック（オプション）
  - 差分更新ロジック: DB の最終取得日から不足分のみ取得、バックフィル日数で後出し修正を吸収（デフォルト backfill_days=3）。
  - カレンダー先読みデフォルト 90 日。
  - ETLResult データクラスを導入（取得/保存件数、品質問題、エラー一覧を格納）。ログ・監査に利用可能な to_dict を提供。
  - 個別ジョブ関数:
    - run_prices_etl, run_financials_etl, run_calendar_etl（それぞれ差分判定・API 取得・保存を行う）。
  - run_daily_etl: 各ステップを独立して例外をハンドルし、1ステップ失敗でも他ステップは継続する設計。品質チェックは quality モジュールを利用。

- 監査ログ（Audit）テーブル群 (src/kabusys/data/audit.py)
  - シグナル → 発注要求 → 約定 のトレーサビリティを完全に記録する監査スキーマを実装。
  - テーブル:
    - signal_events（戦略が生成したシグナル。棄却やエラーも記録）
    - order_requests（冪等キー order_request_id を持つ発注要求）
    - executions（証券会社からの実際の約定情報。broker_execution_id をユニーク制約として冪等性担保）
  - created_at / updated_at を含む監査証跡、すべての TIMESTAMP を UTC で運用（init_audit_schema 内で SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供し、既存接続へ冪等的に監査テーブルを追加可能。
  - インデックス: 日付/銘柄検索、ステータス検索、外部結合用索引等を定義。

- データ品質チェック (src/kabusys/data/quality.py)
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 実装されたチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は許容）。
    - check_spike: 前日比スパイク検出（LAG を用いたウィンドウ関数で変動率を計算、デフォルト閾値 50%）。
  - 各チェックはサンプル行（最大 10 件）を返し、Fail-Fast ではなく全件収集する設計。
  - DuckDB を用いた SQL 実行で効率化、パラメータバインドを使用しインジェクション対策。

- ロギング/運用設計
  - 各モジュールで logger を使用した情報・警告・例外ログを出力。
  - API 呼び出しや ETL の各所で情報ログ・警告ログを追加し可観測性を確保。

### 変更 (Changed)
- 該当なし（初期リリース）。

### 修正 (Fixed)
- 該当なし（初期リリース）。

### 廃止 (Deprecated)
- 該当なし。

### 削除 (Removed)
- 該当なし。

### セキュリティ (Security)
- 該当なし。

注記:
- ドキュメント内やコード内に設計原則（Look-ahead Bias 防止、冪等性、UTC 時刻保存、監査不変条件など）が明記されています。運用時は .env.example を参照のうえ必要な環境変数を設定してください。