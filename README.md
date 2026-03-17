# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）のリポジトリ向け README。  
このドキュメントはソースコード（src/kabusys 以下）に基づき、セットアップ方法、主要機能、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／データ基盤コンポーネント群です。  
主に次を提供します。

- J-Quants API を用いた市場データ（株価・財務・マーケットカレンダー）の取得と DuckDB への永続化
- RSS ベースのニュース収集とテキスト前処理、銘柄（4桁コード）抽出・紐付け
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定・次営業日/前営業日計算・夜間更新ジョブ）
- 監査ログ（signal/order/execution のトレーサビリティ）用スキーマ初期化
- 環境変数ベースの設定管理（.env 自動読み込みをサポート）

設計上のポイント:
- API レート制限やリトライ、トークン自動リフレッシュ対応
- データ取得時の fetched_at 記録で look-ahead bias を軽減
- DuckDB への保存は冪等（ON CONFLICT で更新）を保証
- RSS の収集では SSRF / XML Bomb / メモリ DoS 対策を実装

---

## 主な機能一覧

- 環境設定管理: kabusys.config.Settings（.env 自動ロード・必須チェック）
- J-Quants クライアント: kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - 自動リトライ、レートリミット、IDトークンキャッシュ（自動リフレッシュ）
- ニュース収集: kabusys.data.news_collector
  - RSS フィード取得、前処理、ID 生成（sha256）、DuckDB への保存（冪等）
  - SSRF/リダイレクト検査、gzip サイズ制限、XML パース防御（defusedxml）
  - 銘柄コード抽出・news_symbols への紐付け
- スキーマ管理: kabusys.data.schema
  - Raw / Processed / Feature / Execution 層の DuckDB テーブル定義と初期化
- ETL パイプライン: kabusys.data.pipeline
  - run_daily_etl を筆頭に prices/financials/calendar の差分取得と保存
  - 品質チェック呼び出し（kabusys.data.quality）
- 品質チェック: kabusys.data.quality
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue オブジェクトを返す）
- カレンダー運用: kabusys.data.calendar_management
  - 営業日判定・前後営業日取得・夜間カレンダー更新ジョブ
- 監査ログ: kabusys.data.audit
  - signal_events / order_requests / executions を含む監査テーブルの初期化

---

## 動作要件（想定）

- Python 3.10 以上（型ヒントに | 演算子等を使用）
- 必要パッケージ（主なもの）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

実際のプロジェクトでは requirements.txt を用意してください（本サンプルではソース内から依存関係を推測しています）。

---

## セットアップ手順

1. リポジトリをクローン、作業ディレクトリへ移動

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境の作成（推奨）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージのインストール（例）

   ```bash
   pip install duckdb defusedxml
   ```

4. 環境変数（.env）を準備

   - プロジェクトルートに `.env` または `.env.local` を配置すると、自動的に読み込まれます（ただしテスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください）。
   - 必須環境変数（Settings で必須となるもの）:

     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID

   - 任意 / デフォルトあり:

     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG|INFO|...) — default: INFO
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすることで自動ロードを無効化

   - .env の例:

     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. データベース初期化（DuckDB）

   Python REPL やスクリプトから次を実行してスキーマを作成します。

   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)
   ```

   - ":memory:" を指定するとメモリ DB を使用します。
   - init_schema は冪等で、既存テーブルは上書きしません。

6. 監査ログテーブルの初期化（必要に応じて）

   ```python
   from kabusys.data import audit
   audit.init_audit_schema(conn)
   # or audit.init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要な実行例）

下は代表的な API 呼び出し例です。実運用では適切にログ設定、例外処理、スケジューラ（cron / Airflow / systemd timer 等）を組み合わせてください。

- 日次 ETL を実行（市場カレンダー→株価→財務→品質チェック）

  ```python
  from kabusys.data import schema, pipeline
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブのみ実行

  ```python
  from kabusys.data import calendar_management, schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)  # 既存 DB に接続
  saved = calendar_management.calendar_update_job(conn)
  print("calendar saved:", saved)
  ```

- RSS ニュース収集ジョブ実行

  ```python
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # sources を省略するとデフォルトの RSS ソースを使用
  # known_codes に既知の 4 桁銘柄コードセットを渡すと銘柄紐付けを行う
  known_codes = {"7203", "6758"}  # 例: 有効銘柄コードセット
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants から株価を手動取得して保存

  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(settings.duckdb_path)
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"fetched {len(records)} saved {saved}")
  ```

---

## ディレクトリ構成

主要なファイルとモジュール（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py
    - Settings: 環境変数読み込み・必須チェック・auto .env ロード
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（rate limiting / retry / token refresh）
      - fetch_* / save_* 関数
    - news_collector.py
      - RSS 収集、前処理、DuckDB 保存、銘柄抽出
    - schema.py
      - DuckDB の DDL（Raw / Processed / Feature / Execution レイヤー）
      - init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py
      - 営業日判定、calendar_update_job
    - audit.py
      - 監査ログスキーマ（signal_events / order_requests / executions）
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py (戦略関連は拡張箇所)
  - execution/
    - __init__.py (発注 / 約定処理は拡張箇所)
  - monitoring/
    - __init__.py (監視用コードを配置する場所)

---

## 設計上の注意点・運用メモ

- 環境変数未設定時は Settings のプロパティが ValueError を投げます。必須変数は .env を用意してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を起点に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- J-Quants API はレート制限（120 req/min）を厳守するため、client は固定間隔のスロットリングを実装しています。大量取得を並列で行うと制限に接触する可能性があります。
- fetch_* は pagination に対応しています。fetch の際は id_token の自動キャッシュ（_ID_TOKEN_CACHE）を利用します。
- ニュース収集は SSRF 対策、gzip サイズ制限、XML パースの安全化など複数の防御機構を持っています。RSS フィードの URL は http/https のみ許可されます。
- DuckDB スキーマは初期化時に索引を作成します。init_schema は冪等（存在するテーブルはスキップ）です。
- 品質チェック（quality.run_all_checks）はエラー／警告を列挙して返すだけで、ETL の停止／継続は呼び出し側で判断してください。
- 監査ログは UTC タイムゾーンで扱うように設計されています（audit.init_audit_schema は SET TimeZone='UTC' を実行します）。

---

## トラブルシューティング

- .env が読み込まれない / テストで環境を切り替えたい
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- J-Quants の認証エラー（401）が出る
  - JQUANTS_REFRESH_TOKEN が正しいか確認。クライアントは 401 時に一度だけ自動的にトークンをリフレッシュして再試行します。
- RSS 取得でリダイレクト先が内部アドレスと判定される
  - SSRF 防御のため、プライベートIP/ループバックへのアクセスは拒否されます。外部公開の RSS を使用してください。

---

必要に応じて README を拡張して、CI/CD、テスト方法、運用 runbook、依存関係固定 (requirements.txt / poetry) などの項目を追加してください。