CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣例に従います。
セマンティックバージョニングを使用します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-16
--------------------

Added
- パッケージ初期リリース。パッケージ名: kabusys、バージョン: 0.1.0
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - パッケージの公開モジュール一覧に data, strategy, execution, monitoring を含める。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - export KEY=val 形式やシングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等を考慮した .env パーサを実装。
    - settings オブジェクトを提供。以下の設定プロパティ（必須・任意のデフォルトを含む）を実装:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（検証済み: development / paper_trading / live）
      - LOG_LEVEL（検証済み: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - 環境判定補助プロパティ: is_live, is_paper, is_dev。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装:
      - fetch_daily_quotes(...)
      - fetch_financial_statements(...)
      - fetch_market_calendar(...)
    - API 呼び出し共通処理 _request() を実装。特徴:
      - レート制限遵守（120 req/min）を固定間隔スロットリング (_RateLimiter) で実現。
      - 再試行ロジック（指数バックオフ、最大 3 回）を実装。再試行対象ステータスに 408/429/5xx を含む。429 の場合は Retry-After ヘッダを優先。
      - 401 受信時はリフレッシュ（get_id_token）を自動実行して1回だけ再試行（allow_refresh フラグで無限再帰を回避）。
      - ページネーション対応（pagination_key を使ってページを連結）。
      - JSON デコード失敗時に明確な例外を送出。
    - get_id_token(refresh_token=None) を実装（POST /token/auth_refresh）。モジュールレベルで ID トークンをキャッシュし、ページネーション間で共有。
    - データ取得時に fetched_at（UTC ISO8601）を用いて Look-ahead Bias を抑制する方針を採用。
    - DuckDB への保存関数:
      - save_daily_quotes(conn, records): raw_prices に対して ON CONFLICT DO UPDATE による冪等挿入を実装。
      - save_financial_statements(conn, records): raw_financials に対して冪等挿入を実装。
      - save_market_calendar(conn, records): market_calendar に対して冪等挿入を実装。
    - 型変換ユーティリティ _to_float / _to_int を実装（不正・空値は None、_to_int は "1.0" を許容し小数部が 0 以外なら None）。

- DuckDB スキーマ定義・初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution 層を含む包括的な DDL を定義。
      - raw_prices, raw_financials, raw_news, raw_executions
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - features, ai_scores
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに適切な CHECK 制約・PRIMARY KEY・FOREIGN KEY を設定。
    - 頻出クエリ向けのインデックス定義を追加（code×date、status 検索など）。
    - init_schema(db_path) で DB ファイルの親ディレクトリ作成・DDL 実行を行い、初期化済みの DuckDB 接続を返す（冪等）。
    - get_connection(db_path) を提供（既存 DB への接続。初回は init_schema を推奨）。

- 監査ログ（トレーサビリティ）
  - src/kabusys/data/audit.py
    - 監査用テーブル群および初期化ロジックを実装:
      - signal_events（戦略が生成したすべてのシグナルを記録、棄却やエラーも保存）
      - order_requests（order_request_id を冪等キーにした発注要求ログ）
      - executions（証券会社からの約定ログ、broker_execution_id をユニーク冪等キーとして扱う）
    - init_audit_schema(conn) でタイムゾーンを UTC に設定し、監査DDLとインデックスを作成（冪等）。
    - init_audit_db(db_path) による監査専用 DB 初期化も提供。
    - 設計方針としてすべての TIMESTAMP を UTC 保存、監査ログは削除しない（ON DELETE RESTRICT）を明記。

- データ品質チェック
  - src/kabusys/data/quality.py
    - DataPlatform 設計に基づく品質チェック群を実装:
      - check_missing_data(conn, target_date=None): raw_prices の OHLC 欠損検出（volume は許容）。
      - check_spike(conn, target_date=None, threshold=0.5): 前日比スパイク検出（デフォルト閾値 50%）。
      - check_duplicates(conn, target_date=None): 主キー重複検出（date, code）。
      - check_date_consistency(conn, reference_date=None): 将来日付検出および market_calendar と整合しないデータ検出（非営業日のデータ）。
      - run_all_checks(...) で全チェックをまとめて実行し、QualityIssue のリストを返す。
    - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
    - 各チェックはサンプル行を最大 10 件返し、Fail-Fast ではなく全問題を収集する設計。
    - DuckDB のパラメータバインドを使用して SQL インジェクションリスクを排除。

- パッケージ構造（空のプレースホルダ）
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py, src/kabusys/monitoring/__init__.py を追加（将来的な拡張のためのプレースホルダ）。

Security
- 本リリースではセキュリティに関する既知の脆弱性は報告されていません。ただし、環境変数に秘密情報を保持する都合上、運用時はファイル・アクセス権限や CI/CD のシークレット管理に注意してください。

Migration notes / Usage notes
- 初回起動時:
  - DuckDB スキーマを作成するには data/schema.init_schema(settings.duckdb_path) を呼び出してください（デフォルト path: data/kabusys.duckdb）。
  - 監査ログを別 DB に分ける場合は data.audit.init_audit_db(path) を使用してください。
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - .env / .env.local の自動ロードはプロジェクトルート検出に依存します。配布後に期待どおりに動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動でロードしてください。
- J-Quants API:
  - API レート制限を厳守（120 req/min）。内部でスロットリングと再試行を行いますが、大量取得時はアプリ側でも間引きなどの調整を推奨します。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Acknowledgements
- 本リリースはデータ取得・品質管理・監査・スキーマ周りの基盤を中心に実装しています。戦略ロジックや実取引インテグレーション（kabu API 連携等）は今後のバージョンで追加予定です。