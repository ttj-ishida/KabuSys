# KabuSys

日本株向け自動売買システムのコアライブラリ（骨格実装）。

このリポジトリは、データレイヤ（Raw / Processed / Feature / Execution）と監査ログ（トレーサビリティ）を管理するためのスキーマ定義・初期化、環境設定読み込み、および各サブパッケージ（strategy / execution / monitoring / data）のエントリポイントを提供します。

---

## 主な機能

- 環境変数管理
  - .env / .env.local をプロジェクトルートから自動読み込み
  - 必須環境変数の取得・バリデーション（Settings クラス）
  - 自動読み込みの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）

- データベーススキーマ定義（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - 監査ログ（signal_events, order_requests, executions）用の別モジュール
  - スキーマ初期化ユーティリティ（init_schema, init_audit_schema, init_audit_db）
  - インメモリ DB (":memory:") 対応

- パッケージ構造
  - strategy, execution, monitoring, data のエントリポイント（拡張先）

---

## 前提条件

- Python 3.10 以上（型注釈に `X | Y` を使用）
- 必要パッケージ（例）
  - duckdb

pip でインストールする場合の例:
```
pip install duckdb
```

（パッケージ配布用の pyproject.toml / requirements.txt は本リポジトリに含まれていないため、プロジェクト依存関係に合わせて適宜追加してください。）

---

## セットアップ手順

1. リポジトリをクローン、仮想環境作成、依存パッケージをインストール:
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   pip install --upgrade pip
   pip install duckdb
   ```

2. プロジェクトルートに `.env`（または `.env.local`）を配置して環境変数を設定。
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。
   - 自動読み込みを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. 必要な環境変数（主要なもの）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (オプション、デフォルト: http://localhost:18080/kabusapi)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - KABUSYS_ENV (optional: development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (optional: DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH (optional: デフォルト data/kabusys.duckdb)
   - SQLITE_PATH (optional: デフォルト data/monitoring.db)

   .env の簡単な例:
   ```
   JQUANTS_REFRESH_TOKEN="your_jquants_token"
   KABU_API_PASSWORD="your_kabu_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単な例）

- Settings（環境変数の読み取り）

```python
from kabusys.config import settings

# 必須変数が未設定だと ValueError が発生します
token = settings.jquants_refresh_token
kabu_base = settings.kabu_api_base_url
is_live = settings.is_live
```

- DuckDB スキーマ初期化（ファイル DB）

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

db_path = settings.duckdb_path  # Path オブジェクト
conn = init_schema(db_path)     # ディレクトリを自動作成してスキーマを作る
# conn は duckdb.DuckDBPyConnection
```

- インメモリ DB での初期化（テストなど）

```python
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")
# 必要に応じてテスト用のデータ投入やクエリを実行
```

- 監査ログスキーマを既存接続に追加

```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

- 監査ログ専用の DB を作る場合

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 自動 .env ロードの挙動

- 起点: このモジュールのファイル位置から親ディレクトリを辿り、.git または pyproject.toml を見つけたディレクトリをプロジェクトルートとみなします。
- 読み込み順:
  - OS 環境変数（既存） > .env.local > .env
- 既存の OS 環境変数は上書きされません（ただし .env.local は override=True で上書き可能にしていますが、OS 環境変数は保護されます）。
- 無効化:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動ロードを行いません（テスト等で使用）。

.env のパースは一般的なシェル形式（export KEY=val, シングル/ダブルクォート、コメント）に対応しています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
    - パッケージのバージョンと公開モジュール一覧
  - config.py
    - Settings クラス：環境変数の読み取り・バリデーション、自動 .env ロード
  - data/
    - __init__.py
    - schema.py
      - DuckDB の全レイヤー（Raw / Processed / Feature / Execution）用テーブル定義、インデックス、init_schema/get_connection
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）の DDL と初期化ユーティリティ（init_audit_schema, init_audit_db）
    - audit のスキーマは監査用に UTC 保存など運用方針が組み込まれている
    - (その他) audit/audit専用DB初期化
  - strategy/
    - __init__.py
    - （戦略ロジックを配置するためのパッケージ）
  - execution/
    - __init__.py
    - （発注・注文管理の実装を配置）
  - monitoring/
    - __init__.py
    - （監視・メトリクス関連の実装を配置）

---

## 開発メモ / 設計方針（抜粋）

- データプラットフォームは 3 層＋実行層の分離を重視（Raw → Processed → Feature → Execution）。
- 監査ログは「シグナルから約定まで」を UUID 連鎖で追跡可能にする設計。
- 監査ログは削除せず追跡保持（FK は ON DELETE RESTRICT を使用）。
- すべての TIMESTAMP は UTC で保存（監査スキーマ初期化時に SET TimeZone='UTC' が実行されます）。

---

必要に応じて README を拡張して、具体的な戦略テンプレート、発注フローサンプル、運用手順（本番/ペーパー切替、安全対策）などを追記してください。