# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、DuckDB によるデータ管理、ETL パイプライン、ニュース収集、特徴量計算、品質チェック、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株を対象とした次の機能を持つ内部ライブラリ群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レートリミット・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたデータスキーマ定義と冪等な保存（ON CONFLICT）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集（SSRF 対策・トラッキングパラメータ除去・記事ID冪等化）
- ファクター（モメンタム・ボラティリティ・バリュー等）計算と特徴量探索ツール
- 監査用スキーマ（シグナル→発注→約定のトレース）
- マーケットカレンダー管理・営業日判定ユーティリティ

設計方針として、本番の発注 API には不要な箇所はアクセスせず（Research / Data モジュールは読み取り専用）、冪等性・トレーサビリティ・外部攻撃（SSRF / XML Bomb）対策を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、rate limiter、save_*）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次 ETL（差分取得、バックフィル、品質チェック）
  - news_collector: RSS 取得＆前処理＆DB保存、銘柄抽出
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: JPX カレンダー更新と営業日ユーティリティ
  - audit: 監査ログ用スキーマ（signal/events/order_requests/executions）
  - stats / features: Zスコア正規化等の統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman rank）計算、ファクターサマリー
- config: 環境変数管理（.env 自動読み込み、必須変数取得ユーティリティ）
- その他: execution, strategy, monitoring（パッケージ階層の準備）

---

## 要求環境

- Python 3.9+（typing と型注釈を多用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- （その他）標準ライブラリ多数（urllib, logging, datetime, math, hashlib 等）

パッケージは pyproject.toml / requirements.txt がある想定でインストールしてください。

---

## セットアップ手順（例）

1. リポジトリをクローン / ワークディレクトリへ移動

   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール（例）

   pip install "duckdb>=0.7" defusedxml

   （プロジェクトに requirements ファイルがあればそれを使ってください）

4. パッケージのインストール（開発モード）

   pip install -e .

5. 環境変数設定
   プロジェクトルートに `.env` を置くと自動で読み込まれます（ただしテストやカスタム環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを抑制できます）。

   代表的な環境変数（.env に設定する例）:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_station_password
   KABUSYS_ENV=development           # または paper_trading / live
   LOG_LEVEL=INFO
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   ※ Settings クラスで必須とされるキーは `.config.Settings` のプロパティを参照してください（未設定時は ValueError が発生します）。

---

## 初期データベース初期化（DuckDB）

Python REPL やスクリプトから DuckDB スキーマを初期化します。

例（簡単なスクリプト）:

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" でメモリ DB も可

監査ログ専用 DB を分離して使う場合:

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方例

以下に主要な操作の簡単な使用例を示します。

1) ETL（日次パイプライン）を実行する

from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

- id_token を外部で取得して渡すことも可能（テスト時や明示的なトークン管理）。
- run_daily_etl はカレンダー取得 → 株価取得 → 財務取得 → 品質チェック の順で実行します。エラーは個別に捕捉され、結果の `errors` / `quality_issues` に反映されます。

2) J-Quants から日足を直接取得して保存する

from kabusys.data import jquants_client as jq
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)

3) ニュース収集を実行する

from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄集合
results = run_news_collection(conn, known_codes=known_codes)
print(results)

4) ファクター計算 / リサーチ関数例

from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")  # 事前に prices_daily / raw_financials が揃っていること
d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

5) 特徴量探索（将来リターン・IC）

from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
fwd = calc_forward_returns(conn, target_date=d, horizons=[1,5,21])
# factor_records は例えば calc_momentum の出力
ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])

---

## 主要な API / 公開関数一覧（抜粋）

- kabusys.config.settings: 環境設定アクセス（jquants_refresh_token, kabu_api_password, slack_bot_token 等）
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.pipeline.run_daily_etl
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.data.quality.run_all_checks
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.data.stats.zscore_normalize

---

## 環境設定の注意点

- .env の自動読み込みは `kabusys.config` がプロジェクトルート（.git または pyproject.toml）を見つけた場合に行われます。CWD に依存せず、パッケージ配布後も期待通りに動作する設計です。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト時に利用）。
- 必須の環境変数が不足している場合、Settings のプロパティ参照時に ValueError を投げます。例: `settings.jquants_refresh_token`。

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py
  - config.py               -- 環境設定 / .env 自動読み込み
  - data/
    - __init__.py
    - jquants_client.py     -- J-Quants API クライアント（取得・保存）
    - schema.py             -- DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py           -- ETL パイプライン（run_daily_etl 等）
    - news_collector.py     -- RSS 収集、前処理、DB 保存、銘柄抽出
    - quality.py            -- データ品質チェック（欠損/重複/スパイク/日付不整合）
    - calendar_management.py-- カレンダー更新と営業日ユーティリティ
    - audit.py              -- 監査ログ（signal/events/order_requests/executions）
    - stats.py              -- zscore_normalize 等の統計ユーティリティ
    - features.py           -- features の公開インターフェース（再エクスポート）
    - pipeline.py / etl.py  -- ETL の公開型（ETLResult など）
  - research/
    - __init__.py
    - factor_research.py    -- Momentum / Volatility / Value の計算
    - feature_exploration.py-- 将来リターン、IC、サマリー、rank
  - execution/               -- 発注関連（空 __init__ が用意されている）
  - strategy/                -- 戦略モジュール（空 __init__ が用意されている）
  - monitoring/              -- 監視系（パッケージ準備のみ）
- pyproject.toml / setup.cfg 等（プロジェクトルート）

各モジュールは README 内の使用例のように DuckDB 接続を受け取る形で動作します。多くの関数は本番の発注機能にアクセスしない設計（データ収集・解析専用）です。

---

## 開発・テスト時のヒント

- DuckDB のインメモリ接続 ":memory:" を使うと単体テストが簡便になります。
- jquants_client のネットワーク呼び出しは容易にモック可能です（_urlopen や _request をモック）。
- news_collector._urlopen を置き換えて RSS フェッチをテスト可能です。
- 環境読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ライセンス・貢献

（ここにはプロジェクトのライセンス情報とコントリビュート方法を記載してください）

---

この README はコードベースの主要機能と利用方法を簡潔にまとめたものです。より詳細な設計文書（DataPlatform.md / StrategyModel.md 等）や実運用のオペレーション手順があれば、併記することを推奨します。