# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買およびデータ基盤を想定したライブラリ群です。  
DuckDB を用いたデータレイヤ、J-Quants からのデータ取得クライアント、ETL パイプライン、ニュース収集、ファクター計算（リサーチ向け）や監査ログ等のコンポーネントを含みます。

---

## プロジェクト概要

主な目的:
- J-Quants API を用いた株価・財務・カレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB によるデータレイク（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得、品質チェック）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策・トラッキング除去）
- 戦略／リサーチ用のファクター計算（モメンタム・ボラティリティ・バリュー等）
- 監査・トレーサビリティ用テーブル群（シグナル→発注→約定の追跡）

設計方針の抜粋:
- DuckDB を用いた冪等（ON CONFLICT）なデータ保存
- 外部 API に対してレート制御・リトライ・トークン管理を実装
- リサーチ系関数は発注 API に触れず、標準ライブラリのみで実装している部分が多い
- セキュリティ考慮（SSRF、XML Bomb、URL 正規化、プライベートアドレス検出等）

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（id_token 取得、自動リフレッシュ、ページネーション、リトライ、RateLimiter）
  - fetch/save 用関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / save_* 系
- data/schema.py
  - DuckDB のテーブル定義と init_schema() による初期化（Raw/Processed/Feature/Execution 層）
- data/pipeline.py
  - 日次 ETL 実行 run_daily_etl(): カレンダー・株価・財務の差分取得と品質チェック
- data/news_collector.py
  - RSS フィード取得・前処理・raw_news 保存・銘柄抽出・news_symbols 紐付け
  - SSRF 対策、gzip サイズ上限、トラッキングパラメータ除去、記事ID は正規化URLの SHA-256（先頭32文字）
- data/quality.py
  - 欠損・スパイク・重複・日付不整合のチェック（QualityIssue を返す）
- data/calendar_management.py
  - market_calendar の差分更新ジョブ、営業日判定・前後営業日取得ユーティリティ
- research/*
  - feature_exploration.py: forward returns, IC（Spearman ρ）計算、ランク関数、ファクター要約
  - factor_research.py: momentum / volatility / value 等のファクター計算（prices_daily / raw_financials に依存）
  - data.stats.zscore_normalize を利用した Z スコア正規化ユーティリティ
- audit.py
  - 監査ログ（signal_events / order_requests / executions）用の DDL と初期化ユーティリティ

注意:
- research の関数は「本番口座・発注 API にはアクセスしない」設計です。リサーチ専用に安全に使えます。

---

## 前提・依存関係

推奨 Python バージョン: 3.10 以降（注: ソース内で X | None などのシンタックスを使用）

主な外部ライブラリ:
- duckdb
- defusedxml

（その他、標準ライブラリの urllib / logging / dataclasses / typing 等を使用）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージを editable にインストールする場合
pip install -e .
```

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動で読み込まれます（自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主要な環境変数（Settings 参照）:
- JQUANTS_REFRESH_TOKEN  (必須) - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD       (必須) - kabuステーション API パスワード
- KABU_API_BASE_URL       (省略可, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN         (必須) - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID        (必須) - Slack チャネル ID
- DUCKDB_PATH             (省略可, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH             (省略可, デフォルト: data/monitoring.db)
- KABUSYS_ENV             (省略可, 'development'|'paper_trading'|'live', default 'development')
- LOG_LEVEL               (省略可, 'DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL', default 'INFO')

.env の例（テンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

設定にアクセスするには:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

未設定の必須変数を参照すると ValueError が投げられます。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / コピー
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール（duckdb, defusedxml など）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. DuckDB スキーマの初期化

例:
```bash
# 仮想環境 (Unix 系)
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml

# Python パッケージをプロジェクトに直接インストールする場合
pip install -e .

# .env を作成（上の例を参照）
# DB 初期化は Python REPL やスクリプトから:
python - <<'PY'
from kabusys.config import settings
from kabusys.data.schema import init_schema
conn = init_schema(settings.duckdb_path)
print("Initialized:", settings.duckdb_path)
PY
```

---

## 基本的な使い方（コード例）

- DuckDB スキーマ初期化:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成
```

- 日次 ETL 実行:
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # デフォルトで今日を対象に ETL 実行
print(result.to_dict())
```

- ニュース収集ジョブ実行:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

- ファクター計算 / リサーチユーティリティ:
```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize

conn = init_schema(":memory:")  # or init_schema(settings.duckdb_path)
t = date(2024, 1, 31)

momentum = calc_momentum(conn, t)
forward = calc_forward_returns(conn, t, horizons=[1,5,21])
# 例: mom_1m と fwd_1d の IC
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(momentum, ["mom_1m", "mom_3m", "ma200_dev"])
normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

- J-Quants クライアントを直接使う（注意: Rate limiter・認証を内部で扱います）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
from kabusys.config import settings
from datetime import date

recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(recs))
```

---

## 開発時の注意点 / 実装上のポイント

- 自動で .env を読み込む仕組み
  - プロジェクトルートはソースファイルの場所を基準に .git または pyproject.toml を探索して決定します。テスト等で自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API
  - レート制限は 120 req/min を想定しており、内部的にスロットリングしています。
  - 401 を受けた場合はリフレッシュトークンで自動的に ID トークンを再取得して 1 回だけリトライします。
  - 408/429/5xx 系は指数バックオフでリトライします（最大試行回数 3 回）。
- News collector
  - RSS の取得には SSRF 対策・gzip サイズ上限・XML パースの安全対策（defusedxml）を実装しています。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で冪等性を確保します。
- ETL
  - 差分取得を行い、バックフィル日数を指定して API の後出し修正を吸収する設計です。
  - 品質チェックは Fail-Fast ではなく問題を収集して戻す方針です（呼び出し元で判断）。

---

## ディレクトリ構成

主要ファイル / 主要モジュール（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得 / 保存）
    - news_collector.py              — RSS 収集 / 前処理 / 保存 / 銘柄抽出
    - schema.py                      — DuckDB スキーマ定義 / init_schema
    - stats.py                       — zscore_normalize 等の統計ユーティリティ
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - features.py                    — features への公開インターフェース（再エクスポート）
    - calendar_management.py         — market_calendar 管理ユーティリティ
    - audit.py                       — 監査ログ（signal/order/execution）DDL 初期化
    - etl.py                         — ETLResult 再エクスポート
    - quality.py                     — データ品質チェック
  - research/
    - __init__.py
    - factor_research.py             — モメンタム / ボラティリティ / バリュー 計算
    - feature_exploration.py         — forward returns / IC / summary / rank
  - strategy/                        — （将来的な戦略モジュール用、現状空）
  - execution/                       — （発注系モジュール用、現状空）
  - monitoring/                      — （監視系モジュール用、現状空）

補足: README は最新版のコードベースに合わせて更新してください。各モジュール内の docstring に設計意図・使い方が記載されています。

---

もし希望があれば、以下を追加で作成できます:
- .env.example のテンプレートファイル
- 開発用 Dockerfile / docker-compose 構成（DuckDB はファイルベースなので軽量）
- よく使う CLI スクリプト（init-db, run-etl, collect-news 等）

必要であればどれを出力するか指示してください。