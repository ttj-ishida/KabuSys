# KabuSys

日本株の自動売買プラットフォーム向けデータパイプライン / 基盤ライブラリ

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された Python モジュール群です。  
主に以下を提供します：

- J-Quants API からの市場データ（株価、財務、JPX カレンダー）取得クライアント
- DuckDB を利用したデータスキーマ定義・初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と記事の DB 保存（SSRF対策・サイズ制限付き）
- マーケットカレンダー管理（営業日判定、次/前営業日の検索）
- 監査ログ（シグナル → 発注 → 約定 トレース）用スキーマ

設計上のポイント：
- API レート制御・リトライ・トークン自動リフレッシュ（J-Quants）
- DuckDB への冪等保存（ON CONFLICT）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集でのセキュリティ対策（defusedxml、SSRF/プライベートアドレス回避、受信サイズ制限）

---

## 主な機能一覧

- data.jquants_client
  - 株価日足、財務（四半期）、JPX カレンダーの取得
  - レートリミット（120 req/min）、指数バックオフリトライ、401 時のトークン自動更新
  - DuckDB へ冪等保存する save_* 関数

- data.schema
  - Raw / Processed / Feature / Execution / Audit 層を備えた DuckDB スキーマ定義と初期化（init_schema）

- data.pipeline
  - 差分＋バックフィル方式の日次 ETL（run_daily_etl）
  - 各種個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 品質チェック連携（data.quality）

- data.news_collector
  - RSS 取得・記事前処理・記事ID生成（正規化 URL → SHA-256）・raw_news への保存
  - 記事と銘柄コードの紐付け（news_symbols）
  - SSRF 防止、gzip サイズ保護、XML パースに defusedxml を使用

- data.calendar_management
  - market_calendar の更新ジョブ（calendar_update_job）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day

- data.quality
  - 欠損、スパイク（前日比閾値）、重複、日付不整合を検出するチェック群
  - QualityIssue オブジェクトで問題一覧を返却

- data.audit
  - 監査ログ用テーブル（signal_events, order_requests, executions）と初期化関数

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに `X | Y` を使用）
- pip が利用可能

1. リポジトリをクローン（既にある場合は不要）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作る（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   本コードベースで直接使用している主な外部依存は以下です：
   - duckdb
   - defusedxml

   インストール例：
   ```
   pip install duckdb defusedxml
   ```

   （パッケージ化されていれば `pip install -e .` や `pip install -r requirements.txt` を使用してください）

4. 環境変数（.env）を準備
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` / `.env.local` を置くと自動でロードされます（デフォルト）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   必須環境変数（最小）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション等の API パスワード（使用する場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   その他（任意/デフォルトあり）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
   - SQLITE_PATH: デフォルト `data/monitoring.db`

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単な例）

Python スクリプトや REPL から主要 API を呼び出す例を示します。

- DuckDB スキーマの初期化
  ```python
  from kabusys.data import schema

  conn = schema.init_schema("data/kabusys.duckdb")
  # またはインメモリ: conn = schema.init_schema(":memory:")
  ```

- ETL（日次パイプライン）を実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 個別 ETL（株価）実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")
  ```

- ニュース収集の実行
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes を渡すと記事から銘柄コード抽出して紐付けする
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved calendar rows: {saved}")
  ```

- 監査スキーマの追加（audit）
  ```python
  from kabusys.data.audit import init_audit_schema
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  init_audit_schema(conn)
  ```

注意点：
- J-Quants への API 呼び出しは rate limit と retry 処理が入っています。長時間ループで連続実行する場合は仕様に従ってください。
- news_collector は外部 URL を開くため、環境によってはプロキシ設定等が必要です。
- テスト用途で自動 .env ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings クラス（自動 .env 読み込み機能あり）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch_*, save_*）
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義・初期化（init_schema / get_connection）
    - pipeline.py
      - ETL パイプライン（run_daily_etl など）
    - calendar_management.py
      - market_calendar 管理・営業日ロジック
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）
    - quality.py
      - データ品質チェック
  - strategy/
    - __init__.py (戦略モジュールのためのプレースホルダ)
  - execution/
    - __init__.py (発注 / ブローカー連携のためのプレースホルダ)
  - monitoring/
    - __init__.py (監視機能のプレースホルダ)

補足：
- 多くのモジュールは DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を引数に受け取り処理する設計です。コネクションは schema.init_schema / schema.get_connection で取得してください。

---

## 知っておくと良い実装上の注意点

- config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動でロードします（環境変数が優先）。テスト時は自動ロードを無効化できます。
- jquants_client は内部で固定間隔の RateLimiter を使い 120 req/min を保つ設計です。429 の場合は Retry-After ヘッダを優先します。
- news_collector は URL のスキーム検証、プライベート IP 判定、リダイレクト時の検査、最大受信バイト数制限、gzip 解凍後のサイズ検査などセキュリティ対策を実装しています。
- DuckDB への保存は基本的に冪等（ON CONFLICT）となるよう設計されています。外部キーやインデックスも定義済みです。

---

必要であれば、README に以下を追加できます：
- CLI の使い方（スクリプトやサービス化）
- CI / CD 設定例
- サンプル .env.example ファイル
- 詳細なテーブル定義（DataSchema.md の抜粋）

追加したい内容を教えてください。