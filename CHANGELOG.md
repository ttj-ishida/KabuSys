CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
日付はコードから推測したリリース時期（この出力の作成日）を使用しています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-15
-----------------

Added
- 初回リリース。パッケージ名: kabusys（__version__ = 0.1.0）
- パッケージ構成（モジュールの雛形を含む）を追加:
  - kabusys.config: 環境変数・設定管理
  - kabusys.data: データ関連（schema, audit, audit 用初期化機能 等）
  - kabusys.execution: パッケージ雛形
  - kabusys.strategy: パッケージ雛形
  - kabusys.monitoring: パッケージ雛形
- 環境変数の自動読み込み機能（.env / .env.local）を追加:
  - プロジェクトルートを自動検出（.git または pyproject.toml を基準）して .env を読み込む設計。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト用途など）。
  - ファイル読み込みで失敗した場合は警告を発行して継続。
- .env パーサーの強化:
  - 空行・コメント行（#）の無視。
  - "export KEY=val" 形式に対応。
  - シングルクォート/ダブルクォートで囲った値に対するバックスラッシュエスケープ処理をサポート。
  - クォートなし値のインラインコメント処理をスペース／タブの直前を検出して扱う。
- Settings クラスによる型付き・検証付き設定アクセスを追加:
  - 必須の環境変数取得時に未設定なら ValueError を送出する _require() を利用。
  - サポートされる設定項目（代表例）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（許容値: development, paper_trading, live）
    - LOG_LEVEL（許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - env に基づくヘルパープロパティ: is_live, is_paper, is_dev
- DuckDB ベースのスキーマ定義と初期化機能を追加（kabusys.data.schema）:
  - 3層＋実行層のテーブル設計を提供:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切なデータ型・チェック制約（CHECK）と主キーを設定。
  - 頻出クエリに対するインデックス定義を多数追加（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status 等）。
  - init_schema(db_path) によりデータベースファイルの親ディレクトリを自動作成し、DDL とインデックスを冪等に作成。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。
  - ":memory:" を指定してインメモリ DuckDB を使用可能。
- 監査ログ（トレーサビリティ）用モジュールを追加（kabusys.data.audit）:
  - 監査用テーブル: signal_events, order_requests, executions（監査用の DDL を分離）。
  - 設計方針を反映:
    - UUID ベースのトレーサビリティ（signal_id, order_request_id, execution_id 等）。
    - order_request_id を冪等キーとして扱い二重発注を防止する設計。
    - すべての TIMESTAMP は UTC で保存（init_audit_schema は "SET TimeZone='UTC'" を実行）。
    - エラーや棄却されたイベントも永続化（status フィールドなど）。
    - 外部キーは ON DELETE RESTRICT（監査ログを削除しない前提）。
  - order_requests に対する複数の CHECK により order_type（market/limit/stop）ごとの価格必須条件を保証。
  - インデックスを多数定義（例: idx_order_requests_status, idx_order_requests_broker_order_id, idx_executions_code_executed_at 等）。
  - init_audit_schema(conn) による既存接続への監査テーブル追加（冪等）。init_audit_db(db_path) で監査専用 DB を初期化可能。
- 実装上の使い勝手向上:
  - スキーマ初期化処理は冪等（既存テーブルがあればスキップ）。
  - DB ファイルの親ディレクトリの自動作成により初回実行時の手間を軽減。
  - 明確な制約・インデックス設計により将来のクエリ性能とデータ整合性を想定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （特記事項なし）

Notes / 開発者向けメモ
- .env の自動ロードは開発時の利便性を重視しているため、テスト環境や CI などでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化してください。
- データベース初期化は init_schema()（データ本体）と init_audit_schema()/init_audit_db()（監査ログ）を用途に応じて使い分けてください。通常はまず init_schema() で DB を作成後、同一接続に対して init_audit_schema() を呼ぶ想定です。
- 環境変数の必須チェックは Settings のプロパティで行われ、未設定時は ValueError が発生します。アプリ起動時に適切に設定されていることを確認してください。
- strategy, execution, monitoring モジュールは現時点でパッケージ雛形のみ。実装は今後追加予定。

今後の予定（想定）
- strategy・execution・monitoring の実装追加（シグナル生成、ポートフォリオ構築、実際の発注フロー、モニタリングダッシュボード等）。
- 外部 API 連携（kabuステーション、J-Quants、Slack 通知）の具体的実装。
- マイグレーション機能（スキーマバージョニング）やバックアップ/リストア機能の追加。