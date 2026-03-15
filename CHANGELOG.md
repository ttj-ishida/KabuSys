Keep a Changelog に準拠した CHANGELOG.md

全ての変更は慣例に従いセマンティックバージョニングで管理します。  
このファイルはコードベースから推測して作成しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-15
-------------------
Added
- 初回公開リリース。以下の主要機能を追加。
  - パッケージ初期化
    - src/kabusys/__init__.py にてパッケージのバージョンを 0.1.0 として定義。__all__ に data, strategy, execution, monitoring を追加。
  - 環境変数／設定管理モジュール
    - src/kabusys/config.py を追加。
    - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に検索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - .env のパースは以下に対応：
      - 空行やコメント行（#）を無視
      - export KEY=VALUE 形式に対応
      - シングル/ダブルクォートで囲まれた値のバックスラッシュエスケープ処理
      - インラインコメントの処理（クォートなしでは '#' の直前が空白/タブならコメントと認識）
    - 環境変数読み込み時の上書き制御（.env と .env.local の読み込み優先度）と保護（OS既存環境変数を保護）をサポート。
    - Settings クラスを提供し、次のプロパティで必須設定や既定値、バリデーションを行う：
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (default=http://localhost:18080/kabusapi)
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH (default=data/kabusys.duckdb), SQLITE_PATH (default=data/monitoring.db)
      - KABUSYS_ENV の検証（development, paper_trading, live のみ有効）と補助メソッド is_live / is_paper / is_dev
      - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - DuckDB スキーマ定義・初期化モジュール
    - src/kabusys/data/schema.py を追加。
    - DataSchema.md 想定の 3 層（Raw / Processed / Feature）＋Execution レイヤーのテーブル定義を実装。
    - 主要テーブル（例: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）を DDL で定義。
    - テーブル制約（CHECK, PRIMARY KEY, FOREIGN KEY 等）、型、NULL 制約を明示。
    - 頻出クエリ向けのインデックス定義を追加（例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status など）。
    - init_schema(db_path) を実装：
      - DuckDB 接続を返し、全テーブル／インデックスを冪等に作成。
      - db_path の親ディレクトリを自動作成（":memory:" は除外）。
    - get_connection(db_path) を実装（既存 DB へ接続。スキーマ初期化は行わない）。
  - 監査ログ（トレーサビリティ）モジュール
    - src/kabusys/data/audit.py を追加。
    - シグナル → 発注 → 約定のトレーサビリティを確保する監査テーブル群を定義：
      - signal_events（戦略が生成したシグナルの記録。棄却・エラーも含む）
      - order_requests（冪等キー order_request_id を持つ発注要求ログ。order_type に応じた CHECK 制約で limit/stop の必須価格を検証）
      - executions（証券会社からの約定ログ。broker_execution_id を一意に保持）
    - 監査用インデックスを追加（例: idx_signal_events_date_code, idx_order_requests_status, idx_order_requests_broker_order_id 等）。
    - init_audit_schema(conn) と init_audit_db(db_path) を実装：
      - init_audit_schema は接続に対して UTC タイムゾーンをセット（SET TimeZone='UTC'）して監査テーブルを作成。
      - init_audit_db は専用 DB を作成して監査スキーマを初期化（db_path の親ディレクトリ自動作成）。
    - 設計上の注意事項は docstring に明記（UTC 保存、updated_at の取り扱い、FK は削除制限など）。
  - モジュールスケルトン
    - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（空のパッケージ初期化ファイル、将来の拡張に備える）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数の自動読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）し、OS 環境変数は保護される設計。README/.env.example に秘匿情報の取り扱いを記載することを推奨。

注記
- この CHANGELOG はソースコードのコメント・実装から推測して作成しています。細かな挙動（エラーメッセージ文言や例外型の扱いなど）は実際のランタイムでの確認を推奨します。