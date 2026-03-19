# KabuSys

KabuSys は日本株向けの自動売買プラットフォームの部品群です。データ収集（J-Quants）、DuckDB ベースのデータスキーマ、ETL パイプライン、ニュース収集、ファクター／リサーチ、監査ログなど、トレーディングシステムの基盤となるユーティリティを提供します。

バージョン: 0.1.0

## 特徴（機能一覧）

- 環境変数ベースの設定管理（.env 自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、JPX カレンダーの取得
  - レート制限、リトライ、トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT / RETURNING を利用）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合など）
- ニュース収集（RSS）と記事の前処理、銘柄抽出・紐付け
  - SSRF 対策、gzip サイズ制限、XML パースに対する安全対策
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）

## 必要条件

- Python 3.9+
- 推奨パッケージ（代表例）
  - duckdb
  - defusedxml

（プロジェクトで使用する外部ライブラリは最小限に抑えられていますが、DuckDB と defusedxml は必要です）

インストール例:
```bash
python -m pip install duckdb defusedxml
# 開発時にパッケージとして扱いたい場合:
# pip install -e .
```

## 環境変数（主なもの）

設定は .env ファイルまたは環境変数で行います。パッケージ読み込み時にプロジェクトルート（.git か pyproject.toml を基準）にある `.env` / `.env.local` が自動で読み込まれます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト INFO）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

## セットアップ手順

1. Python と依存パッケージをインストール
   ```bash
   python -m pip install duckdb defusedxml
   ```

2. 環境変数を設定（`.env` をプロジェクトルートに作成）
   - 上記の必須変数を設定してください。

3. DuckDB スキーマを初期化
   - Python REPL やスクリプトで初期化できます（`DUCKDB_PATH` が設定されていることを想定）:
   ```python
   from kabusys.config import settings
   from kabusys.data import schema
   conn = schema.init_schema(settings.duckdb_path)
   conn.close()
   ```
   - インメモリ DB を使う場合:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema(":memory:")
   ```

4. （オプション）監査ログデータベースを初期化
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```

## 使い方（例）

- 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# 初期化済みの DB に接続（init_schema を一度実行済みであること）
conn = get_connection("data/kabusys.duckdb")

# 今日を対象に ETL 実行（id_token を明示的に渡すことも可能）
result = run_daily_etl(conn, target_date=date.today())

print(result.to_dict())
conn.close()
```

- ニュース収集を実行する
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "8306"}  # 有効な銘柄コードセット（例）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
conn.close()
```

- 研究用関数の利用（ファクター計算・IC 計算など）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
fwd = calc_forward_returns(conn, d, horizons=[1,5,21])

# 例: mom の mom_1m と fwd の fwd_1d で IC を計算
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC (mom_1m vs fwd_1d):", ic)
conn.close()
```

- J-Quants からデータを直接フェッチして保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, recs)
print("saved:", saved)
conn.close()
```

- データ品質チェックを実行する
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today(), reference_date=date.today())
for i in issues:
    print(i)
conn.close()
```

## 主要モジュールと API（抜粋）

- kabusys.config
  - settings: 環境変数ラッパー（各種プロパティ）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize

各関数の詳細はドキュメント文字列（docstring）を参照してください。

## ディレクトリ構成

以下は主要ファイル／モジュールの構成（src/kabusys 配下）です。実際のリポジトリでは他に設定ファイルやスクリプトが存在する可能性があります。

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

## 開発上の注意点

- DuckDB を使った SQL 実行はパラメータバインド（?）で行われ、SQL インジェクション対策が施されています。
- J-Quants クライアントはレート制限（120 req/min）を意識しています。大量リクエストを行う際は注意してください。
- ニュース収集では SSRF・XML Bomb・gzip サイズ超過対策などを組み込んでいますが、外部入力を扱う際は常に警戒してください。
- 本コードベースは本番の発注 API（証券会社側）への直接アクセスを意図したモジュールを含みます。live 環境での利用は十分なテストと安全策を講じてください（KABUSYS_ENV=live）。

---

問題や追加してほしい項目（例: 具体的な CLI、セットアップスクリプト、サンプル .env.example）などがあれば教えてください。README を用途に合わせて拡張します。