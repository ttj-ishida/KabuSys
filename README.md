# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、マーケットカレンダー管理、監査ログ（発注〜約定トレーサビリティ）などを提供します。

## プロジェクト概要
KabuSys は以下の目的で設計された内部ライブラリです。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得・保存する
- RSS フィードからニュース記事を収集し、銘柄との紐付けを行う
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution / Audit）を提供する
- ETL パイプライン（差分取得・バックフィル・品質チェック）を簡単に実行できる
- 発注/約定フローを完全にトレースする監査ログをサポートする

設計上の注力点：
- API レート制御・リトライ（指数バックオフ）
- Look-ahead bias 回避（fetched_at に UTC タイムスタンプを保存）
- DB への保存は冪等（ON CONFLICT ...）を意識
- RSS 収集における SSRF / XML 攻撃防御、受信サイズ制限

## 機能一覧
主な機能は以下の通りです。

- 環境変数 / .env の自動読み込み（.env / .env.local、自動ロード無効化可能）
- J-Quants API クライアント
  - 株価日足（fetch_daily_quotes / save_daily_quotes）
  - 財務データ（fetch_financial_statements / save_financial_statements）
  - マーケットカレンダー（fetch_market_calendar / save_market_calendar）
  - トークン自動リフレッシュ・レートリミット・リトライ対応
- RSS ニュース収集器（fetch_rss / save_raw_news / run_news_collection）
  - URL 正規化・トラッキングパラメータ除去・ID 化（SHA-256）
  - SSRF 対策・gzip 上限チェック・XML パース保護（defusedxml）
  - 銘柄コード抽出と news_symbols への紐付け
- DuckDB スキーマ管理（init_schema / get_connection）
  - Raw / Processed / Feature / Execution 層のテーブルとインデックス
- ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - 差分取得・バックフィル・品質チェック（quality モジュール）
- マーケットカレンダー管理（is_trading_day, next_trading_day, prev_trading_day, calendar_update_job）
- 監査ログ（監査用スキーマの初期化: init_audit_schema / init_audit_db）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

## セットアップ手順

前提
- Python 3.10 以上を推奨（コード内での型ヒントに | が使用されています）
- DuckDB を利用するため pip パッケージを導入します

1. リポジトリをクローン / checkout
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux) / .venv\Scripts\activate (Windows)
3. 依存パッケージのインストール（例）
   - pip install duckdb defusedxml
   - 追加で HTTP クライアントや Slack 通知など使う場合は必要なパッケージを追加してください
4. .env ファイル作成
   - プロジェクトルートに `.env` / 任意で `.env.local` を置けば自動で読み込まれます（環境変数優先）
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します

推奨される .env の例:
JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID などは必須（Settings により取得／検証されます）。

例（.env）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

## 環境変数
主に利用される環境変数一覧（Settings 参照）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で自動 .env 読み込みを無効化)

.env のパース挙動について:
- export KEY=val 形式もサポート
- 値にクォートを使った場合のエスケープ・インラインコメントへの配慮あり

## 使い方（コード例）
主要な操作を Python から行う例を示します。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ディスク DB を初期化
conn = init_schema("data/kabusys.duckdb")
# ":memory:" を指定するとインメモリ DB を使用
```

2) 日次 ETL（株価・財務・カレンダーの差分取得と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

3) 単独ジョブ（株価だけ）
```python
from kabusys.data.pipeline import run_prices_etl
from datetime import date

fetched, saved = run_prices_etl(conn, target_date=date.today())
```

4) RSS ニュース収集と保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)  # ソースごとの新規保存数
```

5) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved:", saved)
```

6) 監査ログスキーマ初期化（発注/約定トレース用）
```python
from kabusys.data.audit import init_audit_schema
# 既存の conn に監査テーブルを追加
init_audit_schema(conn)

# または監査専用 DB を新規作成
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

## 注意事項 / 実運用上のポイント
- J-Quants API のレート制限（120 req/min）やエラーコードに対してリトライやバックオフが組み込まれています。ただし実運用では更に前段のキューや適切なスロットリングを推奨します。
- ETL の差分取得はデフォルトで「最終取得日から backfill_days (デフォルト 3 日)」を遡り再取得する設計です（API の後出し修正に対応）。
- DuckDB はファイルロックを利用するため、複数プロセスから同一ファイルへの同時書き込みを行う場合は運用設計が必要です。
- RSS の取得では SSRF 対策・XML パース安全化・受信サイズ制限を行っていますが、外部ソースは常に不安定なのでシステム側での監視を推奨します。
- 全てのタイムスタンプ（monitoring / audit 等）は UTC を想定して扱うようにしています。

## ディレクトリ構成
主要なファイルとモジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - news_collector.py      # RSS ニュース収集と保存ロジック
    - pipeline.py            # ETL パイプライン（run_daily_etl 他）
    - schema.py              # DuckDB スキーマ定義と初期化
    - calendar_management.py # 市場カレンダーヘルパーとバッチジョブ
    - audit.py               # 監査ログテーブル定義・初期化
    - quality.py             # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記はリポジトリ内の主要モジュールのみ抜粋）

## 依存パッケージ（例）
- duckdb
- defusedxml
- （標準ライブラリ：urllib, json, logging, datetime, pathlib, hashlib, re, socket, ipaddress など）

プロジェクトをパッケージ化する場合は requirements.txt / pyproject.toml に上記を追加してください。

## ロギング
- config.Settings.log_level によりログレベルを制御できます（環境変数 LOG_LEVEL）。
- 各モジュールは標準の logging を利用しているため、アプリ側でハンドラ・フォーマットを設定して使ってください。

---

この README はコードベースの主要機能・使い方を簡潔にまとめたものです。個別モジュール（jquants_client, news_collector, pipeline, quality, calendar_management, audit）の詳細や運用ポリシーは該当ファイルのドキュメント文字列（docstring）を参照してください。必要ならばサンプルワークフローやデプロイ手順（コンテナ化・CI/CD・スケジューリング）などの追加ドキュメントを作成します。