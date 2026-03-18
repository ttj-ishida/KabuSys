# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、DuckDB ベースのスキーマ管理、ETL パイプライン、特徴量計算、ニュース収集、監査ログなどを一通りサポートします。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とした研究・運用プラットフォームのコア機能群を提供する Python パッケージです。主な目的は以下です。

- J-Quants API を使った市場データ／財務データの取得と DuckDB への冪等保存
- DuckDB 上のスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース（RSS）収集と銘柄紐付け
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Zスコア正規化）
- 監査ログ（シグナル→発注→約定のトレース）

設計の重点は「冪等性」「Look-ahead バイアス回避」「堅牢な入出力（XML/HTTP/DB）」「テスト容易性」です。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants からの日足（OHLCV）・財務データ・市場カレンダー取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT / UPSERT 相当）
  - 受信日時（fetched_at）で取得タイミングを記録

- ETL / データ品質
  - 差分更新（最終取得日からの新規取得）とバックフィル
  - market_calendar を使った営業日調整
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集
  - RSS 取得（gzip 対応）、XML パース防御（defusedxml）
  - URL 正規化・トラッキングパラメータ除去、SSRF 対策
  - raw_news / news_symbols への冪等保存

- 研究（Research）
  - momentum / volatility / value といったファクター計算
  - 将来リターン計算（forward returns）
  - IC（Spearman ρ）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

- 監査（Audit）
  - signal_events / order_requests / executions を使ったトレーサビリティ
  - UTC 固定、ステータス管理、冪等キー対応

- 設定管理
  - .env（.env.local を上書き）または OS 環境変数から設定を自動読み込み
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化（テスト用）

---

## 必要環境 / 依存関係

- Python 3.9+（型ヒントの union 型等を使用しています）
- 必須パッケージ（一部機能）
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージとしてインストールする場合:
# pip install -e .
```

（プロジェクトをパッケージ化していれば `pip install -e .` などでインストール可能です）

---

## 環境変数 / 設定

KabuSys は .env / .env.local ファイルまたは環境変数から設定を読み込みます（プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数:

- J-Quants 関連
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- kabuステーション API（発注連携など）
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack（通知）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- 実行環境 / ログ
  - KABUSYS_ENV (development|paper_trading|live), デフォルト development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL), デフォルト INFO

環境変数未設定の必須キーを参照すると ValueError が発生します（settings モジュール経由）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンし仮想環境を作成

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 任意: ローカルでパッケージを編集しながら使う場合
pip install -e .
```

2. .env を作成（プロジェクトルートに配置）
   - .env.example がある場合はそれを参考に作成してください（本コードには例ファイルは含まれていませんが、必要なキーは上記に示した通りです）。

3. DuckDB スキーマ初期化

Python スクリプトまたは REPL で:

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# 監査ログ専用 DB を別に作成したい場合:
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

`init_schema` は親ディレクトリを自動作成します。":memory:" を渡せばインメモリ DB で初期化できます。

---

## 使い方（主要な例）

- 日次 ETL 実行（株価・財務・カレンダーの差分取得／保存／品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data import pipeline, schema

# DB 初期化済みと仮定
conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- J-Quants から日足を直接フェッチして保存（テストなど）

```python
from kabusys.data import jquants_client as jq
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"fetched={len(records)} saved={saved}")
```

- ニュース収集ジョブの実行

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")

# known_codes は銘柄抽出に使用する有効コードのセット（省略可能）
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- 研究系（ファクター計算 / IC）

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
fwd = calc_forward_returns(conn, d, horizons=[1,5,21])

# 例: モメンタム 1m と 翌日リターン fwd_1d の IC を計算
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
print("IC:", ic)

# ファクターサマリー
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
print(summary)
```

---

## 主要 API / モジュール一覧（概要）

- kabusys.config
  - settings: 環境変数ベースの設定取得（自動 .env ロードを実装）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 + 保存）
  - news_collector: RSS 取得と raw_news 保存、銘柄抽出
  - schema: DuckDB スキーマ定義と init_schema()
  - pipeline: ETL パイプライン（run_daily_etl 等）
  - quality: データ品質チェック
  - stats / features: 統計ユーティリティ（zscore_normalize）
  - audit: 監査ログテーブル初期化（init_audit_db）
  - calendar_management: 営業日判定 / カレンダー更新ジョブ
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - etl.py
      - features.py
      - stats.py
      - quality.py
      - calendar_management.py
      - audit.py
      - pipeline.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

各ファイルは README に記載した機能ごとに責務を分離しています。詳細は各モジュールの docstring を参照してください。

---

## 注意点 / トラブルシューティング

- 環境変数の未設定
  - settings の必須キー（例: JQUANTS_REFRESH_TOKEN）が未設定だと ValueError が発生します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、必要な値をプログラム内で差し替えてください。

- DuckDB のファイルパス
  - init_schema は親ディレクトリを自動作成しますが、パスに権限問題があると失敗します。パスが正しいか確認してください。

- ネットワーク / API エラー
  - jquants_client はリトライ・レート制御・トークン自動更新を備えていますが、API 側の問題やネットワーク障害はログに出力されます。429 の場合は Retry-After を尊重して再試行します。

- RSS 周りのセキュリティ
  - news_collector は SSRF / XML bomb 等の対策を施していますが、外部フィードの取り扱いには注意してください。

---

## 開発 / テスト

- 自動 .env ロードを無効化する:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env の自動読み込みをスキップできます（単体テストや CI 環境で便利）。

- モジュール間の外部依存（HTTP 呼び出しなど）はモックしやすい設計です（関数に id_token を注入する、_urlopen を差し替える等）。

---

必要であれば、README に具体的な .env.example、テーブル定義の ER 図、または運用時のワークフロー（夜間バッチスケジュール、Slack 通知の例）を追加します。どの情報を優先して追加しましょうか？