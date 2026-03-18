# KabuSys

日本株自動売買システム用のライブラリ群（データ収集・ETL・特徴量生成・監査・研究用ユーティリティ）。  
DuckDB を中心としたローカルデータレイヤと、J-Quants / RSS 等からのデータ取得ロジック、品質チェック、研究用ファクター計算などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的のために設計されたモジュール群です。

- J-Quants API からの株価・財務・市場カレンダー取得（レート制限・リトライ・トークンリフレッシュ対応）
- RSS ニュース収集と記事の正規化・銘柄紐付け
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 研究用ユーティリティ（将来リターン計算、IC、ファクター算出、Zスコア正規化 等）
- データ品質チェック、マーケットカレンダー管理、監査ログ用スキーマ等

設計方針として、本番の発注 API にはアクセスせず、データ層と研究層を分離して安全に扱えるようになっています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御、リトライ、トークンリフレッシュ、DuckDB への保存ユーティリティ）
  - news_collector: RSS フィードの取得、前処理、DuckDB へ冪等保存、銘柄抽出
  - schema: DuckDB スキーマ定義・初期化（raw_prices, prices_daily, features, audit など）
  - pipeline: 日次 ETL（calendar / prices / financials の差分取得、品質チェック）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 市場カレンダーの管理・営業日判定ユーティリティ・夜間更新ジョブ
  - audit: 監査ログ（signal_events, order_requests, executions）のスキーマと初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman rank）計算、ファクター統計サマリー
- config:
  - 環境変数管理、自動 .env ロード（.env.local を優先して読み込む）、必須設定チェック

---

## 要件 (推奨)

- Python 3.10+
- duckdb
- defusedxml

（実行環境に応じて他の標準ライブラリのみで動く部分も多いですが、RSS 解析や DB 利用には上記が必要です。）

インストール例（仮想環境を推奨）:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 自前パッケージとして利用する場合:
pip install -e .
```

※ 本リポジトリがパッケージ化されていれば pip install -e . で開発インストール可能です。

---

## 環境変数 / .env

プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を置くと自動で読み込まれます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack のチャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用途の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)、デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)、デフォルト: INFO

例 (.env):

```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=passw0rd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

.env のサポートする書式はシェルの `KEY=VALUE` 形式に近く、シングル/ダブルクォートや `export KEY=...` 形式も扱えます。

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境を作成して依存ライブラリをインストール
   - 例: `pip install duckdb defusedxml`
3. プロジェクトルートに `.env`（必要な環境変数を設定）を置く
4. DuckDB スキーマの初期化

Python REPL またはスクリプトで:

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # または settings.duckdb_path
# 監査ログ用スキーマを別 DB に作る場合:
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

初期化により必要なテーブル・インデックスが作成されます。

---

## 使い方（主要ユースケース）

以下は代表的な使い方のサンプルです。

1) 日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data import pipeline, schema

# 初期化済みの DB 接続を使う
conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース収集を実行する

```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes を渡すと記事と銘柄の紐付けを実行
known_codes = {"7203", "6758", "9984"}  # 実運用では全銘柄セットを用意
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

3) ファクター計算 / 研究用 API

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# 将来リターンを計算して IC（Spearman）を評価
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

4) J-Quants API から個別データを取得して保存する（テストやバッチ）

```python
from kabusys.data import jquants_client as jq
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

---

## 主要 API の概要

- kabusys.config.settings  
  環境変数からアプリ設定を参照する（例: settings.jquants_refresh_token, settings.duckdb_path）

- kabusys.data.schema.init_schema(db_path)  
  DuckDB スキーマを初期化して接続を返す

- kabusys.data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(conn, records)  
  データ取得・保存ユーティリティ

- kabusys.data.pipeline.run_daily_etl(conn, target_date=...)  
  日次 ETL（カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック）

- kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)  
  RSS からニュース収集して raw_news / news_symbols に保存

- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank  
  研究用・特徴量計算・評価関数群

- kabusys.data.stats.zscore_normalize(records, columns)  
  クロスセクション Z スコア正規化

---

## 注意点 / 補足

- API レート制御・リトライ:
  - J-Quants クライアントは 120 req/min を想定したスロットリングと、408/429/5xx のリトライ、401 時の自動トークンリフレッシュを実装しています。

- DuckDB スキーマは冪等（既存テーブルはスキップ）で作成されます。監査ログは audit モジュールで別途初期化可能です。

- ニュース収集:
  - URL 正規化（トラッキングパラメータ除去）、SSRF 対策、レスポンスサイズ上限などの安全対策を実装しています。
  - 記事 ID は正規化 URL の SHA-256 先頭 32 文字で生成。重複挿入は ON CONFLICT で回避します。

- 品質チェック:
  - デフォルトでスパイク閾値は 50%（run_daily_etl の引数で変更可能）。品質問題は QualityIssue のリストとして返され、呼び出し側で扱いを決定します（エラーで ETL を止めるかログするか等）。

- 環境変数の自動ロード:
  - プロジェクトルートが自動判定できない（例えば配布後）場合は自動ロードはスキップされます。テスト等で自動ロードを停止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主要なファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - etl.py
    - audit.py
    - calendar_management.py
    - stats.py
    - features.py
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

（上記は実装済みモジュールの一覧です。strategy / execution / monitoring の一部は未実装または空の __init__ を含みます。）

---

## 開発・貢献

- コードは型アノテーションを用いており、Python 3.10+ を想定しています。
- テストや CI を追加する際は、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して環境依存を切り離すと便利です。
- DuckDB を使った DB 初期化は init_schema() で行います。開発中は ":memory:" を指定してインメモリ DB を利用できます。

---

この README はコードベースの現状に基づいて作成しています。実際の運用では、発注・実行モジュールや Slack 通知等の実装・設定が必要です。必要であれば各モジュールの使い方（関数引数や戻り値の詳細）についての追記例も作成します。