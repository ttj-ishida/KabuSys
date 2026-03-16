# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従い、セマンティック バージョニングを採用します。

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システムのコア基盤（設定管理、データ取得／保存、DBスキーマ、監査ログ、データ品質チェック）を実装しました。

### Added
- パッケージ初期化
  - pakage `kabusys` の基本構成を追加（src/kabusys/__init__.py）。__version__ を "0.1.0" に設定し、公開 API モジュール（data, strategy, execution, monitoring）を定義。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に検索。ルートが見つからない場合は自動ロードをスキップ。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - .env のパースは export 書式やシングル/ダブルクォート、インラインコメント、エスケープを考慮。
  - 必須設定の取得ヘルパー _require() を実装。未設定時は明示的に ValueError を送出。
  - 設定オブジェクト Settings を提供。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - 環境判定ユーティリティ: is_live, is_paper, is_dev

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API ベースのクライアントを実装。
    - レート制限: 120 req/min を守る固定間隔スロットリング（内部 RateLimiter）。
    - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回、対象ステータス 408/429/5xx をリトライ。
    - 401 受信時の自動トークンリフレッシュを実装（1 回のみリトライ、無限再帰回避）。
    - id_token のモジュールレベルキャッシュを保持し、ページネーション間で共有。
  - 認証関数:
    - get_id_token(refresh_token=None): リフレッシュトークンから idToken を取得（POST）。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
    - 取得件数ログ出力と pagination_key の重複防止をサポート。
  - DuckDB への保存関数（冪等性を保証: ON CONFLICT DO UPDATE）
    - save_daily_quotes(conn, records): raw_prices への保存。fetched_at を UTC で記録。
    - save_financial_statements(conn, records): raw_financials への保存。
    - save_market_calendar(conn, records): market_calendar への保存。HolidayDivision の解釈を実装。
  - データ変換ユーティリティ:
    - _to_float / _to_int（不正値や空値は None を返す、_to_int は小数部が 0 以外なら None）

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - データレイヤを想定したスキーマを実装（Raw / Processed / Feature / Execution）。
  - 主なテーブル:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, CHECK 等）とパフォーマンスを考慮したインデックス群を定義。
  - 公開 API:
    - init_schema(db_path): DB ファイル作成（親ディレクトリ自動作成） → 全テーブル・インデックス作成（冪等）。
    - get_connection(db_path): 既存 DB への接続（スキーマ初期化は行わない）。

- 監査ログ（Audit）スキーマ（src/kabusys/data/audit.py）
  - シグナルから約定に至るトレーサビリティを確保する監査テーブル群を実装。
    - signal_events（戦略が生成したシグナルログ）
    - order_requests（発注要求ログ、order_request_id を冪等キーとして扱う、価格種別に伴う CHECK 制約）
    - executions（証券会社から返る約定ログ、broker_execution_id をユニーク冪等キーとして扱う）
  - インデックスを定義し検索・キュー処理を高速化。
  - 公開 API:
    - init_audit_schema(conn): 既存 DuckDB 接続に監査スキーマを追加（UTC タイムゾーンを設定）。
    - init_audit_db(db_path): 監査ログ専用 DB を初期化して接続を返す。

- データ品質チェックモジュール（src/kabusys/data/quality.py）
  - DataPlatform 準拠の品質チェックを実装。チェックはすべて一覧で返却（Fail-Fast しない）。
  - チェック項目:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損を検出（volume は除外）。
    - 重複チェック (check_duplicates): raw_prices の主キー重複検出。
    - 異常値検出 (check_spike): 前日比のスパイク検出（デフォルト閾値 0.5 = 50%）。
    - 日付不整合チェック (check_date_consistency): 将来日付と market_calendar による非営業日検出。
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - run_all_checks(...) を実装し、すべてのチェックをまとめて実行して結果を返却。
  - DuckDB 接続と SQL（パラメータバインド）で効率的に処理。市場カレンダー未存在時は整合性チェックを安全にスキップ。

### Changed
- （該当なし：初回リリースのため変更履歴はありません）

### Fixed
- （該当なし：初回リリースのためバグ修正履歴はありません）

### Security
- （該当なし）

### Notes / Migration
- 初回リリースのためマイグレーションは不要です。
- 環境変数が未設定の場合は Settings の各プロパティで ValueError が発生します。デプロイ前に .env（または環境変数）を設定してください。参照する主な必須キー:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB の初期化は init_schema() を使用してください。既存 DB に接続するだけでスキーマを作成しない場合は get_connection() を使用します。
- J-Quants API への大量リクエストを行う場合、内部で 120 req/min のレート制限を自動適用します。API 利用時はこの制限に合わせて運用してください。
- audit スキーマは削除を前提としていません（ON DELETE RESTRICT）。監査ログは原則削除しない設計です。

---

今後の予定（アイデア）
- strategy / execution 層の具体的実装（発注ロジック、ポートフォリオ構築）
- テスト・CI 向けのモッククライアントとユニットテスト
- ドキュメント追加（DataSchema.md, DataPlatform.md の詳細化、利用例）
- メトリクス・監視（Prometheus / Slack 通知統合）

もしリリースノートの表現や追加で記載したい詳細（例: 実装方針、既知の制約、使い方サンプル）があれば教えてください。必要に応じて追記・修正します。