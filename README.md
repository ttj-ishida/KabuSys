# KabuSys

日本株向け自動売買基盤ライブラリ（コアモジュール群）

バージョン: 0.1.0

概要、セットアップ、使い方、ディレクトリ構成などをまとめた README です。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・加工・特徴量生成・売買シグナル生成・発注管理を想定した自動売買システムのコアライブラリです。  
主要機能はデータレイヤ（Raw / Processed / Feature / Execution）向けのスキーマ定義や、環境変数ベースの設定管理などを提供します。

このリポジトリには次の要素が含まれます（抜粋）:
- 環境変数/設定管理（自動 .env ロード、必須チェック）
- DuckDB を使ったデータスキーマ定義と初期化処理
- モジュール分割（data / strategy / execution / monitoring）を想定したパッケージ構成

---

## 主な機能一覧

- 環境変数設定管理
  - .env / .env.local をプロジェクトルートから自動で読み込み（OS 環境変数を優先）
  - 必須環境変数未設定時に例外を発生させるユーティリティ
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証

- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution の多層テーブルスキーマを DDL として定義
  - インデックス作成、外部キー・制約を考慮した作成順での初期化
  - init_schema(db_path) でデータベースファイルの親ディレクトリ自動作成を行い初期化（":memory:" にも対応）
  - get_connection(db_path) で既存 DB へ接続

---

## セットアップ手順

前提
- Python 3.10 以上（| 演算子を含む型ヒント等の記法を使用）
- pip が利用可能

1. リポジトリをクローン
   - git clone などで取得

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須（最低限）: duckdb
     - pip install duckdb
   - 実際の運用では J-Quants API、kabu API、Slack 等のクライアントが必要になるため、それらの SDK を追加でインストールしてください。

4. 開発モードでインストール（任意）
   - プロジェクトに setup.cfg/pyproject.toml があれば:
     - pip install -e .

5. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を配置します。
   - 自動ロードはデフォルトで有効。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例: .env に必要なキー（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルトあり）
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
- KABUS_API_BASE_URL — default: http://localhost:18080/kabusapi
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db

注意: .env の自動読み込み順は「OS 環境変数 > .env.local > .env」です。.env.local は .env を上書きしますが、実際の OS 環境変数は保護され上書きされません。

---

## 使い方（簡易例）

- 設定を取得する例:

```python
from kabusys.config import settings

# 必須キーは未設定時に ValueError を送出します
token = settings.jquants_refresh_token
print("KabuSys environment:", settings.env)
print("DuckDB path:", settings.duckdb_path)
```

- DuckDB スキーマを初期化する例:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path を返します（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)

# 接続を使ってクエリ実行
df = conn.execute("SELECT name FROM sqlite_master LIMIT 10").fetchdf()
print(df)
```

- 既存 DB に接続する（スキーマ初期化を行わない）:

```python
from kabusys.data.schema import get_connection
conn = get_connection(":memory:")  # またはファイルパス
```

- 自動 .env ロードを無効化したい（テストなど）:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてプロセスを起動してください。

---

## .env パーサの挙動（簡単な説明）

- 空行や `#` で始まる行は無視されます。
- `export KEY=VALUE` の形式にも対応します。
- 値にシングル/ダブルクォートがある場合はエスケープ（バックスラッシュ）に対応して閉じクォートまで正しくパースします。
- クォートなしの場合、`#` の前に空白またはタブがある場合はコメントとみなして取り扱います。

---

## ディレクトリ構成

（プロジェクトルートに src ディレクトリがある構成の抜粋）

- src/
  - kabusys/
    - __init__.py
      - パッケージメタ情報（__version__ = "0.1.0"）
    - config.py
      - 環境変数読み込み、自動 .env ロード、Settings クラス（アプリケーション設定の操作）
    - data/
      - __init__.py
      - schema.py
        - DuckDB スキーマ定義 & init_schema / get_connection を提供
    - strategy/
      - __init__.py
      - （戦略ロジックを実装するモジュールを配置）
    - execution/
      - __init__.py
      - （発注／注文管理ロジックを配置）
    - monitoring/
      - __init__.py
      - （監視／メトリクス用のロジックを配置）
- .env, .env.local (プロジェクトルートに置く想定)
- pyproject.toml / setup.cfg / .git (プロジェクトルート判定に使用)

---

## 注意事項 / 補足

- スキーマは初期設計であり、実運用時にはインデックス・制約などのチューニングが必要になる場合があります。
- .env.example がある想定でコード内に参照があるため、実際の利用時は .env.example を参考に .env を作成してください。
- 実際の発注や API 通信（kabu ステーション、J-Quants、Slack 等）については本リポジトリの該当モジュール（strategy、execution、monitoring）に実装を追加してください。本 README はコア基盤（設定管理・データスキーマ）の利用方法を中心にまとめています。

---

必要であれば、README に加える以下の情報も作成できます:
- .env.example のテンプレート
- より詳細な DB スキーマ図（DataSchema.md の要約）
- CI / テスト実行手順
- 推奨パッケージ一覧（Slack SDK、J-Quants クライアント等）

どれを追加するか指定してください。