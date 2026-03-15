# KabuSys

日本株向けの自動売買基盤ライブラリ (KabuSys) の README。

バージョン: 0.1.0

概要、機能、セットアップ手順、使い方、ディレクトリ構成を記載します。

---

## プロジェクト概要

KabuSys は日本株のデータ管理、特徴量生成、シグナル管理、発注・約定・ポジション管理までを想定した自動売買システムの基盤ライブラリです。  
主に以下を提供します。

- 環境設定（.env / 環境変数）管理
- DuckDB を用いた多層スキーマ（Raw / Processed / Feature / Execution）
- API 用の設定（J-Quants / kabuステーション / Slack 等）
- 将来的な strategy / execution / monitoring モジュールの基礎構造

このリポジトリはライブラリとしてインポートして利用することを想定しています。

---

## 機能一覧

- 環境変数自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）上の `.env` と `.env.local` を自動で読み込み
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化
  - `.env` のパースはシンプルな引用符、エスケープ、コメント対応（`export KEY=val` も可）
- 設定取得 API
  - `kabusys.config.settings` オブジェクトを通じて設定値を取得
  - 必須設定は未設定時に明示的なエラーを出す
- DuckDB スキーマ管理
  - `init_schema(db_path)` でスキーマを初期化（冪等）
  - Raw / Processed / Feature / Execution の多層テーブル群を定義
  - 頻出クエリに対するインデックスを自動作成
- データ層（主なテーブル）
  - Raw: raw_prices, raw_financials, raw_news, raw_executions
  - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature: features, ai_scores
  - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

---

## セットアップ手順

前提
- Python 3.10+ を推奨（型記法と Future annotations を利用）
- 必要なパッケージ: duckdb（その他は利用状況に応じて追加）

1. リポジトリをクローン
   - 例: git clone <repository-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - pip install duckdb
   - 開発用にパッケージ化されている場合: pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成します。
   - 自動読み込みはデフォルトで有効。テスト等で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env の例（必要なキーはプロジェクトで利用するものを揃えてください）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス（省略時はデフォルトを使用）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

環境変数の優先順位:
- OS 環境変数 > .env.local > .env

---

## 使い方

ここでは主要な使い方（設定取得、DB 初期化）を示します。

1) 設定を取得する
```python
from kabusys.config import settings

# 必須項目は未設定だと ValueError を送出します
token = settings.jquants_refresh_token
kabu_pwd = settings.kabu_api_password

# その他
db_path = settings.duckdb_path  # pathlib.Path
env = settings.env              # development / paper_trading / live
is_live = settings.is_live
```

2) DuckDB スキーマを初期化する
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# settings.duckdb_path は Path を返す
conn = init_schema(settings.duckdb_path)   # ファイルを作成してスキーマを作成
# またはメモリ DB
conn_mem = init_schema(":memory:")

# 既存 DB に接続する場合（スキーマは初回に init_schema を呼ぶ）
conn2 = get_connection(settings.duckdb_path)
```

init_schema はテーブルとインデックスを全て作成します（既に存在する場合はスキップされるため冪等）。

3) .env のパース仕様（主な点）
- 空行・先頭が `#` の行は無視
- `export KEY=val` 形式も許容
- 値がシングル / ダブルクォートで囲まれている場合はエスケープ（\）を考慮して閉じクォートまでを値として扱う
- クォートされていない場合、`#` の直前が空白またはタブであればコメントとして扱う

---

## 設定（環境変数）一覧

必須（未設定だとエラー）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルトあり）
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live。デフォルト: development)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL。デフォルト: INFO)

自動.env読み込みを無効化
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成

主要なファイルとモジュール構成は以下の通りです（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - __version__ = "0.1.0"
    - config.py            # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py         # DuckDB スキーマ定義と初期化 API (init_schema, get_connection)
    - strategy/
      - __init__.py        # 戦略関連（拡張ポイント）
    - execution/
      - __init__.py        # 発注・実行関連（拡張ポイント）
    - monitoring/
      - __init__.py        # モニタリング機能（拡張ポイント）

ドキュメントやデータファイルの格納場所はプロジェクトルートに配置する想定です（例: .env, .env.local, pyproject.toml など）。

---

## その他 / 開発メモ

- スキーマは DataSchema.md を基に設計されています（リポジトリにある場合は参照してください）。
- 外部サービス連携（J-Quants、kabuAPI、Slack）は設定を通じて行います。実際の API 呼び出しやトークン管理は各モジュール（将来的に追加される strategy / execution モジュール）で実装してください。
- テストや CI で .env 自動読み込みを邪魔したくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- DuckDB を利用するため、ローカルに DB ファイルを作るディレクトリは自動作成されます（親ディレクトリが存在しない場合は mkdir されます）。

---

必要であれば、README を拡張して以下を追加できます:
- 実行例（シンプルな戦略のサンプル）
- テストの実行方法
- デプロイ / 運用上の注意（paper/live 切替、Slack 通知設定など）

ご希望があれば追記します。