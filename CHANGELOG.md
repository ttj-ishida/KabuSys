CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
重要なバージョンは semver に従います。

[Unreleased]
------------

- （現在の差分はありません）

0.1.0 - 2026-03-16
------------------

Added
- 初回リリース。パッケージ名: kabusys
  - パッケージ初期化:
    - src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ の公開モジュール指定を追加。
  - 環境設定 / 設定管理:
    - src/kabusys/config.py
      - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（優先順: OS 環境変数 > .env.local > .env）。
      - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - プロジェクトルート検出は .git または pyproject.toml を探索して行う（CWD に依存しない設計）。
      - .env のパースロジックを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの取り扱い等）。
      - Settings クラスを提供し、必須環境変数取得（_require）、既定値、入力検証（KABUSYS_ENV, LOG_LEVEL の許容値）および便利プロパティ（is_live / is_paper / is_dev）を実装。
      - データベースパス（DuckDB/SQLite）の既定値処理（Path.expanduser 対応）。
  - データ取得クライアント（J-Quants）:
    - src/kabusys/data/jquants_client.py
      - J-Quants API クライアントを追加。取得対象: 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー。
      - レート制限（120 req/min）を保つ固定間隔スロットリングを実装（内部 RateLimiter）。
      - 再試行ロジック（指数バックオフ、最大 3 回）。HTTP 408/429/5xx をリトライ対象。429 の場合は Retry-After を優先。
      - 401 受信時にリフレッシュを行い 1 回のみリトライする自動トークンリフレッシュ機能を実装（get_id_token 経由）。モジュールレベルで id_token をキャッシュしてページネーション間で共有。
      - ページネーション対応（pagination_key をループで追跡）で fetch_* 系関数を実装:
        - fetch_daily_quotes
        - fetch_financial_statements
        - fetch_market_calendar
      - DuckDB への保存関数（冪等化: ON CONFLICT DO UPDATE）を実装:
        - save_daily_quotes（raw_prices）
        - save_financial_statements（raw_financials）
        - save_market_calendar（market_calendar）
      - 型変換ユーティリティ (_to_float, _to_int) を実装。_to_int は "1.0" 形式を扱い、小数部が非ゼロの値は None を返す等の安全策を提供。
  - データベーススキーマ / 初期化:
    - src/kabusys/data/schema.py
      - DuckDB 用スキーマを定義・初期化するモジュールを追加。3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を含む。
      - 各テーブルは NOT NULL / CHECK 制約や PRIMARY KEY を備え、冪等的に CREATE TABLE IF NOT EXISTS を実行。
      - 検索パフォーマンスを考慮したインデックス群を定義。
      - init_schema(db_path) によりディレクトリ自動生成後に全 DDL とインデックスを作成し DuckDB 接続を返す。get_connection(db_path) で既存 DB に接続可能。
  - ETL パイプライン:
    - src/kabusys/data/pipeline.py
      - 日次 ETL のエントリ run_daily_etl を実装（カレンダー → 株価 → 財務 → 品質チェックの順）。
      - 差分更新ロジック（最後に取得した日付を参照し、backfill_days により数日前から再取得）を備えた個別ジョブを提供:
        - run_calendar_etl（デフォルトで先読み 90 日）
        - run_prices_etl（デフォルトバックフィル 3 日、最小データ日付を定義）
        - run_financials_etl（同上）
      - ETLResult データクラスを定義し、取得数／保存数／品質問題／エラー一覧などをトラッキング。品質チェックの結果を辞書化する to_dict を提供。
      - 品質チェックは Fail-Fast せず全件収集する方針を採用。
      - 市場カレンダー取得後に target_date を直近の営業日に調整するユーティリティを実装。
  - 監査ログ（トレーサビリティ）:
    - src/kabusys/data/audit.py
      - シグナル→発注要求→約定までトレース可能な監査テーブルを定義・初期化するモジュールを追加。
      - signal_events, order_requests, executions テーブルを追加。order_request_id を冪等キー、broker_execution_id をユニークキーとしている。
      - すべての TIMESTAMP を UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）。
      - 各テーブルに必要な CHECK 制約・外部キーを設定し、インデックス群も定義。
      - init_audit_schema(conn) / init_audit_db(db_path) を提供。
  - データ品質チェック:
    - src/kabusys/data/quality.py
      - 品質チェックモジュールを追加。主なチェック:
        - 欠損データ検出（raw_prices の OHLC 欠損、サンプル最大 10 件を返す）
        - 異常値（スパイク）検出（前日比 ±X% を超える変動を検出、デフォルト閾値 50%）
        - 重複チェック・日付不整合検出（将来日付や非営業日データ）を想定（SQL ベースで実装）。
      - QualityIssue データクラスを導入（check_name / table / severity / detail / sample rows）。
      - DuckDB 上で効率的に実行するためにパラメータバインド（?）を利用した SQL を採用。
  - パッケージ構成:
    - data, strategy, execution, monitoring のサブパッケージ用ディレクトリを追加（__init__.py を含む）。strategy と execution の実装は枠組みを用意。

Changed
- 初版のため過去変更はなし。

Fixed
- 初版のため過去修正はなし。

Removed
- 初版のため削除はなし。

Security
- J-Quants のトークンや Slack トークン等の秘匿情報は Settings 経由で環境変数として扱う設計。.env 自動ロードは必要に応じて無効化可能。

Notes / 注記
- DuckDB スキーマは冪等的に作成されるため、既存 DB に対して安全に初期化が可能です。
- jquants_client のレート制御は固定インターバル方式のため、厳密に 120 req/min 相当の間隔を保ちます（最小間隔 60/120 秒）。
- get_id_token は settings.jquants_refresh_token を参照するため、リフレッシュトークンの設定が必須です（未設定時は ValueError）。
- ETL の品質チェックはデフォルトで有効（run_daily_etl の run_quality_checks パラメータで制御）。
- _to_int/_to_float は不正な文字列や意図しない丸めを防ぐため厳密な変換規則を採用。

問い合わせ・貢献
- 初回リリースです。バグ報告・機能要望は issue を通じてお願いします。