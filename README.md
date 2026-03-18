# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
J-Quants API や RSS を用いたデータ収集、DuckDB を用いたスキーマ定義・ETL・品質チェック、監査ログなどを含みます。

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの取得（レート制御・リトライ・自動トークンリフレッシュ対応）
- RSS からのニュース取得と前処理、銘柄（4桁コード）抽出・DuckDB への保存
- DuckDB ベースのデータスキーマ（Raw / Processed / Feature / Execution / Audit 層）定義と初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal/order/execution のトレーサビリティ用テーブル群）

設計上の特徴：
- J-Quants のレート制限（120 req/min）を守る実装
- 冪等性を意識した DB 保存（ON CONFLICT）
- Look-ahead bias を防ぐための fetched_at / UTC タイムスタンプの記録
- SSRF・XML Bomb 等に配慮した RSS 取得ロジック

---

## 機能一覧

- 環境変数 / .env ロード・管理（`kabusys.config`）
  - 自動でプロジェクトルートの `.env` / `.env.local` をロード（上書きルールあり）
  - 自動ロードを無効化する変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
- J-Quants クライアント（`kabusys.data.jquants_client`）
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
  - レート制御・リトライ（401 の自動リフレッシュ含む）
- ニュース収集（`kabusys.data.news_collector`）
  - RSS 取得、前処理（URL 除去・空白正規化）、ID 生成（正規化 URL の SHA-256 の先頭 32 文字）
  - SSRF 対策、gzip サイズ制限、defusedxml による XML 脆弱性対策
  - DuckDB への保存（raw_news, news_symbols）
- DuckDB スキーマ定義と初期化（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - `init_schema(db_path)` で初期化
- ETL パイプライン（`kabusys.data.pipeline`）
  - 日次 ETL (`run_daily_etl`)：カレンダー → 株価 → 財務 → 品質チェック
  - 差分取得・バックフィルロジック・営業日調整
- カレンダー管理（`kabusys.data.calendar_management`）
  - 営業日判定、next/prev_trading_day、get_trading_days、calendar_update_job
- 品質チェック（`kabusys.data.quality`）
  - 欠損、スパイク（前日比）、重複、日付不整合チェック
  - `run_all_checks` でまとめて実行
- 監査ログ（`kabusys.data.audit`）
  - signal_events, order_requests, executions 等の監査テーブルと初期化ヘルパー

---

## 必要条件（依存パッケージ）

最低限の主要依存（プロジェクトの pyproject/requirements に従ってください）：

- Python 3.10+（型ヒントで | を使用しているため）
- duckdb
- defusedxml

（上記はコードベースから見える依存です。実際のパッケージに合わせて pip 等でインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. Python 仮想環境を作る（任意だが推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows (PowerShell 等)
   ```

3. 開発パッケージをインストール
   - プロジェクトが配布可能なパッケージ構成なら:
     ```bash
     pip install -e .
     ```
   - 必要なライブラリを個別にインストールする場合:
     ```bash
     pip install duckdb defusedxml
     ```

4. 環境変数設定
   - プロジェクトルート（`.git` や `pyproject.toml` があるディレクトリ）に `.env` または `.env.local` を置くと自動でロードされます（読み込み順: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な環境変数（コード上で参照されている主なもの）：
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルトは development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
   KABU_API_PASSWORD=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 初期化（DuckDB スキーマ作成）

Python REPL やスクリプトから：

```python
from kabusys.data import schema

# ファイル DB を作成／初期化する例
conn = schema.init_schema("data/kabusys.duckdb")

# メモリ DB の場合
# conn = schema.init_schema(":memory:")
```

監査ログ用スキーマを個別 DB に作る例：

```python
from kabusys.data import audit
conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要な例）

- J-Quants ID トークン取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を参照
```

- 日次 ETL 実行
```python
from datetime import date
from kabusys.data import schema, pipeline

conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema を実行済みとする
result = pipeline.run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

- 市場カレンダーの夜間バッチ更新（単体）
```python
from kabusys.data import schema, calendar_management
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

- ニュース収集ジョブ（RSS を既定ソースで実行）
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")

# known_codes に有効な銘柄コードセットを与えると自動で紐付けを試みます
known_codes = {"7203", "6758", "9984"}  # 例
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- 品質チェックの実行
```python
from kabusys.data import quality, schema
conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

- 環境設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)  # KABUSYS_ENV に応じた真偽
```

注: 各関数は例外やログでエラーを通知します。実運用ではログ設定や例外ハンドリングを行ってください。

---

## 動作上の注意点 / 実装上のメモ

- J-Quants の API レート制限（120 req/min）を内部で管理しています。短時間に大量リクエストを投げないでください。
- ID トークンの自動リフレッシュ機構があり、401 時に 1 回だけリフレッシュして再試行します。
- ニュース収集は SSRF 対策、gzip サイズ制限、XML の安全パーサ（defusedxml）などを実装しています。
- DuckDB への保存は多くの場合 ON CONFLICT による冪等化を行っています（重複上書き等）。
- 環境変数の自動ロードはプロジェクトルートを .git または pyproject.toml を基準に探して .env / .env.local を読み込みます。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成（抜粋）

プロジェクトは以下のような構成です（主要ファイルのみ抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                       # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py              # J-Quants API クライアント（取得・保存）
    - news_collector.py             # RSS → raw_news / news_symbols
    - schema.py                     # DuckDB スキーマ定義 / init_schema
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        # カレンダー操作（is_trading_day 等）
    - audit.py                      # 監査ログスキーマ
    - quality.py                    # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（各モジュール内にさらに多くの関数・ヘルパーが定義されています。README の更新や外部ドキュメント（DataPlatform.md 等）がプロジェクトルートにあると想定されます。）

---

## 参考・今後の拡張案

- 実運用では Slack 通知や監視ジョブ（Airflow / Cron）から ETL を呼び出して監視することを想定しています。
- execution / strategy / monitoring パッケージは拡張ポイントです。発注ロジックや戦略バージョン管理、リアルタイム監視の実装を追加できます。

---

質問や追加したい使い方（例: CLI スクリプト、Airflow タスク例、CI テスト用のモック方法）があれば教えてください。README を用途に合わせて拡張します。