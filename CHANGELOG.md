# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
バージョニングは SemVer に準拠します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-15
初回リリース

### 追加
- パッケージの基本構成を追加
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ にてエクスポート

- 環境設定 / 読み込み機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を追加
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を基準に .git または pyproject.toml を探索して特定（CWDに依存しない）
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env のパースを堅牢化
    - 空行・コメント行（#）を無視
    - export KEY=val 形式をサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応
    - インラインコメントの判定（クォート有無に応じた扱い）を実装
  - 設定取得ラッパークラス Settings を提供
    - 必須キー取得時に未設定なら ValueError を発生（_require）
    - 主要設定プロパティ:
      - JQUANTS_REFRESH_TOKEN（jquants_refresh_token）
      - KABU_API_PASSWORD（kabu_api_password）
      - KABU_API_BASE_URL（kabu_api_base_url、デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development/paper_trading/live の検証、is_dev/is_paper/is_live ヘルパー）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API ベース URL と主要 API 呼び出しを実装
  - 設計上の特徴:
    - API レート制限を遵守（120 req/min）する固定間隔スロットリング実装（_RateLimiter）
    - リトライロジック（最大 3 回、指数バックオフ、対象ステータス: 408/429/5xx、ネットワークエラー対応）
    - 429 の場合は Retry-After ヘッダを優先
    - 401 を受信した場合は ID トークンを自動リフレッシュして 1 回だけリトライ（無限再帰を防止）
    - ページネーション対応（pagination_key を用いた繰り返し取得）
    - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を抑制
    - ID トークンのモジュールレベルキャッシュ（ページネーション間で共有）
  - 提供する取得関数:
    - fetch_daily_quotes(code, date_from, date_to)
    - fetch_financial_statements(code, date_from, date_to)
    - fetch_market_calendar(holiday_division)
  - DuckDB への保存関数（冪等性を担保）
    - save_daily_quotes(conn, records): raw_prices に ON CONFLICT DO UPDATE を用いて保存
    - save_financial_statements(conn, records): raw_financials に ON CONFLICT DO UPDATE を用いて保存
    - save_market_calendar(conn, records): market_calendar に ON CONFLICT DO UPDATE を用いて保存
  - 値変換ユーティリティ:
    - _to_float: 空値や変換失敗は None を返す
    - _to_int: "1.0" のような文字列は float 経由で変換し、小数部が 0 でない場合は None を返す（切り捨て防止）

- データベーススキーマ（kabusys.data.schema）
  - DuckDB 用スキーマ定義を追加（Data Platform の 3 層＋Execution 層に基づく）
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約や CHECK 制約、PRIMARY KEY を付与
  - よく使うクエリ向けにインデックスを定義（例: code×date スキャンや status 検索用）
  - スキーマ初期化 API:
    - init_schema(db_path): DB ファイルの親ディレクトリ自動作成、すべての DDL とインデックスを実行して接続を返す（冪等）
    - get_connection(db_path): 既存 DB への接続を返す（初期化は行わない）

- 監査ログ（トレーサビリティ）モジュール（kabusys.data.audit）
  - シグナル→発注→約定に至る監査ログ用テーブルを追加
    - signal_events（戦略が生成したすべてのシグナルを保存、棄却等も含む）
    - order_requests（発注要求、order_request_id を冪等キーとして利用）
    - executions（証券会社の約定情報を保存、broker_execution_id をユニークキーとして冪等性を担保）
  - テーブルレベルの整合性チェック（limit/stop/market 注文のチェック制約等）を実装
  - インデックス定義（例: status, signal_id, broker_order_id 等）
  - 監査スキーマ初期化 API:
    - init_audit_schema(conn): 既存の DuckDB 接続に監査ログテーブルを追加（UTC タイムゾーン設定含む）
    - init_audit_db(db_path): 監査ログ専用 DB を初期化して接続を返す（親ディレクトリ自動作成）

- その他
  - duckdb を中心とした永続化設計（デフォルトのパス設定あり）
  - ログ出力（logging）を適所で利用（情報・警告）

### 変更
- なし（初回リリース）

### 削除
- なし

### 非推奨
- なし

### 修正
- なし

### セキュリティ
- なし

注記:
- この CHANGELOG はソースコードから推測して作成しています。実際の動作や意図と差異がある場合があります。必要に応じて追記・修正してください。