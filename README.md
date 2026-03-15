# KabuSys

KabuSys は日本株向けの自動売買システムの基盤ライブラリです。データ取得・格納（DuckDB スキーマ）、環境設定管理、戦略・発注・モニタリング用のモジュール構成を提供します。

バージョン: 0.1.0

---

## 概要

- DuckDB を用いた永続データレイヤ（Raw / Processed / Feature / Execution）スキーマ定義と初期化機能を提供します。
- 環境変数（.env / .env.local / OS 環境）をプロジェクトルート基準で自動読み込みする設定管理機能を備えます。
- 取引戦略・発注・モニタリングのためのモジュール群（strategy / execution / monitoring）の土台を定義しています（各ディレクトリ下に機能を拡張可能）。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local を自動で読み込み（OS 環境変数が優先）
  - 必須環境変数は Settings クラス経由で取得し、未設定時にエラーを投げる
  - 自動読み込みを環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
- DuckDB スキーマ定義 & 初期化
  - Raw / Processed / Feature / Execution レイヤーを含むテーブル群の DDL を定義
  - インデックス定義、外部キー依存を考慮したテーブル作成順で冪等（既存テーブルはスキップ）
  - `init_schema()` でデータベースファイルを作成・初期化
- Settings（環境変数からの安全な設定取得）
  - J-Quants / kabu API / Slack / DB パス / 実行環境（development / paper_trading / live）やログレベル取得

---

## 必要条件

- Python 3.10 以上（型ヒントで PEP 604 の `X | Y` を使用）
- duckdb Python パッケージ（スキーマ初期化に必要）
  - インストール例: `pip install duckdb`

※ 実際の運用では Slack クライアントや kabu API クライアント等の追加依存が必要になる想定です（本リポジトリの該当コードに合わせて追加してください）。

---

## セットアップ手順

1. リポジトリをクローン（例）
   - git clone <リポジトリURL>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - Linux / macOS: `source .venv/bin/activate`
   - Windows: `.venv\Scripts\activate`

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb
   - （運用で必要な追加パッケージは適宜インストールしてください）

4. .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置します。
   - 自動読み込みはデフォルトで有効です。無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env（必須キーはプロジェクトで使う箇所に応じて設定）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabu API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# DB パス（省略時は data/kabusys.duckdb）
DUCKDB_PATH=data/kabusys.duckdb

# 実行環境: development | paper_trading | live
KABUSYS_ENV=development

# ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_LEVEL=INFO
```

---

## 使い方（主要 API）

- 環境設定の取得
  ```python
  from kabusys.config import settings

  # 必須の値は未設定だと ValueError が発生します
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  env = settings.env  # 'development' | 'paper_trading' | 'live'
  ```

- .env 自動ロードについて
  - 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を起点に行います。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - 自動ロードを無効にするには、起動前に環境変数を設定:
    - Linux/macOS: `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
    - Windows (PowerShell): `$env:KABUSYS_DISABLE_AUTO_ENV_LOAD = '1'`

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # 設定されたパスに DuckDB を作成し、テーブルを初期化します
  conn = init_schema(settings.duckdb_path)

  # 以降 conn を用いて SQL を実行できます
  with conn:
      rows = conn.execute("SELECT count(*) FROM prices_daily").fetchall()
      print(rows)
  ```

- 既存 DB への接続（スキーマの初期化は行わない）
  ```python
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  ```

---

## 設定可能な主要環境変数

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略時: data/kabusys.duckdb)
- SQLITE_PATH (省略時: data/monitoring.db)
- KABUSYS_ENV: development / paper_trading / live（省略時: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（省略時: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると自動 .env 読み込みを無効化

.env のパースルールのポイント:
- `export KEY=val` 形式を許容
- シングル/ダブルクォート内のエスケープを考慮して値を抽出
- クォートなしの場合、`#` の直前がスペースまたはタブであればコメントとみなす

---

## ディレクトリ構成

以下は現在の主要ファイルとモジュール構成です。

- src/
  - kabusys/
    - __init__.py            # パッケージ定義（__version__=0.1.0）
    - config.py              # 環境変数・設定管理（.env 自動読み込み, Settings クラス）
    - data/
      - __init__.py
      - schema.py            # DuckDB スキーマ定義と初期化関数（init_schema, get_connection）
    - strategy/
      - __init__.py          # 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py          # 発注・実行モジュール（拡張ポイント）
    - monitoring/
      - __init__.py          # モニタリング関連（拡張ポイント）

主なテーブル（schema.py に定義）
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- 各種インデックスを作成（頻出クエリの高速化）

---

## 開発・拡張のヒント

- strategy / execution / monitoring フォルダに具体的な戦略ロジックや発注ロジックを実装してください。
- DuckDB のスキーマは冪等に作成されるため、init_schema をアプリ起動時に安全に呼び出して構いません。
- Settings クラスはプロパティベースなので、未設定時に ValueError を投げて早期に設定ミスを検出できます。
- .env の自動読み込みはプロジェクトルート検出に .git または pyproject.toml を使用します。配布時やテスト時に動作を変えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。

---

もし README に追加したい項目（例: 実際の API クライアントの使い方、CI 設定、詳細なテーブル定義ドキュメントなど）があれば教えてください。必要に応じて README を追記・整備します。