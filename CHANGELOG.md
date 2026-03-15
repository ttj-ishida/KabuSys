# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。日付はリリース日を示します。

## [0.1.0] - 2026-03-15
初回リリース

### 追加 (Added)
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring
  - 参照ファイル: src/kabusys/__init__.py

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を追加
    - 自動読み込み順序: OS環境変数 > .env.local > .env
    - プロジェクトルートの検出: .git または pyproject.toml を基準に探索（CWD非依存）
    - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env 解析ロジックを実装
    - export KEY=val 形式に対応
    - シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理のサポート
    - コメントの扱い（クォート外の '#' はスペース直前のときのみコメント扱い）
  - Settings クラスを提供（settings インスタンス）
    - J-Quants、kabuステーション、Slack、データベースパス等の設定プロパティ
    - 必須環境変数取得時の検証とエラーメッセージ（_require）
    - env / log_level の検証（許容値の制約）
    - is_live / is_paper / is_dev のユーティリティプロパティ
    - デフォルト値:
      - KABUSYS_ENV: "development"
      - KABUS_API_BASE_URL: "http://localhost:18080/kabusapi"
      - DUCKDB_PATH: "data/kabusys.duckdb"
      - SQLITE_PATH: "data/monitoring.db"

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装
    - ベース URL: https://api.jquants.com/v1
    - レート制限（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）
    - リトライロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx）
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）
    - JSON デコードエラーやネットワークエラーの扱い
  - 認証関数
    - get_id_token(refresh_token: Optional[str]) : リフレッシュトークンから idToken を取得（/token/auth_refresh）
  - データ取得関数（ページネーション対応）
    - fetch_daily_quotes(code?, date_from?, date_to?) : OHLCV（日足）を取得
    - fetch_financial_statements(code?, date_from?, date_to?) : 四半期財務データを取得
    - fetch_market_calendar(holiday_division?) : JPX マーケットカレンダーを取得
    - 取得時に fetched_at を UTC に記録する設計方針を明記（Look-ahead Bias 回避）
  - DuckDB への保存関数（冪等）
    - save_daily_quotes(conn, records) : raw_prices へ INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements(conn, records) : raw_financials へ同様に保存
    - save_market_calendar(conn, records) : market_calendar へ同様に保存
    - PK 欠損行はスキップし、スキップ数を警告ログに出力
  - ユーティリティ
    - _to_float / _to_int: 型変換ユーティリティ（安全な変換と None 処理）
      - _to_int は "1.0" のような文字列は float 経由で変換し、小数部が非ゼロの場合は None を返す

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - 3層データモデルに基づくテーブルを定義（Raw / Processed / Feature / Execution）
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）を多用しデータ整合性を担保
  - 頻出クエリ向けのインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status など）
  - 初期化 API
    - init_schema(db_path) : DB を初期化して全テーブル・インデックスを作成（冪等）
      - db_path の親ディレクトリを自動作成
      - ":memory:" のサポート
    - get_connection(db_path) : 既存 DuckDB へ接続（スキーマ初期化は行わない）

- 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
  - ビジネス要件に基づく監査用テーブルを実装
    - signal_events : 戦略が生成した全シグナル（棄却やエラーも記録）
    - order_requests : 冪等キー（order_request_id）付きの発注要求ログ（limit/stop の CHECK 制約を含む）
    - executions : 証券会社からの約定ログ（broker_execution_id をユニークな冪等キーとして保持）
  - 監査用インデックスを定義（シグナル検索、status スキャン、broker_order_id 検索等）
  - 初期化 API
    - init_audit_schema(conn) : 既存 DuckDB 接続に監査テーブルを追加（UTC タイムゾーンを SET）
    - init_audit_db(db_path) : 監査用 DB を新規作成して初期化
  - 設計上の注意点をドキュメント化（UTC 保存、削除禁止、updated_at はアプリ側で更新など）

### 変更 (Changed)
- 初回リリースのため該当なし

### 修正 (Fixed)
- 初回リリースのため該当なし

### 削除 (Removed)
- 初回リリースのため該当なし

### 既知の注意点 / 移行ガイド
- DB 初期化:
  - 初回は data.schema.init_schema(db_path) を呼んでスキーマを作成してください。
  - 監査ログを別 DB に分離したい場合は data.audit.init_audit_db() を使用してください。既存接続へ追加する場合は init_audit_schema(conn) を呼びます。
- 環境変数ロード:
  - パッケージは起動時にプロジェクトルートを探索して .env / .env.local を自動読み込みします。テストや CI 環境での制御が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants トークン:
  - get_id_token() は settings.jquants_refresh_token を要求します。環境変数 JQUANTS_REFRESH_TOKEN を設定してください。
- ロギングと検証:
  - Settings で KABUSYS_ENV と LOG_LEVEL の値検証を行います。許容される値以外を設定すると ValueError が発生します。

### セキュリティ (Security)
- 初回リリースのため該当なし

---
この CHANGELOG はリポジトリ内の docstring、コメント、関数名、実装ロジックから推測して作成しています。実際の変更履歴やリリースノートとして公開する際は、必要に応じて補足・修正してください。