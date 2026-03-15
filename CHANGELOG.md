CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣例に従います。  
安定版リリースではセマンティックバージョニングを使用します。

フォーマット:
- Added: 新機能
- Changed: 変更
- Fixed: 修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

Unreleased
----------

- （今後の変更をここに記載）

[0.1.0] - 2026-03-15
--------------------

Added
-----

- 初回公開: KabuSys 日本株自動売買システムのベース実装を追加。
  - パッケージ公開情報
    - バージョン: 0.1.0（src/kabusys/__init__.py）
    - __all__ に data, strategy, execution, monitoring を設定し、主要サブパッケージを公開。

- 環境設定・読み込み（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを提供。
  - 自動 .env ロード機能:
    - プロジェクトルート判定に .git または pyproject.toml を使用（__file__ を起点として探索）。
    - 読み込み順序: OS 環境 > .env.local > .env（.env.local は .env を上書き）。
    - OS 環境変数を保護する protected 機構を導入。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等向け）。
  - .env のパース機能を強化:
    - "export KEY=val" 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート。
    - インラインコメントの扱い（クォート外かつ '#' の直前が空白・タブのとき）を実装。
  - 主要設定プロパティ（必須値チェック付き）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABUSYS_ENV（development / paper_trading / live のみ許容）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容）
    - デフォルト DB パス: DUCKDB_PATH -> data/kabusys.duckdb、SQLITE_PATH -> data/monitoring.db

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API クライアントを追加（株価日足、財務データ、JPX マーケットカレンダーの取得）。
  - 設計・実装のポイント:
    - レート制限: 固定間隔スロットリングで 120 req/min を保証（内部 _RateLimiter）。
    - リトライ: 指数バックオフを用いた最大 3 回リトライ（対象: ネットワークエラー、408/429/5xx）。429 の場合は Retry-After を尊重。
    - 認証の自動リフレッシュ: 401 受信時は id_token を自動リフレッシュして 1 回のみリトライ（無限再帰防止）。
    - id_token はモジュールレベルでキャッシュされ、ページネーション中に共有。
    - JSON デコード失敗時の明示的エラー。
    - Look-ahead Bias 防止のため、取得時刻 fetched_at を UTC で付与する運用を想定。
  - 公開 API:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
    - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)
      - DuckDB への保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で実装。
  - ユーティリティ: 型安全な変換関数 _to_float / _to_int を実装（空値や不正値を None にする挙動を明確化）。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - データレイヤーを 3 層（Raw / Processed / Feature）＋Execution 層で定義するスキーマを実装。
  - 主要テーブル（例）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を多数追加してデータ整合性を担保。
  - 頻出クエリ向けのインデックスを定義（コード×日付検索やステータス検索など）。
  - 公開 API:
    - init_schema(db_path) -> DuckDB 接続（:memory: 対応、親ディレクトリ自動作成、冪等）
    - get_connection(db_path) -> DuckDB 接続（スキーマ初期化は行わない）

- 監査ログ（トレーサビリティ）スキーマ（src/kabusys/data/audit.py）
  - シグナルから約定までのトレーサビリティを保持する監査テーブル群を追加。
  - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を想定。
  - テーブル:
    - signal_events（シグナル生成ログ、拒否やエラーも保存）
    - order_requests（発注要求、order_request_id を冪等キーとして利用）
    - executions（証券会社から返された約定ログ、broker_execution_id をユニークキーとして冪等性を確保）
  - 制約・チェックとインデックスを多数追加（status 検索や signal_id / broker_order_id による検索最適化）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。
  - 監査用接続では TimeZone='UTC' を設定して TIMESTAMP を UTC で保存する運用を明確化。

- パッケージ構造
  - placeholder として空のパッケージ __init__.py を strategy, execution, monitoring に追加（将来的な戦略・実行・監視ロジックの拡張場所）。

Changed
-------

- （初回リリースのため該当なし）

Fixed
-----

- （初回リリースのため該当なし）

Deprecated / Removed / Security
-------------------------------

- （初回リリースのため該当なし）

注意・移行メモ
---------------

- スキーマ初期化は冪等です。既存テーブルがあっても上書きされませんが、DDL や制約の変更時は手動での移行が必要になる場合があります。
- デフォルトの DuckDB ファイルパスは data/kabusys.duckdb です。init_schema() は親ディレクトリを自動作成します。
- 監査ログ側は TIMESTAMP を UTC で保存するため、アプリ側はタイムゾーンを意識して取り扱ってください。
- 自動 .env ロードはプロジェクトルートの検出に依存します。パッケージ配布後や特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。

著者
----

- KabuSys 開発チーム（コードベースから推測して自動生成）