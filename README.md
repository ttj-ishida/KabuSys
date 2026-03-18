# KabuSys — 日本株自動売買システム

KabuSys は日本株のデータ取得・ETL・品質チェック・監査ログ・ニュース収集などを行う、DuckDB ベースの自動売買基盤ライブラリです。J-Quants API や RSS フィードを介してデータを取得し、冪等性を保ちながら DuckDB に保存します。戦略・発注・監視層との接続点を提供することを目的としています。

---

## 主な機能
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスを防止
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution / Audit 層を定義
  - 必要なインデックスや制約を含む冪等な DDL
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得、バックフィル対応）
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
- ニュース収集（RSS）
  - RSS から記事収集・前処理・ID 生成（URL 正規化 + SHA-256）
  - SSRF 対策、サイズ上限、XML の安全パース（defusedxml）
  - raw_news / news_symbols への冪等保存
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定までのトレーサビリティ用テーブル群
  - 発注要求は冪等キー（order_request_id）を保持
- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の明示的取得 via kabusys.config.settings

---

## 要件
- Python 3.9+
- 依存主なライブラリ:
  - duckdb
  - defusedxml
- その他標準ライブラリ（urllib, json, datetime 等）

（実際の setup.py / pyproject.toml に依存関係を記載してください）

---

## インストール
開発環境での一例:

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール（例）
   - pip install -r requirements.txt
   - または pyproject.toml を用いる場合は poetry/pipx 等

開発インストール例:
```bash
pip install -e .
```

---

## 設定（環境変数 / .env）
KabuSys はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探し、以下の優先度で環境変数を自動ロードします:

1. OS 環境変数
2. .env.local（存在する場合、.env の値を上書き）
3. .env

自動ロードを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途等）。

主な環境変数（必須は README 内で明記）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — 値: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

設定取得例（コード内）:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
db_path = settings.duckdb_path
```

---

## クイックスタート

### 1) スキーマ初期化（DuckDB）
DuckDB ファイルを初期化して接続を取得します。parent ディレクトリがなければ自動作成します。

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルパス文字列や Path を渡せる
```

既存 DB に接続するだけなら:
```python
from kabusys.data.schema import get_connection
conn = get_connection(settings.duckdb_path)
```

監査ログ専用 DB を初期化する場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

### 2) 日次 ETL の実行
jquants_client を使ってデータを差分取得・保存し、品質チェックを行います。

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 引数で target_date, id_token, backfill_days などを指定可
print(result.to_dict())
```

ETLResult により取得件数・保存件数・品質問題・エラー情報が得られます。

### 3) ニュース収集
RSS フィードから記事を取得して raw_news に保存します。

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 銘柄抽出で参照する有効な銘柄コードのセットを渡すと、news_symbols の紐付けを実行します
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)  # {source_name: 新規保存件数}
```

注意: fetch_rss は SSRF/サイズ等の安全対策を実装しています。defusedxml を用いて XML を安全にパースします。

### 4) J-Quants トークン取得（必要時）
get_id_token を直接呼んで ID トークンを得ることもできます（通常はモジュール内キャッシュを利用）。

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使う
```

jquants_client はリトライ・レート制御・401 時の自動リフレッシュを備えています。

---

## 主なモジュール API（概要）
- kabusys.config
  - settings: アプリ設定プロパティ（jquants_refresh_token / duckdb_path / env / log_level 等）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.audit
  - init_audit_schema, init_audit_db

各関数の詳細な挙動や引数はソースの docstring を参照してください。

---

## 開発・テストのヒント
- 自動 .env 読み込みはプロジェクトルート（.git / pyproject.toml）から行われます。テスト中に自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- jquants_client のネットワーク呼び出しは内部で _rate_limiter や再試行を行います。テストでは get_id_token や _urlopen 等をモックして切り離すと便利です。
- news_collector では _urlopen をモックすることで外部ネットワークを排除できます。

---

## ディレクトリ構成（抜粋）
リポジトリの主要なファイル/ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - audit.py
    - quality.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主に data パッケージが ETL・DB・外部 API 周りのロジックを担っています。strategy / execution / monitoring は別モジュールとして戦略・発注・監視の実装を想定しています。

---

## 注意事項 / 設計上のポイント
- DuckDB への保存は基本的に冪等（ON CONFLICT ... DO UPDATE / DO NOTHING）を心がけています。
- すべての UTC タイムスタンプ（fetched_at / created_at 等）によりデータのトレーサビリティを確保しています。
- ニュース収集では SSRF・XML Bomb・大容量レスポンスへの対策を実装しています。
- Data / Audit スキーマは外部キーやチェック制約を含みます。監査データは削除しない運用を前提としています。
- KABUSYS_ENV により動作モード（development / paper_trading / live）を切り替えられます。live モードでは発注・通知などに注意してください。

---

README に書かれている以外の操作（実際の発注処理、Slack 通知送出、kabu ステーションとの具体的な連携など）は strategy / execution モジュールや利用側の実装に依存します。詳細は各モジュールの docstring を参照してください。

必要があれば、導入手順の具体的なコマンド例や CI / デプロイ手順、サンプル .env.example のテンプレートを追加で作成します。どの情報が欲しいか教えてください。