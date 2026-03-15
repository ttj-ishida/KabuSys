# KabuSys

日本株向けの自動売買システム用ライブラリ（骨組み）。  
本リポジトリはデータレイヤ、戦略、発注／モニタリング周りの基盤的なモジュールを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築のための共通基盤です。  
主に以下を提供します。

- 環境変数ベースの設定管理（自動でプロジェクトルートの `.env` / `.env.local` を読み込み）
- DuckDB を用いたデータスキーマ定義・初期化機能（Raw / Processed / Feature / Execution 層）
- モジュール分割（data / strategy / execution / monitoring）のスケルトン

本コードベースはフル機能の実装ではなく、システム設計のための基盤・ユーティリティを提供します。

---

## 機能一覧

- 設定管理 (`kabusys.config.Settings`)
  - 必須・任意の環境変数を型に合わせて取得
  - 自動 .env 読み込み（`.env` → `.env.local`、`.env.local` は上書き）
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
  - プロジェクトルート判定は `.git` または `pyproject.toml` を探索
- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層のテーブル DDL 定義
  - インデックス定義
  - `init_schema(db_path)` による初期化（冪等）
  - `get_connection(db_path)` による接続取得
- パッケージ分割（将来的に戦略・実行・モニタリングの実装を追加するための名前空間）
  - `kabusys.data`
  - `kabusys.strategy`
  - `kabusys.execution`
  - `kabusys.monitoring`

---

## セットアップ手順

前提: Python がインストールされていること（推奨: 3.9+）。

1. リポジトリをクローン／チェックアウト
   - 例: git clone <repository-url>

2. 仮想環境を作成して有効化（任意だが推奨）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   - 最低限 DuckDB が必要です:
     - pip install duckdb
   - 開発用や追加依存はプロジェクト側で管理してください。

4. パッケージをインストール（開発モード）
   - プロジェクトルートに `pyproject.toml` / `setup.py` がある場合:
     - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数として設定します。
   - 自動読み込みの対象はプロジェクトルート（`.git` または `pyproject.toml`）以下の `.env` と `.env.local` です。
   - `.env.local` は `.env` の値を上書きします。

例: `.env` の最低限の内容（値は環境に合わせて置き換えてください）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
# 任意
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

ヒント:
- 自動読み込みを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方

基本的な使い方（設定と DuckDB スキーマ初期化の例）:

1. 設定読み込み（自動で `.env` を読むため、明示的な読み込みは不要）
```python
from kabusys.config import settings

# 必須環境変数はプロパティアクセス時に検証されます
print("env:", settings.env)
print("duckdb path:", settings.duckdb_path)
```

2. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = init_schema(settings.duckdb_path)

# インメモリ DB の例
mem_conn = init_schema(":memory:")
```

3. 既存 DB へのコネクション取得（スキーマ初期化は行わない）
```python
from kabusys.data.schema import get_connection
conn = get_connection(settings.duckdb_path)
```

4. 監視・戦略・発注モジュールの骨組みはそれぞれの名前空間に配置されています（詳細な実装はプロジェクトの発展に応じて追加）。

注意点:
- `Settings` のプロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）は未設定だと ValueError を送出します。起動前に設定してください。
- 環境 (`KABUSYS_ENV`) は `development`、`paper_trading`、`live` のいずれかである必要があります。
- ログレベル (`LOG_LEVEL`) は `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` のいずれかである必要があります。

---

## ディレクトリ構成

リポジトリ内の主なファイル／ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py            # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py          # DuckDB スキーマ定義・初期化
    - strategy/
      - __init__.py        # 戦略関連（拡張ポイント）
    - execution/
      - __init__.py        # 発注・実行関連（拡張ポイント）
    - monitoring/
      - __init__.py        # モニタリング関連（拡張ポイント）

主要ファイルの説明:
- src/kabusys/config.py
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - Settings クラス：アプリケーション設定をプロパティで提供
- src/kabusys/data/schema.py
  - DuckDB テーブル定義（Raw / Processed / Feature / Execution）
  - init_schema() / get_connection() を提供

---

## 補足 / 運用上の注意

- .env のパースは一般的な shell 形式をサポートしています（export プレフィックス、クォート、インラインコメント処理等）。
- .env 読み込みはプロジェクトルート判定に依存するため、パッケージ配布後やテスト環境で挙動を制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB スキーマは冪等なので、複数回 init_schema を呼んでも問題ありません。
- 実際の J-Quants API、kabu API、Slack 連携、発注ロジック等は本リポジトリの拡張として実装してください。

---

必要であれば、README にサンプルワークフロー（データ取得 → 特徴量作成 → シグナル生成 → 発注 → モニタリング）のテンプレートや、`.env.example` の完全版も追加します。追加希望があれば教えてください。