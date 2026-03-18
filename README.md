# KabuSys

日本株向け自動売買／データプラットフォームライブラリです。  
DuckDB をデータレイクとして使い、J-Quants API から市場データ・財務データ・カレンダーを取得、ETL、品質チェック、特徴量生成、ニュース収集、監査ログなどの基盤機能を提供します。

※ 本リポジトリはライブラリのコア実装（data / research / strategy / execution / monitoring 層）を含みますが、実際の発注や Slack 通知等は環境に応じて呼び出し側で組み合わせて利用します。

---

## 主な特徴

- データ取得
  - J-Quants API クライアント（ページネーション、レートリミット、リトライ、トークン自動リフレッシュ対応）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを取得

- データストレージ
  - DuckDB を利用した 3 層スキーマ（Raw / Processed / Feature）を定義・初期化するDDLを提供
  - 監査ログ用スキーマ（発注・約定トレーサビリティ）

- ETL パイプライン
  - 差分更新（最終取得日に基づいた差分取得）、バックフィル対応
  - 品質チェック（欠損・スパイク・重複・日付不整合検出）

- ニュース収集
  - RSS からニュースを収集し正規化して DuckDB に保存（SSRF 対策・トラッキングパラメータ除去・gzip 上限など）
  - 記事と銘柄コードの紐付け機能

- 研究・特徴量
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化等のユーティリティ

- 設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）と環境変数ベースの設定 accessor
  - 環境で自動ロードを無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

- 設計方針
  - 冪等性（ON CONFLICT を用いた保存）
  - Look-ahead-bias 対策（fetched_at を保存）
  - 外部ライブラリに依存しない箇所は標準ライブラリで実装（研究モジュールなど）

---

## 必要条件

- Python 3.10 以上（typing における `|` 演算子等を使用）
- パッケージ依存
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（実際のプロダクションでは requirements.txt を用意して依存を管理してください）

---

## 環境変数・設定

プロジェクトでは環境変数から設定を読みます。ルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主要な環境変数（README 用ダミー例）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）

例 (.env):

```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

設定は `from kabusys.config import settings` でアクセスできます（プロパティ方式）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を準備する
2. 依存パッケージをインストール（duckdb, defusedxml 等）
3. `DUCKDB_PATH` を含む `.env` を作成
4. DuckDB スキーマを初期化する

DuckDB スキーマ初期化例:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

監査ログ専用 DB 初期化:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 基本的な使い方（例）

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集（RSS -> raw_news, news_symbols）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
conn = duckdb.connect("data/kabusys.duckdb")
# known_codes: 有効な銘柄コードの集合（抽出に使用）
known_codes = {"7203", "6758", "9984", ...}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

- J-Quants から株価取得（直接呼び出し）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from datetime import date

token = get_id_token()  # settings.jquants_refresh_token を利用
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(quotes))
```

- 研究用ファクター計算

```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
```

- 将来リターン・IC 計算・統計サマリー

```python
from kabusys.research import calc_forward_returns, calc_ic, factor_summary, rank
# calc_forward_returns(conn, target_date, horizons=[1,5,21])
# calc_ic(factor_records, forward_records, factor_col, return_col)
```

---

## 主要 API の説明（抜粋）

- kabusys.config
  - settings: 環境変数に基づくプロパティアクセス（例: settings.jquants_refresh_token）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None): refresh token から id token を取得
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
    - ページネーション対応、レートリミット、リトライ、401 の自動リフレッシュ
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)
    - DuckDB への冪等保存（ON CONFLICT）

- kabusys.data.schema
  - init_schema(db_path): DuckDB の全テーブル／インデックスを作成

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...): ETL の上位関数（カレンダー→株価→財務→品質チェック）

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30): RSS 取得・前処理（SSRF 対策、gzip/size制限）
  - save_raw_news(conn, articles), save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
    - 欠損 / 重複 / スパイク / 日付整合性 のチェック、QualityIssue のリストを返す

- kabusys.research
  - calc_momentum / calc_volatility / calc_value: ファクター計算（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank: 将来リターン・IC・統計処理ユーティリティ
  - kabusys.data.stats.zscore_normalize: Zスコア正規化ユーティリティ

---

## ディレクトリ構成

（src/kabusys 配下の主要ファイル・モジュール）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集・保存
    - schema.py              — DuckDB スキーマ定義と初期化
    - etl.py                 — ETL 公開インターフェース
    - pipeline.py            — ETL パイプライン実装（run_daily_etl 等）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - features.py            — 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py — マーケットカレンダー管理
    - audit.py               — 監査ログ（発注・約定トレーサビリティ）
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン / IC / summary
    - factor_research.py     — Momentum / Volatility / Value 計算
  - strategy/
    - __init__.py
    (戦略関連の実装を格納するためのプレースホルダ)
  - execution/
    - __init__.py
    (発注 / 約定処理の実装を格納するためのプレースホルダ)
  - monitoring/
    - __init__.py
    (監視・メトリクス用のプレースホルダ)

---

## 注意点・設計上の考慮

- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を探索）を基準に検出します。テストなどで自動ロードを抑止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants クライアントは 120 req/min のレート制限を尊重するため、固定間隔スロットリングを行います。大量の並列リクエストや高速ループでの利用は注意してください。
- DuckDB の INSERT は ON CONFLICT を使って冪等性を確保していますが、外部から直接 DB を改変する場合は整合性に注意してください。
- 多くのモジュールは「DuckDB 接続を受け取る」インターフェースになっているため、テスト時はインメモリ DB（":memory:"）を利用して単体テスト可能です。
- research モジュールのいくつかは外部ライブラリ（pandas 等）に依存しない実装になっています。大規模解析で高速化が必要な場合は適宜 pandas / numpy を併用してください。

---

## 付録: よく使う小さなコードスニペット

- 簡易 ETL を定期実行する（cron / Airflow 等から呼ぶ）:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date.today())
if res.has_quality_errors:
    # Slack に通知する等の処理を追加
    print("品質チェックでエラーがあります", res.to_dict())
```

- ニュース収集と銘柄紐付け（既知銘柄リストを用意しておく）:

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

---

この README はコードベースの主要機能と簡単な使い方をまとめたものです。各モジュールに詳細な docstring を付与しているため、実際の利用時は該当モジュールのドキュメント（関数 docstring）を参照してください。必要であれば、使い方の具体的なワークフロー（CI/CD における ETL スケジュール、Slack 通知フロー、実際の発注フロー例）を別途作成できます。