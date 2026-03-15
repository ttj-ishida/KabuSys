# KabuSys

日本株向け自動売買システムの共通ライブラリ（プロジェクト基盤）。  
このリポジトリはデータ管理（DuckDB スキーマ）、環境設定、戦略/実行/モニタリング用パッケージを含む基盤コードを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買に必要なデータレイヤ（Raw / Processed / Feature / Execution）を定義し、環境設定や DB 初期化などのユーティリティを提供するパッケージです。戦略・発注・監視ロジックは各サブパッケージ（strategy / execution / monitoring）で実装します。

主な目的:
- DuckDB を用いた永続ストレージスキーマの提供と初期化
- 環境変数（.env / .env.local / OS 環境）の安全な読み込み・管理
- 設定値（API トークンや DB パス等）への一元アクセス

---

## 機能一覧

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可能）
  - 必須設定の取得（例: JQUANTS_REFRESH_TOKEN、SLACK_BOT_TOKEN 等）
  - 環境（development / paper_trading / live）やログレベルのバリデーション
  - デフォルト DB パスの提供（DUCKDB_PATH, SQLITE_PATH）
- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の各レイヤのテーブル DDL を定義
  - インデックス作成やディレクトリ自動生成を含む init_schema() を提供
  - 主要テーブル例: raw_prices, prices_daily, features, signals, signal_queue, orders, trades, positions, portfolio_performance など
- パッケージ構成（拡張点）
  - strategy / execution / monitoring 用のサブパッケージを用意（実装は各自追加）

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントの `|` 演算子や振る舞いを想定）
- pip が利用可能

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール  
   現状で必須なのは duckdb（および運用上必要な API クライアント等）。
   ```
   pip install duckdb
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用）

4. 環境変数の設定  
   プロジェクトルートに `.env`（および必要なら `.env.local`）を配置します。ディレクトリは .git もしくは pyproject.toml を基準に自動検出されます。

   重要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (任意、デフォルト: data/monitoring.db)
   - KABUSYS_ENV (任意, 有効値: development / paper_trading / live, デフォルト: development)
   - LOG_LEVEL (任意, DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト: INFO)

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN="あなたのトークン"
   KABU_API_PASSWORD="kabu_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C12345678"
   DUCKDB_PATH="data/kabusys.duckdb"
   KABUSYS_ENV=development
   ```

5. 自動 .env 読み込みを無効化する場合  
   テスト等で自動読み込みを無効にするには環境変数を設定:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方

- 設定値を取得する
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  is_live = settings.is_live
  db_path = settings.duckdb_path  # pathlib.Path
  ```

- DuckDB スキーマを初期化する
  ```python
  from kabusys.data.schema import init_schema

  # ファイル DB を初期化（親ディレクトリを自動作成）
  conn = init_schema("data/kabusys.duckdb")

  # インメモリ DB を使用
  conn_mem = init_schema(":memory:")
  ```

  - init_schema は既に存在するテーブルを上書きしないため冪等です。
  - 初回は init_schema() でテーブルを作成し、その後は get_connection() で接続可能です。

- 既存 DB に接続する
  ```python
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  ```

- 戦略・発注・監視の実装  
  strategy / execution / monitoring サブパッケージに自分のロジックを実装し、提供される settings と DB 接続を利用してデータ読み書きや発注処理を行います。

---

## ディレクトリ構成

プロジェクト内の主要ファイル/ディレクトリ:

- src/kabusys/
  - __init__.py                — パッケージ初期化、バージョン情報
  - config.py                  — 環境変数・設定管理（自動 .env ロード、Settings クラス）
  - data/
    - __init__.py
    - schema.py                — DuckDB スキーマ定義・初期化 API (init_schema, get_connection)
  - strategy/
    - __init__.py              — 戦略ロジック用パッケージ（拡張ポイント）
  - execution/
    - __init__.py              — 発注・執行ロジック用パッケージ（拡張ポイント）
  - monitoring/
    - __init__.py              — 監視・メトリクス用パッケージ（拡張ポイント）

主要テーブル（抜粋、schema.py に全 DDL を定義）:
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

---

## 補足・注意点

- .env 読み込みの優先順位:
  - OS 環境変数（最優先、保護され上書きされない）
  - .env.local（存在する場合は .env の値より優先して上書き）
  - .env（基本値）
- 自動読み込みのトリガー:
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を基準に .env / .env.local を読み込みます。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数が未設定の場合、Settings のプロパティアクセス時に ValueError が発生します。
- DuckDB の初期化は init_schema を使って行ってください。get_connection はスキーマ作成を行いません。

---

この README はプロジェクトの土台を説明するものです。戦略や実際の取引ロジック、kabu ステーションや J-Quants の具体的なクライアント実装は各サブパッケージで追加してください。質問や改善要望があれば教えてください。