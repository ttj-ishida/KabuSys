# KabuSys

日本株向け自動売買システムの骨組み（ライブラリ）。  
データ取得・保存のスキーマ定義、環境変数/設定管理、取引実行や戦略用のモジュール群の基盤を提供します。

バージョン: 0.1.0 (src/kabusys/__init__.py の __version__)

---

## 概要

KabuSys は日本株の自動売買を支援するための共通基盤ライブラリです。  
主に下記を提供します。

- 環境変数・設定の統一的管理（.env サポート）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）の初期化と接続
- 戦略、実行、モニタリング用モジュールのためのパッケージ構成（プレースホルダ含む）

このリポジトリはフル機能のアプリケーションではなく、複数モジュールを実装するための土台（ライブラリ）です。

---

## 主な機能

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）
  - 環境変数要求時に未設定ならば明示的なエラーを投げる Settings API
  - 実行環境フラグ（development / paper_trading / live）やログレベル検証

- データベーススキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義（銘柄×日付の時系列や執行履歴、ポートフォリオ情報等）
  - 頻出クエリ向けのインデックス定義
  - init_schema() による冪等的な初期化

- 基本ユーティリティ
  - DuckDB への接続取得用 get_connection()
  - パッケージ構成（strategy / execution / monitoring）を想定したモジュール配置

---

## 要件

- Python 3.10 以上（型注釈に `|` 演算子を使用）
- duckdb（DuckDB Python パッケージ）
- （運用時）J-Quants / kabu ステーション / Slack 等の外部 API 用の認証情報

pip で最低限必要なパッケージを入れる例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
```
他の外部 API クライアントや Slack SDK 等は用途に応じて別途追加してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークスペースを準備
```bash
git clone <リポジトリURL>
cd <リポジトリ>
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# 開発インストール（パッケージ化している場合）
pip install -e .
```

2. 環境変数を設定（.env をプロジェクトルートに置く）
- このパッケージはプロジェクトルート（.git または pyproject.toml を持つディレクトリ）を検出して `.env` → `.env.local` の順に自動読み込みします。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env（プロジェクトルートに保存）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabu ステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス（省略時は data/kabusys.duckdb）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

3. 必須環境変数の確認  
コード内の Settings は一部の環境変数を必須とします（指定がないと ValueError）。テストや CI で自動読み込みを避けたい場合は `.env` を手動で管理してください。

---

## 使い方（主な API）

- 設定の利用
```python
from kabusys.config import settings

token = settings.jquants_refresh_token        # JQUANTS_REFRESH_TOKEN を取得（未設定時は例外）
base_url = settings.kabu_api_base_url         # デフォルト: http://localhost:18080/kabusapi
is_live = settings.is_live                    # 環境が 'live' かどうか
db_path = settings.duckdb_path                # Path オブジェクトを返す
```

- DuckDB スキーマの初期化（最初に一度）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path を返す
conn = init_schema(settings.duckdb_path)
# またはインメモリ DB
conn_mem = init_schema(":memory:")
```

- 既存 DB へ接続
```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# conn.execute("SELECT ...") 等でクエリ実行
```

- パッケージ情報
```python
import kabusys
print(kabusys.__version__)
```

---

## .env 自動読み込みの挙動（補足）

- 読み込み順:
  1. OS 環境変数（常に優先）
  2. .env（プロジェクトルート）
  3. .env.local（上書き）
- プロジェクトルートは、`src/kabusys/config.py` の基準で `__file__` から親を遡って `.git` または `pyproject.toml` を探して決定します。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます（テスト用途など）。

.env のパースはシェルライクな簡易仕様を持ち、シングル/ダブルクォート、export プレフィックス、行末コメントなどにある程度対応しています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py               # __version__, __all__
    - config.py                 # 環境変数・設定管理（Settings）
    - data/
      - __init__.py
      - schema.py               # DuckDB スキーマ定義と init_schema(), get_connection()
    - strategy/
      - __init__.py             # 戦略モジュール用パッケージ（空のプレースホルダ）
    - execution/
      - __init__.py             # 実行（注文）モジュール用パッケージ（空のプレースホルダ）
    - monitoring/
      - __init__.py             # モニタリング用パッケージ（空のプレースホルダ）

---

## 開発メモ / 注意点

- DuckDB のスキーマ初期化は冪等（既存テーブルはスキップ）です。複数回実行しても安全です。
- Settings の必須キーが未設定だと ValueError を投げます。CI やテストではモック環境変数を設定してください。
- 現在 strategy / execution / monitoring は基盤パッケージとしての構造のみ用意されています。追加実装は各パッケージに行ってください。
- 外部 API（J-Quants, kabu, Slack 等）との統合は別途クライアント実装が必要です。環境変数は config.Settings から一元的に取得できます。

---

必要であれば README に「インストール用 requirements.txt」「サンプル .env.example」「使い方のより詳細なコード例（取引フロー例）」などを追記します。どの情報を追加したいか教えてください。