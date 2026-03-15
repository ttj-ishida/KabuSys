# Changelog

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の指針に従っています。
このファイルでは、後方互換性のない変更は Breaking Changes に分類します。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-15

### 追加 (Added)
- パッケージ初期リリース
  - パッケージメタ情報を追加（src/kabusys/__init__.py、バージョン "0.1.0"、エクスポート: data, strategy, execution, monitoring）。
- 環境変数・設定管理モジュールを実装（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダを実装。
  - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - プロジェクトルート検出: __file__ を起点に親ディレクトリから .git または pyproject.toml を探索してプロジェクトルートを特定（CWD に依存しない）。
  - .env パーサを実装:
    - 空行・コメント（# で始まる行）を無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮して値を抽出。
    - クォートなし値ではインラインコメントを適切に扱う（'#' の直前がスペース/タブの場合のみコメントと判断）。
  - .env 読み込み時の保護機能:
    - OS 環境変数は protected として扱い、override=False では既存の環境変数を上書きしない。
    - .env.local は override=True で読み込み（ただし protected キーは上書きしない）。
  - 設定アクセス用 Settings クラスを追加（settings インスタンスを公開）。
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID などの必須キーを取得するプロパティ（未設定時は ValueError を送出）。
    - KABU_API_BASE_URL のデフォルト値を "http://localhost:18080/kabusapi" に設定。
    - データベースパスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"（Path オブジェクトとして返却、~ を展開）。
    - KABUSYS_ENV の検証（有効値: development, paper_trading, live）と LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。env 判定用の is_live / is_paper / is_dev ヘルパーも提供。
- DuckDB スキーマ定義・初期化を実装（src/kabusys/data/schema.py）
  - データレイヤ設計（Raw / Processed / Feature / Execution）に基づくテーブル DDL を追加。
  - Raw レイヤ: raw_prices, raw_financials, raw_news, raw_executions。
  - Processed レイヤ: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
  - Feature レイヤ: features, ai_scores（特徴量・AI スコア保存テーブル）。
  - Execution レイヤ: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance（発注・約定・ポジション管理）。
  - 各テーブルに適切な制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY 等）を設定。
  - 頻出クエリに対応するインデックスを定義（例: 銘柄×日付インデックス、status 検索インデックス等）。
  - init_schema(db_path) を追加:
    - 指定した DuckDB ファイルを初期化して全テーブル・インデックスを作成（冪等）。
    - db_path の親ディレクトリが存在しない場合は自動作成。
    - ":memory:" オプションでインメモリ DB をサポート。
    - 初回のみでなく既存テーブルがある場合はスキップして冪等に動作。
  - get_connection(db_path) を追加: 既存 DB へ接続（スキーマ初期化は行わない）。
- 監査ログ（トレーサビリティ）機能を実装（src/kabusys/data/audit.py）
  - DataPlatform 設計に基づく監査テーブル（signal_events, order_requests, executions）を追加。
  - トレーサビリティ階層と設計原則（冪等キー、エラー/棄却の永続化、UTC タイムスタンプ、削除禁止など）を明記。
  - order_requests に order_request_id（冪等キー）を導入、limit/stop 注文に対する CHECK 制約（limit_price/stop_price の整合性）を実装。
  - executions テーブルは broker_execution_id をユニークキーとし、証券会社側の約定単位の冪等性に対応。
  - 監査用インデックスを多数追加（signal_events の日付/銘柄検索、status ベースのキュー検索、broker_order_id による紐付け 等）。
  - init_audit_schema(conn) を追加:
    - 既存の DuckDB 接続に監査ログテーブルとインデックスを作成。
    - すべての TIMESTAMP を UTC で保存するために接続に対して "SET TimeZone='UTC'" を実行。
  - init_audit_db(db_path) を追加: 監査ログ専用 DB を初期化して接続を返す（親ディレクトリ自動作成、":memory:" をサポート）。
- モジュール構造の追加（空イニシャライザ）:
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/data/__init__.py
  - src/kabusys/monitoring/__init__.py

### 変更 (Changed)
- 該当なし（初期リリース）

### 修正 (Fixed)
- 該当なし（初期リリース）

### 削除 (Removed)
- 該当なし（初期リリース）

### セキュリティ (Security)
- 該当なし（初期リリース）

---

備考:
- スキーマの多くに CHECK 制約・外部キー・インデックスを設けており、データ整合性と検索パフォーマンスを意識した設計です。
- 環境変数の自動ロードはテストや CI のために無効化可能です（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- init_schema と init_audit_schema はどちらも冪等に設計されています。初期化順や既存接続の扱いに注意してください。