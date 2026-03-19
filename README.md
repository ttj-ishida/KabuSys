# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、DuckDBスキーマ管理、監査ログなどの機能を提供します。

---

## プロジェクト概要

KabuSys は以下の層を想定したモジュール群を含むライブラリです。

- データ取得 / ETL（J-Quants API 経由）
- DuckDB ベースのデータスキーマ定義と初期化
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量の正規化・作成（feature layer）
- シグナル生成（戦略ロジックに基づく BUY / SELL 判定）
- ニュース収集（RSS）と銘柄紐付け
- 市場カレンダー管理（JPX）
- 発注・監査用スキーマ（発注フロー追跡用）

設計上のポイント:
- ルックアヘッドバイアス対策（計算は target_date 時点のデータのみを使用）
- 冪等性（DB 保存は ON CONFLICT で安全に更新）
- DuckDB を中心とした軽量ローカルDB運用
- 外部依存は最小限（標準ライブラリ中心、DuckDB / defusedxml 等のみ）

---

## 主な機能一覧

- data
  - J-Quants API クライアント（取得・ページネーション・自動リフレッシュ・レート制御）
  - DuckDB スキーマ定義 / 初期化（init_schema）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ニュース収集（RSS取得、前処理、raw_news 保存、銘柄抽出）
  - マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - 統計ユーティリティ（Z スコア正規化）
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量探索ユーティリティ（forward returns, IC, summary）
- strategy
  - 特徴量構築（build_features: features テーブルへの upsert）
  - シグナル生成（generate_signals: features / ai_scores / positions を参照して BUY/SELL を保存）
- monitoring / execution / audit
  - 発注・監査用スキーマとテーブル（監査ログ・order_requests / executions 等のDDLを含む）

---

## 依存関係

最低限必要なパッケージ（例）:

- Python 3.10+
- duckdb
- defusedxml

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（プロジェクトで requirements.txt / pyproject.toml があればそちらを利用してください）

---

## 環境変数 / 設定

settings（kabusys.config.Settings）で参照する主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用（本プロジェクト設定値）
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション / デフォルトあり:
- KABUSYS_ENV — 実行環境（development / paper_trading / live） デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に `1` を設定

自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探して `.env` / `.env.local` を自動で読み込みます。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローン
```
git clone <repo-url>
cd <repo>
```

2. 仮想環境を作成して有効化
```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

3. 必須パッケージをインストール
```
pip install duckdb defusedxml
```

4. 環境変数設定
- プロジェクトルートに `.env` を作成し、必要なキーを設定します（.env.example を参照することを推奨）。
例:
```
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB スキーマ初期化（Python コンソールまたはスクリプト）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# ファイルパスを明示するか settings.duckdb_path を使用
conn = init_schema(settings.duckdb_path)
```

---

## 使い方（主要な例）

以下は主要な機能を利用する際の例コードスニペットです。

- 日次 ETL 実行（株価 / 財務 / カレンダーの差分取得）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量構築（features テーブルへ書き込み）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date(2024, 1, 10))
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブルへ書き込み）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date(2024, 1, 10), threshold=0.6)
print(f"signals generated: {count}")
```

- ニュース収集ジョブ
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = get_connection(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 既知銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- JPX カレンダー更新バッチ
```python
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- 各関数は DuckDB の接続オブジェクトを受け取ります。init_schema は必要に応じて DB ファイルの親ディレクトリを作成します。
- ETL / API クライアントはネットワークアクセス・認証情報（JQUANTS_REFRESH_TOKEN 等）を必要とします。

---

## ディレクトリ構成

（主要ファイルのみ抜粋、src 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数設定の読み込み・Settings 定義
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得・保存）
    - schema.py                      — DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - news_collector.py              — RSS 取得・前処理・DB 保存
    - calendar_management.py         — 市場カレンダー管理（is_trading_day 等）
    - audit.py                       — 監査ログ用 DDL とインデックス
    - features.py                    — 統計ユーティリティ再エクスポート
    - stats.py                       — z-score 正規化など統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py             — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py         — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py         — build_features（features テーブル作成）
    - signal_generator.py            — generate_signals（BUY/SELL 判定）
  - execution/                        — 発注関連の実装（空の __init__ など）
  - monitoring/                       — 監視・サマリー用（別モジュール想定）

---

## 開発上の注意点 / 補足

- Python 3.10 以上を想定しています（| 型ヒントなどを使用）。
- DuckDB はローカルの分析 DB として想定。パフォーマンスに応じてインデックス等を調整してください。
- J-Quants API のレート制限（120 req/min）に対応する内部レートリミッタとリトライロジックを実装しています。
- ニュース収集では SSRF 対策、XML パースに defusedxml を利用した安全対策を実装しています。
- 環境変数は .env / .env.local の自動読み込みを行います。テスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 本リポジトリは戦略仕様（StrategyModel.md 等）に基づいた実装を行っています。実運用の前に十分なバックテスト・検証を行ってください。

---

必要であれば、README に含めるサンプル .env.example、CI スクリプト例、より詳細な API リファレンスや開発フロー（テスト、型チェック、Lint 設定）なども追加できます。追加項目の希望があれば教えてください。