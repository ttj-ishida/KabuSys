# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
※日付はリリース日を示します。

## [Unreleased]

## [0.1.0] - 2026-03-15

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージルート: src/kabusys/__init__.py にてバージョンと公開モジュールを定義。

- 環境設定管理モジュール (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む機能を追加。
  - 自動ロード順序:
    - OS 環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能（テスト用途）。
  - .env パーサーを実装:
    - コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などを考慮。
    - 無効行はスキップ。
  - 環境変数読み込みの制御:
    - _load_env_file に override フラグと protected セットを導入し、OS 環境変数の上書きを防止。
  - Settings クラスを提供（settings インスタンスを公開）:
    - J-Quants / kabuステーション / Slack / DB パスなどのプロパティ（例: jquants_refresh_token, kabu_api_password, slack_bot_token, duckdb_path, sqlite_path）。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）。
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - ヘルパー: is_live / is_paper / is_dev。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 支持するデータ取得:
    - 株価日足（OHLCV）: fetch_daily_quotes()
    - 財務データ（四半期 BS/PL）: fetch_financial_statements()
    - JPX マーケットカレンダー: fetch_market_calendar()
  - 設計・実装の主な特徴:
    - レート制限: 120 req/min を厳守する固定間隔スロットリング（_RateLimiter）。
    - リトライロジック: 指数バックオフ、最大 3 回、対象は 408/429/5xx およびネットワークエラー。429 の場合は Retry-After を優先。
    - 401 Unauthorized を検出した場合は ID トークンを自動リフレッシュして 1 回だけ再試行（無限再帰を防止）。
    - モジュールレベルの ID トークンキャッシュを保持し、ページネーション間でトークンを共有。
    - ページネーション対応: pagination_key を用いた繰り返し取得。
    - JSON デコードエラー時の明確な例外メッセージ。
    - タイムアウト設定（urllib の timeout=30）。
    - ロギングを適切に出力（取得件数、リトライ、警告など）。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes(conn, records): raw_prices に保存（ON CONFLICT DO UPDATE による冪等性）。
    - save_financial_statements(conn, records): raw_financials に保存（冪等）。
    - save_market_calendar(conn, records): market_calendar に保存（冪等）。
    - 取得時の fetched_at は UTC (ISO8601、Z 表記) で記録して Look-ahead Bias を防止。
    - PK 欠損行はスキップしスキップ数を警告ログ出力。
  - 入出力変換ユーティリティ:
    - _to_float/_to_int: 空値・変換失敗時は None を返す。_to_int は "1.0" のような文字列を float 経由で処理し、小数部が非ゼロの場合は None を返す（意図しない切り捨てを防止）。

- DuckDB スキーマ定義・初期化モジュール (src/kabusys/data/schema.py)
  - DataSchema.md の想定に基づく 3 層＋実行層のテーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）や型（DECIMAL, BIGINT, TIMESTAMP など）を定義。
  - パフォーマンスを考慮したインデックス群を作成（頻出クエリパターンに対応）。
  - init_schema(db_path) を提供:
    - db_path の親ディレクトリ自動作成、":memory:" のサポート。
    - テーブル作成は冪等（IF NOT EXISTS）。
    - 全 DDL とインデックスを実行して DuckDB 接続を返す。
  - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない）。

- 監査ログ・トレーサビリティモジュール (src/kabusys/data/audit.py)
  - シグナルから約定までを UUID 連鎖でトレース可能にする監査テーブルを追加。
  - 主なテーブル:
    - signal_events: 戦略が生成した全シグナル（棄却されたものも含む）を記録。decision と reason を保持。
    - order_requests: 発注要求を冪等キー(order_request_id)付きで記録。order_type ごとのチェック制約（limit/stop/market に応じた価格必須制約）を追加。
    - executions: 実際の約定情報を broker_execution_id を用いて記録（ユニーク、冪等性）。
  - 監査ポリシーの設計反映:
    - すべての TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）。
    - FK は ON DELETE RESTRICT（監査ログは削除しない前提）。
    - created_at / updated_at を用いた更新トラッキング（アプリ側で updated_at を更新する運用を想定）。
  - 監査用インデックス群を作成（status 検索、signal_id/日付/銘柄検索など）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供:
    - 既存の DuckDB 接続に監査テーブルを追加（冪等）。
    - init_audit_db は専用 DB を初期化して接続を返す（親ディレクトリ自動作成、":memory:" サポート）。

- パッケージ構成
  - 空のサブパッケージ/プレースホルダ: execution, strategy, monitoring（将来的な拡張のための初期プレースホルダ）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- API 認証トークンの取り扱いに注意:
  - J-Quants リフレッシュトークンは環境変数経由で供給され、コード内にハードコーディングしない設計。
  - 自動 .env ロード機能は必要に応じて無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注記:
- 本リリースは内部設計文書（DataSchema.md, DataPlatform.md 等）に基づいた初期実装です。  
- 次期リリースではストラテジー実装、発注送信ロジック、モニタリング/アラート、テストカバレッジの追加が想定されます。