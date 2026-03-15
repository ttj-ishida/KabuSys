# KabuSys

日本株向けの自動売買システム基盤ライブラリ（プロトタイプ）

バージョン: 0.1.0

このリポジトリは、取引データの格納／スキーマ定義、環境設定管理、戦略・発注・モニタリングのためのモジュール群の骨組みを提供します。実際のアルゴリズムや発注ロジックは各モジュール内で拡張して利用します。

---

## 概要

KabuSys は日本株の自動売買（バックテスト／ペーパー／実運用を想定）で利用するための共通基盤を提供します。主な目的は次のとおりです。

- データレイヤ（Raw / Processed / Feature / Execution）を想定した DuckDB スキーマの提供
- 環境変数・設定の集中管理（.env ファイルの自動読み込み機能含む）
- 戦略（strategy）、発注（execution）、モニタリング（monitoring）のためのパッケージ構成（拡張ポイント）

パッケージの公開 API の起点:
- kabusys.config.settings — 環境設定（必須トークンなど）へアクセス
- kabusys.data.schema.init_schema／get_connection — DuckDB スキーマ初期化／接続

---

## 機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（環境変数優先）
  - 必須設定を取得するヘルパ（未設定時に明示的なエラー）
  - 認識する主要環境設定: KABUSYS_ENV（development / paper_trading / live）, LOG_LEVEL
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- データベース（DuckDB）スキーマ管理
  - Raw / Processed / Feature / Execution の各レイヤ用テーブル定義
  - インデックス定義（一般的なクエリパターンを想定）
  - init_schema(db_path) による初期化（冪等）
  - get_connection(db_path) で既存 DB へ接続
  - ":memory:" を指定すればインメモリ DB が使用可能

- パッケージ構造（拡張ポイント）
  - kabusys.strategy, kabusys.execution, kabusys.monitoring により戦略・注文・監視ロジックを実装可能

---

## セットアップ手順

前提
- Python 3.10 以上（コード内での型ヒント（|）を使用しているため）

1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo-url>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate（macOS / Linux）
   - .venv\Scripts\activate（Windows）

3. 必要パッケージをインストール
   - DuckDB が必須: pip install duckdb
   - （将来的に依存パッケージが追加される可能性があるため、setup.py / pyproject.toml があれば pip install -e . を推奨）
   - 例: pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動読み込みされます。
   - 必須の環境変数（以下を参照）を .env に設定してください。

サンプル .env（最低限）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# 環境設定
KABUSYS_ENV=development
LOG_LEVEL=INFO

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

補足:
- .env.local が存在する場合は .env の上書き（.env → .env.local の順で読み込まれ、.env.local が優先されます）
- export KEY=val 形式やシングル／ダブルクォート、行コメントなどをパーサがサポートします
- 自動読み込みを無効化したいときは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト実行などで便利です）

---

## 使い方（簡単な例）

以下は DuckDB スキーマを初期化する基本例です。

Python インタラクティブやスクリプト:
```
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection

# settings.duckdb_path はデフォルトで data/kabusys.duckdb（~展開あり）
db_path = settings.duckdb_path

# スキーマ初期化（ファイルがなければ親ディレクトリを自動作成）
conn = init_schema(db_path)

# 以降 conn を用いてクエリを実行
with conn:
    df = conn.execute("SELECT name FROM sqlite_master").fetchdf()  # 例（DuckDB のメタ情報取得）
```

既存 DB へ接続する場合:
```
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

環境設定の参照例:
```
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 未設定だと ValueError が送出される
print(settings.env)  # development / paper_trading / live のいずれか
```

注意:
- init_schema は冪等であり、テーブルが既に存在していればスキップします。
- インメモリ DB を使うには db_path に ":memory:" を渡してください。

---

## ディレクトリ構成

リポジトリ内の主なファイル／ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - __version__ = "0.1.0"
    - __all__ = ["data", "strategy", "execution", "monitoring"]
    - config.py                — 環境設定・.env ローダ
    - data/
      - __init__.py
      - schema.py              — DuckDB スキーマ定義／初期化
    - strategy/
      - __init__.py            — 戦略モジュール（拡張用）
    - execution/
      - __init__.py            — 発注／実行モジュール（拡張用）
    - monitoring/
      - __init__.py            — モニタリング機能（拡張用）

主要テーブル（schema.py に定義）
- Raw Layer:
  - raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer:
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer:
  - features, ai_scores
- Execution Layer:
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

インデックスや外部キーもスキーマで定義されています（頻繁に使われるクエリパターンを想定）。

---

## 補足と運用上の注意

- 必須環境変数（未設定だと Settings でエラーになります）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

- ログレベルや運用モードは環境変数 KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/...）で制御します。無効な値が設定されるとエラーになります。

- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml から特定して行います。運用や CI 環境で意図しない読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

- 現状は基盤部分（スキーマ、設定管理、拡張モジュールの土台）に重点があり、個別の戦略や注文実行の実装は各自で追加して利用してください。

---

この README はコードベースの現状（スキーマと設定管理中心）に基づいたサマリです。利用や拡張、CI/CD 配置などに合わせて追記してください。質問や追加で載せたい内容（例: サンプル戦略、CI 設定、運用手順）があれば教えてください。