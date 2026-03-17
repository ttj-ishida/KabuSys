# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得（J-Quants）、ETLパイプライン、データ品質チェック、ニュース収集、監査ログ／実行用スキーマなどを提供します。

---

## プロジェクト概要

KabuSys は日本株を対象としたデータ基盤と自動売買のための共通機能群をまとめた Python モジュール群です。主な役割は以下です。

- J-Quants API からのマーケットデータ取得（株価日足・財務データ・マーケットカレンダー）
- DuckDB を利用したデータスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS からのニュース収集と銘柄抽出
- 監査ログ（信号→発注→約定のトレーサビリティ）用スキーマ
- カレンダー（営業日）管理、ニュースの安全な取得（SSRF対策等）

設計方針として、API レート制限・リトライ・冪等性（ON CONFLICT）・トレーサビリティ・セキュリティ（XML脆弱性対策、SSRF 対策など）を重視しています。

---

## 機能一覧

- 環境設定読み込み（.env / .env.local 自動ロード、環境変数優先）
- J-Quants クライアント
  - トークンリフレッシュ（自動）
  - レート制御（120 req/min）
  - リトライ（指数バックオフ、401 の自動リフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への冪等保存 save_* 系関数
- DuckDB スキーマ管理
  - init_schema(db_path)：全テーブル・インデックス作成（Raw / Processed / Feature / Execution）
  - get_connection(db_path)
- ETL パイプライン
  - run_daily_etl：カレンダー取得→株価差分取得→財務差分取得→品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
  - 差分更新・バックフィル対応
- データ品質チェック（quality モジュール）
  - 欠損検出、スパイク検出、重複、日付不整合
  - QualityIssue オブジェクトで結果返却
- ニュース収集（news_collector）
  - RSS フィード取得（gzip 対応、最大受信サイズ制限）
  - defusedxml による安全な XML パース
  - URL 正規化・記事ID生成（SHA-256 の先頭32文字）
  - SSRF 対策（スキームチェック、プライベートホストの拒否、リダイレクト検証）
  - raw_news / news_symbols への冪等保存（INSERT ... RETURNING）
- カレンダー管理（market_calendar）
  - 営業日判定・次/前営業日の取得・期間内営業日列挙
  - 夜間バッチでのカレンダー差分更新
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査スキーマ
  - init_audit_db / init_audit_schema

---

## セットアップ手順

前提：
- Python 3.8+（プロジェクトの型ヒントで | を使っているため 3.10+ が推奨される可能性があります）
- Git（プロジェクトルート自動検出に利用）

1. リポジトリをクローンして作業ディレクトリへ移動

   ```
   git clone <repo-url>
   cd <project-root>
   ```

2. 仮想環境の作成（例）

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージのインストール

   必須ライブラリ（主要なもの）:
   - duckdb
   - defusedxml

   例:

   ```
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt または pyproject.toml がある場合はそちらを使用してください）

4. 環境変数の設定

   プロジェクトでは以下の環境変数を使用します。最低限必要なのは J-Quants のリフレッシュトークン等、機能を利用するモジュールに応じて必要な変数を設定してください。

   必須（主要）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API のパスワード（実行モジュールが使用する場合）
   - SLACK_BOT_TOKEN — Slack 通知を使う場合
   - SLACK_CHANNEL_ID — Slack チャネルID

   任意 / デフォルトあり:
   - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

   .env の例（プロジェクトルートに配置）:

   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   注意: config モジュールは自動でプロジェクトルートの .env / .env.local を読み込みます（OS 環境変数が優先）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動ロードを無効にできます。

5. データベースの初期化（DuckDB）

   例：デフォルトパスへスキーマを作成する

   ```python
   >>> from kabusys.data import schema
   >>> conn = schema.init_schema("data/kabusys.duckdb")
   >>> conn.close()
   ```

   監査ログ専用 DB を作る場合：

   ```python
   >>> from kabusys.data import audit
   >>> audit_conn = audit.init_audit_db("data/audit_kabusys.duckdb")
   >>> audit_conn.close()
   ```

---

## 使い方（簡易例）

以下は代表的な利用例です。プロダクション実行は適宜ログ・例外処理やスケジューラ（cron / Airflow 等）で管理してください。

1. 日次 ETL を実行する（J-Quants からデータを取得して保存、品質チェックまで実行）

   ```python
   from datetime import date
   from kabusys.data import schema, pipeline
   from kabusys.config import settings

   # DB を初期化済みであれば get_connection を使っても良い
   conn = schema.init_schema(settings.duckdb_path)

   # 本日をターゲットに日次 ETL を実行
   result = pipeline.run_daily_etl(conn, target_date=date.today())

   print(result.to_dict())
   conn.close()
   ```

   - run_daily_etl はカレンダー→株価→財務→品質チェックの順に処理します。
   - id_token を外から注入してテストすることも可能です。

2. ニュース収集ジョブ実行例

   ```python
   from kabusys.data import news_collector, schema

   conn = schema.get_connection("data/kabusys.duckdb")
   # 既知銘柄コードセットを渡すと銘柄紐付けが行われる
   known_codes = {"7203", "6758", "9984"}  # 例
   results = news_collector.run_news_collection(conn, known_codes=known_codes)
   print(results)
   conn.close()
   ```

3. J-Quants から株価を直接取得する（テストやユーティリティ向け）

   ```python
   from kabusys.data import jquants_client as jq

   token = jq.get_id_token()  # settings からリフレッシュトークンを参照
   records = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
   ```

4. 監査ログ初期化（別DBまたは同DBへ追加）

   ```python
   from kabusys.data import audit, schema
   conn = schema.get_connection("data/kabusys.duckdb")
   audit.init_audit_schema(conn)  # 既存接続に監査テーブルを追加
   ```

---

## 主要な API / モジュール一覧（抜粋）

- kabusys.config
  - settings: アプリ設定アクセサ（settings.jquants_refresh_token 等）
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.quality
  - run_all_checks(conn, ...)
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.audit
  - init_audit_db(db_path), init_audit_schema(conn, transactional=False)

---

## 開発・テストに関するメモ

- 環境変数の自動読み込みは config モジュールがプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込みます。テスト時に自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector では外部ネットワークアクセスを行うため、ユニットテストでは kabusys.data.news_collector._urlopen をモックして外部依存を切り離してください。
- J-Quants API のレート制御はモジュール内の _RateLimiter で行われますが、同一プロセス内で複数のクライアントを起動する場合や並列化する場合は注意が必要です。

---

## ディレクトリ構成

以下は本リポジトリに含まれる主要ファイル（本ドキュメント作成時点）のツリー（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/ (__init__.py)
    - strategy/ (__init__.py)
    - monitoring/ (__init__.py)
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - quality.py

各モジュールは責務ごとに分かれており、データ取得・保存、ETL、品質チェック、ニュース収集、監査ログがそれぞれ独立してテスト・運用できるよう設計されています。

---

## ライセンス／貢献

（ここにライセンス情報とコントリビュート方法を記載してください）

---

README に不足している具体的な実行例や CI/デプロイ手順、API キーの取得方法などがありましたら、使用ケースに合わせて追記します。必要な出力形式（日本語の説明をさらに簡潔に、あるいは英語版 README も作成など）があれば教えてください。