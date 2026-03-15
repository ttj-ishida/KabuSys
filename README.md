# KabuSys

日本株の自動売買システム（ライブラリ／フレームワーク）のコア部です。  
このリポジトリはデータレイヤ（DuckDBスキーマ）、環境設定の管理、戦略・実行・監視のためのパッケージ構成を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的を持ったモジュール群を含むプロジェクトです。

- 市場データ・財務データ・ニュース・約定データ等の生データ（Raw Layer）を保管
- 日次整形データ（Processed Layer）、戦略用特徴量（Feature Layer）を管理
- シグナル発生・発注キュー・注文・約定・ポジション・ポートフォリオ情報（Execution Layer）を管理
- 環境変数からの設定管理（.env 自動読み込み機能）
- DuckDB を用いたローカルデータベーススキーマ初期化

このリポジトリはコアのデータ管理と設定周りにフォーカスしており、実際の API 呼び出し・戦略ロジック・Slack通知等はそれぞれ別モジュール（未実装／拡張）として統合する前提です。

---

## 機能一覧

- 環境変数管理（.env / .env.local の自動読み込み）
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行う
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - export 形式、引用符付き値、行内コメントなどに対応したパーサを実装
- Settings クラス（プロパティ経由で必須／任意設定を取得）
  - J-Quants/JQUANTS_REFRESH_TOKEN（必須）
  - kabuステーション API パスワード等（KABU_API_PASSWORD、KABU_API_BASE_URL）
  - Slack 関連（SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）
  - DB パス（DUCKDB_PATH、SQLITE_PATH）
  - 環境モード（KABUSYS_ENV: development / paper_trading / live）
  - ログレベル（LOG_LEVEL）
- DuckDB スキーマ初期化ユーティリティ
  - raw / processed / feature / execution の各レイヤのテーブル DDL を用意
  - インデックス作成
  - init_schema(db_path) で冪等にスキーマを作成
  - get_connection(db_path) で接続を取得可能

---

## 要件

- Python 3.10 以上（型注釈で | を使用しているため）
- 必須パッケージ（このコードベースで直接必要なもの）
  - duckdb

pip 等でインストールしてください:
```
pip install duckdb
```

プロジェクト自体はパッケージとしてインストールして使用することを想定しています:
```
pip install -e .
```
（pyproject.toml / setup.cfg がある前提）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. Python 3.10+ の仮想環境を用意して有効化
3. 必要パッケージをインストール（最低限 duckdb）
   ```
   pip install duckdb
   ```
4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成することで自動的に読み込まれます（既存の OS 環境変数は上書きされません）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

例: .env（テンプレート）
```
# 必須
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# オプション
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方

主に以下の API が利用できます。

- 環境設定の取得
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token  # 環境変数が未設定だと ValueError
  db_path = settings.duckdb_path          # Path オブジェクト
  if settings.is_live:
      print("ライブモードです")
  ```

- DuckDB スキーマの初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # ファイル/ディレクトリを自動作成してテーブルを作る
  # 以降 conn を使ってクエリを実行
  with conn:
      df = conn.execute("SELECT COUNT(*) FROM prices_daily").fetchdf()
      print(df)
  ```

- 既存 DB への接続（スキーマ初期化は行われません）
  ```python
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  ```

注意点:
- init_schema は冪等（既にテーブルがあればスキップ）です。
- .env の自動読み込みは、モジュールインポート時に行われます（プロジェクトルートが検出できた場合）。テストや特殊な用途で自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成

主要ファイル／モジュール:

- src/
  - kabusys/
    - __init__.py             (パッケージ初期化、バージョン定義)
    - config.py               (環境変数・設定管理)
    - data/
      - __init__.py
      - schema.py             (DuckDB スキーマ定義・初期化)
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

各レイヤの説明:
- kabusys.config: .env の自動読み込みロジック、Settings クラスを提供
- kabusys.data.schema: 全テーブル DDL 定義、init_schema/get_connection を提供
- kabusys.strategy: 戦略ロジックを配置するための名前空間（拡張点）
- kabusys.execution: 発注・注文管理ロジックを配置するための名前空間（拡張点）
- kabusys.monitoring: モニタリング・記録系（監視DBなど）を配置するための名前空間（拡張点）

---

## 開発メモ / 実装のポイント

- .env パースは shell 風の細かなケースをハンドリング（export 形式、引用符、エスケープ、コメント）しています。厳密な仕様に従った取り扱いを行うため、特殊ケースの .env を利用する際は挙動を確認してください。
- DuckDB スキーマは Raw / Processed / Feature / Execution の 3+1 層構造で設計されています。実際のデータパイプラインでは Raw を取り込み、Processed → Feature を作成し、Execution 層の signals→orders→trades→positions に繋げる流れを想定しています。
- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかで検証されます。

---

## 今後の拡張点（例）

- J-Quants / kabu API のクライアント実装
- Slack 通知（settings で指定した token / channel を利用）
- 戦略モジュールのテンプレート
- CI / テスト用の設定とテストケース
- Docker イメージ化やサービス化

---

必要に応じて、この README に実行コマンドや環境ファイルのサンプルを追記します。ほかに載せたい情報（CI、デプロイ手順、依存関係リストなど）があれば教えてください。