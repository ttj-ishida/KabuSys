# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
J-Quants API からデータを取得して DuckDB に蓄積し、特徴量計算・品質チェック・ETL パイプライン・ニュース収集・監査ログ等を提供します。

## 概要

KabuSys は以下の目的で設計されたモジュール群を含みます。

- J-Quants API と連携して株価・財務・市場カレンダー等を取得・保存するデータレイヤ
- DuckDB 上でスキーマを定義・初期化するユーティリティ
- ETL（差分取得・保存・品質チェック）パイプライン
- RSS ベースのニュース収集と記事→銘柄紐付け
- 研究用途のファクター計算（モメンタム、ボラティリティ、バリュー等）と IC / 統計サマリ
- 発注やモニタリングなどの実行層・監査層のためのスキーマとユーティリティ

設計上のポイント：
- DuckDB をコア DB として使用（ファイル or :memory:）
- 冪等（idempotent）な保存（ON CONFLICT）を重視
- Look-ahead bias を避けるため取得時刻（fetched_at）を記録
- 標準ライブラリ中心で依存を最小化（ただし duckdb, defusedxml 等は必要）

## 機能一覧

主な提供機能（モジュール別）

- kabusys.config
  - .env または OS 環境変数から設定を読み込む自動ロード
  - Settings オブジェクトで必要な環境変数を取得

- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・ページネーション・保存ユーティリティ）
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - save_daily_quotes / save_financial_statements / save_market_calendar
  - schema: DuckDB スキーマ定義と init_schema(), get_connection()
  - pipeline: run_daily_etl(), 個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news 保存・銘柄抽出（SSRF 対策・gzip 制限・XML 安全パース等）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）と集約 run_all_checks()
  - calendar_management: market_calendar の管理と営業日判定ユーティリティ
  - audit: 監査ログ（signal / order_request / execution）テーブルの初期化ユーティリティ

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility（prices_daily / raw_financials を参照）
  - feature_exploration: calc_forward_returns, calc_ic（スピアマンρ）, factor_summary, rank
  - data.stats: zscore_normalize（クロスセクションの Z スコア正規化）

- その他
  - execution / strategy / monitoring：パッケージ構造あり（実装箇所はプロジェクト参照）

## 動作要件

- Python 3.10 以上（型ヒントの | 演算子などを使用）
- 主な外部ライブラリ
  - duckdb
  - defusedxml

推奨インストール例（仮の requirements）:
pip install duckdb defusedxml

（プロジェクトをパッケージ化している場合は pip install -e . などでインストールしてください）

## 環境変数 / .env

Settings が参照する主な環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用
- SLACK_CHANNEL_ID (必須) — Slack チャネルID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — 値: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL (任意) — 値: DEBUG / INFO / WARNING / ERROR / CRITICAL

自動読み込み：
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を検出）を起点に `.env` と `.env.local` を自動ロードします。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env.example（README 用サンプル）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CHANNELID123
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

## セットアップ手順

1. リポジトリをクローン（またはパッケージをインストール）
   git clone <repo-url>
   cd <repo>

2. Python 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install duckdb defusedxml

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数を設定
   - ルートに .env を作成するか OS 環境変数を設定してください。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

5. DuckDB スキーマの初期化（例）
   下記「使い方」のスニペットを参照して DB を初期化します。

## 使い方（基本的な例）

以下は簡単なコード例です。実行はプロジェクト内のスクリプトや REPL で行います。

- DuckDB スキーマ初期化（ファイル DB）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# 設定された DUCKDB_PATH に DB を初期化
conn = init_schema(settings.duckdb_path)
# もしくは :memory: を使う
# conn = init_schema(":memory:")
```

- 監査ログ専用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL の実行（カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コード集合（例: {"7203", "6758", ...}）
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # ソース毎の新規保存件数
```

- 研究用ファクター計算 / 正規化
```python
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 31)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# 例: Zスコア正規化
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])

# 将来リターン計算（翌日/週/月）
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

# IC 計算（例: mom_1m と fwd_1d）
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)

# 統計サマリ
summary = factor_summary(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
print(summary)
```

- J-Quants API を直接使ってデータ取得（テストやバッチで id_token を注入可能）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.config import settings
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=None, date_to=None)  # 全件取得は注意
saved = save_daily_quotes(conn, records)
```

## 主要 API（概要）

- data.schema.init_schema(db_path) — DuckDB スキーマ作成
- data.audit.init_audit_db(db_path) — 監査 DB 初期化
- data.pipeline.run_daily_etl(conn, target_date, ...) — 日次 ETL 実行（返り値: ETLResult）
- data.jquants_client.fetch_* / save_* — J-Quants との I/O
- data.news_collector.run_news_collection(conn, sources, known_codes) — RSS 収集＋保存＋銘柄紐付け
- data.quality.run_all_checks(conn, ...) — 品質チェック
- research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- data.stats.zscore_normalize — Z スコア正規化

## 注意点 / 運用上のヒント

- 自動発注等を行う場合は KABUSYS_ENV を必ず設定し、実運用時は is_live フラグで保護してください（Settings.is_live）。
- J-Quants API のレート制限（120 req/min）に配慮した実装が含まれていますが、実行環境からの過剰な同時呼び出しは避けてください。
- news_collector は RSS の XML を扱うため、defusedxml を用いた安全なパースを行っています。外部からの feed URL を扱う場合は SSRF 対策に注意してください（本実装でも複数対策あり）。
- DuckDB ファイルはバックアップを推奨します。init_schema は既存テーブルに対して冪等に DDL を実行しますが、スキーマ変更には注意してください。

## ディレクトリ構成

主要ファイル・ディレクトリ（ソースベース）
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
    - etl.py
    - features.py
    - quality.py
    - calendar_management.py
    - audit.py
    - audit.py
    - ...（その他 data 関連モジュール）
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

（README と同階層に pyproject.toml や .git がある想定）

## 貢献・拡張

- 新しい ETL ジョブ、品質チェック、ファクターを追加する際は既存の設計規約（DuckDB を用いた SQL 主導の処理、冪等保存、取得時刻の記録）に従ってください。
- 発注ロジックや実行層の統合は監査ログ（audit）と密に連携させ、order_request_id による冪等性維持を徹底してください。

---

この README はコードベースの現在の実装（主要モジュール）を要約したものです。詳細な API ドキュメントや運用手順は各モジュールの docstring を参照してください。必要であればサンプルスクリプトや補助的な CLI を追記できます。ご希望があれば追加します。