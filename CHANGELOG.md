CHANGELOG.md
=============

すべての注目すべき変更は「Keep a Changelog」の形式に従って記録されています。  
このプロジェクトはセマンティックバージョニングに従います。

[Unreleased]
-------------

（なし）

0.1.0 - 2026-03-16
------------------

初回リリース。

Added
- パッケージ: kabusys (version = 0.1.0)
  - パッケージルートに __version__ を追加し、公開モジュール一覧（data, strategy, execution, monitoring）を __all__ で定義。

- 設定 / 環境変数読み込み (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機構:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml で検出（CWD非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト時に有用）。
    - OS 環境変数は protected として上書きを防止。
    - .env パーサは export KEY=val 形式に対応し、クォート（シングル/ダブル）の中のエスケープやインラインコメントを適切に処理。
    - クォートなし値の '#' は直前がスペース/タブの場合のみコメントとして扱う挙動を採用。
  - Settings でアプリ固有の必須設定をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須項目は未設定時に ValueError を送出。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）のデフォルト、KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証ロジックを提供。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しラッパーを実装:
    - ベース機能: GET/POST、JSON ボディ処理、タイムアウト、JSON デコードエラーの扱い。
    - レート制限: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter を実装。
    - リトライロジック: 指数バックオフ（base=2s）、最大リトライ回数3回、対象ステータス 408/429/5xx およびネットワークエラーに対応。
    - 401 Unauthorized を受信した場合は ID トークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止）。
    - ID トークンはモジュールレベルでキャッシュ（ページネーション間で共有）し、強制リフレッシュオプションあり。
    - ページネーション対応（pagination_key を用いた繰り返し取得）。
  - API 用ユーティリティ関数:
    - get_id_token(refresh_token=None)
    - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - DuckDB への保存関数（冪等性確保）:
    - save_daily_quotes(conn, records): raw_prices へ INSERT ... ON CONFLICT DO UPDATE（PK欠損行はスキップして警告ログ）。
    - save_financial_statements(conn, records): raw_financials へ同様の保存ロジック。
    - save_market_calendar(conn, records): market_calendar へ同様の保存ロジック。HolidayDivision を解釈して is_trading_day / is_half_day / is_sq_day を算出。
  - データ変換ユーティリティ:
    - _to_float(value): None / 空文字 → None、変換不能なら None。
    - _to_int(value): "1.0" のような float 文字列は許容して int へ、ただし小数部が非ゼロの値は None を返す（意図しない切捨て防止）。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の 3 層＋監査用テーブルを含む詳細な DDL を定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY 等）を明示。
  - 頻出クエリに合わせたインデックスを作成。
  - init_schema(db_path) により DB ファイルの親ディレクトリを自動作成し、全テーブル／インデックスを冪等に作成して DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）。

- 監査ログ（Audit） (src/kabusys/data/audit.py)
  - 戦略→シグナル→発注要求→約定 までのトレーサビリティを確保する監査用テーブルを追加:
    - signal_events（戦略が生成したすべてのシグナルを記録、棄却含む）
    - order_requests（order_request_id を冪等キーにした発注要求ログ。limit/stop の価格必須チェックを含む）
    - executions（証券会社からの約定ログ、broker_execution_id をユニークな冪等キーとして保持）
  - FK の ON DELETE は RESTRICT（監査ログは削除しない前提）。
  - init_audit_schema(conn) で UTC タイムゾーンを設定して監査テーブル／インデックスを作成。
  - init_audit_db(db_path) により監査専用 DB を初期化して接続を返す（親ディレクトリ自動作成）。

- データ品質チェック (src/kabusys/data/quality.py)
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 実装されたチェック:
    - check_missing_data(conn, target_date=None): raw_prices の OHLC 欠損検出（volume は除外）。検出時は severity="error"。
    - check_spike(conn, target_date=None, threshold=0.5): 前日比スパイク（デフォルト 50%）の検出。LAG ウィンドウを使用し severity="warning"。
    - check_duplicates(conn, target_date=None): raw_prices の主キー重複検出（通常は ON CONFLICT で排除されるが念のため）。
    - check_date_consistency(conn, reference_date=None): 将来日付の検出、および market_calendar と矛盾する非営業日のデータ検出（存在する場合）。
  - run_all_checks(conn, ...) により全チェックを実行し、検出した QualityIssue のリストを返す（Fail-Fast ではなく全件収集）。

- その他
  - 空のパッケージ初期ファイルを各サブパッケージに配置（execution, strategy, data, monitoring の __init__）。
  - ロギングメッセージを各所に追加して実行状況が追跡できるようにした。

Notes / Migration
- 初回起動時は data.schema.init_schema(path) または data.audit.init_audit_db(path) を実行して DuckDB スキーマを初期化してください。init_schema は親ディレクトリを自動作成します。
- 環境変数や .env に依存する機能があるため、本番環境では必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定してください。未設定時は Settings の対応プロパティが ValueError を送出します。
- J-Quants API 呼び出しは内部でレート制御・リトライ・トークンリフレッシュを行います。API のレートやレスポンスコードに応じた挙動を考慮した実装になっています。
- DuckDB に保存するレコードでは PK 欠損行はスキップされ、重複時は ON CONFLICT DO UPDATE により最新の fetched_at 等で更新されます。

Fixed
- なし

Changed
- 初リリースのため該当なし

Security
- 初版のため該当なし

Acknowledgements
- このリリースは内部設計文書（DataSchema.md / DataPlatform.md 等）に基づいて構築されています。