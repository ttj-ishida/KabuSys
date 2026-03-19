# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
本リポジトリはデータ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどのコンポーネントを含むモジュール群を提供します。

> 注: この README はパッケージのソースコードに基づいて作成しています。実際の運用では証券会社APIや本番資金での運用前に十分な検証を行ってください。

---

## プロジェクト概要

KabuSys は以下のレイヤーを想定した日本株向けデータ＆戦略フレームワークです。

- Raw Layer: J-Quants 等から取得した生データ（株価、財務、ニュースなど）
- Processed Layer: 整形済み市場データ（prices_daily 等）
- Feature Layer: 戦略・AI向けの特徴量（features, ai_scores）
- Execution Layer: シグナル・注文・約定・ポジション等の監査・トレーサビリティ

主な設計方針:
- DuckDB を主要なデータストアとして使用（ローカルファイルまたはメモリ）
- J-Quants API のレート制限・リトライ・トークンリフレッシュ対応を実装
- ルックアヘッドバイアス対策（取得時刻/fetched_at の記録、target_date ベースの計算）
- 冪等性を重視（DB 保存は ON CONFLICT / トランザクションで安全に）

---

## 機能一覧

主要モジュールと機能（抜粋）:

- kabusys.config
  - .env 自動読み込み（プロジェクトルートの `.env` / `.env.local`、環境変数優先）
  - 必須設定の取得（JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_ENV / LOG_LEVEL 等の検証

- kabusys.data.jquants_client
  - J-Quants API クライアント（株価日足 / 財務 / カレンダー）
  - レートリミット、リトライ、トークンリフレッシュ対応
  - DuckDB への冪等保存ユーティリティ（save_daily_quotes 等）

- kabusys.data.schema
  - DuckDB スキーマ定義・初期化（init_schema）
  - テーブル定義（raw_prices / prices_daily / features / signals / orders / executions 等）

- kabusys.data.pipeline
  - 日次 ETL 実行（run_daily_etl）: カレンダー・株価・財務の差分取得 + 品質チェック
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）

- kabusys.data.news_collector
  - RSS 収集（fetch_rss / run_news_collection）
  - テキスト前処理、URL 正規化、SSRF 対策、DB 保存（save_raw_news / save_news_symbols）

- kabusys.research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
  - zscore_normalize（正規化ユーティリティ）

- kabusys.strategy
  - 特徴量作成（build_features）
  - シグナル生成（generate_signals）
    - final_score 計算、Bear レジーム抑制、BUY/SELL シグナルの DB 保存

- kabusys.data.calendar_management
  - 営業日判定 / next/prev trading day / カレンダー更新ジョブ

- kabusys.data.audit
  - 発注〜約定までの監査ログテーブル定義

---

## セットアップ手順

想定環境:
- Python 3.10 以上（PEP 604 の型記法 `X | Y` を使用）
- pip が使用可能

1. リポジトリをクローン・作業ディレクトリへ移動
   - 例: git clone ... && cd ...

2. 仮想環境を作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージをインストール
   - pip install -e .    # 編集可能インストール（プロジェクトルートに setup/pyproject がある場合）
   - 依存ライブラリの明示的インストール:
     - pip install duckdb defusedxml

   （注）実プロジェクトでは requirements.txt / pyproject.toml を参照してください。

4. 環境変数 / .env を用意
   - プロジェクトルートに `.env`（および `.env.local`）を配置すると自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   最低限設定すべき環境変数（例）
   - JQUANTS_REFRESH_TOKEN=xxxxx
   - KABU_API_PASSWORD=xxxxx
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C0123456
   - KABUSYS_ENV=development  # または paper_trading / live
   - LOG_LEVEL=INFO

   DB 関連（任意・デフォルト）
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db

5. データディレクトリを作成（必要なら）
   - mkdir -p data

---

## 使い方（主な操作例）

以下は Python REPL / スクリプト内での利用例です。DuckDB のパスは settings.duckdb_path を使うのが推奨です。

1. スキーマ初期化（DuckDB 作成）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成されます
```

2. 日次 ETL 実行（J-Quants から差分取得して保存）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. 特徴量（features）作成
```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4. シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals

count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
```

5. ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "6954"}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6. カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

7. 設定値の取得例
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)  # development / paper_trading / live
```

補足:
- 上記 API は基本的にデータベース接続（DuckDB の connection）を受け取ります。テストや一時実行では init_schema(":memory:") でメモリDBを使用できます。
- シグナル生成・特徴量計算は target_date 時点のデータのみを参照し、ルックアヘッドバイアスを避ける設計です。

---

## 必要な環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

.env の例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## ディレクトリ構成

主要なファイル/モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py            # RSS 収集・保存
    - schema.py                    # DuckDB スキーマ定義・init_schema
    - stats.py                     # 統計ユーティリティ（zscore_normalize）
    - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py       # カレンダー管理
    - audit.py                     # 監査ログテーブル定義
    - features.py                  # features 再エクスポート
  - research/
    - __init__.py
    - factor_research.py           # calc_momentum / calc_volatility / calc_value
    - feature_exploration.py       # calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py       # build_features
    - signal_generator.py          # generate_signals
  - execution/                     # （発注層：現在はパッケージ構成のみ）
  - monitoring/                    # 監視・モニタリング用 DB/処理（SQLite 等）用ディレクトリ

ドキュメント参照（ソース内コメント）:
- StrategyModel.md, DataPlatform.md, DataSchema.md 等（設計仕様参照がソースコメントに記載されています）。実際のリポジトリに同梱されていれば参照してください。

---

## 運用上の注意

- 本コードベースには発注処理の最終経路（証券会社API 呼び出し）を含めない/限定している箇所があります。リアルマネーで運用する前に必ず検証、リスク管理ルールの実装、冗長性チェックを行ってください。
- J-Quants の API トークン / 各種秘密情報は厳重に管理してください（.env は git 管理しないこと）。
- DuckDB ファイルは定期的にバックアップすることを推奨します。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env 自動ロードを抑止できます。

---

もし README に追加したい内容（例: CI / テストの実行方法、より詳しい設定例、サンプルワークフローの YAML ジョブ定義など）があれば教えてください。必要に応じて追記します。