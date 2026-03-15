Keep a Changelog
=================

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
リリース日付は本リポジトリの現状（このコードベース）から推測して設定しています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-15
------------------

初期リリース。日本株自動売買システム「KabuSys」のコア基盤を提供します。

Added
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - __all__ に data / strategy / execution / monitoring を公開。

- 設定管理（kabusys.config）
  - .env および環境変数からの設定自動読み込み機能を実装。
    - プロジェクトルートは __file__ から上位ディレクトリを探索し .git または pyproject.toml で判定（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パーサは export プレフィックス、シングル / ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などを考慮。
    - 読み込み失敗時は警告を出力（warnings.warn）。
  - Settings クラスを実装し、アプリで利用する主要設定プロパティを提供:
    - J-Quants / kabu ステーション / Slack トークン関連の必須項目取得（未設定時は ValueError を送出）。
    - DB パス（DuckDB, SQLite）のデフォルトと Path 型での取得。
    - KABUSYS_ENV の検証（development / paper_trading / live）およびログレベルの検証（DEBUG/INFO/...）。
    - ヘルパープロパティ: is_live / is_paper / is_dev。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを追加。
    - サポートするデータ: 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー。
    - API レート制限（120 req/min）に従う固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ）を実装。対象: ネットワークエラー、HTTP 408/429/5xx。最大 3 回リトライ。
    - 401 応答時は ID トークンを自動リフレッシュして 1 回リトライ（再帰防止ロジック含む）。
    - ID トークンのモジュールレベルキャッシュ（ページネーション間で共有）。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
      - 各関数は pagination_key を追跡して重複を避ける。
    - _request は JSON デコードエラーやタイムアウト等のハンドリング・ロギングを行う。
    - ロギングによる情報・警告（取得レコード数、リトライ、401 リフレッシュ等）。
  - DuckDB への永続化関数（冪等な upsert 実装）:
    - save_daily_quotes: raw_prices テーブルへ保存（ON CONFLICT DO UPDATE）。
      - fetched_at は UTC で記録（ISO 8601 'Z' 表記）。
      - PK 欠損行はスキップして警告出力。
    - save_financial_statements: raw_financials テーブルへ保存（同上）。
    - save_market_calendar: market_calendar テーブルへ保存（同上）。HolidayDivision を解釈して is_trading_day / is_half_day / is_sq_day を設定。
  - データパースユーティリティ: _to_float, _to_int（文字列・数値変換、非整合値は None）。

- データベーススキーマ（kabusys.data.schema）
  - DuckDB 用のスキーマ定義を追加（Raw / Processed / Feature / Execution の 3 層 + 実行層）。
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤー: features, ai_scores
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック・PRIMARY KEY・FOREIGN KEY 制約を付与。
  - 頻出クエリに対するインデックスを多数定義（コード×日付スキャン、ステータス検索など）。
  - init_schema(db_path) を実装: DB ファイルの親ディレクトリを自動作成し、全 DDL とインデックスを適用して接続を返す（冪等）。
  - get_connection(db_path) を実装: 既存 DB への接続を返す（スキーマ初期化は行わない）。

- 監査ログ（kabusys.data.audit）
  - 監査用テーブル群と初期化ロジックを追加（Signal → OrderRequest → Execution のトレーサビリティ）。
    - signal_events: シグナル生成ログ（ステータス列・decision 列による棄却理由の記録等）。
    - order_requests: 発注要求ログ（order_request_id を冪等キーとして実装）。order_type に応じた CHECK 制約（limit/stop の価格必須など）。
    - executions: 約定ログ（broker_execution_id を一意キーとして冪等性保持）。
  - init_audit_schema(conn) および init_audit_db(db_path) を実装。init_audit_schema は "SET TimeZone='UTC'" を実行して UTC で TIMESTAMP を保存。
  - 監査向けインデックス群を定義（status や signal_id, broker_order_id 等での検索を高速化）。
  - 設計原則に基づき、削除を前提としない（ON DELETE RESTRICT）外部キーを採用。

- 空パッケージ作成
  - kabusys.execution, kabusys.strategy, kabusys.monitoring のパッケージ（__init__）ファイルを追加（将来の実装のためのプレースホルダ）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 備考
- DuckDB の初期化関数は :memory: をサポート。ファイル DB の場合は親ディレクトリを自動作成するため手動作成は不要。
- .env 自動読み込みはプロジェクトルートの検出に依存する（.git または pyproject.toml）。配布後の挙動を考慮して実装。
- J-Quants API 呼び出しは最大 3 回のリトライを行い、429 の場合は Retry-After ヘッダを優先して待機。401 はトークンリフレッシュを試行して 1 回のみ再試行する仕組み。
- 保存関数は欠損 PK の行をスキップして警告を出す（データ品質保護のため）。
- 今後のマイナー / メジャーリリースでは strategy / execution / monitoring の実装、テスト、型注釈強化、CI・デプロイ関連の導入が想定されます。

互換性
- 本リリースは初期版のため既存との互換性に関する破壊的変更はありません。今後のメジャーアップデートでスキーマ変更が発生する可能性があります。