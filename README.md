# KabuSys

日本株向けの自動売買システム基盤ライブラリ (バージョン 0.1.0)

このリポジトリは、データ取得・スキーマ管理・環境設定等を提供する最小限の基盤コンポーネント群です。実トレードを行うための戦略（strategy）、発注（execution）、監視（monitoring）などのモジュールを統合して拡張できます。

---

## 主な特徴

- 環境変数 / .env 管理
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込み
  - export 形式、クォート、コメント等に対応した堅牢なパーサ
  - OS 環境変数を優先 (読み込み順: OS 環境変数 > .env.local > .env)
  - 自動読み込みを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - アクセス用: `from kabusys.config import settings`

- DuckDB を用いたレイヤ化されたスキーマ管理
  - Raw / Processed / Feature / Execution の 4 層でテーブル定義を提供
  - インデックスも定義済み（頻出クエリの高速化）
  - スキーマ初期化関数: `kabusys.data.schema.init_schema(db_path)`
  - 既存 DB への接続取得: `kabusys.data.schema.get_connection(db_path)`

- 軽量で拡張しやすいパッケージ構成（strategy / execution / monitoring のエントリポイントを用意）

---

## 機能一覧（サマリ）

- 設定管理 (src/kabusys/config.py)
  - 必須・任意の環境変数取得ラッパー (`settings` オブジェクト)
  - 環境種別検証 (`KABUSYS_ENV`: `development` / `paper_trading` / `live`)
  - ログレベル検証 (`LOG_LEVEL`)

- データスキーマ管理 (src/kabusys/data/schema.py)
  - テーブル群（例）
    - Raw: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature: `features`, `ai_scores`
    - Execution: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - インデックス定義（`idx_...`）
  - スキーマ初期化 (冪等)

- パッケージ構成（拡張ポイント）
  - `kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring`（各モジュールに機能を実装して拡張）

---

## セットアップ手順

前提:
- Python 3.8+（本リポジトリは typing の構文を使用）
- pip

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール
   - 本コードベースでは少なくとも duckdb を利用します。プロジェクトに pyproject.toml / requirements.txt がある場合はそれに従ってください。
   ```
   pip install duckdb
   # パッケージを開発モードでインストールする場合:
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成してください。
   - 必須の環境変数（実行時に `settings` を参照すると例外が発生します）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト値を持つもの:
     - KABUSYS_ENV（default: development）: `development` / `paper_trading` / `live`
     - LOG_LEVEL（default: INFO）
     - KABU_API_BASE_URL（default: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（default: data/kabusys.duckdb）
     - SQLITE_PATH（default: data/monitoring.db）

   例: `.env` の最小例
   ```
   JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
   KABU_API_PASSWORD="your_kabu_api_password"
   SLACK_BOT_TOKEN="xoxb-xxxxxxxxxxxx"
   SLACK_CHANNEL_ID="C0123456789"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. 自動 .env 読み込みを無効化したいとき
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（例）

1. スキーマ初期化（DuckDB ファイルを作成してテーブルを生成）
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema, get_connection

   # settings.duckdb_path は Path オブジェクトを返します（デフォルト: data/kabusys.duckdb）
   conn = init_schema(settings.duckdb_path)  # ファイルがなければディレクトリを作成して DB を作る

   # 以降、conn.execute(...) で SQL 操作可能
   with conn:
       df = conn.execute("SELECT COUNT(*) FROM prices_daily").fetchdf()
       print(df)
   ```

2. settings の利用
   ```python
   from kabusys.config import settings

   print(settings.env)            # development / paper_trading / live
   print(settings.is_live)        # True なら live 環境
   print(settings.kabu_api_base_url)
   token = settings.jquants_refresh_token  # 必須値（未設定なら例外）
   ```

3. 自動ロードの振る舞い
   - プロジェクトルートに `.env` / `.env.local` があれば自動で取り込みます。
   - OS 環境変数が優先され、`.env.local` は `.env` の上書き（`.env.local` の方が優先）になります。
   - テストなどで自動読み込みを抑止する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

以下は主要ファイルの一覧（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                  # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義と初期化 API
    - strategy/
      - __init__.py              # 戦略モジュール（拡張先）
    - execution/
      - __init__.py              # 発注/実行モジュール（拡張先）
    - monitoring/
      - __init__.py              # 監視モジュール（拡張先）

主要 API:
- kabusys.config.settings
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url
  - settings.slack_bot_token
  - settings.slack_channel_id
  - settings.duckdb_path
  - settings.sqlite_path
  - settings.env / is_live / is_paper / is_dev
  - settings.log_level

- kabusys.data.schema
  - init_schema(db_path: str | Path) -> duckdb connection
  - get_connection(db_path: str | Path) -> duckdb connection

---

## 開発・拡張ポイント

- strategies: `kabusys.strategy` に戦略を実装して、`features` / `ai_scores` などを参照し、`signals` を出力する設計が想定されています。
- execution: `kabusys.execution` に注文ロジック（kabuステーション API とのやり取りや order 管理）を実装して `orders` / `trades` / `positions` へ反映します。
- monitoring: `kabusys.monitoring` に Slack 通知やパフォーマンス集計を実装して監視基盤を構築してください。

---

もし README に追加してほしい具体的な内容（例: CI/CD、デプロイ手順、.env.example のテンプレート、自動テストの設定等）があれば教えてください。