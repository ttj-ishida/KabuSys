# Changelog

すべての注目すべき変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

最新版: 0.1.0 (初回リリース)

---

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システム (KabuSys) の基盤機能を提供する最初の実装を追加しました。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py にパッケージ名とバージョン（0.1.0）を定義。モジュール公開対象として data, strategy, execution, monitoring を設定。

- 環境設定 / ロード
  - src/kabusys/config.py
    - .env、.env.local、および OS 環境変数からの設定読み込みを実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により、自動読み込みを CWD に依存せずに行う。
    - export KEY=val 形式やクォート・エスケープ、行コメントの取り扱いに対応した .env パーサを実装。
    - 自動ロード無効化環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、J-Quants/J-Quants リフレッシュトークン、kabuステーション API、Slack、DB パス、実行環境 (development/paper_trading/live) とログレベルの検証付きプロパティを公開。
    - デフォルト値（例: KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）を設定。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - J-Quants API への HTTP クライアントを実装（株価日足、財務データ、マーケットカレンダー取得）。
    - レート制限対応（固定間隔スロットリング: 120 req/min を想定）を _RateLimiter で実装。
    - 再試行（指数バックオフ、最大 3 回）・ステータスコード（408, 429, 5xx）に対するリトライ処理を実装。
    - 401 Unauthorized を受けた場合、自動でリフレッシュ（get_id_token）して 1 回だけ再試行するロジックを実装。
    - ページネーション対応（pagination_key を利用）を実装。
    - 取得時刻 (fetched_at) を UTC ISO8601 で付与（Look-ahead bias 対策／トレーサビリティ）。
    - DuckDB へ保存するための冪等的な保存関数を実装（ON CONFLICT DO UPDATE を利用）:
      - save_daily_quotes -> raw_prices に保存
      - save_financial_statements -> raw_financials に保存
      - save_market_calendar -> market_calendar に保存
    - 型変換ユーティリティ (_to_float, _to_int) を用意し、受信データの堅牢な取り扱いを実現。

- DuckDB スキーマ定義と初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution 層のテーブル DDL を定義。
    - prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, signals, orders, trades, positions, portfolio_performance などのテーブルを含む包括的なスキーマ。
    - 頻出クエリ向けのインデックス定義を含む（例: code × date、status インデックス等）。
    - init_schema(db_path) でデータベースファイルの親ディレクトリ自動作成、テーブル作成を行う（冪等）。
    - get_connection(db_path) で既存接続を取得。

- ETL パイプライン
  - src/kabusys/data/pipeline.py
    - 日次 ETL パイプライン run_daily_etl を実装（市場カレンダー、株価、財務、品質チェック）。
    - 差分更新ロジック: DB の最終取得日を参照し、デフォルトは営業日 1 日分の差分更新。backfill_days により直近数日を再取得して後出し修正を吸収。
    - calendar の先読み（デフォルト 90 日）をサポートし、営業日調整に使用。
    - 各ステップは個別にエラーハンドリングされ、1 ステップ失敗でも他ステップは継続（全エラーを収集して ETLResult に格納）。
    - ETLResult データクラスを導入し、実行結果（取得数、保存数、品質問題、発生エラー）を構造化して返却。
    - 個別ジョブ run_prices_etl / run_financials_etl / run_calendar_etl を提供。

- 監査ログ（トレーサビリティ）スキーマ
  - src/kabusys/data/audit.py
    - signal_events, order_requests, executions テーブルを定義する監査ログ DDL を実装。
    - 発注の冪等性を担保する order_request_id、broker_execution_id による重複排除を設計。
    - すべての TIMESTAMP を UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）。
    - init_audit_schema(conn) / init_audit_db(db_path) を提供。

- データ品質チェック
  - src/kabusys/data/quality.py
    - 欠損データ検出（raw_prices の OHLC 欄）を実装（check_missing_data）。
    - スパイク検出（前日比の絶対変動 > 閾値、デフォルト 50%）を実装（check_spike）。
    - QualityIssue データクラスを提供し、各チェックは複数の問題を返す（Fail-Fast ではなく全件収集）。
    - DuckDB を用いた SQL ベースの効率的なチェック実装。

### 変更 (Changed)
- （初版のため過去バージョンからの変更は無し）

### 修正 (Fixed)
- （初版のため無し）

### その他 / 注意点 (Notes)
- J-Quants クライアントは標準ライブラリの urllib を使用しており、同期処理／time.sleep ベースのレート制限を行います。大量同時呼び出しや非同期環境での利用時は注意してください。
- .env の自動ロードは開発時に便利な反面、テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化できます。
- schema の初期化は init_schema を呼ぶ必要があります。初回は init_schema() を使用し、その後は get_connection() を使用して既存 DB に接続してください。
- strategy/ execution / monitoring パッケージの __init__.py は雛形のみで、実際の戦略や発注ロジックはまだ実装されていません。
- 品質チェックは ETL の一部として optional（run_quality_checks）にしてあり、重大度に応じて呼び出し元で停止するか警告に留めるかを判断できます。
- DuckDB の ON CONFLICT を用いたアップサートにより冪等性を確保していますが、スキーマ変更を行う際はマイグレーション戦略を検討してください。

### 既知の制限 / TODO（短期）
- テストスイートがこのリポジトリ内に含まれていないため、ユニットテスト／統合テストを追加する必要があります。
- 非同期/並列実行対応（特に API 呼び出しとレート制御）やバックオフ戦略の詳細チューニングが今後の改善点です。
- execution 層（証券会社 API と実際の発注処理）および strategy 層の実装が未実装（雛形のみ）。

---

## 参考: 必須環境変数（本リリース時点）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD (kabuステーション API 用)
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

その他、環境に応じて KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL を設定可能。

---

今後のリリースでは、strategy と execution 層の実装、CI／テストの追加、非同期対応、マイグレーション機能などを予定しています。