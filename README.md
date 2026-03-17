# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants や RSS フィード、kabu ステーション（発注系）などの外部データ・サービスと連携し、データ収集（ETL）、品質チェック、ニュース収集、マーケットカレンダー管理、監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

このプロジェクトは以下の目的を持ちます:

- J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを取得する
- RSS フィードからニュースを収集して正規化・保存する
- DuckDB 上に Data Lake スキーマを用意し、Raw / Processed / Feature / Execution 層を管理する
- ETL パイプライン（差分更新、バックフィル、品質チェック）を実装する
- マーケットカレンダーや営業日判定、監査ログ（発注→約定のトレーサビリティ）を提供する

設計上のポイント:
- API レート制限・リトライ・トークン自動リフレッシュを備えた堅牢なクライアント
- DuckDB への冪等保存（ON CONFLICT / INSERT ... RETURNING 等）による安全なデータ更新
- SSRF 対策、XML インジェクション対策、レスポンスサイズ制限などセキュリティ考慮
- ETL は各ステップを独立してエラーハンドリングし、品質チェックを実施

---

## 機能一覧

- data.jquants_client
  - J-Quants API クライアント（ID トークン管理、リトライ、レートリミット）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB に保存するための save_* 関数（冪等）

- data.news_collector
  - RSS フィード取得・XML パース（defusedxml 使用）
  - URL 正規化（トラッキングパラメータ除去）・記事ID の生成（SHA-256）
  - raw_news への保存（チャンク/トランザクション）と銘柄コード抽出・紐付け

- data.schema
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) でテーブルとインデックスを生成

- data.pipeline
  - 日次 ETL（run_daily_etl）
  - 差分取得・バックフィル・品質チェック（quality モジュールを利用）
  - run_prices_etl / run_financials_etl / run_calendar_etl

- data.calendar_management
  - market_calendar 管理・夜間更新ジョブ（calendar_update_job）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day

- data.audit
  - 監査ログ（signal_events / order_requests / executions）スキーマと初期化
  - init_audit_schema / init_audit_db

- data.quality
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - run_all_checks で一括実行し QualityIssue を返す

- config
  - 環境変数管理（.env の自動読み込み、Settings クラス）
  - 必須変数チェック、環境モード（development / paper_trading / live）とログレベルの検証

---

## セットアップ手順

前提: Python 3.9+（型ヒントで標準 library の union 型などを使用）。プロジェクトのパッケージ化方法に応じて適宜調整してください。

1. リポジトリをクローン

   git clone <リポジトリ URL>
   cd <repo>

2. 仮想環境を作成・有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール

   最低限必要なパッケージ（一例）:
   - duckdb
   - defusedxml

   例:

   pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）
   開発用にローカルパッケージとしてインストールするには:

   pip install -e .

4. 環境変数の設定

   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須の環境変数（Settings で必須とされているもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   オプション / デフォルト:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
   - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH: デフォルト "data/monitoring.db"

   例 `.env`:

   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB スキーマの初期化

   Python REPL やスクリプトで:

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # 親ディレクトリを自動作成
   conn.close()

   監査ログ用スキーマを別 DB に分けたい場合:

   from kabusys.data import audit
   conn = audit.init_audit_db("data/audit.duckdb")
   conn.close()

---

## 使い方（主要な実行例）

以下はライブラリ API を使った簡単な呼び出し例です。実運用ではロギングや例外処理、スケジューラ（cron / Airflow / systemd timer 等）を組み合わせてください。

1. 日次 ETL を実行する

   from datetime import date
   from kabusys.data import schema, pipeline

   conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema を実行済みとする
   result = pipeline.run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

   run_daily_etl は市場カレンダー、株価、財務データの取得・保存と品質チェックを順次実行します。戻り値は ETLResult で取得件数や検出された品質問題を含みます。

2. 単体 ETL（価格のみ）を実行する

   from datetime import date
   from kabusys.data import schema, pipeline

   conn = schema.get_connection("data/kabusys.duckdb")
   fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
   print(f"fetched={fetched}, saved={saved}")

