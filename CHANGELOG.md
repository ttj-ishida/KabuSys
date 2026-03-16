# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

全般ルール:
- すべてのバージョンは後方互換性の観点で記載しています。
- 本リリースノートは与えられたコードベースから推測して作成しています。

## [Unreleased]

- (なし)

## [0.1.0] - 2026-03-16

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージ記述: "KabuSys - 日本株自動売買システム"（src/kabusys/__init__.py）

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 自動読み込みの優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルート判定は __file__ を基点に .git または pyproject.toml を探索して行うため、CWDに依存しない。
    - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env の行パーサを実装（export 句、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
  - 環境変数参照ヘルパ Settings を提供（settings オブジェクト）。
    - 必須設定（取得時に未設定なら ValueError）:
      - JQUANTS_REFRESH_TOKEN
      - KABU_API_PASSWORD
      - SLACK_BOT_TOKEN
      - SLACK_CHANNEL_ID
    - デフォルト値:
      - KABU_API_BASE_URL: http://localhost:18080/kabusapi
      - DUCKDB_PATH: data/kabusys.duckdb
      - SQLITE_PATH: data/monitoring.db
    - 環境値検証:
      - KABUSYS_ENV: development | paper_trading | live
      - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
    - ヘルパプロパティ: is_live / is_paper / is_dev

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - ベース機能:
    - 株価日足 (OHLCV)、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得機能を実装。
  - ネットワーク制御:
    - 固定間隔スロットリングによるレート制限 (_RateLimiter、120 req/min を想定)。
    - リトライ戦略（指数バックオフ、最大 3 回）を実装。リトライ対象は 408 / 429 / 5xx、およびネットワークエラー。
    - 429 の場合は Retry-After ヘッダを尊重。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して1回だけ再試行。
    - ページネーション対応（pagination_key を用いた全件取得）。
    - id_token のモジュール内キャッシュを実装（ページネーション間で共有）。
  - DuckDB への保存:
    - save_daily_quotes / save_financial_statements / save_market_calendar：取得レコードを DuckDB に冪等的に保存（ON CONFLICT DO UPDATE を使用）。
    - PK 欠損行はスキップしログ出力。
  - ユーティリティ:
    - _to_float / _to_int の堅牢な変換処理（空値/変換失敗で None、"1.0" のような float 文字列の int 変換ルール等）。
  - ログ出力: 取得件数・保存件数・警告を記録。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - 3層データレイヤ（Raw / Processed / Feature）および Execution 層のテーブル DDL を提供。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（NOT NULL、CHECK、PRIMARY KEY、外部キー）を定義。
  - インデックス定義（頻出クエリパターンを考慮）。
  - 公開 API:
    - init_schema(db_path) : ディレクトリ作成を含む初期化（冪等）。
    - get_connection(db_path) : 既存 DB への接続（スキーマ初期化は行わない）。
  - デフォルト DuckDB パス: data/kabusys.duckdb（Settings 参照）

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新に基づく ETL 実装。
    - 差分単位: デフォルトは営業日単位。
    - backfill_days による再取得（デフォルト 3 日）で API の後出し修正を吸収。
    - 市場カレンダーの先読み (lookahead, デフォルト 90 日)。
    - ページネーション・id_token 注入でテスト容易性を確保。
  - ETLResult dataclass を導入（fetch/save 数、品質チェック結果、エラー集約）。
  - 個別ジョブ:
    - run_calendar_etl / run_prices_etl / run_financials_etl（差分判定、fetch と save を呼び出し、ログ出力）。
  - メイン:
    - run_daily_etl: カレンダー取得 → 営業日調整 → 株価・財務 ETL → 品質チェック（オプション）という順序で安全に実行。各ステップは独立してエラーハンドリング（1ステップ失敗でも他は継続）。
  - 内部ヘルパ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day: 非営業日の調整（market_calendar が存在しない場合はフォールバックして元日付を返す）

- 監査ログ (src/kabusys/data/audit.py)
  - 戦略から約定までを UUID 連鎖でトレースする監査テーブルを定義。
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求ログ、order_request_id を冪等キーに利用）
    - executions（約定ログ、broker_execution_id をユニークキー）
  - すべての TIMESTAMP を UTC で扱う（init_audit_schema は "SET TimeZone='UTC'" を実行）。
  - テーブル作成・インデックス作成 API:
    - init_audit_schema(conn) : 既存 DuckDB 接続に監査テーブルを追加（冪等）
    - init_audit_db(db_path) : 監査専用 DB を作成して初期化
  - 発注／約定ステータスの想定遷移や制約（limit/stop/market のチェック制約等）を明記。

- データ品質チェックモジュール (src/kabusys/data/quality.py)
  - 品質チェック群（欠損・スパイク・重複・日付不整合）を実装するための骨組みを提供。
  - QualityIssue dataclass を定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（サンプル行取得、カウント、severity="error"）
    - check_spike: LAG による前日比スパイク検出（デフォルト閾値 50%）
  - 設計方針: Fail-Fast ではなく全問題を収集して返す。SQL パラメータバインドで実行。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated / Removed / Security
- （初回リリースのため該当なし）

Notes / 使用上のメモ
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます（テストなどで有用）。
- DuckDB 初期化:
  - data.schema.init_schema(settings.duckdb_path) を呼ぶことで全テーブルとインデックスを作成します。
  - 監査ログは data.audit.init_audit_schema(conn) / data.audit.init_audit_db(path) を使用。
- ETL の実行例（推測）:
  - conn = init_schema(settings.duckdb_path)
  - result = run_daily_etl(conn)
  - result.to_dict() で監査用に ETL 結果を取得可能
- ネットワーク挙動:
  - J-Quants API へのリクエストはモジュール内でレート制御・リトライ・トークン自動更新を行うため、呼び出し側はシンプルに fetch_* を呼ぶだけでよい想定。
- データ整合性:
  - DuckDB への保存は ON CONFLICT DO UPDATE により冪等に設計されているため、再実行での二重投入を防止。
- ロケール・タイムゾーン:
  - 監査ログ関連処理は UTC を前提（init_audit_schema が TimeZone を UTC に設定）。

既知の制約・今後の拡張（コードから推察）
- jquants_client は urllib による実装のため、将来的に非同期化（async）や requests へ移行する余地あり。
- quality モジュールはチェックのうち一部（重複、日付不整合）の詳細実装が文書で指示されているが、既存コードはスパイク・欠損のチェックを中心に実装されている。追加チェックの実装が想定される。
- ETL のスケジューリングや監視（Slack 通知など）は Settings に Slack 設定があることから想定されているが、実際の通知フローは別モジュールで実装される可能性あり。

---

この CHANGELOG はコードの実装内容から推測して作成しています。リリースノートやユーザー向けドキュメント作成のため、実際の運用フローや追加要件があれば反映できます。必要であれば英語版やより詳細なマイグレーション手順も作成します。