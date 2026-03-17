KabuSys — 日本株自動売買基盤（README）
=================================

概要
----
KabuSys は日本株のデータ取得・ETL・品質チェック・ニュース収集・監査ログなどを備えた自動売買プラットフォームのライブラリ群です。  
主な目的は、外部 API（J-Quants 等）からのデータ取得を堅牢に行い、DuckDB ベースのデータレイヤ（Raw / Processed / Feature / Execution）を管理して、戦略や発注系へ安全にデータを提供することです。

主要な設計方針（抜粋）
- API レート制限・リトライ・トークン自動リフレッシュを内包した安全なクライアント実装
- データの冪等保存（ON CONFLICT 句）による安全な再実行
- News RSS の SSRF／XML攻撃・サイズ攻撃対策
- DuckDB による軽量で高速なローカルデータベース管理
- 品質チェック（欠損・スパイク・重複・日付整合性）を組み込み

機能一覧
--------
- データ取得（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーの取得
  - レート制限（120 req/min）と指数バックオフを伴うリトライ、401時のトークン自動リフレッシュ
  - DuckDB への冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分算出・バックフィル）
  - 日次 ETL（run_daily_etl）でカレンダー→株価→財務→品質チェックを実行

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、期間の営業日列挙
  - 夜間バッチでカレンダー更新（calendar_update_job）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理（URL除去・空白正規化）・記事ID生成（正規化 URL の SHA-256）
  - SSRF 対策、gzip サイズ検査、defusedxml による安全なパース
  - raw_news への冪等保存・銘柄コード抽出（extract_stock_codes）と news_symbols への紐付け

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出
  - 全チェック実行 API（run_all_checks）

- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution のトレーサビリティ用テーブル定義と初期化

セットアップ手順
--------------
前提
- Python 3.9+（コードは typing の一部に 3.10 の構文を使っている箇所がありますが、互換性に注意）
- DuckDB（Python パッケージ経由で使用）
- defusedxml

1. リポジトリをクローンしてパッケージをインストール（開発モード）
   ```
   git clone <repo-url>
   cd <repo-dir>
   pip install -e .
   ```
   必要なパッケージ（例）
   ```
   pip install duckdb defusedxml
   ```

2. 環境変数 / .env
   - 本ライブラリは .env/.env.local を自動でプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（Settings クラスにより参照）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API のパスワード
     - SLACK_BOT_TOKEN       : Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID      : Slack チャネル ID
   - オプション/デフォルト
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/...) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   サンプル .env（プロジェクトルートに配置）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで schema.init_schema を呼ぶ:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイル作成およびテーブル作成
   ```
   - 監査ログ用テーブルを追加する場合:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

基本的な使い方
------------

- 日次 ETL 実行（最も一般的なエントリポイント）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 個別 ETL（株価・財務・カレンダー）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- J-Quants からの直接取得（テスト等）
  ```python
  from kabusys.data import jquants_client as jq
  token = jq.get_id_token()  # settings から refresh token を使用
  records = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, known_codes={'7203','6758'})  # known_codes を渡すと銘柄紐付けを行う
  ```

- 市場カレンダー関数
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_open = is_trading_day(conn, date(2024,3,15))
  next_day = next_trading_day(conn, date(2024,3,15))
  ```

- 品質チェックを個別に/全体で実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date.today())
  for issue in issues:
      print(issue)
  ```

注意点 / 実運用上のヒント
------------------------
- API レート制限: jquants_client は 120 req/min の制限を守るための内部レートリミッタを持ちます。大量データ取得時は間隔に注意してください。
- トークンの自動リフレッシュ: 401 を受けると一度だけトークンを自動更新して再試行します。get_id_token は明示的に呼び出すことも可能です。
- ETL の再実行: 保存処理は冪等です（ON CONFLICT DO UPDATE / DO NOTHING）。バックフィル日数を調整して後出しの修正にも耐えられるように設計されています。
- News collector は外部から受け取る RSS を扱うため、SSRF 対策（内部アドレス拒否）や XML 攻撃対策を組み込んでいます。
- 環境変数自動ロード: パッケージはプロジェクトルート（.git または pyproject.toml のある場所）から .env/.env.local を自動読み込みします。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）
- src/kabusys/
  - __init__.py                          -- パッケージ定義（version 等）
  - config.py                            -- 環境設定（Settings）と .env 自動読み込み
  - data/
    - __init__.py
    - jquants_client.py                  -- J-Quants API クライアント（取得 + 保存）
    - news_collector.py                  -- RSS ニュース収集・保存・銘柄抽出
    - pipeline.py                        -- ETL パイプライン（run_daily_etl 等）
    - schema.py                          -- DuckDB スキーマ定義・初期化
    - calendar_management.py             -- カレンダー管理・営業日ロジック
    - audit.py                           -- 監査ログ（signal/order_request/execution）
    - quality.py                         -- データ品質チェック
  - strategy/
    - __init__.py                         -- 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                         -- 発注／約定管理（拡張ポイント）
  - monitoring/
    - __init__.py                         -- 監視・メトリクス（拡張ポイント）

API 参照（主な関数）
-------------------
- kabusys.config.settings
  - jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id, duckdb_path, env, log_level, is_live, is_paper, is_dev

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path)

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_prices_etl(conn, target_date, ...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, s, e)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

貢献 / 拡張ポイント
-------------------
- strategy/、execution/、monitoring/ は拡張用のエントリポイントです。ここに戦略の実装、発注ラッパー、監視ダッシュボード等を追加してください。
- ニュースのソース追加は DEFAULT_RSS_SOURCES を拡張してください。
- 外部ブローカー連携は execution 層で実装し、audit の order_requests / executions と連携させるとトレーサビリティが保たれます。

ライセンス
---------
（本リポジトリに準拠するライセンス表記をここに置いてください）

補足
----
本 README は、提供されたコードベースから抽出可能な機能と想定される利用方法をまとめたものです。実運用前に機密情報の管理、API クレジット・レート制限、エラーハンドリングの追加設定（リトライポリシーや通知等）を検討してください。質問やドキュメント追加の要望があれば教えてください。