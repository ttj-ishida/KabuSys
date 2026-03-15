# KabuSys

日本株向け自動売買基盤ライブラリ (v0.1.0)

KabuSys は日本株のデータ管理、特徴量生成、戦略・発注のための基盤コンポーネント群を提供するパッケージです。DuckDB を用いたスキーマ定義や、環境変数による設定管理、監査ログ（トレーサビリティ）など、取引システムの基盤機能を備えています。

## 主な機能

- 環境変数 / .env ファイルからの設定自動読み込み（プロジェクトルート検出）
- アプリケーション設定ラッパー（settings オブジェクト）
  - J-Quants、kabuステーション、Slack、DBパス等の設定取得
  - 環境（development / paper_trading / live）とログレベル検証
- DuckDB ベースのデータスキーマ初期化
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 推奨インデックスの作成
  - init_schema(db_path) / get_connection(db_path)
- 監査ログ（audit）用スキーマ
  - signal_events / order_requests / executions テーブル
  - 冪等性（order_request_id、broker_execution_id）と監査要件を満たす設計
  - init_audit_schema(conn) / init_audit_db(db_path)
- 最低限のモジュール分割：data, strategy, execution, monitoring（拡張可能）

## セットアップ

前提:
- Python 3.9+（typing 表記を含むため）
- DuckDB を使用するため `duckdb` パッケージが必要

例: 仮想環境を作成して依存をインストールする手順（任意のパッケージ管理に合わせて調整してください）

1. 仮想環境作成・有効化
   - macOS / Linux:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール
   ```bash
   pip install duckdb
   ```

3. パッケージを開発モードでインストール（任意）
   プロジェクトルートに `pyproject.toml` / `setup.py` がある場合:
   ```bash
   pip install -e .
   ```

## 環境変数と .env の自動読み込み

- プロジェクトルートは `src/kabusys/config.py` の実装により、`.git` または `pyproject.toml` の存在するディレクトリを起点として自動検出されます。
- 自動読み込みの優先順位:
  1. OS 環境変数
  2. .env.local（存在すれば上書き）
  3. .env（存在すれば読み込み）
- 自動読み込みを無効化するには環境変数を設定:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

.env のパースについて:
- `export KEY=val` 形式に対応
- 値はシングル・ダブルクォートをサポートし、クォート内ではバックスラッシュエスケープが有効
- クォートなしの場合、`#` は先頭または直前がスペース/タブの場合にコメントとして扱われる

### 必要な（例）環境変数
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略時: data/kabusys.duckdb)
- SQLITE_PATH (省略時: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live) デフォルト: development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) デフォルト: INFO

サンプル .env:
```
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## 使い方（簡易ガイド）

基本的な使い方は設定の読み込み、DB 初期化、監査スキーマ初期化の順です。

1. 設定の取得
```python
from kabusys.config import settings

# 必須項目が未設定の場合 ValueError が投げられます
token = settings.jquants_refresh_token
kabu_pass = settings.kabu_api_password
db_path = settings.duckdb_path  # Path オブジェクト
print(settings.env, settings.log_level)
```

2. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB または ":memory:" を指定可能
conn = init_schema(db_path)
# conn は duckdb.DuckDBPyConnection
```

3. 監査ログ（audit）スキーマを同じ DB に追加
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

4. 監査ログ専用 DB を作る場合
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

5. 既存 DB に接続する（スキーマ初期化は行わない）
```python
from kabusys.data.schema import get_connection

conn = get_connection(db_path)
```

エラーハンドリング:
- settings の必須プロパティは未設定時に ValueError を投げします（例: JQUANTS_REFRESH_TOKEN が未設定）。
- KABUSYS_ENV / LOG_LEVEL は許可された値でないと ValueError を投げます。

## ディレクトリ構成

以下はコードベースの主要ファイル／ディレクトリ構成です（抜粋）:

- src/
  - kabusys/
    - __init__.py             (パッケージ初期化, version=0.1.0)
    - config.py               (環境変数 / 設定管理)
    - data/
      - __init__.py
      - schema.py             (DuckDB スキーマ定義・初期化: init_schema, get_connection)
      - audit.py              (監査ログスキーマ: init_audit_schema, init_audit_db)
      - audit.py
      - audit.py
      - audit.py
      - audit.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

実際のリポジトリではさらにドキュメント（DataSchema.md, DataPlatform.md 等）や実装モジュールが置かれる想定です。

（注）上記は現在のコードスニペットに基づく要約です。strategy / execution / monitoring はパッケージ用の __init__ が存在しますが、機能の実体はこのスニペットに含まれていません。必要に応じて戦略の実装や発注モジュールを追加してください。

## 開発・運用上の注意点

- DuckDB へは init_schema を経てテーブル・インデックスを作成してください。init_schema は冪等（既存ならスキップ）です。
- 監査ログは削除しない前提で設計されています（FOREIGN KEY は ON DELETE RESTRICT）。履歴保存を意図しています。
- タイムゾーン:
  - audit スキーマは UTC に固定するため、init_audit_schema は `SET TimeZone='UTC'` を実行します。
- .env の自動ロードはプロジェクトルートを基準に行われます。テストなどでロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

## 今後の拡張案（参考）

- strategy, execution モジュール内に具体的な戦略・ブローカー接続実装を追加
- Slack 通知や J-Quants データ同期のユーティリティの追加
- テスト用の Fixtures / CI 設定

---

問題やドキュメント補足の要望があれば教えてください。README に追加したい使用例や環境変数のテンプレートも作成します。