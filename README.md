# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
DuckDB をデータレイクとして用い、J-Quants API や RSS を通じたデータ収集、品質チェック、特徴量生成、監査ログなどの機能を提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- 環境変数（設定）
- セットアップ手順
- 使い方（クイックスタート）
  - DB 初期化
  - 日次 ETL 実行
  - ニュース収集ジョブ
  - ファクター計算 / 研究ユーティリティ
  - 監査スキーマ初期化
- 開発・テスト時の注意点
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株に対する以下のワークフローをサポートするモジュール群です。

- データ収集（J-Quants API から日足・財務・カレンダー、RSS ニュース）
- DuckDB を中心としたスキーマ定義・永続化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、統計サマリー、Z スコア正規化）
- ニュース収集・前処理・銘柄抽出（SSRF 対策・トラッキング除去・冪等保存）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計方針として、研究系モジュールは発注 API など本番実行にはアクセスせず、標準ライブラリのみで完結する処理（ただし DuckDB には依存）を心がけています。

---

## 機能一覧
主な機能（モジュール）:

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）、必須環境変数チェック
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能
- kabusys.data.jquants_client
  - J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - fetch / save の冪等的実装（ON CONFLICT）
- kabusys.data.schema
  - DuckDB の全スキーマ定義と init_schema()
- kabusys.data.pipeline
  - 日次 ETL 実装（run_daily_etl）: カレンダー・株価・財務の差分取得と品質チェック
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合の確認
- kabusys.data.news_collector
  - RSS 取得・前処理・保存・銘柄抽出（SSRF / Gzip / XML の安全対策）
- kabusys.research
  - calc_momentum, calc_volatility, calc_value（ファクター）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索）
  - zscore_normalize（data.stats で提供）
- kabusys.data.audit
  - 監査用テーブル定義・初期化（トレーサビリティ保護）

---

## 前提・依存関係
最低限の依存（必須）:
- Python 3.9+（typing の一部構文を使用）
- duckdb
- defusedxml

その他（本番連携や追加機能に応じて）:
- J-Quants API 利用に必要なネットワーク環境・トークン
- Slack / kabu ステーション連携（環境変数で設定）

例: 必要なパッケージを手動でインストールする場合
pip install duckdb defusedxml

（パッケージ配布時は requirements.txt / pyproject.toml を参照してください）

---

## 環境変数（主なキー）
以下はソースコードが参照する主要な環境変数です（.env に定義しておくことを想定）。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD    : kabuステーション API 用パスワード
- SLACK_BOT_TOKEN      : Slack ボットトークン
- SLACK_CHANNEL_ID     : 通知先チャンネル ID

任意（デフォルト値あり）:
- KABUSYS_ENV          : environment の種類（development / paper_trading / live）. デフォルト: development
- LOG_LEVEL            : ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）. デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env の読み込みを無効化

データベースパス:
- DUCKDB_PATH          : DuckDB のパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH          : 監視用 SQLite（デフォルト: data/monitoring.db）

--- 

## セットアップ手順（ローカル / 開発）
1. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそちらを利用）

3. プロジェクトルートに .env を作成
   .env (例)
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG

   - .env.local を用いた環境差分上書きもサポート（.env を先に読み、その後 .env.local で上書き）

4. DuckDB スキーマ初期化（例: Python REPL またはスクリプト）
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

   ※ init_schema は親ディレクトリを自動作成します。

---

## 使い方（クイックスタート例）

### DB スキーマを作成する
Python スクリプト例:
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

監査ログ専用 DB を作る:
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

### 日次 ETL を実行する
日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）を実行:
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

run_daily_etl は API トークン（id_token）を省略可能。モジュール内で settings.jquants_refresh_token を用いて id_token を取得します。

### ニュース収集ジョブを実行する
RSS を取得して raw_news / news_symbols へ保存:
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)

### ファクター計算（研究用）
duckdb 接続を渡してファクターを計算:
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = get_connection("data/kabusys.duckdb")
d = date(2024, 1, 10)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

これらの関数は prices_daily / raw_financials テーブルのみを参照し、発注や外部 API にはアクセスしません（研究用途に安全）。

### 監査スキーマを初期化する
既存の DuckDB 接続に監査テーブルを追加:
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)

---

## 開発・テスト時の注意点・ヒント
- 自動 .env ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテスト等で便利）。
- settings（kabusys.config.Settings）は環境変数をその場で参照します。テストの際は os.environ を操作するか Settings をモックしてください。
- research モジュール（calc_momentum 等）は外部 API を呼ばないためユニットテストが容易です（DuckDB の in-memory 接続 ":memory:" を使用すると便利）。
- news_collector は外部ネットワークアクセスを行います。テストでは network をモックするか fetch_rss/_urlopen を差し替えてください。
- jquants_client 内の _RateLimiter はモジュール単位でインスタンス化されているため、API 呼び出し回数の制御に注意してください（テストでは短縮するかモック化すること）。

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - stats.py
  - pipeline.py
  - features.py
  - calendar_management.py
  - audit.py
  - etl.py
  - quality.py
- research/
  - __init__.py
  - feature_exploration.py
  - factor_research.py
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

主要な公開 API（例）:
- kabusys.config.settings
- kabusys.data.schema.init_schema / get_connection
- kabusys.data.pipeline.run_daily_etl
- kabusys.data.news_collector.run_news_collection
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.data.stats.zscore_normalize
- kabusys.data.audit.init_audit_schema / init_audit_db

---

必要であれば README に含めるサンプル .env ファイルやより詳しい API 使い方（引数説明・返り値構造の例）を追加します。どの部分を詳細化したいか教えてください。