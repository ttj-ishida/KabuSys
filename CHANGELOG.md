# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

- リリース日付は ISO 形式 (YYYY-MM-DD) を使用します。
- このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムのコア基盤を実装しました。

### Added
- パッケージ基本情報
  - パッケージ名とバージョンを定義（kabusys.__version__ = "0.1.0"）。
  - k abusys パッケージの公開モジュール一覧を __all__ に設定（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートを .git または pyproject.toml から自動検出するため、CWD に依存しないロードを実現。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - 環境変数による自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱い等に対応）。
  - .env 読み込み時に既存 OS 環境変数を保護する protected キー処理を実装。
  - .env ファイル読み込み失敗時に警告を出す挙動を追加。
  - Settings クラスを実装し、アプリ設定をプロパティ経由で提供:
    - J-Quants / kabuAPI / Slack / DB パス（DuckDB/SQLite） / 環境（development/paper_trading/live） / ログレベルの取得と検証。
    - env と log_level に対する入力検証（不正値は ValueError を送出）。
    - is_live / is_paper / is_dev ユーティリティプロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - ベース機能:
    - REST API 呼び出しラッパー（JSON デコード、タイムアウト、共通ヘッダ対応）。
  - 認証:
    - refresh_token から id_token を取得する get_id_token() を追加。
    - モジュールレベルで id_token をキャッシュし、ページネーション間で再利用。
    - 401 発生時にはトークンを自動リフレッシュして 1 回だけリトライする処理を実装（無限再帰を回避）。
  - レート制御とリトライ:
    - 固定間隔スロットリングによるレートリミット制御（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429 および 5xx）。
    - 429 の場合は Retry-After ヘッダを尊重。
  - データ取得関数（ページネーション対応）を追加:
    - fetch_daily_quotes(): 株価日足（OHLCV）。
    - fetch_financial_statements(): 財務データ（四半期 BS/PL）。
    - fetch_market_calendar(): JPX マーケットカレンダー（祝日・半日・SQ）。
  - 取得データのトレーサビリティを考慮:
    - Look-ahead Bias 防止のため fetched_at を UTC で記録する設計を採用（保存時に UTC タイムスタンプを付与）。

- DuckDB 保存ユーティリティ（kabusys.data.jquants_client）
  - raw テーブル群への保存関数（冪等性を考慮）を実装:
    - save_daily_quotes(), save_financial_statements(), save_market_calendar()
    - INSERT ... ON CONFLICT DO UPDATE を使用して重複を排除し、更新を行う。
    - 主キー欠損行はスキップし、スキップ件数をログ出力。
  - 値変換ユーティリティを実装:
    - _to_float(), _to_int()：変換失敗や不正フォーマット時は None を返す。整数変換では小数部が非ゼロの場合は None を返して誤った切り捨てを防止。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - 3 層（Raw / Processed / Feature）と Execution 層を想定したスキーマを定義。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック（CHECK 制約）・主キー・外部キーを定義。
  - 頻出クエリのためのインデックス群を定義（銘柄×日付スキャン、ステータス検索等を想定）。
  - init_schema(db_path) を実装: ディレクトリ自動作成、DDL の一括実行、冪等的な初期化を提供。
  - get_connection(db_path) を実装: 既存 DB への接続を返す（スキーマ初期化は行わない）。

- 監査ログ（トレーサビリティ）テーブル（kabusys.data.audit）
  - シグナルから約定に至るトレーサビリティを保持するための監査テーブルを実装:
    - signal_events（戦略が生成したシグナルの全記録）
    - order_requests（発注要求、order_request_id を冪等キーとして扱う）
    - executions（証券会社から返された約定ログ、broker_execution_id をユニークキーとして冪等）
  - ステータス管理、制約、created_at / updated_at ポリシーを明記（UTC タイムスタンプ）。
  - init_audit_schema(conn) と init_audit_db(db_path) を実装: 既存接続への監査テーブル追加、あるいは監査専用 DB の初期化を提供。
  - 監査用インデックス群を追加（信号・注文・約定の検索効率化、broker_order_id/broker_execution_id 関連検索等）。

- 空のパッケージプレースホルダ
  - strategy, execution, monitoring の各パッケージ __init__.py を配置（今後の実装領域を確保）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （今回のリリースで報告されたセキュリティ修正なし）

----

注記:
- 本リリースはインフラ（DB スキーマ、API クライアント、設定読み込み、監査ログ）に重点を置いています。戦略ロジック、注文実行ドライバ、監視・通知機能の具体的実装は今後のリリースで追加予定です。