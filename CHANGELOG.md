KEEP A CHANGELOG
すべての変更は https://keepachangelog.com/ja/ に準拠して記載します。

[Unreleased]

0.1.0 - 2026-03-15
------------------
Added
- 初回リリース。パッケージ名: kabusys、バージョン __version__ = "0.1.0" を追加。
- パッケージ構成:
  - kabusys: package エントリ（__all__ に data, strategy, execution, monitoring を公開）。
  - 空のモジュールプレースホルダ: kabusys.execution, kabusys.strategy, kabusys.monitoring（将来的な実装のために用意）。
- 環境変数・設定管理 (src/kabusys/config.py)
  - Settings クラスを導入し、環境変数から設定を取得するプロパティを提供。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得。
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）を Path 型で取得。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）と便捷な is_dev / is_paper / is_live プロパティ。
    - LOG_LEVEL のバリデーション（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
  - .env ファイル自動読み込み:
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env、.env.local を自動読み込み。
    - 読み込み順: OS 環境変数 > .env.local > .env。既存の OS 環境変数は保護される（protected set）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサ:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮した解析。
    - クォートなしの場合のコメント扱い（# の直前が空白/タブのときだけコメントとみなす）など、堅牢なパース実装。
  - _require ヘルパーにより必須環境変数未設定時は ValueError を送出。

- DuckDB スキーマおよび初期化 API (src/kabusys/data/schema.py)
  - データレイヤー（Raw / Processed / Feature / Execution）に対応するテーブル定義を追加。
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤー: features, ai_scores
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに主キー・チェック制約（非負チェック、列整合性チェックなど）を設定してデータ整合性を担保。
  - 外部キー制約（news_symbols → news_articles、orders → signal_queue など）を定義。
  - 頻出クエリを想定したインデックスを定義（コード×日付、ステータス検索、FK 結合用など）。
  - init_schema(db_path)：
    - 指定した DuckDB ファイルを初期化し、全テーブルとインデックスを作成して接続を返す。
    - 冪等（既存テーブルはスキップ）。
    - db_path の親ディレクトリが無ければ自動作成。":memory:" をサポート。
  - get_connection(db_path)：既存 DB への接続を返す（スキーマ初期化は行わない）。

- 監査ログ（トレーサビリティ）: Data audit モジュール (src/kabusys/data/audit.py)
  - 監査用テーブル群を追加（戦略→シグナル→発注→約定 までを UUID で連鎖してトレース可能）。
    - signal_events: 戦略が生成した全シグナル（棄却・エラー含む）を記録。decision と reason を保持。
    - order_requests: 発注要求（order_request_id を冪等キーとして定義）。order_type に応じた CHECK 制約（limit/stop の価格必須など）。
    - executions: 証券会社から返された約定情報を記録。broker_execution_id をユニーク（冪等キー）として扱う。
  - 監査テーブルのインデックスを追加（date/code 検索、status キュー走査、broker_order_id 紐付けなど）。
  - init_audit_schema(conn)：既存の DuckDB 接続に監査テーブルを追加（冪等）。
    - すべての TIMESTAMP を UTC で保存するために SET TimeZone='UTC' を実行。
  - init_audit_db(db_path)：監査専用 DB を初期化して接続を返す（親ディレクトリ自動作成、":memory:" 対応）。

Changed
- n/a（初回リリースのため変更履歴なし）

Fixed
- n/a（初回リリースのため修正履歴なし）

Notes / 設計方針
- スキーマ定義は DataSchema.md / DataPlatform.md に準拠した構成を意図している（ファイル中に参照あり）。
- スキーマ初期化は冪等性を重視し、運用中に再実行しても安全になるよう設計。
- 監査ログは基本的に削除しない前提（FK は ON DELETE RESTRICT）で監査証跡を保持。
- .env 自動読込は開発利便性のために導入。ただしテストや特殊環境では無効化可能。
- 今後のリリースで strategy/ execution/ monitoring モジュールに具体的ロジック（シグナル生成・注文送信・モニタリング）を追加予定。

なお、詳細な仕様や設計文書はソース内の docstring（DataSchema.md / DataPlatform.md 参照）を参照してください。