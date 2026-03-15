# KabuSys

日本株向けの自動売買システム用ライブラリ（ライブラリ本体の一部）。  
このリポジトリはデータレイヤ（DuckDB スキーマ定義）、環境設定管理、実行／戦略／監視モジュールの骨組みを提供します。

---

## プロジェクト概要

KabuSys は、次のような機能を前提とした自動売買プラットフォームの基盤コードです。

- データ保存・解析のための DuckDB スキーマ（Raw / Processed / Feature / Execution の多層設計）
- 環境変数 / .env 管理（自動ロード・パース機能）
- API キーや各種エンドポイントを集中管理する Settings オブジェクト
- 発注・モニタリング・戦略用のサブパッケージ（骨組み）

現時点では、主に設定管理とデータベーススキーマの初期化ロジックが実装されています。

---

## 主な機能

- 環境変数読み込み・管理
  - プロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を自動読み込み
  - OS 環境変数 > .env.local > .env の優先順位
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能
  - `.env` のパースは `export KEY=VAL`, クォート、エスケープ、コメントなどに対応

- Settings クラス
  - 必須キーは未設定時に ValueError を送出して明示的に通知
  - 代表的なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL（DEBUG/INFO/...）

- DuckDB スキーマの定義と初期化
  - raw_prices / raw_financials / raw_news / raw_executions
  - prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など
  - インデックス作成と外部キーを考慮したテーブル作成順をサポート
  - init_schema(db_path) は冪等にテーブルを作成

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈に X | Y 形式を使用しているため）
- pip が利用可能

手順例:

1. リポジトリをクローンして開発環境に入る
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 依存ライブラリをインストール
   - 最低限必要なパッケージ:
     ```
     pip install duckdb
     ```
   - ローカル開発としてパッケージを editable install する場合:
     ```
     pip install -e .
     ```

3. 環境変数を用意する
   - リポジトリのルートに `.env`（と必要に応じて `.env.local`）を作成してください。
   - 標準で期待される環境変数（例）
     - 必須:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
       - SLACK_BOT_TOKEN
       - SLACK_CHANNEL_ID
     - 任意 / デフォルトあり:
       - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
       - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
       - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
       - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
       - SQLITE_PATH — デフォルト: data/monitoring.db

   - サンプル行（.env）
     ```
     JQUANTS_REFRESH_TOKEN="your_jquants_token"
     KABU_API_PASSWORD="your_kabu_password"
     SLACK_BOT_TOKEN="xoxb-..."
     SLACK_CHANNEL_ID="C01234567"
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. 自動 .env ロードを無効化したい場合（テストなど）
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（簡易ガイド）

- Settings の取得例
  ```python
  from kabusys.config import settings

  # 必要な値はプロパティ経由で取得。未設定の必須値は ValueError を送出する。
  token = settings.jquants_refresh_token
  base_url = settings.kabu_api_base_url
  db_path = settings.duckdb_path  # pathlib.Path
  ```

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # settings.duckdb_path のパス（デフォルト: data/kabusys.duckdb）を作成・初期化
  conn = init_schema(settings.duckdb_path)

  # conn は duckdb の接続オブジェクト（duckdb.DuckDBPyConnection）
  with conn:
      # 例: テーブル一覧を確認
      print(conn.execute("SHOW TABLES").fetchall())
  ```

- 既存 DB への接続（スキーマ初期化は行わない）
  ```python
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  ```

- エラーハンドリング
  - 必須環境変数が無い状態で settings のプロパティにアクセスすると ValueError が発生します。スクリプト開始時に設定の検証を行うと安全です。

---

## ディレクトリ構成

リポジトリの主要なファイル / モジュール（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py              — 環境変数 / Settings 管理（自動 .env ロード・パース）
    - data/
      - __init__.py
      - schema.py            — DuckDB スキーマ定義・init_schema / get_connection
    - strategy/
      - __init__.py          — 戦略関連のエントリポイント（未実装の骨組み）
    - execution/
      - __init__.py          — 発注 / 実行関連（骨組み）
    - monitoring/
      - __init__.py          — 監視・ログ等（骨組み）

主要なファイルの説明:
- src/kabusys/config.py
  - プロジェクトルート探索（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動読み込み
  - _parse_env_line: .env の複雑なパース（クォート、エスケープ、コメント）に対応
  - Settings クラス: 各種設定値をプロパティ経由で取得

- src/kabusys/data/schema.py
  - DuckDB テーブル DDL を定義し、init_schema() でまとめて作成
  - テーブルは外部キー依存に配慮した順序で作成され、インデックスも作成
  - init_schema は冪等（既存テーブルはスキップ）

---

## 補足 / 注意点

- Python バージョン: 本コードはタイプヒントに `X | Y`（PEP 604）を用いているため Python 3.10 以上を想定しています。
- .env の自動読み込みはプロジェクトルートの検出に依存します。パッケージ化して配布した場合、CWD によらず正しいルートが見つかるよう意図されていますが、検出できない場合は自動読み込みをスキップします。
- init_schema の db_path に ":memory:" を渡すとインメモリ DB が使用されます。
- Settings のプロパティは実行時に環境変数を参照します。ユニットテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用して自動ロードを止め、テスト用に os.environ を操作する方法が便利です。
- 将来的には strategy、execution、monitoring パッケージに実際のロジック（シグナル生成、発注実行、Slack 通知など）を実装していく想定です。

---

必要であれば、.env.example のテンプレートやサンプルスクリプト（データの取り込み、シグナル生成、発注フローの例）も作成できます。どのサンプルが欲しいか教えてください。