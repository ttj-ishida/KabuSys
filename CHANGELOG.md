# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。セマンティック バージョニングを採用しています。

## [Unreleased]

n/a

## [0.1.0] - 2026-03-15

Added
- 初回リリース: kabusys パッケージを追加。
  - パッケージメタ情報:
    - バージョン: 0.1.0（src/kabusys/__init__.py の __version__）
    - パッケージ公開 API: data, strategy, execution, monitoring（__all__）
- 環境設定モジュール（src/kabusys/config.py）を追加。
  - .env 自動読み込み
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出して .env / .env.local を読み込む（CWD に依存しない実装）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - .env.local は .env の値を上書き（override）。OS 環境変数は保護され、上書きされない。
    - .env ファイル読み込み失敗時は warnings.warn で警告を出す。
  - 柔軟かつ安全な .env パーサー
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートされた値のバックスラッシュエスケープ処理を考慮して正しくパース。
    - クォートなし値のインラインコメント（#）は直前が空白/タブの場合のみコメントとして扱うなど、現実的な .env ルールに対応。
  - 必須環境変数チェック
    - _require() による必須キー取得。未設定時は ValueError を送出。
  - Settings クラス（settings = Settings()）で以下プロパティを提供:
    - J-Quants / kabu API / Slack 用の必須トークン取得プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）。
    - kabu_api_base_url のデフォルト（http://localhost:18080/kabusapi）。
    - データベースパス: duckdb_path（デフォルト data/kabusys.duckdb）、sqlite_path（デフォルト data/monitoring.db）。Path.expanduser() を使用。
    - システム設定: KABUSYS_ENV（development, paper_trading, live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）。
    - 環境判定プロパティ: is_live, is_paper, is_dev。
- DuckDB スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）を追加。
  - 3層＋実行レイヤー構成に基づく DDL を実装（Raw / Processed / Feature / Execution）。
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型、制約（CHECK／PRIMARY KEY／FOREIGN KEY）を定義。
  - 頻出クエリに備えたインデックス定義を追加（銘柄×日付スキャン、ステータス検索、ジョイン列など）。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb connection
      - データベースファイルの親ディレクトリを自動作成。
      - ":memory:" を指定してインメモリ DB を利用可能。
      - すべての DDL とインデックスを冪等に適用して接続を返す。
    - get_connection(db_path: str | Path) -> duckdb connection
      - 既存 DB への単純接続（スキーマ初期化は行わない）。
- 監査ログ（トレーサビリティ）モジュール（src/kabusys/data/audit.py）を追加。
  - DataPlatform の設計に基づく監査テーブル群を実装:
    - signal_events（戦略が生成した全シグナルログ。棄却やエラーも記録）
    - order_requests（発注要求。order_request_id を冪等キーとして実装。limit/stop のチェック制約あり）
    - executions（証券会社から返る約定情報。broker_execution_id をユニークな外部冪等キーとして扱う）
  - 設計上の注意点を反映:
    - 監査ログは削除しない前提（外部キーは ON DELETE RESTRICT）。
    - すべての TIMESTAMP は UTC で保存（init_audit_schema は "SET TimeZone='UTC'" を実行）。
    - created_at / updated_at を含む設計（アプリ側で updated_at を更新する前提）。
    - ステータス遷移やエラー情報を格納するカラム設計。
  - 関連インデックスを作成（戦略別検索、ステータスでのキュー取得、broker_order_id / broker_execution_id による検索等）。
  - 公開 API:
    - init_audit_schema(conn: duckdb connection) -> None
      - 既存接続に監査テーブル群を冪等で追加。UTC タイムゾーン設定を行う。
    - init_audit_db(db_path: str | Path) -> duckdb connection
      - 監査ログ専用 DB を作成して初期化済み接続を返す。親ディレクトリ自動作成、":memory:" 対応。
- パッケージ構造のプレースホルダ (__init__.py) を追加:
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/data/__init__.py
  - src/kabusys/monitoring/__init__.py
  - 実装は今後の拡張を想定したモジュール分割を反映（現状は空のパッケージ初期化ファイル）。

Security / Design notes
- 監査ログは改変・削除されない前提で設計されており、トレーサビリティ（戦略→シグナル→発注要求→約定）を UUID 連鎖で追跡可能。
- .env 自動読み込みでは OS 環境変数を保護する仕組みを導入（上書き不可）。
- すべてのタイムスタンプは UTC の使用を想定（監査スキーマ初期化時に TimeZone を設定）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

詳細
- 実際の SQL DDL やインデックスの詳細は src/kabusys/data/schema.py および src/kabusys/data/audit.py を参照してください。

[0.1.0]: https://example.com/your/project/releases/tag/v0.1.0 (リンクは必要に応じて更新してください)