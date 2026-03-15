# KabuSys

日本株自動売買システムのコアライブラリ（パッケージ）。データ取得・スキーマ定義・戦略・発注・モニタリングの基盤を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けの内部ライブラリセットです。  
主に以下を提供します。

- 環境変数・設定の安全な読み込み（.env/.env.local の自動読み込みを含む）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）の定義・初期化
- 設計上のモジュール境界（data, strategy, execution, monitoring）

このリポジトリはライブラリのコア部分のみを含み、実際の戦略や発注ロジックは strategy / execution 以下に実装します。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み
  - export 形式やクォート、インラインコメント、エスケープ処理に対応したパーサ
  - 必須環境変数の取得ヘルパ（未設定時に例外）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution の4層でテーブルを定義
  - DDL は冪等（既存テーブルがあればスキップ）
  - インデックス作成（頻出クエリに対する最適化）
  - init_schema(db_path) によりディレクトリ作成→テーブル作成→接続を返す
  - get_connection(db_path) により既存 DB へ接続（初回は init_schema を推奨）

- 設定プロパティ
  - J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）等を properties で取得

---

## 要件

- Python 3.10+
  - 型アノテーションで | を使用しているため 3.10 以上が必要です
- duckdb（Python パッケージ）
- （必要に応じて）kabu API クライアント、J-Quants クライアント、Slack SDK など

インストール例（pip）:
```
pip install duckdb
```

パッケージをローカルで開発する場合:
```
pip install -e .
```
（pyproject.toml / setup が整っていることを前提）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成・有効化し、必要な依存をインストール
3. プロジェクトルートに .env（およびローカル用 .env.local）を作成
   - 自動的に読み込まれる（環境変数が優先される）
4. DuckDB スキーマを初期化

サンプル .env:
```
# J-Quants
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"

# kabuステーション API
KABU_API_PASSWORD="your_kabu_api_password"
KABU_API_BASE_URL="http://localhost:18080/kabusapi"  # デフォルトがあるため省略可

# Slack
SLACK_BOT_TOKEN="xoxb-xxxx"
SLACK_CHANNEL_ID="C0123456789"

# DB パス（省略時は data/kabusys.duckdb）
DUCKDB_PATH="data/kabusys.duckdb"
SQLITE_PATH="data/monitoring.db"

# 実行環境（development, paper_trading, live）
KABUSYS_ENV=development

# ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
LOG_LEVEL=INFO
```

自動読み込みを無効化したい場合（テスト等）:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（簡単な例）

- 設定値の取得:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
base_url = settings.kabu_api_base_url
is_live = settings.is_live
db_path = settings.duckdb_path  # Path オブジェクト
```

- DuckDB スキーマ初期化:
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

- 既存 DB へ接続（初回は init_schema を呼ぶこと）:
```python
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
```

- 自動読み込みを無効化して環境を自前で設定する:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
export JQUANTS_REFRESH_TOKEN=...
export KABU_API_PASSWORD=...
```

---

## ディレクトリ構成

リポジトリ内の主要なファイル・ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py            (パッケージ定義、__version__ = "0.1.0")
    - config.py              (環境変数 / Settings 管理、自動 .env ロード)
    - data/
      - __init__.py
      - schema.py           (DuckDB スキーマ定義・初期化: init_schema, get_connection)
    - strategy/
      - __init__.py          (戦略モジュール用パッケージプレースホルダ)
    - execution/
      - __init__.py          (発注/実行モジュール用パッケージプレースホルダ)
    - monitoring/
      - __init__.py          (モニタリング用パッケージプレースホルダ)

---

## データスキーマ概要

スキーマは DataSchema.md に準拠した 4 層構造です（schema.py に DDL が定義されています）。

- Raw Layer（取得生データ）
  - raw_prices, raw_financials, raw_news, raw_executions

- Processed Layer（整形済み市場データ）
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols

- Feature Layer（戦略／AI 用特徴量）
  - features, ai_scores

- Execution Layer（発注／約定／ポジション管理）
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

インデックスも頻出クエリを想定して作成されます（例: idx_prices_daily_code_date など）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, 値: development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (任意, 値: DEBUG | INFO | WARNING | ERROR | CRITICAL, デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意, 1 を設定すると .env 自動読み込みを無効化)

注意: Settings の必須プロパティを参照すると未設定時に ValueError が発生します。

---

## 開発・貢献メモ

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。パッケージ配布後も正しく動作するよう、__file__ から親ディレクトリを探索します。
- .env のパースはシェル風の簡易実装（export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い）に対応しています。
- DuckDB の初期化は冪等であり、既存テーブルは上書きされません。初回は init_schema を呼んでください。

---

必要であれば README に以下を追加できます:
- 実行環境（Dockerfile / docker-compose）サンプル
- CI / テストの実行方法
- 各テーブル（カラム）の詳細説明（DataSchema.md の内容）