# KabuSys

日本株自動売買プラットフォームのライブラリ群。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのコアライブラリです。  
主に以下を目的として設計されています。

- J-Quants API から株価・財務・カレンダーを取得して DuckDB に格納する ETL パイプライン
- RSS フィードからのニュース収集と銘柄紐付け（raw_news / news_symbols）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- JPX マーケットカレンダー管理（営業日判定、翌営業日/前営業日の取得等）
- 監査ログ（シグナル → 発注 → 約定 のトレースを行う監査スキーマ）
- 環境設定管理（.env 自動ロード、必須設定の検証）

設計上の特徴：
- J-Quants API のレート制限（120 req/min）を尊重する RateLimiter を実装
- HTTP リトライ（指数バックオフ、401 の自動リフレッシュ等）
- DuckDB へ冪等（idempotent）に保存する SQL（ON CONFLICT を利用）
- RSS 取得時の SSRF 対策・XML 安全処理・サイズ制限など安全性を考慮

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - get_id_token（リフレッシュトークンから id_token を取得）
  - save_* 系関数で DuckDB に冪等保存

- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl（まとめて ETL を実行し品質チェックを行う）

- data.news_collector
  - fetch_rss（RSS 取得・前処理）
  - save_raw_news / save_news_symbols / run_news_collection

- data.schema
  - init_schema / get_connection（DuckDB のスキーマ初期化・接続管理）

- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチでカレンダー更新）

- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（すべての品質チェックをまとめて実行）

- data.audit
  - init_audit_schema / init_audit_db（監査ログ用スキーマの初期化）

- 環境設定: kabusys.config
  - .env 自動ロード（プロジェクトルートにある .env / .env.local を適用、OS 環境変数優先）
  - 必須設定の検証（settings オブジェクト経由）

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | 記法などを利用）
- DuckDB を利用するためネイティブライブラリが必要（pip で duckdb パッケージをインストール）

1. リポジトリをクローン / 配布を配置
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトで別途 requirements.txt を用意している場合は pip install -r requirements.txt）

4. 環境変数の準備
   - プロジェクトルート（.git のあるディレクトリ、または pyproject.toml のあるディレクトリ）に `.env`（必要であれば `.env.local`）を配置すると自動的に読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

必須環境変数（Settings クラスが要求するもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意/デフォルト値を持つ設定:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 で自動 .env ロード無効
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUS_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi

サンプル .env（プロジェクトルートに置く）
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な API と実行例）

※ 以下は Python スクリプト/REPL からの利用例です。path は実際の環境に合わせて置き換えてください。

1) スキーマ初期化（DuckDB）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成され、全テーブルが作成される
```

2) 監査ログスキーマ初期化（追加）
```python
from kabusys.data.audit import init_audit_schema
# 既存の conn を渡す（init_schemaで作った conn を流用）
init_audit_schema(conn, transactional=True)
```

3) 日次 ETL を実行（J-Quants から差分取得して保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定しなければ今日で実行
print(result.to_dict())
```

4) ニュース収集ジョブを実行（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) マーケットカレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} records")
```

6) J-Quants から直接データを取得して保存（低レベル API）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
# 例: 1銘柄の日足を取得して保存
records = jq.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
jq.save_daily_quotes(conn, records)
```

7) 品質チェック（個別または全件）
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 設計上の注意点 / 実運用に向けて

- J-Quants API に対してはモジュール内でレート制御とリトライを行いますが、分散実行や並列化する場合は追加のレート管理が必要です。
- DuckDB は単一ファイル DB を想定しているため高頻度の同時書き込みがある本番では運用設計（ロック・排他）を検討してください。
- RSS 取得は外部サイトに対する HTTP リクエストを行います。ネットワークタイムアウトやエンコーディング等の例外に注意してください。
- 環境変数は `.env` / `.env.local` に保存し、機密情報（トークン）は適切に管理してください。
- tests や CI で自動的に環境ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。

---

## ディレクトリ構成

パッケージトップは src/kabusys 配下に配置されています。主要ファイル・モジュールは以下のとおりです。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存）
    - news_collector.py          — RSS ニュース収集・前処理・保存
    - schema.py                  — DuckDB スキーマ定義・初期化
    - pipeline.py                — ETL パイプライン（差分更新・日次実行）
    - calendar_management.py     — マーケットカレンダー管理（営業日判定等）
    - audit.py                   — 監査ログスキーマ（シグナル→発注→約定トレース）
    - quality.py                 — データ品質チェック
  - strategy/
    - __init__.py                — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                — 実際の発注/ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py                — モニタリング用の追加機能（拡張ポイント）

各モジュールは責務ごとに分離されており、必要な箇所だけをインポートして利用できます。例えば ETL は data.pipeline.run_daily_etl を利用するのが最も簡単です。

---

## 追加情報 / FAQ

- Q: .env の読み込み順は？
  - A: OS 環境変数 > .env.local > .env の順で適用されます。既存の OS 環境変数は保護されます。

- Q: 自動的に .env を読み込ませたくないときは？
  - A: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Q: サポートしている Python バージョンは？
  - A: 型注釈に Python 3.10 の構文（X | Y）を使用しています。Python 3.10 以上を推奨します。

- Q: DuckDB のファイル場所を変えたい
  - A: 環境変数 `DUCKDB_PATH` を設定するか、schema.init_schema/get_connection に直接パスを渡してください。

---

必要に応じて README のサンプルコマンドや CI の例（自動 ETL の cron/スケジューラ）、運用時の監視（Slack 通知等）を追加します。追加したい項目があれば教えてください。