3. RSS ニュース収集ジョブを実行する

   from kabusys.data import schema, news_collector

   conn = schema.get_connection("data/kabusys.duckdb")
   # known_codes は銘柄抽出に使う有効なコード集合。ない場合は紐付けを行わない。
   known_codes = {"7203", "6758", "9984"}
   results = news_collector.run_news_collection(conn, known_codes=known_codes)
   print(results)

4. マーケットカレンダーの夜間更新

   from kabusys.data import schema, calendar_management

   conn = schema.get_connection("data/kabusys.duckdb")
   saved = calendar_management.calendar_update_job(conn)
   print(f"calendar saved: {saved}")

5. J-Quants の ID トークン取得（テスト用）

   from kabusys.data.jquants_client import get_id_token
   token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN が必要

注意点:
- 実運用（live）では KABUSYS_ENV を `live` に設定し、十分なログ・モニタリング・二重送信防止（order_request の冪等キー）を行ってください。
- API キーやトークンは厳重に管理し、リポジトリに入れないでください。

---

## ディレクトリ構成

プロジェクトの主要ファイル / モジュールは以下のとおりです（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                -- 環境変数 / Settings
    - data/
      - __init__.py
      - jquants_client.py      -- J-Quants API クライアント、保存用関数
      - news_collector.py      -- RSS ニュース収集・保存
      - schema.py              -- DuckDB スキーマ定義 / 初期化
      - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py -- マーケットカレンダー管理
      - audit.py               -- 監査ログスキーマ（信号→注文→約定の追跡）
      - quality.py             -- データ品質チェック
    - strategy/
      - __init__.py            -- 戦略層（入出力インターフェース）
    - execution/
      - __init__.py            -- 発注・約定・ブローカー連携（placeholder）
    - monitoring/
      - __init__.py            -- 監視関連（placeholder）

主要な役割:
- data/schema.py: DB スキーマを全て定義し init_schema で作成します。
- data/jquants_client.py: API 呼び出し、レート制御、トークン管理、データ取得と保存。
- data/pipeline.py: 差分取得・バックフィル・品質チェックを含む日次 ETL。
- data/news_collector.py: RSS 取得、前処理、DuckDB への保存、銘柄抽出。

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルト値あり:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
- KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動読み込みを無効化

設定は .env（プロジェクトルート）または環境変数で行います。config.Settings クラス経由でアクセスできます（例: from kabusys.config import settings）。

---

## 運用・セキュリティ上の注意

- API トークン・パスワードは決して公開リポジトリに含めないでください。`.gitignore` に `.env.local` / `data/` 等を追加してください。
- J-Quants やブローカー API のレート制限に従ってください（jquants_client はデフォルトで 120 req/min を守る実装）。
- RSS 取得は外部 URL を扱うため、SSRF や XML Bomb などの対策が入っていますが、許可するソースは厳格に管理してください。
- DuckDB ファイルは同時アクセスやロックの制約を運用設計で考慮してください（複数プロセスでの書き込みなど）。
- 実際に発注する機能を利用する場合は sandbox / paper_trading で十分にテストしてください。

---

## 開発・拡張ガイド

- 戦略層 (kabusys.strategy) と発注層 (kabusys.execution) はプレースホルダです。ここに戦略ロジック・ポジション管理・ブローカ連携を実装します。
- テスト時は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットして .env の自動読み込みを無効化できます。
- news_collector._urlopen や jquants_client のネットワーク呼び出しはテスト用にモック可能な設計になっています。
- DuckDB のスキーマは DataPlatform.md（設計書）に基づくので、実装やマイグレーション時は互換性に留意してください。

---

必要であれば以下を追加で提供できます:
- Dockerfile / docker-compose の例
- 実運用向けの systemd unit / cron ジョブテンプレート
- テスト用モック・ユーティリティのサンプル

ご希望があればどれを追加するか教えてください。