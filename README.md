# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETL、DuckDB スキーマ、ニュース収集、特徴量計算、研究用ユーティリティ、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 主な機能一覧
- 必要条件 / 依存パッケージ
- セットアップ手順
- 環境変数一覧 (.env の例)
- 使い方（主要ユースケースの例）
  - DuckDB スキーマ初期化
  - 日次 ETL 実行
  - ニュース収集ジョブ
  - 研究用ファクター計算
- ディレクトリ構成（主要ファイル説明）
- 補足 / 設計上の注意点

---

## プロジェクト概要
KabuSys は、日本株の自動売買システム向けに設計された内部ライブラリです。  
主に次を実現します。
- J-Quants API を使った市場データ・財務データ・カレンダーの取得（レート制御・リトライ・トークンリフレッシュ対応）
- DuckDB を用いた永続データベースのスキーマ定義・初期化・ETL パイプライン
- RSS を用いたニュース収集と銘柄抽出（SSRF 対策・サイズ制限・冪等保存）
- ファクター計算・特徴量探索・統計ユーティリティ（研究用途）
- 監査ログ用スキーマ（シグナル → 発注 → 約定のトレーサビリティ）
- データ品質チェックモジュール

設計方針としては、外部 API への過度な依存を避け、DuckDB と標準ライブラリ中心で堅牢に実装することを重視しています。

---

## 主な機能一覧
- data/
  - jquants_client: J-Quants API クライアント（ページネーション / リトライ / レートリミット / トークンリフレッシュ）
  - schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 差分 ETL（prices / financials / calendar）の実行、run_daily_etl を提供
  - news_collector: RSS 取得 → 前処理 → raw_news 保存 → 銘柄紐付け
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマの初期化（signal_events, order_requests, executions）
  - stats: Zスコア正規化等の統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランク化関数
- config: 環境変数読み込み・管理。プロジェクトルートから `.env` / `.env.local` を自動読み込み（無効化可）
- execution, strategy, monitoring: パッケージプレースホルダ（戦略・発注・監視ロジックを拡張可能）

---

## 必要条件 / 依存パッケージ
推奨 Python バージョン: 3.10 以上（型注釈に | を使用しているため）  
主な依存:
- duckdb
- defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発用にパッケージを editable インストールする場合:
# pip install -e .
```

（実際の packaging 情報は pyproject.toml や setup.py を参照してください）

---

## セットアップ手順

1. 仮想環境の作成・依存パッケージのインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   ```

2. 環境変数を設定（.env をプロジェクトルートに作成）
   - 下の「環境変数一覧」を参照してください。
   - パッケージは起動時にプロジェクトルートの `.env` / `.env.local` を自動読み込みします（無効化可）。

3. DuckDB スキーマ初期化（例）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は .env で指定可能
   ```

4. 監査ログ用スキーマを追加したい場合:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)  # 既存の接続に監査テーブルを追加
   ```

---

## 環境変数一覧（.env の例）

必須環境変数:
- JQUANTS_REFRESH_TOKEN = <your_jquants_refresh_token>
- SLACK_BOT_TOKEN = <slack_bot_token>
- SLACK_CHANNEL_ID = <slack_channel_id>
- KABU_API_PASSWORD = <kabu_api_password>

任意（デフォルト値があるもの）:
- KABUSYS_ENV = development | paper_trading | live  (デフォルト: development)
- LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL (デフォルト: INFO)
- KABU_API_BASE_URL = http://localhost:18080/kabusapi (kabuステーション用)
- DUCKDB_PATH = data/kabusys.duckdb (DuckDB ファイルパス)
- SQLITE_PATH = data/monitoring.db

自動 .env 読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を自動で読み込みます。
- テスト等で自動読み込みを無効にする場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

.env.example（簡易例）
```
JQUANTS_REFRESH_TOKEN=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=yourpassword
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=/path/to/data/kabusys.duckdb
```

---

## 使い方（代表的な例）

以下は簡単な Python スクリプト例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

run_daily_etl は次の処理を行います（独立したエラーハンドリングで継続）:
- 市場カレンダー ETL（lookahead 取得）
- 株価日足 ETL（差分取得・backfill）
- 財務データ ETL（差分取得）
- 品質チェック（quality モジュール）

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", ...}  # 既知銘柄セット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

4) J-Quants から株価を直接取得（テスト用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings
from datetime import date

token = get_id_token()  # settings.jquants_refresh_token を用いて取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(records))
```

5) 研究用: ファクター計算 / IC 計算
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("/path/to/kabusys.duckdb")
target = date(2024,1,31)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

# 例: mom の mom_1m と fwd_1d の IC を計算
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)

summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
print(summary)
```

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（自動 .env ロード、必須変数要求）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レート制御、リトライ、token refresh、保存ユーティリティ）
    - news_collector.py
      - RSS フェッチ、前処理、raw_news 保存、銘柄抽出、SSRF 対策
    - schema.py
      - DuckDB の DDL 定義、init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（差分取得・backfill・品質チェック）、run_daily_etl
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - audit.py
      - 監査ログテーブル定義・初期化（signal_events, order_requests, executions）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - features についての公開インターフェース（zscore の再エクスポート）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、rank
  - strategy/
    - __init__.py  （戦略実装用のプレースホルダ）
  - execution/
    - __init__.py  （発注ロジック用のプレースホルダ）
  - monitoring/
    - __init__.py  （監視用のプレースホルダ）

---

## 補足 / 設計上の注意点
- J-Quants API はレート制限があるため jquants_client は固定間隔スロットリングで制御しています（120 req/min）。
- jquants_client は 401 発生時に自動でリフレッシュトークンを使った ID トークンの再取得を1回行います。
- DuckDB へのデータ保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識して実装されています。
- news_collector では SSRF 対策、受信サイズ制限、XML の脆弱性対策（defusedxml）を組み込んでいます。
- カレンダーや ETL の一部処理は market_calendar が未取得のときに曜日ベースのフォールバックを行います。
- audit スキーマはトレーサビリティを重視しており、削除を前提としない設計です。

---

必要であれば、README に含める具体的な .env.example、起動スクリプト例、Dockerfile、または CI 用のコマンド例を追加します。どの情報を優先的に追加しますか？