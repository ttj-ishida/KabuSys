# KabuSys

日本株自動売買プラットフォームのコアライブラリ。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ・監査など、研究→運用に必要な主要コンポーネントを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けの自動売買システムの基盤となる Python ライブラリ群です。主な役割は以下です。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 研究向けファクター計算（Momentum / Volatility / Value 等）
- 特徴量正規化・合成（features テーブルへの保存）
- シグナル生成（最終スコア計算、BUY/SELL 判定）
- ニュース収集（RSS → raw_news、銘柄紐付け）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ用スキーマ（signal_events / order_requests / executions 等）

設計方針として、ルックアヘッドバイアス防止、冪等性（ON CONFLICT / トランザクション）、外部依存を最小化する実装が採られています。

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env / 環境変数自動ロード（優先順位: OS 環境 > .env.local > .env）
  - 必須設定値取得（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）
  - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL 等

- kabusys.data.jquants_client
  - J-Quants API 呼び出し（レート制御、リトライ、トークン自動リフレッシュ）
  - データ取得: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存: save_daily_quotes / save_financial_statements / save_market_calendar

- kabusys.data.schema
  - DuckDB のスキーマ定義と初期化（init_schema, get_connection）

- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.news_collector
  - RSS フィード取得・前処理・正規化・DB 保存・銘柄抽出

- kabusys.data.calendar_management
  - 営業日判定 / next_trading_day / prev_trading_day / calendar_update_job

- kabusys.data.stats
  - zscore_normalize（クロスセクション Z スコア正規化）

- kabusys.research
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials に基づくファクター）
  - 研究用ユーティリティ: calc_forward_returns / calc_ic / factor_summary / rank

- kabusys.strategy
  - build_features（feature_engineering）
  - generate_signals（signal_generator）

- kabusys.execution / kabusys.monitoring
  - 実行・モニタリング用のプレースホルダ（実装の拡張を想定）

---

## 必要要件

- Python 3.10 以上（PEP 604 の型表記（|）を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリのみで実装されている箇所が多く、追加依存は限定的）

pip を使った例:
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# プロジェクトを editable install する場合:
pip install -e .
```

（プロジェクト配布に setup/pyproject がある前提で editable インストール可能）

---

## 環境変数・設定 (.env)

自動的にプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` をロードします。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション等の API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）

任意 / デフォルト値あり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化するフラグ（任意）

.env 例（.env.example を参照して作成してください）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・パッケージインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   # 必要なら他の依存も追加
   ```

3. 環境変数をセット（.env をプロジェクトルートに配置）
   - `.env` または `.env.local` に必須変数を設定

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # conn は duckdb.DuckDBPyConnection
   conn.close()
   ```

---

## 使い方（主要なユースケース例）

以下はライブラリの基本的な使い方の例です。実行は Python スクリプトやジョブスケジューラから行います。

- 日次 ETL を実行する（市場カレンダー・株価・財務を更新して品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 特徴量をビルドして features テーブルへ保存
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
conn.close()
```

- シグナル生成（features + ai_scores → signals）
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")
conn.close()
```

- ニュース収集ジョブ（RSS から raw_news に保存、銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
conn.close()
```

- マーケットカレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
conn.close()
```

---

## 注意点 / 運用上のポイント

- トークン管理
  - J-Quants は id_token の自動リフレッシュをサポート（refresh_token を .env に設定）。
  - HTTP エラー時のリトライ・レート制御が組み込まれています。

- 冪等性
  - DuckDB への保存は ON CONFLICT / トランザクションで設計されているため、再実行が安全です。

- ルックアヘッドバイアス
  - ファクター計算・シグナル生成は target_date 時点の情報のみを使うように設計されています。

- カレンダー未取得時のフォールバック
  - market_calendar が未構築の場合、曜日ベースで営業日判定を行います。

- KABUSYS_ENV による環境切替
  - live/paper_trading/development を区別して運用できます。is_live / is_paper / is_dev プロパティで判定可能です。

---

## ディレクトリ構成

リポジトリの主要なファイル・ディレクトリ（抜粋）:

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
    - audit（監査関連DDL等）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/  (発注ロジック等の実装想定)
  - monitoring/ (監視/通知用実装想定)

ファイル例（主要）:
- src/kabusys/config.py — 環境変数のロードと Settings クラス
- src/kabusys/data/schema.py — DuckDB の DDL と init_schema()
- src/kabusys/data/jquants_client.py — API クライアントと保存ユーティリティ
- src/kabusys/research/factor_research.py — momentum/volatility/value の計算
- src/kabusys/strategy/feature_engineering.py — features テーブル生成
- src/kabusys/strategy/signal_generator.py — シグナル生成ロジック
- src/kabusys/data/news_collector.py — RSS 収集と raw_news 保存

---

## 開発・テストのヒント

- 自動 .env ロードはプロジェクトルート検出を行うため、テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、必要な環境変数を明示的に注入してください。
- DuckDB のテストには `:memory:` を使うことで一時 DB を利用できます:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```
- news_collector や jquants_client のネットワーク層は関数単位でモックしやすい作りになっています（例: _urlopen を差し替える等）。

---

以上が README の概要です。README に加えたい具体的な使用例（CI ジョブ、cron スクリプト、Slack 通知フロー等）があれば、用途に合わせてサンプルやテンプレートを追加できます。必要なら日本語の .env.example も作成します。