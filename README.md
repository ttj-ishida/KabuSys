# KabuSys

日本株自動売買システム（ライブラリ基盤）

KabuSys は日本株のデータ管理、特徴量生成、戦略・発注・監査のための基盤ライブラリ群です。本リポジトリはデータレイヤ（Raw / Processed / Feature / Execution）と監査ログを DuckDB で管理するスキーマ定義、および環境設定管理を提供します。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / .env の自動読込と型チェック（kabusys.config）
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。
  - `.env` → `.env.local` の順で読み込み、`.env.local` は上書き（ただし OS 環境変数は保護）。
  - 自動読み込みを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - 主要な設定プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - 3〜4 層のデータレイヤを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス設定、外部キー制約、各種チェック制約を含む DDL を提供
  - init_schema(db_path) による初期化（冪等）

- 監査ログ（トレーサビリティ）テーブル（kabusys.data.audit）
  - signal_events, order_requests, executions の DDL を提供
  - 発注フローを UUID 連鎖でトレース可能に設計
  - 全ての TIMESTAMP は UTC で保存（init_audit_schema は TimeZone を UTC に設定）
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化

- パッケージ化されたサブモジュール構成
  - data, strategy, execution, monitoring（骨組み）

---

## セットアップ手順

前提
- Python 3.10 以上（アノテーションに PEP 604 (`|` 型合成) を使用しているため）
- pip が使用可能であること

1. リポジトリをクローン／取得

2. 仮想環境を作成してアクティベート（推奨）
   - Linux / macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 依存パッケージのインストール
   - 最小: duckdb
   - 例:
     - pip install duckdb

   （プロジェクトに requirements.txt や pyproject.toml があればそちらを利用してください）

4. .env の準備
   - プロジェクトルートに `.env` を置きます（または OS 環境変数で設定）。
   - 例（.env.example を参考に作成）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
   - 注意: `.env.local` が存在する場合は `.env` の設定を上書きします（ただしすでに OS 環境に存在するキーは上書きされません）。

5. 自動 .env ロードを無効化したい場合
   - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。

---

## 使い方

基本的な API 使用例を示します。

1) 設定へのアクセス
- Python から設定値を参照する:
  - from kabusys.config import settings
  - settings.jquants_refresh_token など

例:
```
from kabusys.config import settings

token = settings.jquants_refresh_token
base_url = settings.kabu_api_base_url  # デフォルト: http://localhost:18080/kabusapi
if settings.is_live:
    print("ライブ環境です")
```

2) DuckDB スキーマ初期化（データ用 DB）
```
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイル DB または ":memory:"
# 以降 conn を使ってクエリ実行
```

3) 既存 DB への接続（スキーマの初期化は行わない）
```
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

4) 監査ログテーブル初期化（既存接続に追加）
```
from kabusys.data.audit import init_audit_schema
# 既に init_schema した conn を渡す
init_audit_schema(conn)
# init_audit_schema は UTC タイムゾーンをセットします
```

5) 監査専用 DB を別途作る場合
```
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

6) 自動 .env ロードを無効化してプログラムを実行する例（UNIX シェル）
```
KABUSYS_DISABLE_AUTO_ENV_LOAD=1 python -m my_app
```

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py               -- パッケージ定義（__version__ 等）
  - config.py                 -- 環境変数 / .env 読込と Settings クラス
  - data/
    - __init__.py
    - schema.py               -- DuckDB スキーマ定義・init_schema / get_connection
    - audit.py                -- 監査ログ（signal_events / order_requests / executions）初期化
    - audit.py                -- 監査用インデックス・DDL
    - audit.py / schema.py により、raw / processed / feature / execution 層を管理
    - audit.py などで UTC タイムゾーンを利用
  - strategy/
    - __init__.py             -- 戦略層用モジュール（拡張ポイント）
  - execution/
    - __init__.py             -- 発注・ブローカー連携モジュール（拡張ポイント）
  - monitoring/
    - __init__.py             -- モニタリング関連（拡張ポイント）

注: 上記は現状のコードベースに基づく骨組みです。実際の戦略ロジック・発注実装・モニタリング機能は各サブモジュール内に実装して拡張します。

---

## 注意点 / 補足

- Python バージョン: 本コードは Python 3.10 以上を想定しています。
- データベース:
  - DuckDB をデフォルトで使用します（duckdb パッケージが必要）。
  - init_schema は冪等です（既存テーブルがあればスキップ）。
- 監査ログ:
  - 監査テーブルは基本的に削除せず永続化することを前提に設計されています（FK は ON DELETE RESTRICT）。
  - すべてのタイムスタンプは UTC で保存されます。
- セキュリティ:
  - API シークレットやトークンは .env に平文で置くのではなく、可能であれば OS 環境変数や安全なシークレットマネージャを利用してください。

---

必要であれば README に例となる .env.example、サンプルデータ投入スクリプト、典型的なクエリ例（価格取得、特徴量計算、シグナル登録、監査ログ参照）を追加できます。どの項目を優先して追加するか教えてください。