# KabuSys

日本株自動売買システム（骨組み）。  
本リポジトリは、データレイヤ（DuckDBスキーマ定義）、環境設定読み込み、戦略／発注／監視モジュールの雛形を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株の自動売買システムの基盤です。  
- 環境変数ベースの設定管理（.env ファイルの自動ロードをサポート）  
- DuckDB を用いた多層データスキーマ（Raw / Processed / Feature / Execution）  
- 戦略（strategy）、発注（execution）、監視（monitoring）のためのパッケージ構成

このリポジトリはフル機能の実装ではなく、データモデルと設定まわりの基礎を提供します。

---

## 主な機能

- 環境変数 / .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を読み込む
  - OS 環境変数を保護しつつ `.env.local` で上書き可能
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
- Settings クラスによるアクセス（必須値を未設定時に例外）
  - J-Quants、kabuステーション、Slack、データベースパス、実行環境など
- DuckDB ベースのスキーマ定義
  - Raw Layer: raw_prices / raw_financials / raw_news / raw_executions
  - Processed Layer: prices_daily / market_calendar / fundamentals / news_articles / news_symbols
  - Feature Layer: features / ai_scores
  - Execution Layer: signals / signal_queue / portfolio_targets / orders / trades / positions / portfolio_performance
  - インデックス定義と初期化関数 `init_schema()` を提供
- モジュール構成（strategy / execution / monitoring）はプレースホルダ（拡張向け）

---

## 必要条件

- Python 3.8+
- duckdb（Pythonパッケージ）
- （利用する外部APIに応じて）slack-sdk、requests など

依存パッケージはプロジェクトに合わせて追加してください。

---

## セットアップ手順

1. リポジトリをクローン / ダウンロード
   ```
   git clone <your-repo-url>
   cd <your-project-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール（例）
   ```
   pip install duckdb
   # 実際の運用では slack-sdk 等もインストール
   # pip install slack-sdk requests
   ```

4. .env を準備
   プロジェクトルートに `.env` と optional な `.env.local` を配置します。以下は例（機密情報は適切に管理してください）。

   ```
   # .env の例
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   注意: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動で `.env` を読み込まなくなります（テスト等で利用）。

---

## 使い方

基本的な利用フローの例を示します。

1. Settings の利用
   ```python
   from kabusys.config import settings

   # 必須環境変数が未設定の場合、この時点で ValueError が発生することがあります
   print(settings.jquants_refresh_token)
   print(settings.kabu_api_base_url)
   print(settings.env)   # development / paper_trading / live
   ```

2. DuckDB スキーマの初期化
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   # settings.duckdb_path は Path を返す
   conn = init_schema(settings.duckdb_path)

   # conn を使ってクエリ実行
   with conn:
       res = conn.execute("SELECT name FROM sqlite_master LIMIT 10").fetchall()
   ```

   - 初回は `init_schema()` を呼んでテーブルを作成してください（冪等）。
   - 既に初期化済みで接続だけ欲しい場合は `get_connection(db_path)` を使います。

3. シンプルな接続取得
   ```python
   from kabusys.data.schema import get_connection
   from kabusys.config import settings

   conn = get_connection(settings.duckdb_path)
   ```

4. 自動環境ロードの挙動
   - パッケージ読み込み時（kabusys.config がロードされたタイミング）に、プロジェクトルートを探索して `.env` / `.env.local` を読み込みます。
   - プロジェクトルートは `.git` または `pyproject.toml` の存在で決定されます。
   - テスト時などで自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション / デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読み込みを無効化)

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py                # パッケージ定義、__version__ = "0.1.0"
    - config.py                  # 環境変数 / Settings クラス、自動 .env 読み込み
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義と init_schema / get_connection
    - strategy/
      - __init__.py              # 戦略モジュール（拡張用）
    - execution/
      - __init__.py              # 発注モジュール（拡張用）
    - monitoring/
      - __init__.py              # 監視モジュール（拡張用）

---

## 注意事項 / 補足

- このリポジトリは基盤部分（設定・DBスキーマ）を提供します。実際の発注ロジック、API クライアント、戦略アルゴリズムは別途実装してください。
- 環境変数や API トークンは慎重に管理してください（.env をバージョン管理しない等）。
- DuckDB のファイルデータは `DUCKDB_PATH` で指定します。":memory:" を渡すとインメモリで動作します。
- スキーマは外部キーやチェック制約を含みます。運用時のデータ投入ロジックはそれらの整合性を満たす必要があります。

---

もし README に追加したい情報（例: 依存パッケージの完全な一覧、CI / テスト手順、実際の戦略サンプルなど）があれば教えてください。追記して整備します。