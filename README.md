# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
DuckDB を中心としたデータレイク、J‑Quants API からのデータ取得、ニュース収集、特徴量計算、ETL パイプライン、品質チェック、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです。

- J‑Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に蓄積
- RSS からニュースを収集して記事・銘柄紐付けを行う
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と IC 計算
- ETL の差分更新ロジック / バックフィル戦略
- 発注・監査ログ用スキーマ（発注ライフサイクルのトレーサビリティ）

設計方針のポイント:
- DuckDB を中心に SQL ウィンドウ関数を活用し高速に集計
- 冪等性（ON CONFLICT / INSERT ... RETURNING 等）を重視
- 外部 API 呼び出しはレート制御・リトライ・トークン自動更新など堅牢化済み
- 研究用（research）モジュールは本番 API にアクセスしない設計

---

## 主な機能一覧

- 環境設定管理（.env 自動読み込み / 必須環境変数検証）
- J‑Quants API クライアント（レートリミット、リトライ、トークン更新）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - 保存関数 save_daily_quotes / save_financial_statements / save_market_calendar
- DuckDB スキーマ定義・初期化（data.schema.init_schema）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- データ品質チェック（missing / spike / duplicates / date_consistency）
- ニュース収集（RSS パース、URL 正規化、SSRF 対策、raw_news 保存、銘柄抽出）
- ファクター計算（calc_momentum / calc_volatility / calc_value）
- 研究支援（将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化）
- 監査ログスキーマ（signal_events / order_requests / executions 等）

---

## 必要条件・インストール

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

簡単なセットアップ例:

1. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージのインストール
   （プロジェクトに requirements.txt がある場合はそちらを使ってください）
   ```bash
   pip install duckdb defusedxml
   ```

3. パッケージとして開発インストール（プロジェクトルートで）
   ```bash
   pip install -e .
   ```

---

## 環境変数

このプロジェクトは環境変数から設定を読み込みます（.env /.env.local をサポート）。自動読み込みの優先順は OS 環境変数 > .env.local > .env です。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須変数:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

オプション:
- KABUSYS_ENV — 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（データベース初期化）

DuckDB スキーマを初期化して接続を得る基本例:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照します
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

監査ログ専用 DB を初期化する場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（主要操作）

1) 日次 ETL の実行（市場カレンダー取得→株価差分→財務差分→品質チェック）

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース収集ジョブ実行（RSS 収集→raw_news 保存→銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に保有している有効銘柄セット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

3) ファクター / 研究用 API

- モメンタム計算:
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.research.factor_research import calc_momentum

conn = init_schema("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2024, 1, 31))
# records は [{ "date": date, "code": "7203", "mom_1m": ..., "ma200_dev": ... }, ...]
```

- 将来リターンと IC の計算:
```python
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
fwd = calc_forward_returns(conn, target_date=date(2024,1,31), horizons=[1,5,21])
# factor_records は calc_momentum 等の戻り値
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

4) J‑Quants からのデータ直接フェッチ（テストや手動取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```
ID トークンは内部でキャッシュ・自動リフレッシュされます。

---

## CLI / バッチ運用（例）

cron / systemd timer などで日次 ETL を実行する場合、単純な実行スクリプト例:

run_daily.py:
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

これを定期実行（例: 毎朝）することでデータ基盤を更新できます。

---

## 注意点 / 実装上のメモ

- J‑Quants API: レート制限（120 req/min）を内部で管理します。429/408/5xx に対するリトライ・指数バックオフ、401 時はトークン自動更新を実装済みです。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。CI やテストで自動読み込みを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- NewsCollector は SSRF 対策・gzip 上限・XML パースにおける defusedxml 利用など安全面を考慮しています。
- DuckDB に対する DDL は冪等に実行されますが、監査スキーマ初期化時にタイムゾーンを UTC に固定します（init_audit_schema）。
- research モジュールは本番 API にアクセスしない方針で、prices_daily / raw_financials からのみデータを参照します。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要ファイル抜粋）

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - features.py
    - stats.py
    - calendar_management.py
    - audit.py
    - etl.py
    - quality.py
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

各モジュールの役割:
- config.py: 環境変数読み込み・設定アクセス
- data/: データ取得・保存・ETL・品質チェック・スキーマ
- research/: 特徴量・ファクター計算・IC や統計ユーティリティ
- execution/: 発注ロジック（将来実装の想定）
- strategy/: 戦略管理（将来実装の想定）
- monitoring/: 監視/アラート関連（将来実装の想定）

---

## 貢献 / 開発

- コードベースはタイプヒント・ドキュメンテーション文字列が充実しており、ユニットテストを追加しやすい設計です。
- 新しいデータソースの追加や、発注インターフェース（kabu ステーション連携）の実装は data / execution モジュールに機能を追加してください。
- DB マイグレーションやスキーマ変更は既存のデータ互換性を考慮して行ってください（DuckDB の制約に注意）。

---

必要であれば README に含める具体的な .env.example、cron 定義、もしくはユースケース別のコードスニペット（バックフィルのやり方、ローカルテストのための in-memory DB 使用例など）を追加します。どの情報を優先して追加しますか？