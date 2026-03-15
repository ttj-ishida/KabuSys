Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。本ドキュメントは Keep a Changelog のガイドラインに準拠します。

フォーマット
-----------

各リリースは「Added / Changed / Fixed / Deprecated / Removed / Security」などのカテゴリで記載します。

0.1.0 - 2026-03-15
-----------------

Added
- パッケージ初期リリース（kabusys v0.1.0）。
- パッケージ初期化:
  - src/kabusys/__init__.py にてバージョンと公開サブパッケージを定義（data, strategy, execution, monitoring）。
- 環境変数・設定管理モジュール（src/kabusys/config.py）を追加:
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - _load_env_file は OS 環境変数を保護する protected オプションを用意（.env.local は override=True にて既存値を上書き）。
  - Settings クラスを提供し、J-Quants トークンやkabuステーションパスワード、Slack トークン/チャネル、DB パス、実行環境（development/paper_trading/live）やログレベル検証をプロパティで取得・検証。
  - env/log_level の値が無効な場合は ValueError を送出。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）を実装:
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得に対応。
  - レート制限管理: 固定間隔スロットリングで 120 req/min を保持する RateLimiter を実装。
  - リトライロジック: 指数バックオフ、最大 3 回の再試行。対象ステータス（408, 429, 5xx）を再試行。429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized 受信時に自動で ID トークンをリフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh フラグを使用）。
  - ページネーション対応（pagination_key を利用）で fetch_* 系関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias 防止のため「いつデータを知り得たか」をトレース可能に。
  - DuckDB へ保存する save_* 関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。INSERT は ON CONFLICT DO UPDATE により冪等性を確保。
  - 型変換ユーティリティ _to_float/_to_int を実装。float / int 変換ルールや不正値処理を明示。
  - モジュールレベルで ID トークンをキャッシュし、ページネーション間で共有。
- DuckDB スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）を追加:
  - DataSchema.md 想定の 3 層（Raw / Processed / Feature）+ Execution 層のテーブル定義を含む DDL を用意。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw レイヤーテーブル。
  - prices_daily, market_calendar, fundamentals 等の Processed レイヤーテーブル。
  - features, ai_scores などの Feature レイヤーテーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution レイヤーテーブル。
  - 頻出クエリに対するインデックス定義を含む。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成・DDL 実行・インデックス作成を行い、初期化済みの DuckDB 接続を返す（:memory: 対応）。
  - get_connection(db_path) は既存 DB への接続を返す（スキーマ初期化は行わない）。
- 監査ログ（Audit）モジュール（src/kabusys/data/audit.py）を追加:
  - シグナルから発注、約定に至る監査トレース用テーブルを定義（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとして取り扱い、二重発注防止を想定。
  - テーブルは UTC タイムスタンプを前提に初期化（init_audit_schema は SET TimeZone='UTC' を実行）。
  - ステータス遷移や各種 CHECK 制約、外部キー制約（ON DELETE RESTRICT）を含む設計。
  - init_audit_db(db_path) で監査専用 DB の初期化を行うユーティリティを提供。
- 空のパッケージ初期化ファイルを追加:
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py（将来拡張のためのプレースホルダ）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated / Removed / Security
- （初回リリースのため該当なし）

備考 / 実装上の注意
- .env パーシングは比較的堅牢に実装されていますが、非常に複雑なシェル展開や行継続などはサポートしていません。必要に応じて .env の形式を簡潔に保ってください。
- J-Quants クライアントの _request は urllib を使用しており、タイムアウトや例外処理を内包しています。環境や運用に応じてログ設定やリトライポリシーを調整してください。
- DuckDB の ON CONFLICT 構文やインデックスは現行の実装で冪等性と検索性能を見込んでいますが、大規模データ投入時のパフォーマンス評価は別途推奨します。

今後の予定（例）
- execution / strategy 層の実装（注文送信、約定処理、ポジション管理ロジック）。
- モニタリング通知（Slack 連携）やメトリクス収集の追加。
- テストカバレッジ強化、CI/CD の導入。

もし上記の変更点について詳細な説明や特定ファイルごとの注釈（設計意図、使用例、API 使用方法）を別途作成希望であればお知らせください。