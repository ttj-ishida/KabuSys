CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記載します。
このプロジェクトは Keep a Changelog の形式に準拠しています。
履歴は後方互換性の観点で管理します。

v0.1.0 - 2026-03-15
-------------------

初回リリース。日本株自動売買システムのコアモジュールを追加しました。

Added
- パッケージ初期化
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - サブパッケージ: data, strategy, execution, monitoring（strategy / execution / monitoring は初期プレースホルダとして __init__ を追加）

- 環境設定モジュール (kabusys.config)
  - .env / .env.local および OS 環境変数から設定を自動ロードするロジックを追加。
    - ロード優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの自動検出: .git または pyproject.toml を起点に探索（__file__ を基準に探索するため CWD 非依存）。
    - 自動ロード無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途向け）。
    - OS 環境変数を保護するため、.env の上書きを制御（protected set を使用）。
  - 高機能な .env パーサを実装:
    - "export KEY=val" 形式に対応
    - シングル／ダブルクォート内のバックスラッシュエスケープに対応
    - 非クォート値のインラインコメントは「# の直前がスペース/タブ」の場合のみコメントとみなすなど、現実の .env 例に耐性を持つ
  - Settings クラスを提供し、主要設定をプロパティ経由で取得可能:
    - 必須設定 (未設定時は ValueError): JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値を持つ設定: KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi), DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db)
    - 環境種別検証: KABUSYS_ENV は development / paper_trading / live のいずれかであることを保証
    - LOG_LEVEL 検証: DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許可
    - ヘルパープロパティ: is_live/is_paper/is_dev

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアント実装:
    - ベースURL: https://api.jquants.com/v1
    - レート制御: 固定間隔スロットリングで 120 req/min（_RateLimiter、最小間隔 = 60/120 秒）を実装
    - リトライロジック: 指数バックオフ（最大試行回数 3 回）、対象ステータス: 408/429 および 5xx。ネットワーク例外もリトライ対象。
      - 429 の場合は Retry-After ヘッダを優先して待機
    - 認証トークン更新: 401 を受信した場合は ID トークンを自動で 1 回リフレッシュして再試行（無限再帰を避けるため allow_refresh 制御）
    - ページネーション対応: fetch_* 系で pagination_key を追跡
    - id_token のモジュールレベルキャッシュ: ページネーション間でトークンを共有
    - データ取得関数:
      - get_id_token(refresh_token=None): リフレッシュトークンから idToken を取得（POST /token/auth_refresh）
      - fetch_daily_quotes(...): 日足（OHLCV）取得（ページネーション対応）
      - fetch_financial_statements(...): 四半期財務データ取得（ページネーション対応）
      - fetch_market_calendar(...): JPX マーケットカレンダー取得
    - 保存関数（DuckDB 向け、冪等）:
      - save_daily_quotes(conn, records): raw_prices へ INSERT ... ON CONFLICT DO UPDATE（fetched_at は UTC で記録、PK 欠損行はスキップ）
      - save_financial_statements(conn, records): raw_financials へ同様に保存
      - save_market_calendar(conn, records): market_calendar へ同様に保存（HolidayDivision を解釈して is_trading_day / is_half_day / is_sq_day を決定）
    - ユーティリティ:
      - _to_float/_to_int: 型変換時の安全処理（空値や不正値は None、"1.0" のような float 文字列は int に変換可能だが "1.9" は None など挙動を明示）

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataLayer に基づくスキーマ実装（Raw / Processed / Feature / Execution の 4 層）
  - 多数のテーブル定義（主なもの）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各カラムに対する CHECK 制約や PRIMARY KEY / FOREIGN KEY を定義
  - パフォーマンスを考慮したインデックス群を定義（例: prices_daily(code, date), signal_queue(status) 等）
  - 公開 API:
    - init_schema(db_path): DuckDB を初期化して全テーブル・インデックスを作成（冪等、親ディレクトリ自動作成、":memory:" 対応）
    - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない）

- 監査ログ（トレーサビリティ）モジュール (kabusys.data.audit)
  - トレーサビリティ用テーブルを追加:
    - signal_events: 戦略が出したシグナルログ（decision / reason / created_at など）
    - order_requests: 発注要求ログ（order_request_id を冪等キーとして利用、order_type に応じた CHECK 制約を実装）
    - executions: 証券会社からの約定ログ（broker_execution_id をユニークな冪等キーとして保持）
  - インデックス定義（シグナル検索、status=’pending’ スキャン、broker_order_id での参照など）
  - 公開 API:
    - init_audit_schema(conn): 既存 DuckDB 接続に監査テーブルを追加（SET TimeZone='UTC' を実行）
    - init_audit_db(db_path): 監査専用 DB を作成して初期化
  - 設計上の注意点:
    - すべての TIMESTAMP は UTC 保存を前提
    - 監査ログは削除しない前提（ON DELETE RESTRICT を採用）

Notes / Usage
- データベース初期化:
  - 最初に init_schema(settings.duckdb_path) を呼んでスキーマを作成することを推奨
  - 監査ログを利用する場合は init_audit_schema(conn) を呼ぶと既存接続に監査テーブルが追加される
- 環境変数:
  - 実行に必要な必須環境変数を設定しておくこと（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
  - .env / .env.local に設定を書く場合、プロジェクトルートの検出が正常に行われる必要がある
- API レート制御とリトライ:
  - J-Quants API のレート制限（120 req/min）に合わせた実装が組み込まれているため、外部から追加でレート制御を行う必要は通常ない
  - リフレッシュトークン等の扱いは慎重に（トークンの漏洩防止）

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Breaking Changes
- なし（初回リリース）

セキュリティ上の注意
- リフレッシュトークンや API パスワード等は機密情報です。公開リポジトリに平文で置かないでください。
- .env ファイルの読み込みは自動で行われますが、テスト等で明示的に無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。