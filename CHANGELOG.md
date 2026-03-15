# CHANGELOG

すべての重要な変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

※ 初期リリース（コードベースの初期導入内容）を 0.1.0 として記載しています。

## [0.1.0] - 2026-03-15

Added
- パッケージ初期構成を追加
  - パッケージ名: kabusys（src/kabusys）
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - public モジュール: data, strategy, execution, monitoring を export

- 環境変数 / 設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み
    - 読み込み順: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出: カレントファイルの親ディレクトリから .git または pyproject.toml を探索して判定（配布後の実行でも動作する設計）
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
    - OS 環境変数（既存変数）は protected として .env の上書きを制御
  - .env のパース:
    - 空行、コメント行、export プレフィックス、クォート文字列、エスケープシーケンス、インラインコメント（クォートなしは空白直前の # をコメント扱い）に対応
    - 無効行はスキップ
  - Settings クラス（settings インスタンス）
    - J-Quants / kabu / Slack / DB パスなどのプロパティを提供（必須項目は未設定時に ValueError を送出）
    - デフォルト値:
      - KABUS_API_BASE_URL のデフォルト http://localhost:18080/kabusapi
      - DUCKDB_PATH デフォルト data/kabusys.duckdb（Path.expanduser を使用）
      - SQLITE_PATH デフォルト data/monitoring.db
      - KABUSYS_ENV の検証（development, paper_trading, live のみ許可）
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - 機能
    - ID トークン取得（refresh token → idToken）
    - 株価日足 (OHLCV)、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数（ページネーション対応）
    - DuckDB に保存する save_* 関数（raw_prices / raw_financials / market_calendar）を提供し、冪等性を保つため ON CONFLICT...DO UPDATE を使用
    - 取得時刻（fetched_at）を UTC で記録（Look-ahead Bias 防止のため）
  - 設計上の特徴
    - レート制限（120 req/min）を遵守する固定間隔スロットリング実装（_RateLimiter）
    - リトライロジック（最大 3 回、指数バックオフ、408/429/5xx を対象）
      - 429 の場合は Retry-After ヘッダを優先
    - 401 レスポンス受信時は自動的にトークンをリフレッシュして 1 回リトライ（無限再帰を回避）
    - ID トークンはモジュールレベルでキャッシュ（ページネーションや複数呼び出しで共有）
    - JSON デコードエラーやネットワークエラー向けのエラーハンドリングとログ
  - 入出力・ユーティリティ
    - _to_float / _to_int ユーティリティ: 空値・不正値は None を返却。_to_int は "1.0" のような文字列を float 経由で安全に int に変換（小数部が 0 以外なら None）
    - fetch_* は pagination_key を用いたページネーションループ
    - save_* は PK 欠損行をスキップし、スキップ数をログ出力

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）
  - DataLayer 設計に基づくテーブル群（Raw / Processed / Feature / Execution）
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに整合性制約（CHECK / PRIMARY KEY / FOREIGN KEY 等）を付与
  - パフォーマンス用インデックスを複数定義（銘柄×日付スキャン、status 検索、JOIN 用インデックス等）
  - 提供関数
    - init_schema(db_path): DB ファイルの親ディレクトリを自動作成し、全テーブルとインデックスを冪等に作成して DuckDB 接続を返す
    - get_connection(db_path): 既存 DB への単純接続を返す（スキーマ初期化は行わない）
  - ":memory:" を使用したインメモリ DB のサポート

- 監査ログ（トレーサビリティ）モジュールを追加（src/kabusys/data/audit.py）
  - 監査用テーブル群を定義（signal_events, order_requests, executions）
  - トレーサビリティ設計（business_date → strategy_id → signal_id → order_request_id → broker_order_id）
  - order_request_id を冪等キーとし、各種状態遷移（pending → sent → filled/partially_filled/cancelled/rejected/error）をモデル化
  - 全 TIMESTAMP を UTC で保存するため init_audit_schema は "SET TimeZone='UTC'" を実行
  - 提供関数
    - init_audit_schema(conn): 既存の DuckDB 接続に監査用テーブルとインデックスを追加（冪等）
    - init_audit_db(db_path): 監査用 DB を新規初期化して接続を返す（親ディレクトリ自動作成）

Changed
- 初回リリースのため「追加」のみ。既存コードからの破壊的変更はなし。

Fixed
- 初版リリース。既知のバグ修正はなし（新規実装）。

Security
- 認証トークンや必須キーが未設定の場合は ValueError を投げることで運用ミスを早期発見可能
- .env の読み込みで OS 環境変数を保護する設計（override 制御）

Notes / 補足
- ロギング: 主要処理（fetch/save、リトライ、401 更新など）に info/warning ログが仕込まれています。
- API クライアントや DB 初期化は外部リソース（ネットワーク、ファイルシステム）に依存するため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD の設定やモックを推奨します。
- strategy / execution / monitoring パッケージは __init__ が作成されているのみで、実装は今後追加予定です。

BREAKING CHANGES
- なし（初期リリース）。

---