# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

最新: 0.1.0 (初回リリース)

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - モジュール公開インターフェースを定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルや環境変数から設定を自動読み込みする仕組みを実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出（.git または pyproject.toml を基準）を行い、CWD に依存しない自動読み込み実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - .env パーサー実装（export プレフィックス、クォートとエスケープ、行内コメント対応）。
  - Settings クラスを実装し、アプリケーション設定をプロパティとして提供（J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス、実行環境・ログレベルチェックなど）。
  - 必須環境変数が未設定の場合に明確なエラーを投げる _require を追加。
  - 有効な env 値（development / paper_trading / live）や LOG_LEVEL 値の検証を実装。
  - デフォルトの DB パス（DuckDB / SQLite）のサポート（Path 型で返却）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants から以下データを取得する API ラッパーを実装:
    - 株価日足（fetch_daily_quotes）
    - 財務データ（fetch_financial_statements）
    - JPX マーケットカレンダー（fetch_market_calendar）
  - 認証トークン取得関数 get_id_token を実装（リフレッシュトークン → idToken）。
  - HTTP リクエストユーティリティ _request を実装し、以下をサポート:
    - レート制限遵守（固定間隔スロットリング、120 req/min をデフォルト）
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 429 の場合は Retry-After ヘッダを優先
    - 401 受信時は自動で id_token をリフレッシュして 1 回だけリトライ（無限再帰防止）
    - JSON デコードエラー時の明確な例外
    - タイムアウトとネットワークエラーへの再試行
  - ページネーション対応（pagination_key）を実装し、ページ間で id_token を共有するためのキャッシュ機構を追加。
  - データ取得時に取得時刻を UTC 形式でトレースする設計（fetched_at を付与することを意図）。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataPlatform.md に基づく多層スキーマを追加:
    - Raw layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature layer: features, ai_scores
    - Execution layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PK, CHECK）を付与し、データ整合性を強化。
  - 利用頻度に基づくインデックスを定義（銘柄×日付検索やステータス検索等を想定）。
  - init_schema(db_path) を提供し、DB ファイルの親ディレクトリ自動作成やテーブル作成（冪等）を行う。
  - get_connection(db_path) を提供（既存 DB に接続するユーティリティ）。

- DuckDB への保存ユーティリティ（kabusys.data.jquants_client 内）
  - fetch_* の結果を DuckDB に保存する idempotent な保存関数を実装:
    - save_daily_quotes(conn, records)
    - save_financial_statements(conn, records)
    - save_market_calendar(conn, records)
  - 挿入は ON CONFLICT DO UPDATE を使用し、重複や再実行に耐える設計。
  - PK 欠損行のスキップとログ出力を実装。
  - save_* は保存件数を返す。

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注 → 約定のトレーサビリティを保証する監査テーブル群を実装:
    - signal_events, order_requests (冪等キー order_request_id を含む), executions
  - テーブル定義によりエラーや棄却も記録する方針を採用（status カラム等）。
  - init_audit_schema(conn) により既存接続へ監査テーブルを追記（UTC 保存を保証するため SET TimeZone='UTC' を実行）。
  - init_audit_db(db_path) による専用 DB 初期化ユーティリティを追加。
  - 検索性向上のための監査用インデックス群を定義（signal_id、status、broker_order_id 等）。

- データ品質チェック（kabusys.data.quality）
  - DataPlatform.md に基づく品質チェック群を追加:
    - 欠損データ検出: check_missing_data（raw_prices の OHLC 欄）
    - 異常値検出: check_spike（前日比スパイク検出、デフォルト閾値 50%）
    - 重複チェック: check_duplicates（主キー重複の検出）
    - 日付不整合検出: check_date_consistency（将来日付、market_calendar と矛盾するデータ）
    - run_all_checks による一括実行（すべてのチェックを集めて返す）
  - 各チェックは QualityIssue dataclass を返し、全検出結果を収集する（Fail-fast ではない）。
  - SQL はパラメータバインドで実行し、効率的かつ安全に DuckDB 上でチェックを実行。
  - 異常時のサンプル行（最大 10 件）を返す設計。
  - ロギングで検出件数を報告。

- ユーティリティ関数
  - 値変換ヘルパー _to_float, _to_int を実装（空値・不正値は None、_to_int は "1.0" 対応、非ゼロ小数部は None）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security & Behavior notes
- J-Quants API 利用時は rate limit（120 req/min）と retry ロジックに注意。自動トークンリフレッシュ機能があるが、get_id_token など内部での呼び出しは allow_refresh フラグにより無限再帰が防がれるよう設計されています。
- DuckDB スキーマは多数の制約を含みます。既存データベースに導入する場合はバックアップを推奨します。
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT）で設計されているため、運用上のデータ保持ポリシーに注意してください。
- 環境変数の自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストなどで利用）。

---

注: この CHANGELOG はリポジトリ内の現行コードを基に推測して作成しています。実際のリリースノートとして利用する際は、追加のドキュメント（リリース日、作者、マイグレーション手順等）を追記してください。