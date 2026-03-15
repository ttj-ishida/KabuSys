# KabuSys

日本株自動売買システムのコアライブラリ（パッケージ）です。マーケットデータの格納・加工、戦略・特徴量レイヤー、発注・約定・ポジション管理のためのスキーマと設定管理を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのための内部ライブラリ群です。  
主に次の役割を持ちます。

- 環境変数 / 設定の集中管理（自動で .env を読み込み）
- DuckDB を用いたデータスキーマ（生データ → 整形データ → 特徴量 → 発注/執行）定義と初期化
- 戦略、発注、モニタリング等のモジュールを格納するパッケージ構造の土台

コードは `src/kabusys` 以下に配置されています。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（読み込み順: OS 環境変数 > .env.local > .env）
  - `Settings` クラスで必要な設定値（J-Quants トークン、kabu API パスワード、Slack トークンなど）をプロパティとして提供
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動読み込み無効化
  - .env のパースは `export KEY=val`、シングル/ダブルクォート、インラインコメント等に対応

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution の層ごとにテーブルを定義
  - prices_daily, raw_prices, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など多数のテーブルを作成
  - インデックスを作成し、典型的クエリの高速化を考慮
  - スキーマを初期化する `init_schema(db_path)` を提供（冪等）

- パッケージ構成の雛形
  - strategy、execution、monitoring のモジュール用ディレクトリを用意

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈で `X | Y` を使用しているため）

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限: duckdb
     - pip install duckdb
   - 実運用で外部 API / Slack 連携等を行う場合はそれらのクライアントも追加
     - 例: pip install requests slack-sdk
   - （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらに従ってください）
   - 開発インストール（パッケージを編集しながら利用する場合）
     - pip install -e .

3. 環境変数ファイル（.env）を用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env に設定する主なキー
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略時: data/kabusys.duckdb)
- SQLITE_PATH (省略時: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live。省略時は development)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL。省略時は INFO)

> 注意: `Settings` の必須プロパティは未設定だと `ValueError` を送出します。`.env.example` を参照して `.env` を作成してください（リポジトリに例ファイルがある場合）。

---

## 使い方

以下は主要なユースケースの例です。

- 設定値の参照

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print(settings.kabu_api_base_url)
print(settings.is_live, settings.is_paper, settings.is_dev)
```

- DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = init_schema(settings.duckdb_path)

# インメモリ DB を使う場合
mem_conn = init_schema(":memory:")
```

- 既存 DB への接続（スキーマ初期化は行わない）

```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# SQL 実行例
df = conn.execute("SELECT * FROM prices_daily LIMIT 10").fetchdf()
```

- 自動 .env 読み込みの挙動
  - デフォルトでは OS 環境変数を優先して読み込みます（上書きされません）。
  - プロジェクトルートが検出できない場合は自動読み込みをスキップします（安全措置）。
  - `.env.local` は `.env` の後に読み込まれ、同じキーが上書きされます（ただし OS 環境変数は保護される）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル / ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py          # パッケージ初期化（__version__ 等）
    - config.py            # 環境変数・設定管理（Settings）
    - data/
      - __init__.py
      - schema.py          # DuckDB スキーマ定義と初期化（init_schema, get_connection）
    - strategy/
      - __init__.py        # 戦略関連モジュール（実装場所）
    - execution/
      - __init__.py        # 発注・執行関連モジュール（実装場所）
    - monitoring/
      - __init__.py        # モニタリング関連（実装場所）

主要ファイルの役割:
- config.py: 自動 .env 読み込み、Settings クラス（J-Quants / kabu / Slack / DB パス / 環境判定等）
- data/schema.py: DuckDB 用のすべてのテーブル定義（Raw / Processed / Feature / Execution 層）とインデックス、init_schema 関数

---

## 注意点 / 補足

- Python バージョン: 3.10 以上を想定しています（Union 型の | を使用）。
- 実際の運用では、kabuステーション API や J-Quants への接続ライブラリ・認証処理、Slack 通知等を別途実装する必要があります。本パッケージはその土台（設定とデータ層）を提供します。
- DuckDB の DB パスはデフォルトで `data/kabusys.duckdb` に設定されます。環境変数 `DUCKDB_PATH` で変更できます。
- データベースを初期化する際、ファイルパスの親ディレクトリがなければ自動で作成されます。メモリ DB を利用する場合は `":memory:"` を指定してください。

---

必要であれば、README にサンプル .env.example、実際の依存関係リスト（requirements.txt / pyproject.toml）や、戦略・発注フローの使用例を追記できます。必要な追加情報を教えてください。