# KabuSys

KabuSys は日本株の自動売買およびデータプラットフォーム向けのライブラリ群です。  
DuckDB を中心としたデータレイヤ、J-Quants API 経由のデータ取得、ETL パイプライン、データ品質チェック、ファクター計算（リサーチ用ユーティリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

主な目的は「日本株のデータ収集・整形・特徴量生成・監査・発注フロー」を一貫して扱うためのユーティリティを提供することです。  
設計方針の要点：

- DuckDB をデータストアとして使用（スキーマは冪等に作成可能）
- J-Quants API から株価・財務・マーケットカレンダーを取得（レートリミット遵守、トークン自動リフレッシュ、リトライ実装）
- RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事IDは SHA-256 のハッシュで冪等化）
- ETL は差分更新・バックフィル・品質チェックを備える
- リサーチ用にファクター計算・将来リターンや IC（Spearman）が計算可能
- 監査ログ（シグナル→発注→約定トレース）用テーブルを提供

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・リトライ・トークン自動リフレッシュ）
  - news_collector: RSS フィードの収集・前処理・DB 保存（SSRF・サイズ制限対策）
  - schema: DuckDB スキーマ定義 & 初期化（Raw / Processed / Feature / Execution 層）
  - pipeline / etl: 日次 ETL（差分取得・保存・品質チェック）とヘルパー
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 市場カレンダーの管理と営業日判定ユーティリティ
  - stats / features: 汎用統計ユーティリティ（Zスコア正規化等）
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマと初期化
- research/
  - factor_research: モメンタム・ボラティリティ・バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）計算、ファクター要約
- execution/, strategy/, monitoring/ はパッケージプレースホルダ（利用者実装向け）

主要機能のハイライト：

- ETL の run_daily_etl による日次データ更新（calendar → prices → financials → 品質チェック）
- fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- save_* 関数は DuckDB への冪等保存を行う（ON CONFLICT 句）
- ニュース収集の run_news_collection（記事抽出→raw_news 保存→銘柄紐付け）
- research の calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary

---

## 動作要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトの requirements.txt があればそちらを利用してください）

---

## 環境変数（必須 / 任意）

自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD ではなくパッケージファイル位置からルートを探索）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（コード内で _require によってチェックされるもの）:
- JQUANTS_REFRESH_TOKEN -- J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      -- kabuステーション API パスワード
- SLACK_BOT_TOKEN        -- Slack ボットトークン（通知用）
- SLACK_CHANNEL_ID       -- Slack チャンネルID

その他（任意・デフォルトあり）:
- KABUSYS_ENV           -- 環境: development / paper_trading / live （default: development）
- LOG_LEVEL             -- ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL （default: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD -- 自動 .env 読み込み無効化（値は任意）
- DUCKDB_PATH           -- DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH           -- 監視DB等（default: data/monitoring.db）
- KABU_API_BASE_URL     -- kabu API のベース URL（default: http://localhost:18080/kabusapi）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローンしてインストール（開発モード例）
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   pip install -e .
   ```

2. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、システム環境変数を設定します（上の「環境変数」を参照）。

3. DuckDB スキーマ初期化
   Python で以下を実行して、DuckDB ファイルを作成・スキーマを初期化します。

   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成されます
   ```

4. 監査ログ DB（任意）
   監査ログ専用 DB を使う場合:

   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（基本例）

- 日次 ETL 実行（J-Quants からの差分取得・保存・品質チェック）

```python
from kabusys.data import etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # または init_schema で初期化した conn
result = etl.run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブ実行

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードのセット（抽出で参照）
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # sourceごとの新規保存件数
```

- J-Quants から日足を直接取得して保存

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved", saved)
```

- リサーチ用ファクター計算例

```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
t = date(2024, 1, 31)
mom = calc_momentum(conn, t)
vol = calc_volatility(conn, t)
val = calc_value(conn, t)

# 将来リターンと IC
fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)

# zscore 正規化
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

---

## 注意事項・設計上のポイント

- J-Quants API: レート制御（120req/min）とリトライ（408/429/5xx）、401 時は自動でリフレッシュして1回だけリトライする実装があります。
- ニュース取得: SSRF や XML Bomb、過大レスポンス等への防御処理を備えています。
- ETL の差分更新ではバックフィル機能を持ち、API 側の後出し修正を吸収します（デフォルト backfill_days=3）。
- DuckDB スキーマ作成は冪等です。既存の DB に対するスキーマ追加（監査ログ等）もサポートしています。
- 多くの関数は DuckDB の接続オブジェクトを受け取る設計で、テスト時はインメモリ DB（":memory:"）を利用できます。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）をベースに行います。テスト時などに自動読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成（主要ファイル）

（抜粋 — 実ファイルは src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数・設定管理（.env 自動読み込み含む）
  - data/
    - __init__.py
    - jquants_client.py           # J-Quants API クライアント（取得 + 保存）
    - news_collector.py           # RSS 取得・前処理・DB 保存
    - schema.py                   # DuckDB スキーマ定義・初期化
    - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
    - etl.py                      # ETL の公開型（ETLResult）
    - quality.py                  # データ品質チェック
    - stats.py                    # 統計ユーティリティ（zscore_normalize）
    - features.py                 # features インターフェース（再エクスポート）
    - calendar_management.py      # マーケットカレンダー管理ユーティリティ
    - audit.py                    # 監査ログスキーマ & 初期化
  - research/
    - __init__.py
    - feature_exploration.py      # 将来リターン / IC / factor_summary / rank
    - factor_research.py          # momentum/volatility/value ファクター計算
  - strategy/                      # パッケージプレースホルダ
  - execution/                     # パッケージプレースホルダ
  - monitoring/                    # パッケージプレースホルダ

---

## 開発 / 貢献

- テスト: DuckDB のインメモリ DB（":memory:"）を利用してユニットテストが書きやすく設計されています。
- lint / formatting: プロジェクト基準があればそれに従ってください（例: black, ruff など）。

---

必要があれば、この README をベースに「.env.example」や具体的な CLI ツール（ETL 実行スクリプト）に関するセクションも追加できます。どの項目をより詳しく記載したいか教えてください。