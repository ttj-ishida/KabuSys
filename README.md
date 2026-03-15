# KabuSys

日本株向け自動売買システムの基盤ライブラリ。データ取得〜特徴量生成〜発注までのワークフローを想定した共通モジュール群を提供します（構成はデータ層・戦略層・実行層・監視層）。

バージョン: 0.1.0

---

## 概要

このパッケージは以下を含みます。

- 環境変数・設定の集中管理（自動 .env ロード）
- DuckDB を用いたスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 戦略（strategy）・発注（execution）・監視（monitoring）のためのパッケージプレースホルダ

目的は、個別の戦略実装や実行ロジックを載せるための共通土台（設定、DBスキーマ、接続）を提供することです。

---

## 主な機能一覧

- 環境変数の自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動読み込み
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能
  - シンプルだが POSIX ライクな `.env` のパース（export 形式・クォート・インラインコメント対応）
- 設定オブジェクト（settings）
  - J-Quants、kabuステーション、Slack、DBパス、環境（development / paper_trading / live）等の取得
  - 必須項目が未設定の場合は例外を投げて明示
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義を含む DDL を持ち、初期化関数で一括作成
  - インデックス定義、外部キーやチェック制約を含む堅牢なスキーマ
  - 初回用 init_schema() と通常接続用 get_connection() を提供

---

## 必要条件

- Python 3.10+
- duckdb（DuckDB Python パッケージ）
- （実運用では Slack SDK や kabu API クライアント、J-Quants クライアント等が別途必要）

簡単な依存パッケージの例（最低限）:

pip:
```
pip install duckdb
```

本リポジトリに requirements ファイルがある場合はそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローン / ダウンロード
2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install -U pip
   pip install duckdb
   # 実際のプロジェクトでは `pip install -r requirements.txt` や `pip install -e .` を利用
   ```
4. 環境変数を準備
   - プロジェクトルートに `.env`（`pyproject.toml` または `.git` があるディレクトリが自動探索の基準）を配置すると、自動で読み込まれます。
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してからパッケージをインポートしてください。

---

## 環境変数（.env）について

主要なキー（必須項目は Settings で require されます）:

- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（オプション、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

例（.env）:
```
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C12345678"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパーシングは export を含む形式やクォート、エスケープ、コメントなどに対応しています。

---

## 使い方（簡単な例）

- 設定参照:
```python
from kabusys.config import settings

print(settings.kabu_api_base_url)
print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_live)
```

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path を使って DB を初期化（ファイルパスの親ディレクトリは自動作成）
conn = init_schema(settings.duckdb_path)

# conn は duckdb の接続オブジェクト（duckdb.DuckDBPyConnection）
with conn:
    # 例えばテーブル一覧を確認
    print(conn.execute("PRAGMA show_tables()").fetchall())
```

- 既存 DB へ接続:
```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# スキーマ初期化は行われない点に注意（初回のみ init_schema を使う）
```

- 自動 .env ロードを無効化したい（テストなど）:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # POSIX
# Windows (PowerShell)
$env:KABUSYS_DISABLE_AUTO_ENV_LOAD = "1"
```
この環境変数を設定してからパッケージをインポートすると、自動で .env を読み込みません。

---

## 主要 API（概要）

- kabusys.config
  - settings: Settings インスタンス（プロパティ経由で各種設定を取得）
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev
- kabusys.data.schema
  - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
    - DuckDB のファイルを作成（親ディレクトリ自動生成）し、テーブルとインデックスを作成（冪等）
  - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
    - 既存 DB への接続（スキーマ初期化は行わない）

---

## ディレクトリ構成

リポジトリ内の主なファイル/ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py               # 環境変数・設定管理、自動 .env ロード
    - data/
      - __init__.py
      - schema.py            # DuckDB スキーマ定義と init_schema / get_connection
    - strategy/
      - __init__.py          # 戦略モジュール（拡張用プレースホルダ）
    - execution/
      - __init__.py          # 発注 / 実行モジュール（拡張用プレースホルダ）
    - monitoring/
      - __init__.py          # 監視 / メトリクス用プレースホルダ

その他:
- pyproject.toml（存在する場合はプロジェクトルートの探索対象）
- .env, .env.local（プロジェクトルートに置くことで自動読み込みされる）

---

## 補足 / 注意点

- settings はプロパティアクセス時に環境変数の値を検証し、必須値がなければ ValueError を発生させます。CI やローカルで動作させる前に .env を適切に用意してください。
- init_schema() はテーブル定義をすべて作成します。既存テーブルがあっても安全（CREATE IF NOT EXISTS）に実行できますが、スキーマ変更は注意して行ってください。
- 本パッケージは「基盤」を提供するものであり、実際のデータ取得ロジック、戦略、発注処理（kabu API 連携等）は別途実装する必要があります。
- Python の型記法（X | Y）を使っているため Python 3.10 以上を想定しています。

---

必要であれば README を拡張して、具体的な .env.example、依存パッケージ一覧、開発フロー（テスト・Lint・CI 設定例）、サンプル戦略のテンプレートなども追加します。どの情報を追加しますか？