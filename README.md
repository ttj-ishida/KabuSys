# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
J-Quants や RSS を用いたデータ収集、DuckDB スキーマ定義、ETL パイプライン、データ品質チェック、監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の役割を持つ内部ライブラリ群を含むプロジェクトです。

- J-Quants API から株価・財務・カレンダー等のデータを取得して DuckDB に保存するクライアント／保存ロジック
- RSS フィードからニュースを収集・正規化して DuckDB に保存するニュース収集器
- DuckDB のスキーマ定義と初期化ユーティリティ（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（シグナル → 発注 → 約定のトレース用テーブル群）
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）

設計上のポイント:
- J-Quants のレート制限（120 req/min）やリトライ、トークン自動リフレッシュに対応
- ETL と DB 保存は冪等性を重視（ON CONFLICT を活用）
- RSS 収集は SSRF / XML Bomb / 大容量レスポンス等の安全対策を実装
- 監査ログは削除せず時系列トレースを保証（UTC タイムスタンプ）

---

## 機能一覧

- データ取得
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（J-Quants）
  - RSS フィード取得（gzip, リダイレクト検査, トラッキングパラメータ除去）
- データ保存（DuckDB）
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - save_raw_news / save_news_symbols（ニュースと銘柄の紐付け）
- ETL
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl（まとめて差分取得・保存・品質チェック）
- カレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job（夜間バッチでカレンダー更新）
- データ品質チェック
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks（総合チェック）
- スキーマ初期化
  - init_schema（全レイヤー）、init_audit_schema / init_audit_db（監査ログ用）
- 環境設定管理
  - 自動 .env ロード（プロジェクトルート検出）
  - Settings オブジェクト経由で設定取得（必須環境変数のチェック）
- 監査
  - signal_events, order_requests, executions 等のテーブル

---

## 必要環境 / 依存ライブラリ

最低限の依存（代表的なもの）:
- Python 3.10+
- duckdb
- defusedxml

（標準ライブラリで実装されている部分が多いため、プロジェクトで必要なパッケージは環境に応じて requirements.txt を用意してください。）

---

## セットアップ手順

1. リポジトリをクローンし、任意の仮想環境を作成・有効化します。

   ```bash
   git clone <リポジトリURL>
   cd <リポジトリ>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストールします（例）:

   ```bash
   pip install duckdb defusedxml
   ```

   プロジェクトに requirements.txt があればそれを使ってください。

3. 環境変数の準備

   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると無効化可能）。
   - 必須環境変数（Settings で明示）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
   - 例 (.env):

     ```
     JQUANTS_REFRESH_TOKEN=xxxx...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO
     KABUSYS_ENV=development
     ```

---

## 初期化（DuckDB スキーマ）

DuckDB のスキーマを作成するには、Python から `init_schema` を呼び出します。

サンプル:

```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリは自動作成）
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

監査ログ（audit）テーブルだけを初期化する場合:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

既存 DB に接続するには:

```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

---

## 使い方（代表的な API）

1. 日次 ETL 実行（株価・財務・カレンダーの差分取得 + 品質チェック）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

run_daily_etl はエラーや品質問題を ETLResult オブジェクトで返します。

2. 個別 ETL（株価のみ等）

```python
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

3. RSS ニュース収集ジョブ

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
results = run_news_collection(conn)
print(results)  # {source_name: new_records_count}
```

4. カレンダー更新ジョブ（夜間バッチ）

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved calendar entries: {saved}")
```

5. 品質チェックを個別に呼ぶ

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

6. J-Quants トークン取得（内部的に使われますが、手動取得も可能）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使う
```

---

## 設定／挙動に関する注意点

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` と `.env.local` を読み込みます。テスト等で無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Settings クラスは必須変数未設定時に ValueError を投げます。
- J-Quants API クライアントはレート制限・リトライ・401 自動リフレッシュ（1回）を備えています。ページネーション対応で pagination_key を利用します。
- RSS 収集では SSRF/プライベートアドレスチェック、gzip 大きさ制限、XML パースの安全化（defusedxml）を行っています。
- DuckDB に保存する際はできる限り冪等性（ON CONFLICT）を担保しています。

---

## ディレクトリ構成

（src 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得 + 保存）
    - news_collector.py     — RSS ニュース収集器（取得・前処理・保存）
    - schema.py             — DuckDB のスキーマ定義と初期化
    - pipeline.py           — ETL パイプライン（差分更新・統合）
    - calendar_management.py— 市場カレンダー管理（営業時間判定等）
    - audit.py              — 監査ログテーブル定義・初期化
    - quality.py            — データ品質チェック
  - strategy/
    - __init__.py
    —（戦略実装用モジュールを配置）
  - execution/
    - __init__.py
    —（発注 / 約定連携用モジュールを配置）
  - monitoring/
    - __init__.py
    —（モニタリング関連モジュールを配置）

---

## 開発・テストについて（短いメモ）

- settings の自動ロードを無効にしてユニットテストを行う場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ネットワーク依存部（_urlopen / HTTP クライアント、J-Quants クライアント）はテストでモック差替えがしやすい設計になっています（モジュール関数をモック）。
- DuckDB はインメモリ ":memory:" を使って高速にテストできます。

---

必要に応じて README にコマンドラインツールや CI ワークフローの説明、requirements.txt の具体化、サンプル .env.example を追加できます。具体的に追記したい項目があれば教えてください。