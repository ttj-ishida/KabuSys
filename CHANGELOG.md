# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、後方互換性の有無を明記しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に合わせています。

次のリリースノートは、リポジトリ内のコードから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回公開リリース

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py）。
  - __all__ に主要サブパッケージを公開: data, strategy, execution, monitoring。

- 環境設定/読み込み（src/kabusys/config.py）
  - Settings クラスを実装し、アプリケーション設定を環境変数から取得する API を提供。
  - 必須設定を厳格に検証する _require() を実装（未設定時は ValueError を送出）。
  - サポートする設定（例）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（有効値: development, paper_trading, live。デフォルト: development）
    - LOG_LEVEL（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）
    - ヘルパー: is_live, is_paper, is_dev

  - .env 自動読み込み機能を追加
    - プロジェクトルートを .git または pyproject.toml から探索（_find_project_root）。
    - ルートが見つかれば .env を読み込み（既存 OS 環境変数を上書きしない）、続けて .env.local を上書き読み込み。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - OS の既存環境変数は protected として扱い .env/.env.local の上書きを制御。

  - .env パーサを細かく実装（_parse_env_line）
    - "export KEY=val" 形式に対応。
    - クォートあり（シングル/ダブル）の場合のバックスラッシュエスケープに対応し、対応する閉じクォートまでを値とする（以降の inline コメントは無視）。
    - クォートなしの値については、'#' をコメントとみなすかどうかを直前が空白/タブかで判定する挙動を実装。
    - 無効行（空行、コメント行、キーがない行等）は無視。

- DuckDB ベースのデータスキーマ（src/kabusys/data/schema.py）
  - データレイヤ設計に基づくテーブル群を実装（冪等にテーブル作成）。
    - レイヤ構成（ドキュメント DataSchema.md 準拠）:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対してデータ整合性を担保する CHECK 制約、PRIMARY KEY、FOREIGN KEY を設定（例: 非負チェック、size > 0 等）。
  - 頻出クエリを想定したインデックス群を追加（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status 等）。
  - init_schema(db_path) を実装:
    - 指定したパスの親ディレクトリを自動作成し、全テーブルとインデックスを作成して DuckDB 接続を返す。
    - ":memory:" に対応（インメモリ DB）。
    - 既にテーブルが存在する場合はスキップするため冪等。
  - get_connection(db_path) を実装:
    - 既存 DB へ接続のみを行う（スキーマ初期化は行わないことを明記）。

- 監査ログ（audit）テーブル群（src/kabusys/data/audit.py）
  - シグナルから約定までのトレーサビリティを目的とした監査テーブルを実装（DataPlatform.md セクションに準拠）。
  - トレーサビリティ階層と設計原則を実装（例: order_request_id は冪等キー、監査ログは削除しない想定で FK は ON DELETE RESTRICT）。
  - テーブル:
    - signal_events: 戦略が生成したシグナルを全て記録（決定/棄却理由やステータスを含む）。
    - order_requests: 発注要求（order_request_id を冪等キー。注文タイプ別の CHECK 制約あり）。
    - executions: 証券会社からの約定情報（broker_execution_id を UNIQUE として冪等性を確保）。
  - すべての TIMESTAMP を UTC で保存するため init_audit_schema(conn) 実行時に "SET TimeZone='UTC'" を適用。
  - 監査用インデックス群を追加（例: idx_signal_events_date_code, idx_order_requests_status, idx_executions_code_executed_at 等）。
  - init_audit_schema(conn) と init_audit_db(db_path) を実装:
    - 既存接続へ監査テーブルを追加するパターンと、監査専用 DB を新規作成するパターンを両方提供。

### Notes / Usage
- 初期化の推奨:
  - メイン DB を初期化するには:
    from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)
  - 監査テーブルを既存接続に追加するには:
    from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn)
  - 監査専用 DB を作るには:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/kabusys_audit.duckdb")
- get_connection() はスキーマの初期化を行わない点に注意（初回は init_schema() を実行すること）。
- 環境変数の自動読み込みはプロジェクトルートが判定不能な場合はスキップされる（CI/パッケージ配布後の安全策）。
- アプリ側は監査テーブルの updated_at 等のフィールドを更新する際、必ず current_timestamp をセットする設計方針。

### Removed
- なし

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Security
- 初回リリースのため該当なし

---

バージョン 0.1.0 は、プロジェクトの基盤（設定読み込み・.env の柔軟なパース、DuckDB を用いたデータ/監査スキーマ、初期化ユーティリティ）を中心に実装した初期リリースです。今後は戦略実装（strategy）、発注実行ロジック（execution）、監視（monitoring）などを追加していく予定です。