# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）、J-Quants からのデータ収集、RSS ニュース収集、特徴量計算・リサーチ用ユーティリティ、ETL パイプライン、監査ログの初期化・管理などを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得・保存
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - API レート制御、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）

- ETL / データパイプライン
  - 差分フェッチ・バックフィル対応
  - 市場カレンダー先読み
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集
  - RSS フィード取得（SSRF対策、gzip上限、XML安全パーサ）
  - 記事正規化・ID生成（URL正規化→SHA-256）
  - raw_news / news_symbols への冪等保存

- リサーチ / 特徴量
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Zスコア正規化ユーティリティ

- カレンダー管理
  - 営業日判定、前後営業日検索、カレンダー自動更新ジョブ

- 監査ログ（Audit）
  - signal / order_request / executions の監査テーブルとインデックス定義
  - トレーサビリティの初期化ユーティリティ

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数のラッピング（kabusys.config.settings）

---

## 必要要件

- Python 3.10 以上（型ヒントに | 演算子や dict[str,...] 等を使用）
- pip パッケージ
  - duckdb
  - defusedxml
（プロジェクトで追加のパッケージが必要になる場合があります。適宜 requirements.txt を用意してください。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## 環境変数（.env）

自動的にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` と `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。  
必須となる環境変数の例:

- J-Quants 関連
  - JQUANTS_REFRESH_TOKEN

- kabuステーション API
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)

- Slack（通知等）
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

- DB パス（任意）
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (モニタリング DB 等、デフォルト: data/monitoring.db)

- 実行設定
  - KABUSYS_ENV (development|paper_trading|live)
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

サンプル `.env`（README 用）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

kabusys.config.settings 経由で各値にアクセスできます。

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成してアクティブ化
3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
4. `.env` をプロジェクトルートに作成し、必要な環境変数を設定
5. DuckDB スキーマの初期化（下記参照）

---

## 初期化（DuckDB スキーマ）

DuckDB データベースを初期化して全テーブルを作成します。デフォルトパスは settings.duckdb_path（環境変数 DUCKDB_PATH で上書き可）。

Python スニペット例:
```
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# または設定値を使う場合:
from kabusys.config import settings
conn = schema.init_schema(settings.duckdb_path)
```

監査ログ（Audit）テーブルを別 DB に初期化する場合:
```
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

既存 DB に監査スキーマを追加する場合:
```
from kabusys.data import audit
audit.init_audit_schema(conn, transactional=True)
```

---

## 使い方（主なユースケース）

以下は代表的な利用方法の例です。いずれも Python スクリプトや CLI（ラッパー）から呼び出して使用します。

1) 日次 ETL（市場カレンダー・株価・財務・品質チェック）
```
from kabusys.data import pipeline, schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

2) 株価データを J-Quants から個別に取得して保存
```
from kabusys.data import jquants_client as jq, schema
conn = schema.init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

3) RSS ニュース収集ジョブ実行
```
from kabusys.data import news_collector, schema

conn = schema.init_schema("data/kabusys.duckdb")
# known_codes は証券コード一覧（例: {"7203","6758",...}）
res = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
print(res)  # {source_name: saved_count}
```

4) ファクター / リサーチ
```
from kabusys.research import calc_momentum, calc_volatility, calc_value
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
d = date(2024, 2, 1)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
```

5) 将来リターン・IC・サマリー
```
from kabusys.research import calc_forward_returns, calc_ic, factor_summary, rank

fwd = calc_forward_returns(conn, date(2024,2,1), horizons=[1,5,21])
ic = calc_ic(factor_records=..., forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(factor_records, ["mom_1m", "mom_3m"])
```

6) Z スコア正規化
```
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "atr_20"])
```

---

## 主要モジュール（API 短説明）

- kabusys.config
  - settings: 環境変数のラッパー（必須変数チェック、自動 .env 読み込み）

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token

- kabusys.data.schema
  - init_schema(db_path) / get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)

- kabusys.data.news_collector
  - fetch_rss(url, source) / save_raw_news / run_news_collection

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, ...)

- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize （data.stats から再エクスポート）

- kabusys.data.audit
  - init_audit_schema / init_audit_db

---

## 開発者向け補足

- .env のパース実装はシェル風の export KEY=val 形式やクォート・コメントを考慮しています。
- 自動 .env ロードはプロジェクトルート探索に基づきます（.git または pyproject.toml を検出）。
- DuckDB への DDL は冪等（CREATE TABLE IF NOT EXISTS 等）で実装されています。
- RSS 取得時は SSRF 対策（リダイレクト検査、プライベートIP拒否）、gzip サイズ上限、defusedxml による安全な XML パースを行います。
- J-Quants クライアントはレートリミッタ・リトライ・401 トークンリフレッシュのロジックを備えています。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
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
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py

（実際のファイル一覧はリポジトリのツリーを参照してください。）

---

## ライセンス・注意事項

- 本プロジェクトは金融データ・売買ロジックを扱います。実運用（特にライブ口座での発注）を行う際は十分な理解と検証、リスク管理を行ってください。
- J-Quants や証券会社 API の利用は各サービスの利用規約・レート制限に従ってください。
- この README はコードベースからの要点をまとめたものであり、実装の詳細や追加ユーティリティはソースコードを参照してください。

---

必要であれば、典型的なワークフロー（cron / CI での ETL スケジュール、簡易 CLI ラッパー例、.env.example ファイル）を追加で作成します。どの項目を詳しく書けば良いですか？