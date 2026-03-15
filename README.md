# KabuSys

日本株向け自動売買システムのベースライブラリ (KabuSys)。  
市場データ収集、特徴量算出、シグナル生成、発注・約定管理、監視のための基盤となるモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株自動売買システムの土台となる Python パッケージです。  
主な目的は以下のとおりです。

- 各種外部 API の認証情報や設定を環境変数で一元管理
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）のスキーマ定義と初期化
- 戦略（strategy）、実行（execution）、データ管理（data）、監視（monitoring）のためのモジュール構成

現状はライブラリ骨格（設定読み込み・DBスキーマ定義など）を実装しています。実際の取得・解析・発注ロジックは各モジュール配下で実装していく想定です。

---

## 主な機能一覧

- 環境変数 / .env 管理
  - プロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を自動読み込み
  - OS 環境変数の上書きを保護する仕組み
  - 必須値を取得するユーティリティ（未設定時に例外）
  - 自動読み込みを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）

- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution の 3〜4 層構造テーブルを作成
  - テーブル作成は冪等（既存テーブルがあればスキップ）
  - 便利なインデックスを作成
  - init_schema(db_path) / get_connection(db_path) API

- パッケージ構成（拡張ポイント）
  - data: データ格納・スキーマ管理
  - strategy: 戦略ロジック
  - execution: 発注・約定・ポジション管理
  - monitoring: 監視・通知

---

## 必要条件

- Python 3.10 以上（型注釈で `Path | None` 等を使用）
- duckdb Python パッケージ

必要に応じて他の依存（API クライアントや Slack ライブラリ等）を追加してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール
   ```
   pip install --upgrade pip
   pip install duckdb
   # 開発用にパッケージを編集可能モードでインストールする場合:
   # pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（既存の OS 環境変数は保護）。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な環境変数（必須 / デフォルト値）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
     - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
     - KABUSYS_ENV (任意, 値: development / paper_trading / live, デフォルト: development)
     - LOG_LEVEL (任意, 値: DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト: INFO)

   例 (.env の一例)
   ```
   JQUANTS_REFRESH_TOKEN="your_jquants_token"
   KABU_API_PASSWORD="your_kabu_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C0123456"
   DUCKDB_PATH="data/kabusys.duckdb"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方

以下は主要な API の簡単な利用例です。

- 設定値の取得
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  base_url = settings.kabu_api_base_url
  is_live = settings.is_live
  ```

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # ファイルを自動作成してスキーマを初期化
  # conn は duckdb.DuckDBPyConnection
  ```

- 既存 DB への接続
  ```python
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  ```

- 注意点
  - init_schema はテーブル作成を行います。初回実行時に呼ぶことを推奨します。
  - .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基に行われます。ルートが見つからないと自動ロードをスキップします。
  - 設定の必須項目が未設定の場合、settings のプロパティ呼び出しで ValueError が発生します。

---

## ディレクトリ構成

リポジトリ内の主要ファイル/ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py            # パッケージメタ情報（__version__ など）
    - config.py              # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py            # DuckDB スキーマ定義・初期化 (init_schema / get_connection)
    - strategy/
      - __init__.py          # 戦略ロジック用モジュール（拡張ポイント）
    - execution/
      - __init__.py          # 注文・約定・ポジション管理（拡張ポイント）
    - monitoring/
      - __init__.py          # モニタリング・通知（拡張ポイント）

主なテーブル（schema.py で定義）
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

---

## 開発者向けメモ

- 環境変数のパースはシェル形式（クォートや export の有無、インラインコメントなど）にある程度対応しています。
- .env ファイルの読み込み順序: OS環境変数 > .env.local > .env。既存の OS 環境変数は保護されます。
- 型アノテーションやコードスタイルは Python 3.10 以降を想定しています。

---

ご不明点や追加したい機能（例: API クライアント、Slack 通知、戦略テンプレートなど）があれば教えてください。README をそれに合わせて拡張します。