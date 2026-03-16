Keep a Changelog準拠のCHANGELOG.md（日本語）

すべての変更はセマンティックバージョニングに従います。  
このプロジェクトの初期リリースを以下に記録します。

Unreleased
----------
（なし）

0.1.0 - 2026-03-16
-----------------
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート判定は __file__ から親ディレクトリを探索し、.git または pyproject.toml を基準に行うため、CWD に依存しない自動読み込みを実現。
  - .env / .env.local の読み込み順と .env.local による上書き挙動をサポート。OS 環境変数を保護する protected セットを採用。
  - 読み込みの自動無効化用に KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能（テスト用途）。
  - .env の行パースは以下をサポート／厳密化:
    - コメント行（#）の取り扱い
    - export KEY=val 形式の対応
    - シングル／ダブルクォート内でのバックスラッシュエスケープ処理
    - インラインコメントの安全な無視（クォートあり/なしの差異を正しく扱う）
  - 必須環境変数取得時に未設定なら ValueError を送出する _require() を実装。
  - settings オブジェクトで主要設定をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）
    - 実行環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）チェックと is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、四半期財務（BS/PL）、JPX マーケットカレンダー取得を行う fetch_* 関数群を実装:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - ページネーション対応（pagination_key）およびモジュールレベルの id_token キャッシュ
  - 認証: get_id_token(refresh_token=None) を提供し、リフレッシュトークンから idToken を取得。
  - HTTP リクエストユーティリティ _request を実装:
    - レート制限（120 req/min）を固定間隔スロットリングで保護する RateLimiter 実装
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx のリトライ）
    - 401 発生時の自動トークンリフレッシュ（1 回のみ）と再試行制御（allow_refresh フラグ）
    - JSON デコードエラーやネットワーク例外のラップと適切なログ出力
  - DuckDB へ保存する冪等的な保存関数を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 各関数は fetched_at を UTC ISO 8601 で記録し、PK 欠損行はスキップ・ログ警告
    - INSERT ... ON CONFLICT DO UPDATE による重複排除／更新を実装
  - データ変換ユーティリティ _to_float / _to_int を実装し、不正な値の扱いを定義

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）と Execution 層のテーブル DDL を定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリ向け）を追加
  - init_schema(db_path) で DB ファイルの親ディレクトリ作成と全テーブル・インデックス作成（冪等）を実行
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）

- 監査ログ（トレーサビリティ）スキーマ（src/kabusys/data/audit.py）
  - DataPlatform.md に基づき、シグナル→発注→約定の UUID 連鎖で完全トレース可能な監査テーブルを定義:
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求、order_request_id を冪等キーとして定義。limit/stop の価格チェック等の制約有）
    - executions（証券会社からの約定ログ、broker_execution_id をユニーク冪等キー）
  - 監査専用のインデックスを定義（status や broker_order_id などによる検索最適化）
  - init_audit_schema(conn)（既存接続へ追加）, init_audit_db(db_path)（専用 DB 初期化）を提供
  - すべての TIMESTAMP を UTC で保存するため init_audit_schema は SET TimeZone='UTC' を実行

- データ品質チェックモジュール（src/kabusys/data/quality.py）
  - DataPlatform.md Section 9 に基づき、複数の品質チェックを実装:
    - 欠損データ検出: check_missing_data（raw_prices の OHLC 欠損を検出）
    - 重複チェック: check_duplicates（主キー重複）
    - 異常値検出: check_spike（前日比スパイク検出、デフォルト閾値 50%）
    - 日付不整合検出: check_date_consistency（未来日付・market_calendar で非営業日データを検出）
  - 各チェックは QualityIssue dataclass を返す（check_name, table, severity, detail, rows）
  - run_all_checks(conn, ...) で一括実行し、検出した問題をまとめて返す
  - DuckDB SQL を用いた効率的な実装、SQL はパラメータバインドで安全化
  - 各チェックは Fail-Fast を採らず、すべての問題を収集して返却（呼び出し側が重大度に応じて対応）

- パッケージモジュール初期化ファイルを配置（空の __init__.py を各サブパッケージに追加）
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Security
- 初回リリースのため該当なし

Notes / 実装上の設計・運用メモ
- Look-ahead Bias の防止: データ取得時に fetched_at を UTC で保存し、「システムがデータを知り得た時刻」を追跡可能にしている。
- 冪等性: DuckDB への挿入は ON CONFLICT DO UPDATE により上書きしているため、ETL の再実行に耐える設計。
- API レートリミットとリトライ設計により、J-Quants API の利用制約（120 req/min、Retry-After 等）に対応。
- .env パーサは一般的なエッジケース（クォート内のエスケープ、インラインコメント、export プレフィックス）を考慮している。
- 監査ログテーブルは削除を想定しない（ON DELETE RESTRICT）ため、監査証跡が保全される設計。

今後の予定（例）
- execution（発注）層の実装: kabuステーションやブローカー API との接続ラッパー、約定処理の実装
- strategy 層のサンプル戦略と特徴量生成パイプラインの強化
- モニタリング（Slack 通知等）および運用ドキュメントの追加
- 単体テスト・統合テストの充実（特に HTTP クライアント、.env パーサ、DuckDB SQL）

----- End of CHANGELOG -----