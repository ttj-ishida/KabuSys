# KabuSys

日本株向けの自動売買基盤（ライブラリ）。データ取得・加工、特徴量生成、発注管理、モニタリングのための共通コンポーネント群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株アルゴリズム取引を構築するための基盤ライブラリです。主な提供機能は以下の通りです。

- 環境変数 / 設定の管理（.env 自動読み込みを含む）
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution の層構造）
- 発注・実行・モニタリングのパッケージ枠組み（strategy / execution / monitoring の骨格）
- Slack 連携や外部 API（J-Quants、kabuステーション）用の設定管理

---

## 機能一覧

- settings（kabusys.config.Settings）
  - J-Quants / kabu API / Slack / DB パス / 環境（development / paper_trading / live）/ ログレベル 等を環境変数から取得
  - 必須キー未設定時はエラーを送出
- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` / `.env.local` を読み込み
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすると自動ロードを無効化可能
  - シングル/ダブルクォート、エスケープ、コメント等に対する堅牢なパース実装
- DuckDB スキーマ（kabusys.data.schema）
  - レイヤー構成:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（CHECK, PRIMARY KEY, FOREIGN KEY）と索引を定義
  - init_schema(db_path) でスキーマ作成（冪等）／get_connection で接続取得
  - `":memory:"` を指定するとインメモリ DB を使用可能

---

## セットアップ手順

前提: Python 3.8+（型注釈に Path | None を使用しているため、環境に合わせて適宜）

1. リポジトリをクローン／配置
2. 必要パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
   - pip を使う例:
     - pip install duckdb
   - 開発時は editable インストール:
     - python -m pip install -e .
     （プロジェクトに pyproject.toml / setup.py がある前提です）
3. 環境変数を設定
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を配置するか、OS 環境変数を設定します。
   - 自動ロードを無効にしたい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例: 必要な環境変数（最低限）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意: development | paper_trading | live)
- LOG_LEVEL (任意: DEBUG | INFO | WARNING | ERROR | CRITICAL)

簡易的な .env の例:
```
JQUANTS_REFRESH_TOKEN="your_jquants_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C12345678"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方

- 設定を参照する:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print(settings.env, settings.is_dev, settings.log_level)
```

- DuckDB スキーマを初期化して接続を取得する:
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# ファイル DB を指定（settings.duckdb_path は Path オブジェクト）
conn = init_schema(settings.duckdb_path)

# またはインメモリ DB
mem_conn = init_schema(":memory:")

# 既存 DB へ接続（スキーマ初期化は行わない）
conn2 = get_connection(settings.duckdb_path)
```

- .env 自動ロードの挙動
  - import 時点で、`.env` と `.env.local` をプロジェクトルートから自動的に読み込みます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD` が設定されている場合は無効化されます）。
  - OS 環境変数が優先され、`.env.local` は `.env` より優先して読み込まれます（.env.local の方が override=True）。

注意: Settings の必須プロパティを参照すると、環境変数未設定で ValueError が発生します。実行前に必要な変数を設定してください。

---

## ディレクトリ構成

リポジトリの主要ファイル（抜粋）:

src/kabusys/
- __init__.py        — パッケージ初期化（__version__ = "0.1.0"）
- config.py          — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
- data/
  - __init__.py
  - schema.py        — DuckDB スキーマ定義・初期化（init_schema, get_connection）
- strategy/
  - __init__.py      — 戦略関連モジュール（拡張用）
- execution/
  - __init__.py      — 発注・実行関連モジュール（拡張用）
- monitoring/
  - __init__.py      — モニタリング関連モジュール（拡張用）

README やドキュメント（存在する場合）はプロジェクトルートに配置されます。

---

## 実装上のポイント / 備考

- .env パーサはクォート、エスケープ、インラインコメントなど一般的な .env 記法に対して堅牢に設計されています。
- DuckDB テーブルは外部キーや CHECK 制約を含み、索引を用意して典型的なクエリの性能を考慮しています。
- スキーマ初期化は冪等（既存テーブルの再作成は行いません）。
- プロジェクトの環境（development / paper_trading / live）により挙動を切り替える想定（settings.is_live / is_paper / is_dev を利用）。
- 現状はフレームワークと基盤部分が中心で、実際のデータ取得・発注ロジック・監視ロジックは各サブパッケージ（data/strategy/execution/monitoring）に実装していくことを前提としています。

---

必要に応じて README を拡張して、インストール手順（pyproject / setup.py に合わせた具体コマンド）、テスト方法、運用時の注意点、例となる戦略実装テンプレートなどを追加してください。