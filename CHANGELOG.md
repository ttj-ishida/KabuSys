# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  

既知のバージョン: 0.1.0

## [Unreleased]
- 今後の変更やマイナーバージョン向けの予定をここに記載します。

## [0.1.0] - 2026-03-15

### 追加 (Added)
- 初期リリースとして日本株自動売買システムの基盤を追加。
  - パッケージエントリポイント
    - src/kabusys/__init__.py にてバージョンと公開モジュールを定義（__version__ = "0.1.0", __all__ = ["data", "strategy", "execution", "monitoring"]）。
  - 環境設定管理モジュール
    - src/kabusys/config.py を導入。
      - .env および OS 環境変数から設定を読み込む自動ローダーを実装。プロジェクトルート（.git または pyproject.toml を基準）を起点に .env, .env.local を順に読み込む（.env.local は上書き）。
      - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - .env の行解析を厳密に処理（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルールに対応）。
      - OS 環境変数を保護する protected キーセットを導入し、上書きの挙動を制御。
      - Settings クラスを公開（settings）。次のプロパティを提供:
        - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
        - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
        - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
        - KABUSYS_ENV の検証（development, paper_trading, live のみ許容）
        - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        - is_live / is_paper / is_dev のユーティリティプロパティ
      - 必須環境変数未設定時は ValueError を送出する _require を実装。
  - データ層（DuckDB）スキーマ定義
    - src/kabusys/data/schema.py を導入。
      - Raw / Processed / Feature / Execution の4層スキーマを DDL で定義。
      - 主なテーブル:
        - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
        - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
        - Feature 層: features, ai_scores
        - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
      - 各カラムに対する型、CHECK 制約（負値防止、サイズチェック、列挙チェック等）および主キーを定義。
      - 頻出クエリに対するインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status 等）。
      - init_schema(db_path) を公開:
        - 指定した DuckDB ファイルの親ディレクトリを自動作成
        - 全テーブル・インデックスを冪等的に作成し、DuckDB 接続を返す
        - ":memory:" によるインメモリ DB をサポート
      - get_connection(db_path) を公開（既存 DB 接続取得、スキーマ初期化は行わない）。
  - 監査ログ（オーディット）モジュール
    - src/kabusys/data/audit.py を導入。
      - シグナルから約定までのトレーサビリティを保証する監査用テーブルを定義:
        - signal_events（戦略が生成したすべてのシグナルを保存、棄却やエラーも含む）
        - order_requests（発注要求、order_request_id を冪等キーとして扱う）
        - executions（証券会社からの約定ログ、broker_execution_id をユニーク冪等キーとして扱う）
      - テーブル間の外部キー制約を設計（ON DELETE RESTRICT を採用し監査ログは削除しない方針）。
      - order_requests における order_type 別の CHECK 制約（limit は limit_price 必須、stop は stop_price 必須等）を実装。
      - 監査用インデックスを定義（例: idx_signal_events_date_code, idx_order_requests_status, idx_executions_code_executed_at 等）。
      - init_audit_schema(conn) を公開:
        - 既存の DuckDB 接続に監査テーブルを追加（冪等）
        - 「SET TimeZone='UTC'」を実行し、すべての TIMESTAMP を UTC として保存する運用を明示
      - init_audit_db(db_path) を公開（監査専用 DB の初期化と接続取得、親ディレクトリ自動作成、UTC 保存）。
  - パッケージ構造（空の __init__.py を配置）
    - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py, src/kabusys/monitoring/__init__.py を追加し、将来的な拡張に備える。

### 仕様・設計ノート (Notes)
- .env 読み込みの優先順位: OS 環境変数 > .env.local > .env
  - .env.local は .env の値を上書きする（override=True）。ただし既存 OS 環境変数は protected として上書き不可。
- .env 行解析の挙動:
  - export KEY=VAL 形式に対応
  - シングル/ダブルクォート内部はバックスラッシュによるエスケープを解釈し、対応する閉じクォートまでを値として扱う（インラインコメントを無視）
  - クォート無しの値では、先行のスペース/タブの直後に現れる # をコメントとして扱う
- DuckDB 初期化は冪等（既存テーブルやインデックスが存在する場合はスキップ）。初回は data.schema.init_schema() を呼び出すこと。
- 監査ログは削除しない前提、updated_at はアプリ側で更新時に current_timestamp を設定すること。
- すべての TIMESTAMP は監査テーブルで UTC 保存を前提とする（init_audit_schema は SET TimeZone='UTC' を実行）。

### 変更 (Changed)
- 該当なし（初期リリース）。

### 修正 (Fixed)
- 該当なし（初期リリース）。

### 非推奨 (Deprecated)
- 該当なし。

### 削除 (Removed)
- 該当なし。

### セキュリティ (Security)
- 該当なし（初期リリース）。

---

使用例（抜粋）
- 環境設定:
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token
- DB 初期化:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
- 監査ログ初期化:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn)

注: この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノートは運用ポリシーや変更履歴に合わせて適宜更新してください。