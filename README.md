# KabuSys

日本株向けの自動売買 / データ基盤ライブラリセット (KabuSys)。  
DuckDB をデータ層に使い、J-Quants API からのデータ取得、ETL、データ品質チェック、ファクター計算、ニュース収集、監査ログなどを提供します。

---

## 概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- データ取得・保存（J-Quants から株価・財務・市場カレンダー・ニュースなど）
- DuckDB スキーマ定義と初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース RSS 収集と銘柄紐付け
- ファクター計算（モメンタム・ボラティリティ・バリューなど）と研究ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計方針として、DuckDB と標準ライブラリ中心で実装され、外部 API への不必要なアクセスは行わないようになっています（Research / Feature 計算は DB のみ参照）。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レート制御、リトライ、トークン自動更新、ページネーション対応）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB へ冪等に保存する save_* 関数
- data/schema.py
  - DuckDB 向けのスキーマ定義と init_schema()
- data/pipeline.py
  - run_daily_etl：市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェックを実行
  - 個別 ETL ヘルパー（run_prices_etl 等）
- data/quality.py
  - 欠損 / スパイク / 重複 / 日付不整合 の検出
- data/news_collector.py
  - RSS 取得（SSRF 対策、サイズ上限、gzip 対応、XML 攻撃対策）
  - raw_news への冪等保存、銘柄コード抽出と news_symbols への保存
- data/calendar_management.py
  - market_calendar の管理、営業日判定・next/prev_trading_day 等
- data/audit.py
  - 監査ログ用テーブル（signal_events / order_requests / executions）と初期化
- research/*
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
  - data.stats の zscore_normalize を再エクスポート
- config.py
  - .env 自動読み込み（OS 環境変数 > .env.local > .env）、必要な設定値をラップする Settings

（strategy/execution/monitoring パッケージは API の土台を提供するための空モジュール／プレースホルダが含まれます）

---

## 要件

- Python 3.10 以上（型アノテーションの union 型や構文を使用）
- 主な依存パッケージ（必要に応じて追加）
  - duckdb
  - defusedxml

pip での最低インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# （必要に応じて他のライブラリを追加）
```

※ 実運用で Slack 通知や kabuステーション連携を行う場合は、それらの SDK を別途インストールしてください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   ```

2. 環境変数を準備する（.env または OS 環境変数）
   必須の環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN — Slack 通知を使う場合
   - SLACK_CHANNEL_ID — Slack 通知を使う場合
   - KABU_API_PASSWORD — kabuステーション API を使う場合

   任意 / デフォルトあり:
   - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

   .env の自動読み込みは、プロジェクトルート（.git または pyproject.toml）を起点に行われ、優先順位は:
   OS 環境変数 > .env.local > .env
   自動ロードを無効化する場合:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

3. DuckDB スキーマ初期化
   Python でスキーマを作成します（デフォルトで parent ディレクトリを自動作成します）:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   # 監査ログ（別 DB）を初期化する場合:
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表例）

- 日次 ETL 実行（J-Quants から差分取得して DB 保存・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data import schema, pipeline
# DB 初期化済みとする（init_schema を既に実行していること）
conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ETL の個別実行（株価のみ）
```python
from datetime import date
from kabusys.data import schema, pipeline
conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- ニュース収集ジョブの実行
```python
from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 既知銘柄セット（例）
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- ファクター計算（Research）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
t = date(2024, 1, 31)
mom = calc_momentum(conn, t)
vol = calc_volatility(conn, t)
val = calc_value(conn, t)

# 前方リターン計算
fwd = calc_forward_returns(conn, t, horizons=[1,5,21])

# IC 計算（例）
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")

# Z スコア正規化
normed = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

- J-Quants から直接データ取得（低レベル）
```python
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# 取得データを DB に保存
conn = schema.get_connection("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)
```

---

## 環境変数（Settings API）

kabusys.config.Settings により以下プロパティが提供されます。いずれも環境変数から読み込まれます。

必須:
- JQUANTS_REFRESH_TOKEN (settings.jquants_refresh_token)
- KABU_API_PASSWORD (settings.kabu_api_password)
- SLACK_BOT_TOKEN (settings.slack_bot_token)
- SLACK_CHANNEL_ID (settings.slack_channel_id)

オプション / デフォルト:
- KABUSYS_ENV: development | paper_trading | live（settings.env）
- LOG_LEVEL: DEBUG|INFO|...（settings.log_level）
- DUCKDB_PATH: data/kabusys.duckdb（settings.duckdb_path に Path を返す）
- SQLITE_PATH: data/monitoring.db

.env 読み込みの挙動:
- .env ファイルのパースはシェル互換（export KEY=...、クォート、コメント）を考慮
- OS 環境変数が優先され、.env.local は .env 上書きで読み込まれます
- 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 初期化 API（要点）

- schema.init_schema(db_path)  
  DuckDB ファイルを作成し、すべてのテーブル・インデックスを作成して接続を返す。

- schema.get_connection(db_path)  
  既存 DB へ接続（スキーマ初期化は行わない）。

- audit.init_audit_db(db_path) / audit.init_audit_schema(conn)  
  監査ログ用テーブルを初期化。

---

## 注意点 / 設計上のポイント

- J-Quants クライアントはレート制限（120 req/min）を守るため内部でスロットリングを行います。
- HTTP エラー時は指数バックオフでリトライし、401 受信時はリフレッシュトークンで自動再取得を試みます。
- News collector は SSRF 対策・XML 攻撃対策・gzip 上限チェックなど堅牢性を重視。
- ETL は Fail-Fast ではなく、可能な限り各ステップを独立実行し結果を集約して返す設計です。
- DuckDB 上の INSERT は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で重複を扱います。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - quality.py
    - calendar_management.py
    - etl.py
    - audit.py
    - features.py
    - pipeline.py
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

（開発中のモジュールやドキュメントに基づく抜粋です。詳細はソースツリーをご確認ください。）

---

## 開発・テスト時のヒント

- 自動 .env ロードを無効化してユニットテストを行いたい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- network 等の外部呼び出しを伴う箇所（jquants_client._urlopen、news_collector._urlopen 等）はモックしやすいように実装されています。
- DuckDB の in-memory モード ":memory:" を使えばローカルでのテストが簡単です：
  ```python
  conn = schema.init_schema(":memory:")
  ```

---

## ライセンス / コントリビューション

（本 README にはライセンス情報は含まれていません。リポジトリの LICENSE を参照してください。）  

バグ報告や機能要望は issue を通じてお願いします。プルリクエスト歓迎です。

---

以上がこのコードベースの概観と基本的な使い方です。特定の機能や API の使い方サンプルが必要であれば、用途に合わせた短いサンプルを作成しますのでお知らせください。