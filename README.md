# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETLパイプライン、DuckDBスキーマ、ニュース収集、監査ログなどの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための内部ユーティリティ群です。  
主に以下の責務を持つモジュールで構成されています。

- J-Quants API からの市場データ取得（OHLCV、財務データ、JPXカレンダー）
- ニュース（RSS）収集と銘柄紐付け
- DuckDB を用いたスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev）
- 監査ログ（シグナル→発注→約定のトレース可能化）
- 環境変数管理（.env の自動読み込み、必須設定の検証）

設計では、API レート制限遵守、リトライ戦略、冪等性（ON CONFLICT）、Look-ahead バイアス防止（fetched_at の記録）等を重視しています。

---

## 機能一覧

- データ取得（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの取得
  - レートリミット制御、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（kabusys.data.news_collector）
  - RSS から記事を取得し前処理して raw_news に保存
  - URL 正規化（トラッキングパラメータ除去）、SSRF防止、gzip 除去、XML攻撃対策（defusedxml）
  - 記事IDは正規化URLの SHA-256（先頭32文字）で冪等性を保証
  - 銘柄コード抽出と news_symbols への紐付け
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義・初期化
  - インデックス定義、DuckDB 初期化ユーティリティ（init_schema / get_connection）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新・バックフィル・品質チェック（kabusys.data.quality）
  - run_daily_etl による一括 ETL 実行（カレンダー → 株価 → 財務 → 品質チェック）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、期間内営業日取得、夜間カレンダー更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のテーブルと初期化ユーティリティ
  - UTC タイムゾーン固定、冪等キー（order_request_id）等
- 環境設定（kabusys.config）
  - .env / .env.local の自動読込（プロジェクトルート検出）
  - 必須環境変数の取得ラッパー（settings オブジェクト）
  - 自動読み込みを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## セットアップ手順

前提: Python 3.9+（typing 機能を利用）を想定しています。

1. リポジトリをクローン／プロジェクトを配置

2. 依存パッケージをインストール（例）
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例（pip）:
     ```
     pip install duckdb defusedxml
     ```

3. 環境変数を設定
   - プロジェクトルート（.git もしくは pyproject.toml のあるディレクトリ）に `.env` を作成すると自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_DISABLE_AUTO_ENV_LOAD=   # 自動ロード無効化する場合は 1 を設定
   ```

4. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで以下を実行して DB とテーブルを作成します。
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # デフォルトパスは settings.duckdb_path
   ```

5. 監査ログ用スキーマの初期化（任意）
   ```python
   from kabusys.data import audit, schema
   conn = schema.get_connection("data/kabusys.duckdb")
   audit.init_audit_schema(conn, transactional=True)
   # または専用DB:
   # audit_conn = audit.init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（簡易ガイド）

以下はよく使われる操作例です。

- 日次 ETL の実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import pipeline, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # ETL 実行（target_date を指定しなければ今日）
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- スキーマ初期化（再掲）
  ```python
  from kabusys.data import schema
  conn = schema.init_schema(":memory:")  # インメモリ DB
  ```

- ニュース収集ジョブの実行
  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes を渡すと抽出/紐付けを行う（set of "7203", ...）
  result = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})
  print(result)  # {source_name: inserted_count, ...}
  ```

- J-Quants トークン取得（内部では自動で行われますが明示的に呼ぶことも可能）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を参照
  ```

- 品質チェックを個別に実行
  ```python
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意点:
- J-Quants API は 120 req/min のレート制限を想定しており、クライアントは内部でスロットリングとリトライを行います。
- 認証トークンが 401 を返した場合、ID トークンは自動リフレッシュされて1回のみリトライされます。
- データ保存は冪等（ON CONFLICT）を基本としていますので、再実行で重複を増やしません。

---

## ディレクトリ構成

主要ファイルとモジュールの構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと設定（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、fetch_* / save_* 関数
    - news_collector.py
      - RSS 取得、前処理、raw_news 保存、銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
    - calendar_management.py
      - 営業日判定、更新ジョブ、next/prev_trading_day 等
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）初期化
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py
    - （戦略実装を置くための名前空間）
  - execution/
    - __init__.py
    - （発注・ブローカー連携を置くための名前空間）
  - monitoring/
    - __init__.py
    - （監視・アラート周りの拡張用）

プロジェクトルート（パッケージ外）
- .env, .env.local（任意）
- pyproject.toml / setup.cfg 等（パッケージ化設定）

---

## 環境変数（主なキー）

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL: kabu API のベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（default: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（default: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

自動 .env ロード:
- プロジェクトルートにある `.env` / `.env.local` を自動で読み込みます。先に OS 環境変数が優先され、.env.local が .env を上書きします。
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 補足（設計上の配慮）

- API 呼び出しはレート制限（120 req/min）およびリトライ戦略を備えています。
- データ取得時間（fetched_at）を UTC で記録して Look-ahead Bias のトレースを可能にしています。
- DuckDB のテーブルは冪等に作成／更新するよう設計されています。
- ニュース収集では SSRF や XML 攻撃、受信サイズ制限（最大 10MB）などのセキュリティ対策を実装しています。
- 品質チェックは Fail-Fast せず問題を集めて戻す設計のため、呼び出し側で対処を決められます。

---

必要なら README の英語版や、具体的なスクリプト（cron / Airflow での定期実行例）、Docker 化や CI 設定のテンプレートも作成します。どの部分を優先して追加しますか？