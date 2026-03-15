# KabuSys

日本株向けの自動売買基盤（骨格実装）。  
市場データ収集・加工、特徴量作成、シグナル生成、発注／約定管理、監視までを想定したモジュール群を含みます。

現在のバージョン: 0.1.0

---

## 概要

KabuSys は日本株自動売買システムの基礎ライブラリです。  
以下の主要コンポーネントを提供します（骨格のみ／実運用ロジックはユーザー実装想定）:

- data: データモデル・DuckDB スキーマ定義と初期化
- strategy: 戦略実装用パッケージプレースホルダ
- execution: 発注・実行ロジックのプレースホルダ
- monitoring: 監視・通知ロジックのプレースホルダ
- config: 環境変数／設定管理

データベースは DuckDB を想定し、スキーマは Raw / Processed / Feature / Execution の多層構造で定義されています。

---

## 主な機能

- 環境変数の自動ロード (.env, .env.local)。プロジェクトルート（.git または pyproject.toml）を基準に読み込む。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
  - .env のパースはシングルクォート／ダブルクォートやエスケープ、コメントに対応
- Settings クラスによる型つきアクセス（必須値は未設定時に例外）
  - J-Quants / kabu API / Slack / DB パス / 実行モード（development/paper_trading/live）など
- DuckDB スキーマ定義と初期化
  - テーブル群（raw_prices, prices_daily, features, signals, orders, trades, positions, portfolio_performance など）
  - 性能を考慮したインデックス定義
  - init_schema(db_path) により冪等にテーブル作成
- DuckDB 接続ヘルパー（get_connection）

---

## 要件

- Python 3.9+
- duckdb（DuckDB Python パッケージ）
- そのほか利用する外部 API（kabuステーション、J-Quants、Slack）に応じたライブラリは別途導入

（プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境作成（例）
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 依存パッケージをインストール
   - 最低限 DuckDB が必要:
     - pip install duckdb
   - プロジェクト配下に pyproject.toml / requirements.txt があれば:
     - pip install -r requirements.txt
     - または pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成します。自動ロードはプロジェクトルートを基準に行われます。
   - 自動ロードを無効にする場合は、環境で `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

サンプル `.env`（必須項目を含めた最小例）:
```
# J-Quants API
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
# KABU_API_BASE_URL は省略時 http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（省略可能）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行モード: development / paper_trading / live
KABUSYS_ENV=development

# ログレベル（任意）
LOG_LEVEL=INFO
```

---

## 使い方（簡易ガイド）

- 設定値を参照する

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path
```

必須の環境変数が未設定の場合、Settings のプロパティは ValueError を投げます。

- DuckDB スキーマを初期化する

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# ファイル DB を初期化（設定の DUCKDB_PATH を使用）
conn = init_schema(settings.duckdb_path)

# インメモリ DB（テスト用）
conn_mem = init_schema(":memory:")
```

init_schema は親ディレクトリが存在しない場合は自動作成し、DDL を順次実行してテーブルとインデックスを作成します（冪等）。

- 既存 DB に接続する

```python
from kabusys.data.schema import get_connection
conn = get_connection(settings.duckdb_path)
```

- 自動ロードの振る舞い
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - .env/.env.local の読み込みはプロジェクトルートが見つからない場合スキップ
  - .env のロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境に設定

---

## ディレクトリ構成

現状の主要ファイルは以下のとおりです:

- src/
  - kabusys/
    - __init__.py             (パッケージ定義: __version__ = "0.1.0")
    - config.py               (環境変数・設定管理)
    - data/
      - __init__.py
      - schema.py             (DuckDB スキーマ定義 / init_schema / get_connection)
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主なモジュールの説明:
- kabusys.config
  - Settings クラス（settings = Settings() をモジュールスコープで提供）
  - 自動 .env ロード機能（.git または pyproject.toml をプロジェクトルート判定）
  - 環境変数検証（KABUSYS_ENV, LOG_LEVEL 等）
- kabusys.data.schema
  - DuckDB 用の DDL（Raw / Processed / Feature / Execution レイヤ）
  - init_schema(db_path) によりテーブルとインデックスを作成
  - get_connection(db_path) で既存 DB に接続

---

## 開発／運用上の注意

- Settings は必須値未設定時に例外を投げます。CI やテストでは必須環境変数を一時的にセットするか、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用して自動読み込みを抑止してください。
- init_schema は既存のテーブルがあれば何度実行しても安全（CREATE TABLE IF NOT EXISTS を使用）。
- 実取引を行う場合（KABUSYS_ENV=live）、発注ロジックやエラーハンドリング・レート制限などを十分に実装・検証してください。
- SQLite（monitoring 用）パスは `SQLITE_PATH` で設定可能（コード上での利用箇所に応じて別途実装が必要）。

---

必要に応じて、戦略実装のテンプレート、実行エンジン、監視アダプタ（Slack 通知など）のサンプルを追加していくと良いでしょう。