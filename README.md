# KabuSys

日本株自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
J-Quants / RSS 等から市場データ・ニュースを収集し、DuckDB に保存・品質検査、監査ログを記録することを主な目的としたモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の機能を持つ内部ライブラリ群です。

- J-Quants API を利用した株価（OHLCV）・財務データ・JPX マーケットカレンダーの取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- RSS フィードからのニュース収集と銘柄コード抽出（SSRF対策・XML攻撃対策・サイズ制限）
- DuckDB に対するスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日の取得）
- 監査ログ（signal → order → execution のトレース用スキーマ）
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）

設計上の特徴として、Look-ahead bias を避けるための fetched_at 記録、冪等保存（ON CONFLICT）やトランザクション管理、外部リクエスト時のセキュリティ対策（SSRF / XML bomb / レスポンスサイズ制限）などを重視しています。

---

## 機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存: save_daily_quotes, save_financial_statements, save_market_calendar
  - レート制御（120 req/min）、リトライ／バックオフ、401 の自動トークン再取得
- data.news_collector
  - RSS フィード取得（gzip 対応、SSRF リダイレクト検査）
  - 記事正規化・ID生成（URL正規化→SHA-256 前半）
  - raw_news への冪等保存、news_symbols への銘柄紐付け
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）・初期化関数 init_schema / get_connection
- data.pipeline
  - 差分 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 日次パイプライン run_daily_etl（品質チェックと連携して ETLResult を返す）
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチ更新）
- data.quality
  - 欠損データ、重複、スパイク、日付不整合などの検出（QualityIssue を返す）
- data.audit
  - 監査用スキーマ（signal_events, order_requests, executions）と初期化関数（init_audit_schema / init_audit_db）
- config
  - .env / 環境変数の自動読み込み（プロジェクトルート基準）と Settings オブジェクト

---

## セットアップ手順

前提: Python 3.8+（型注釈により 3.9+ が想定される箇所があります）。プロジェクトはパッケージ形式で配置されていることを想定します。

1. Python 環境を用意
   - 推奨: 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate (UNIX) / .venv\Scripts\activate (Windows)

2. 依存パッケージをインストール
   - 最小依存:
     - duckdb
     - defusedxml
   - 例:
     - python -m pip install --upgrade pip
     - python -m pip install duckdb defusedxml

   - （プロジェクトがパッケージ化されていれば）
     - python -m pip install -e .

3. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）が見つかると、自動的に `.env` → `.env.local` を読み込みます（OS 環境変数が優先されます）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1 / Windows 環境変数で同等設定

   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - 任意
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）

   - 例：.env（最小）
     - JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

4. データベース初期化
   - DuckDB スキーマを作成:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - 監査ログスキーマを追加:
     - from kabusys.data.audit import init_audit_schema
     - init_audit_schema(conn)
   - 監査専用 DB を別で初期化する場合:
     - from kabusys.data.audit import init_audit_db
     - audit_conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主要ユースケース）

以下は代表的なサンプルコードです。実際はログ設定や例外処理を適宜追加してください。

1. DuckDB の初期化

```python
from kabusys.data.schema import init_schema

# デフォルトの場所: data/kabusys.duckdb
conn = init_schema("data/kabusys.duckdb")
```

2. 日次 ETL の実行（run_daily_etl）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())

# ETL の結果
print(result.to_dict())
if result.has_errors:
    print("ETL 中にエラーが発生しました:", result.errors)
if result.has_quality_errors:
    print("品質チェックでエラーが検出されました")
```

- 引数で id_token を注入することでテスト容易性を向上できます（jquants_client.get_id_token を使用して取得）。

3. ニュース収集ジョブの実行

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes を与えると抽出・紐付けを行う（例: {"7203", "6758", ...}）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(results)  # {source_name: new_saved_count, ...}
```

4. カレンダー更新ジョブ（バッチ）

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

5. 監査ログの初期化（既存接続へ追加）

```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)  # 監査用テーブルが追加される
```

6. J-Quants の ID トークン取得（必要な場面で）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を参照して取得
```

---

## 環境変数（主要一覧）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, 値: development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (任意, DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意, 1 を設定すると自動 .env ロードを無効化)

設定に不備があると Settings プロパティで ValueError が発生します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数・設定読み込み
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント（取得・保存）
    - news_collector.py       -- RSS ニュース収集・保存
    - pipeline.py             -- ETL パイプライン（差分取得 / 日次実行）
    - schema.py               -- DuckDB スキーマ定義・初期化
    - calendar_management.py  -- マーケットカレンダー管理ロジック
    - audit.py                -- 監査ログスキーマと初期化
    - quality.py              -- データ品質チェック
  - strategy/
    - __init__.py             -- 戦略関連（空のパッケージ）
  - execution/
    - __init__.py             -- 発注/実行関連（空のパッケージ）
  - monitoring/
    - __init__.py             -- 監視関連（空のパッケージ）

補足:
- data/schema.py にスキーマの DDL がまとまっています。init_schema() で全テーブル／インデックスを作成します。
- news_collector と jquants_client は DuckDB への保存を行うユーティリティ関数を提供します（保存は冪等設計）。

---

## 運用に関する注意点

- API レート制限を守る設計になっていますが、大量同時実行など運用負荷には注意してください（J-Quants のポリシーに従ってください）。
- .env のトークン等は取り扱いに注意してください。Git リポジトリにコミットしないでください。
- DuckDB ファイルはデフォルトで data/ 以下に作成されます。適切なバックアップ・パーミッション管理を行ってください。
- run_daily_etl の戻り値（ETLResult）をログや監視に利用して、品質チェック結果やエラー発生の検出・アラートを組み込むことを推奨します。
- RSS 取得では SSRF や XML 攻撃対策を行っていますが、外部 URL の取り扱いは常に注意してください。

---

必要であれば README に含めるサンプル .env.example、より詳細な運用手順（例: cron / systemd timer の設定、Slack 通知のサンプル）、あるいは packaging（pyproject.toml / requirements.txt）のテンプレートも作成します。どの情報を追加したいか教えてください。