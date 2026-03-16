# Changelog

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog に準拠しています。
比較的安定した公開バージョンのみをここに記載します。

## [Unreleased]
（現時点のブランチに対する未リリースの変更点やメモを置く場所）

---

## [0.1.0] - 2026-03-16

初期リリース。以下の主要機能・設計を実装しました。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージの基本モジュール構成を追加（data, strategy, execution, monitoring を公開）。
  - strategy/execution サブパッケージのプレースホルダ（初期化ファイル）を配置。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
    - プロジェクトルートを .git または pyproject.toml から探索して決定（__file__基準で探索、CWD非依存）。
  - .env パーサを実装（export KEY=val 形式、シングル/ダブルクォート、エスケープ、行内コメント対応）。
  - Settings クラスを追加し、プロパティ経由で各種設定にアクセス可能に。
    - 必須設定取得時は未設定で ValueError を送出する _require() を提供。
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを実装。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーション実装。
    - duckdb/sqlite のデフォルトパスを指定（例: data/kabusys.duckdb、data/monitoring.db）。

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API からデータ取得するクライアントを実装。
    - 取得対象: 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー。
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装（ページネーション対応）。
  - 認証/トークン管理:
    - get_id_token() 実装（refresh token → idToken）。
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）。
    - 401 受信時はトークン自動リフレッシュを 1 回実施してリトライ（無限再帰を防止）。
  - レート制御・リトライ:
    - 固定間隔スロットリングで 120 req/min を厳守（_RateLimiter）。
    - ネットワーク/サーバーエラーに対する指数バックオフリトライ（最大 3 回）、408/429/5xx を対象。
    - 429 の場合は Retry-After ヘッダを優先して待機時間を決定。
  - HTTP レスポンスの JSON デコード失敗時に明示的なエラーメッセージを出力。

- DuckDB 保存ユーティリティ（冪等保存）
  - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - 保存時に fetched_at を UTC ISO8601 で記録（Look-ahead bias 対策）。
    - INSERT ... ON CONFLICT DO UPDATE による冪等性を確保（重複更新を上書き）。
    - PK 欠損行のスキップとログ出力。

- スキーマ定義・初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層を備えた DuckDB スキーマを定義。
    - raw_prices, raw_financials, raw_news, raw_executions など Raw 層。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed 層。
    - features, ai_scores など Feature 層。
    - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution 層。
  - 各種制約（CHECK, PRIMARY KEY, FOREIGN KEY）とデータ型を明示。
  - よく使うクエリに対するインデックス定義（code/date によるスキャン高速化等）。
  - init_schema(db_path) を実装。親ディレクトリ自動作成、冪等的にテーブル/インデックスを作成。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL パイプライン run_daily_etl を実装（市場カレンダー → 株価 → 財務 → 品質チェック）。
    - 差分更新ロジック: DB の最終取得日を元に未取得分のみを取得。デフォルトバックフィルは 3 日。
    - カレンダーはデフォルトで当日から 90 日先まで先読み（lookahead）。
    - 各ステップは独立したエラーハンドリング（Fail-Fast ではなくエラーを収集して続行）。
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl を提供。
  - ETLResult データクラスを提供：
    - 対象日、取得件数/保存件数、品質問題リスト、発生したエラーメッセージを保持。
    - has_errors / has_quality_errors 等のユーティリティ。

- 品質チェック (kabusys.data.quality)
  - QualityIssue データクラスを実装（check_name, table, severity, detail, rows）。
  - 実装済チェック:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損検出（volume は除外）。
    - スパイク検出 (check_spike): LAG を用いて前日比変動率が閾値（デフォルト 50%）を超えるレコードを検出。
    - （重複・日付不整合チェックについてはモジュール設計に言及。実装拡張の余地あり。）
  - 各チェックは問題のサンプル行（最大 10 件）とカウントを返す。重大度は "error" / "warning"。

- 監査ログ（Audit） (kabusys.data.audit)
  - シグナル → 発注 → 約定 のトレーサビリティを保証する監査スキーマを実装。
    - signal_events, order_requests, executions テーブルを定義。
    - order_request_id を冪等キーとして扱い二重発注を防止。
    - 全 TIMESTAMP を UTC で保存するため init_audit_schema は "SET TimeZone='UTC'" を実行。
    - 各テーブルに created_at/updated_at を設置し監査証跡を保証。
    - 適切な制約・チェック（order_type により limit_price/stop_price の必須制約等）を実装。
    - 監査用インデックスを多数追加（status スキャン、signal_id などの JOIN 最適化）。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- （初期リリースのため該当なし）

---

注記 / 今後の作業候補
- strategy および execution サブモジュールは初期シェルのみで、戦略実装・ブローカー接続ロジックはこれから。
- quality モジュールに重複チェックや将来日付検出など追加チェックを拡張する余地あり。
- jquants_client は urllib を用いた実装。将来的に requests 等へ置換検討（タイムアウト/セッション制御の利便性向上）。
- DuckDB の型やインデックスは実運用データ量に応じてチューニング推奨。
- ドキュメント（DataSchema.md, DataPlatform.md 等）を参照する設計注記がコード内に残っています。実運用用ドキュメントの整備が必要。

必須環境変数の例（設定が足りないと起動時に ValueError を発生させます）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

以上。