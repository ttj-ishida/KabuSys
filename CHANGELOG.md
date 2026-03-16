# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このファイルはパッケージのコードベースから推測して作成された初期の変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-16

Added
- パッケージ起点を導入
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ として公開。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索し、CWD に依存しない実装。
    - 自動ロードの無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き禁止）。
  - .env 行パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - Settings クラスを提供し、必須設定取得時に未設定なら ValueError を送出。
    - J-Quants / kabuステーション / Slack / DB パスなど主要プロパティを定義。
    - KABUSYS_ENV の検証（development / paper_trading / live）と LOG_LEVEL の検証。
    - パスプロパティは Path を返す（DUCKDB/SQLITE のデフォルトパス含む）。
    - is_live / is_paper / is_dev の便宜プロパティ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API からのデータ取得（株価日足、財務データ、JPX マーケットカレンダー）を実装。
  - 設計上の特徴:
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（内部 RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）。
    - 401 Unauthorized 判定時にリフレッシュトークンで id_token を自動更新して 1 回だけ再試行。
    - ページネーション対応（pagination_key を用いたループ、モジュールレベルの id_token キャッシュ共有）。
    - データ取得時の fetched_at を UTC で記録する運用方針の注釈。
  - 公開 API:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
    - save_daily_quotes(conn, records): DuckDB への冪等保存（ON CONFLICT DO UPDATE）
    - save_financial_statements(conn, records)
    - save_market_calendar(conn, records)
  - ユーティリティ: 安全な型変換関数 _to_float / _to_int を実装（不正な値は None を返す）。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataPlatform 設計に基づく多層スキーマを定義（Raw / Processed / Feature / Execution）。
  - Raw 層: raw_prices, raw_financials, raw_news, raw_executions 等を定義。
  - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等を定義。
  - Feature 層: features, ai_scores を定義。
  - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等を定義。
  - インデックス群を定義（頻出クエリに対応する複数の CREATE INDEX）。
  - 公開 API:
    - init_schema(db_path) -> DuckDB 接続: ディレクトリ自動作成、全テーブル・インデックス作成（冪等）。
    - get_connection(db_path) -> DuckDB 接続: スキーマ初期化は行わない既存接続取得。

- 監査ログ（Audit）モジュール (src/kabusys/data/audit.py)
  - シグナルから約定までのトレーサビリティを担保する監査テーブル群を定義。
  - テーブル:
    - signal_events: 戦略が生成したシグナル（ステータス、理由等を含む）
    - order_requests: 発注要求（order_request_id を冪等キーとして扱う）
    - executions: 実際の約定ログ（broker_execution_id を冪等キー）
  - 制約・チェック・外部キーを厳格に設定（ON DELETE RESTRICT 等）。
  - UTC タイムゾーン保存（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 公開 API:
    - init_audit_schema(conn)
    - init_audit_db(db_path) -> DuckDB 接続

- データ品質チェックモジュール (src/kabusys/data/quality.py)
  - DataPlatform の品質チェック方針に基づいた検査を実装。
  - QualityIssue データクラスを定義（チェック名・テーブル・重大度・詳細・サンプル行）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は除外）
    - check_spike: 前日比スパイク検出（デフォルト閾値 50%）
    - check_duplicates: raw_prices の主キー重複検出
    - check_date_consistency: 将来日付および market_calendar と整合しない非営業日データ検出
    - run_all_checks: すべてのチェックを実行して合成結果を返却
  - 各チェックはサンプル行（最大 10 件）を返し、Fail-Fast ではなく全検出を収集。
  - SQL はパラメータバインドを使用し、DuckDB で効率的に処理。

- その他
  - data, strategy, execution, monitoring パッケージの基本構成ファイルを追加（空の __init__.py によるパッケージ化）。
  - 多くのモジュールに詳細なドキュメント文字列（設計方針、使い方、制約）を追加。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Notes / Known limitations
- execution, strategy, monitoring モジュールはパッケージのプレースホルダとして存在するが、振る舞い（具体的戦略ロジック、実際の発注フロー、モニタリング処理）は未実装の箇所がある（拡張の余地あり）。
- J-Quants クライアントは urllib を用いた同期実装。大規模並列取得や非同期処理が必要な場合は将来的な改修が推奨される。
- DuckDB を前提としているため、別の DB を用いる場合はスキーマ/保存関数の移植が必要。
- テスト用に自動環境読み込みを抑止するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）が用意されているが、ユニットテスト用の詳細なテストヘルパーは未提供。

セキュリティ
- 保持するトークン類は環境変数から読み込む想定。ソースコードやリポジトリにトークンを埋め込まないことを推奨。

Authors
- 本 CHANGELOG はコードベースの内容から推測して作成されました。実際の開発履歴やリリース日・注記はプロジェクトの公式履歴と合わせて調整してください。