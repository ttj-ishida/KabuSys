# Changelog

すべての変更点は Keep a Changelog の形式に従い、重要度の高い順に記載しています。このプロジェクトはセマンティックバージョニング（MAJOR.MINOR.PATCH）を採用します。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムの骨格とデータ基盤／監査機能、外部 API クライアント、環境設定周りの実装を含む初期実装。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージの初期化（__version__ = "0.1.0"）。
  - サブパッケージ骨子: data, strategy, execution, monitoring。

- 環境設定/読み込み (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（優先順位: OS 環境変数 > .env.local > .env）。プロジェクトルート検出は .git または pyproject.toml を起点に探索するため、CWD に依存しない実装。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーの実装（_parse_env_line）:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしのインラインコメント処理（'#' の直前がスペース/タブの場合のみコメントとみなす）
  - 必須環境変数取得ヘルパー _require。
  - Settings での各種プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント (kabusys.data.jquants_client)
  - ベース実装:
    - レート制限ガード（120 req/min）を固定間隔スロットリングで実装する _RateLimiter。
    - リトライロジック（指数バックオフ、最大 3 回）。対象: 408, 429, および 5xx 系ネットワークエラー。
    - 401 受信時には ID トークンを自動リフレッシュして 1 回リトライ（無限再帰を防止）。
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間のトークン共有）。
    - JSON デコード失敗時の適切な例外取り扱い。
    - fetch_* 系関数の実装（ページネーション対応、pagination_key を用いた取得ループ）:
      - fetch_daily_quotes (OHLCV)
      - fetch_financial_statements (四半期 BS/PL)
      - fetch_market_calendar (JPX マーケットカレンダー)
    - get_id_token(refresh_token=None)（POST /token/auth_refresh）を実装。

  - DuckDB への保存関数（冪等化を考慮）:
    - save_daily_quotes(conn, records)
      - fetched_at を UTC ISO フォーマットで記録（Look-ahead バイアス防止）。
      - ON CONFLICT DO UPDATE を用いた冪等保存。
      - PK 欠損行のスキップとログ出力。
    - save_financial_statements(conn, records)
      - 同上。主キー (code, report_date, period_type)。
    - save_market_calendar(conn, records)
      - HolidayDivision を元に is_trading_day / is_half_day / is_sq_day を適切に判定して保存。

  - ユーティリティ:
    - _to_float(), _to_int()（変換失敗時は None を返す。_to_int は "1.0" のような文字列を float 経由で安全に変換し、小数部がある場合は None を返す等の厳密な挙動）。

- DuckDB スキーマ定義 / 初期化モジュール (kabusys.data.schema)
  - 3 層（Raw / Processed / Feature）＋ Execution レイヤに基づくテーブル定義を実装。
  - 主なテーブル（CREATE TABLE IF NOT EXISTS）:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）と型付けを含む設計。
  - よく使うクエリ向けのインデックス定義（idx_*）。
  - init_schema(db_path) 実装:
    - db_path の親ディレクトリを自動作成（:memory: は除く）。
    - 全 DDL とインデックスを順序保証のもとに実行して接続を返す。
  - get_connection(db_path) 実装（スキーマ初期化は行わない接続取得）。

- 監査ログ（トレーサビリティ）モジュール (kabusys.data.audit)
  - 監査用テーブル定義（signal_events, order_requests, executions）を実装。
  - 注文要求に対する冪等キー (order_request_id) を明示的に定義。
  - 発注と約定のトレースを UUID 連鎖で追跡するための設計（business_date → strategy_id → signal_id → order_request_id → broker_order_id）。
  - ステータス遷移の列挙や、order_requests のチェック制約（limit/stop/market それぞれの価格必須条件）を実装。
  - init_audit_schema(conn): UTC タイムゾーン設定（SET TimeZone='UTC'）とテーブル／インデックス作成。
  - init_audit_db(db_path): 監査専用 DB の初期化ユーティリティ（親ディレクトリ自動作成）。

### 変更 (Changed)
- 初版リポジトリの設計方針として、以下の運用上の設計原則をコードに反映:
  - API レート制限遵守、リトライ、トークン自動リフレッシュ、UTC による fetched_at/実行時刻保存、DuckDB での冪等性（ON CONFLICT）などを明確に実装。

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 機密情報は環境変数経由で取得する設計（.env 取り扱いはファイル読み込みのみでライブラリ内に平文で埋め込まない前提）。
- OS 環境変数を保護するための読み込み時オプション（protected set）を導入。

### 既知の注意点 / 使用上のメモ
- 必須環境変数が未設定の場合は settings の各プロパティが ValueError を投げます（例: JQUANTS_REFRESH_TOKEN 等）。
- 自動 .env 読み込みをテスト等で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- get_id_token() は内部で _request を POST 呼び出しし、allow_refresh=False に設定しているため再帰的トークンリフレッシュを防止します。
- init_schema()／init_audit_db() は親ディレクトリを自動作成します。":memory:" を渡すことでインメモリ DB を使用可能です。
- DuckDB の SQL 文（ON CONFLICT / CHECK / FOREIGN KEY 等）を利用しているため、将来的に別 DB に移行する場合は DDL の変換が必要になる可能性があります。

---

このリリースはシステムのコアとなるデータ取得・保存・監査基盤を提供します。戦略ロジック（strategy）や取引実行（execution）の具体実装、監視（monitoring）の詳細実装は今後のリリースで追加されます。