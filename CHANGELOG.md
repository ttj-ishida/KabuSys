CHANGELOG
=========

すべての注目すべき変更点をここに記録します。  
フォーマットは「Keep a Changelog」を準拠しています。  
<https://keepachangelog.com/ja/1.0.0/>

0.1.0 - 2026-03-15
------------------

Added
- 初回リリース: KabuSys — 日本株自動売買システムのベース実装を追加。
  - パッケージ公開点:
    - src/kabusys/__init__.py: パッケージ名・バージョン (0.1.0) と主要サブモジュールをエクスポート（data, strategy, execution, monitoring）。
    - strategy/, execution/, monitoring/ の各モジュールはプレースホルダとして初期化ファイルを含む。
- 環境変数/設定管理（src/kabusys/config.py）を追加:
  - プロジェクトルート検出ロジック: __file__ を基点に上位ディレクトリを探索し、.git または pyproject.toml を見つけてプロジェクトルートを特定（配布後も動作）。
  - 自動 .env ロード:
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - OS 環境変数は保護され、.env/.env.local による上書きを防止（protected キー機構）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト等で利用）。
  - .env パーサーの実装:
    - 空行・コメント行（先頭 #）を無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォートで囲まれた値を解釈し、バックスラッシュによるエスケープをサポート（対応する閉じクォートまでを値として扱い、内部のインラインコメントは無視）。
    - クォートなしの場合、`#` が前にスペース/タブを伴う場合は以降をコメントとみなす。
    - .env 読み込み失敗時は警告を出力。
  - Settings クラス（settings インスタンスを提供）:
    - J-Quants: jquants_refresh_token (必須)
    - kabuステーション API: kabu_api_password (必須)、kabu_api_base_url（既定: http://localhost:18080/kabusapi）
    - Slack: slack_bot_token、slack_channel_id（必須）
    - DB パス: duckdb_path（既定: data/kabusys.duckdb）、sqlite_path（既定: data/monitoring.db）
    - システム設定: env（有効値: development, paper_trading, live）、log_level（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - ヘルパープロパティ: is_live, is_paper, is_dev
    - 必須環境変数が未設定の場合は _require() によって ValueError を送出。
- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）を追加:
  - データレイヤーを階層化して設計:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに詳細な型・制約（CHECK、PRIMARY KEY、FOREIGN KEY）を設定してデータ整合性を担保。
  - 頻出クエリを想定したインデックスを多数定義（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status など）。
  - init_schema(db_path) を提供:
    - DuckDB ファイルの親ディレクトリを自動作成。
    - ":memory:" でインメモリ DB をサポート。
    - 全テーブル・インデックスを冪等に作成して接続を返す。
  - get_connection(db_path): 既存の DuckDB 接続を返す（スキーマ初期化は行わない）。
  - デフォルトの DuckDB パスは settings で指定可能（data/kabusys.duckdb）。
- 監査ログ（Data audit）（src/kabusys/data/audit.py）を追加:
  - 目的: シグナル → 発注 → 約定 までのトレーサビリティを UUID 連鎖で保証する監査テーブル群を提供。
  - トレーサビリティの階層化設計と設計原則（冪等性、削除不可、UTC タイムスタンプ、updated_at の運用ルール 等）をコメントで明記。
  - 主なテーブル:
    - signal_events: 戦略が生成したシグナルログ（decision フィールドに各種拒否理由等を保持）
    - order_requests: 発注要求（order_request_id を冪等キーとして扱う、order_type ごとの CHECK）
    - executions: 実際の約定ログ（broker_execution_id は証券会社の約定ID・冪等キー）
  - 監査用インデックス群（status スキャン、signal_id 関連検索、broker_order_id による一意制約等）を定義。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供:
    - conn に対して監査テーブルを追加する（冪等）。
    - 実行時に "SET TimeZone='UTC'" を実行し、すべての TIMESTAMP を UTC で保存することを明示。
    - init_audit_db は専用 DB を作成して接続を返す（親ディレクトリ自動作成、":memory:" サポート）。
- 開発者向け注意・既定値:
  - デフォルトの DB ファイル: data/kabusys.duckdb（DuckDB）、data/monitoring.db（SQLite 用既定パス）。
  - スキーマ初期化は init_schema() を呼び出して行うこと。監査テーブルは init_audit_schema() または init_audit_db() を使用。
  - 必須環境変数未設定の場合は起動時に例外となるため、.env を用意するか OS 環境変数を設定すること。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 環境変数ロード時に OS 環境変数を保護する仕組みを導入（.env/.env.local による上書きを防止）。
- .env ファイル読み込み失敗時は警告を出して安全にフォールバック。

Notes
- このバージョンは基盤部分（設定管理、永続化スキーマ、監査ログ）を整備することに注力しています。取引ロジック、ブローカー連携、戦略実装等は今後のリリースで追加予定です。
- DuckDB を利用しており、duckdb パッケージが必要です。