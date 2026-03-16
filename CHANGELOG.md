# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に従っています。セマンティックバージョニング (https://semver.org/) を採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買システムの基盤機能を実装しました。

### Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - __all__ に data, strategy, execution, monitoring を公開（strategy・execution・monitoring は現時点ではスタブ）。
- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行うため、CWD に依存しない実装。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - ロード順: OS 環境変数 > .env.local > .env（.env.local は .env を上書き可能）。
  - .env パーサの強化:
    - export プレフィックス対応、シングル／ダブルクォート内のエスケープ処理、インラインコメント対応など。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - J-Quants / kabu API / Slack / DB パス等のプロパティを定義。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - デフォルト DuckDB パス: data/kabusys.duckdb、デフォルト SQLite パス: data/monitoring.db。
    - 必須項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定時に ValueError を送出。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 基本機能:
    - 株価日足（OHLCV）, 財務データ（四半期 BS/PL）, JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - ネットワーク設計:
    - レート制限対応（固定間隔スロットリング、120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回。対象は 408, 429, 5xx とネットワークエラー）。
    - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動リフレッシュして 1 回だけリトライ（無限再帰防止）。
    - JSON デコードエラーやタイムアウトに対する明確なエラーメッセージ。
    - モジュール単位の id_token キャッシュを保持（ページネーション間で共有）。
  - DuckDB への保存:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 保存は冪等（ON CONFLICT DO UPDATE）で重複を排除。
    - PK 欠損行はスキップしログ出力。
    - 取得時刻（fetched_at）は UTC タイムスタンプで記録（ISO 形式）。
  - ユーティリティ:
    - 型変換ユーティリティ _to_float / _to_int を実装（安全な変換ルール、意図しない切り捨て回避等）。
- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - 3 層構造（Raw / Processed / Feature）＋ Execution 層のテーブル DDL を実装。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種インデックスを定義（頻出アクセスパターンを想定）。
  - init_schema(db_path) でディレクトリ自動作成＋テーブル作成（冪等）し DuckDB 接続を返す。
  - get_connection(db_path) を用意（スキーマ初期化は行わない）。
- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - signal_events, order_requests, executions の DDL を実装（UUID ベースのチェーン、order_request_id を冪等キーとして使用）。
  - 監査設計方針に基づく制約（ON DELETE RESTRICT 等）、updated_at をアプリ側で更新する運用前提。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供。タイムゾーンは UTC に設定して初期化。
  - 監査用インデックスを追加（戦略別検索、status によるキュー取得、broker_order_id 紐付け等を想定）。
- データ品質チェック (src/kabusys/data/quality.py)
  - QualityIssue データクラス（チェック名、テーブル、severity、詳細、サンプル行）を定義。
  - 実装されたチェック:
    - check_missing_data: raw_prices の OHLC 欠損（error）。
    - check_duplicates: raw_prices の主キー重複検出（error）。
    - check_spike: 前日比スパイク検出（デフォルト閾値 50%）（warning）。
    - check_date_consistency: 将来日付検出 / market_calendar と整合しない非営業日データ検出（future_date は error、non_trading_day は warning）。
  - run_all_checks(conn, ...) で一括実行し検出結果一覧を返す（Fail-Fast ではなく全件収集の方針）。
  - SQL はパラメータバインドを使用し、DuckDB 上で効率的に集計。
- パッケージスタブ
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（将来的な実装のためのプレースホルダ）。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings を利用する際に必須。未設定時は ValueError。
  - .env.example を参照して .env を作成してください。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - 変更する場合は環境変数 DUCKDB_PATH / SQLITE_PATH を設定してください。
- 時刻関連:
  - 取得時刻や監査タイムスタンプは UTC で保存する設計。
- API 利用制限:
  - J-Quants API は 120 req/min のレート制限に準拠するため内部でスロットリングを実装しています。高頻度の並列呼び出し時は注意してください。

### Fixed
- （初版のため該当なし）

### Changed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- （現時点で特記事項なし）

---

開発・運用における注意や今後の予定（例: execution/strategy の実装、監視・アラート機能の追加、CI での自動テストなど）は別途ドキュメントにまとめる予定です。必要であれば CHANGELOG の拡張や項目の追記を行います。