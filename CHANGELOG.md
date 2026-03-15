CHANGELOG
=========

すべての注目すべき変更点を記載します。本ファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 変更はカテゴリ別（Added, Changed, Fixed, Security）に整理しています。
- バージョンは package の __version__ に合わせています。

[Unreleased]
-----------

（なし）

[0.1.0] - 2026-03-15
--------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基本モジュール群を追加。
  - パッケージエントリポイント
    - src/kabusys/__init__.py: __version__ = "0.1.0"、公開サブパッケージ(data, strategy, execution, monitoring) を定義。
  - 設定・環境変数管理
    - src/kabusys/config.py:
      - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
      - 自動 .env 読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - .env のパースで export プレフィックス、クォート（シングル/ダブル、エスケープ）やインラインコメントを適切に処理するロジックを実装。
      - 自動読み込みを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト向け）。
      - 必須環境変数の検査メソッド（_require）と、KABUSYS_ENV / LOG_LEVEL の値検証（有効値チェック）を追加。
      - デフォルト設定:
        - KABUS_API_BASE_URL のデフォルト: http://localhost:18080/kabusapi
        - DUCKDB_PATH のデフォルト: data/kabusys.duckdb
        - SQLITE_PATH のデフォルト: data/monitoring.db
  - J-Quants API クライアント
    - src/kabusys/data/jquants_client.py:
      - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 系関数を追加（ページネーション対応）。
      - get_id_token(): リフレッシュトークンから id_token を取得する POST 実装を追加。
      - HTTP ユーティリティ(_request) にて:
        - 固定間隔スロットリングによるレート制限（120 req/min）を実装。
        - リトライロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx）実装。
        - 401 受信時は id_token を自動リフレッシュして 1 回だけ再試行する仕組みを実装（無限再帰防止）。
        - JSON デコードエラーやネットワークエラーへのハンドリング。
      - モジュールレベルの id_token キャッシュ（ページネーション跨ぎでトークンを共有）。
      - データ永続化関数 save_* 系（save_daily_quotes, save_financial_statements, save_market_calendar）を追加:
        - DuckDB への挿入は冪等性を担保（ON CONFLICT DO UPDATE）。
        - fetched_at を UTC の ISO8601 形式で記録し、いつデータを得たかを明示（Look-ahead Bias 対策）。
      - 数値変換ユーティリティ _to_float, _to_int を追加（安全な型変換とエッジケース処理）。
  - DuckDB スキーマ
    - src/kabusys/data/schema.py:
      - Raw / Processed / Feature / Execution の 3+1 層データモデルに基づいたテーブル DDL を提供（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
      - 頻繁に参照されるクエリ向けのインデックスを定義。
      - init_schema(db_path) によりディレクトリ作成とテーブル作成（冪等）を行い、DuckDB 接続を返す。
      - get_connection(db_path) で既存 DB への接続を返す（初回は init_schema を推奨）。
  - 監査（Audit）ログ
    - src/kabusys/data/audit.py:
      - signal_events, order_requests, executions の監査用テーブル定義を追加（監査トレーサビリティ用）。
      - order_request_id による冪等性、外部キーとステータス遷移定義、UTC タイムゾーン強制などの設計原則に準拠。
      - init_audit_schema(conn) で監査テーブルとインデックスを既存接続に追加（SET TimeZone='UTC' を実行）。
      - init_audit_db(db_path) により専用 DuckDB を初期化するヘルパーを提供。
  - パッケージ構成
    - 空のパッケージ初期化ファイルを追加:
      - src/kabusys/data/__init__.py
      - src/kabusys/execution/__init__.py
      - src/kabusys/strategy/__init__.py
      - src/kabusys/monitoring/__init__.py

Changed
- N/A（初回リリースのため変更履歴なし）

Fixed
- N/A（初回リリースのため修正履歴なし）

Security
- J-Quants API のトークン自動リフレッシュを実装し、トークン取扱いの基本を備える。ただし初回リリースではトークンの永続化や細かな秘匿化（シークレット管理プラグイン等）は含めていないため、運用時は環境変数管理に注意。

Notes / 備考
- デフォルトの DuckDB/SQLite パスは相対パス（data/...）になっているため、本番運用時は適切な永続化パスへ変更してください。
- .env 自動読み込みはプロジェクトルートを基に行うため、配布後/インストール後に CWD が異なる環境でも正しく動作することを想定しています。CI/テスト等で自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制御は固定間隔（スロットリング）で実装されています。高スループットの同期要求がある場合は別途バッチ化や非同期化を検討してください。
- DuckDB の DDL は冪等（CREATE TABLE IF NOT EXISTS）かつ外部キー依存を考慮した順序で適用されます。監査テーブルは別モジュールで初期化可能です。

既知の制限（今後の改善候補）
- jquants_client の HTTP 実行は urllib を使用する同期実装。並列取得や asyncio 対応は未実装。
- エラー時の通知（Slack 連携など）の実装は設定値のみ存在し、実運用向けの通知パイプラインは未実装。
- strategy / execution / monitoring の具体的実装は未提供（空パッケージ）。戦略や発注ロジックは今後追加予定。

署名
- 初版: KabuSys チーム (コードベースから推測して作成)