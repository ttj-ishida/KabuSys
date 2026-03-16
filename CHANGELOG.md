CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」規約に準拠しています。
バージョン表記はパッケージ本体の __version__（src/kabusys/__init__.py）に合わせています。

未リリースの変更
----------------
（現時点ではなし）

[0.1.0] - 2026-03-16
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0", __all__ の定義）

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装
    - プロジェクトルートを .git または pyproject.toml で探索して自動読み込み（CWD 非依存）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - .env の行パースはコメント・export 形式・引用符・エスケープを考慮
    - .env と .env.local の読み込み優先度（OS 環境変数 > .env.local > .env）を実装
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB 等の設定をプロパティ経由で取得可能
    - 必須環境変数未設定時は ValueError を発生
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL のバリデーション
    - パス系設定（DUCKDB_PATH, SQLITE_PATH）は Path に変換して展開

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得のフェッチ関数を実装
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）
  - API 呼び出しの共通ユーティリティを実装（_request）
    - レート制限実装（固定間隔スロットリング、120 req/min を遵守）
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止設計）
    - タイムアウト・JSON デコード失敗の取り扱い
    - id_token のモジュールレベルキャッシュ共有（ページネーション間でトークン共有）
  - トークン取得関数 get_id_token（リフレッシュトークン→IDトークン、POST）
  - DuckDB への保存関数（冪等化された INSERT ... ON CONFLICT を使用）
    - save_daily_quotes: raw_prices テーブルへ保存、fetched_at を UTC で記録、PK 欠損行をスキップ
    - save_financial_statements: raw_financials へ保存、fetched_at を記録、PK 欠損行をスキップ
    - save_market_calendar: market_calendar へ保存（取引日/半日/SQ 日の判定ロジック）、PK 欠損行をスキップ
  - 型変換ユーティリティ: _to_float, _to_int（安全な変換: 空値や不正値は None、"1.0" のような float 文字列の扱いを明確化）

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - 3 層データレイヤ（Raw / Processed / Feature）および Execution 層のテーブル DDL を定義
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 頻出クエリ向けのインデックス定義を追加
  - テーブル作成順を依存関係に配慮して定義
  - init_schema(db_path) により DuckDB ファイル生成（親ディレクトリ自動作成）とテーブル作成を行い接続を返す（冪等）
  - get_connection(db_path) により既存 DB への接続を返す（スキーマ初期化は行わない）

- 監査ログ（Audit）スキーマ (src/kabusys/data/audit.py)
  - シグナル→発注→約定までを UUID 連鎖でトレースする監査テーブルを定義
    - signal_events, order_requests（冪等キー order_request_id を持つ）, executions
  - 監査に関する制約とステータス遷移ルールを定義（例: order_requests のチェック制約）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供
    - 全ての TIMESTAMP を UTC で保存するため init 時に SET TimeZone='UTC' を実行
  - 監査用インデックスを追加（signal_id、status、broker_order_id 等）

- データ品質チェック (src/kabusys/data/quality.py)
  - DataPlatform に基づく各種品質チェックを実装
    - 欠損チェック: check_missing_data（raw_prices の OHLC 欠損を検出）
    - 異常値（スパイク）検出: check_spike（前日比の変動率を LAG で計算、閾値はデフォルト 50%）
    - 重複チェック: check_duplicates（主キー重複のグルーピング検出）
    - 日付整合性: check_date_consistency（未来日付・market_calendar と非営業日の整合性検査）
  - QualityIssue データクラスを定義し、各チェックは QualityIssue のリストを返す（Fail-Fast ではなく全件収集）
  - run_all_checks によりまとめて実行し結果を集約・ログ出力

- パッケージ構成（パッケージディレクトリ初期プレースホルダ）
  - src/kabusys/{execution, strategy, monitoring, data} をパッケージ構成として用意（__init__.py あり）

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Security
- N/A（初回リリース）

Notes / 実装上の重要事項
- J-Quants API のレート制限（120 req/min）を守るため固定間隔（スロットリング）実装を採用。短時間に多数の同時リクエストを行う用途では注意。
- id_token の自動リフレッシュは 401 発生時に一度だけ行い、無限再帰を防止する設計（allow_refresh フラグで制御）。
- DuckDB の INSERT ... ON CONFLICT を利用して冪等性を確保。ETL 外部からの不整合に備え quality.check_duplicates を用意。
- すべてのタイムスタンプ（監査ログや fetched_at）は UTC を利用する方針。
- .env パースはシェル風の quoting/escaping とインラインコメントの取り扱いをできる限り再現するが、極端に複雑なケースは非想定。
- 今後のタスク例: strategy / execution 層の実処理実装、監視・アラート（monitoring）モジュールの具体実装、単体テスト・統合テストの追加、パッケージ化用の CI 設定等。

Author
- 開発チーム（コードベースから推定して作成）

（以降のバージョンはここに追記してください）