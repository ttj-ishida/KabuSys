# KabuSys

日本株自動売買システム用のコアライブラリ（プロトタイプ）。  
データプラットフォーム（DuckDB）スキーマ、環境設定、監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株に対する自動売買システムの基盤コンポーネント群です。本コードベースは主に以下を提供します。

- データレイク／データベース（DuckDB）用のスキーマ定義と初期化機能
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を保持する監査スキーマ
- 環境変数ベースの設定管理（.env 自動読み込み機能）
- 将来的な戦略・実行・モニタリング用の名前空間（パッケージ構成）

このリポジトリはライブラリ／モジュール群として利用し、戦略実装・発注ロジック・外部連携（kabuステーションや J-Quants、Slack 等）はこれらの上に実装します。

---

## 機能一覧

- DuckDB ベースのデータスキーマ初期化
  - Raw / Processed / Feature / Execution 層を含むテーブル群
  - 頻出クエリ向けインデックス定義
- 監査ログ（audit）モジュール
  - signal_events, order_requests, executions テーブル
  - 冪等キー（order_request_id / broker_execution_id 等）によるトレーサビリティ
  - すべての TIMESTAMP は UTC で保存（init 時に TimeZone を設定）
- 環境設定管理（kabusys.config.Settings）
  - .env / .env.local の自動ロード（プロジェクトルートを .git または pyproject.toml で特定）
  - 必須環境変数チェック（未設定時はエラー）
  - KABUSYS_ENV / LOG_LEVEL 等の検証
  - 自動ロードの無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD）
- パッケージ構造（strategy, execution, monitoring のための名前空間）

---

## 必要条件

- Python 3.10+
  - 型注釈に `X | Y` を使用しているため Python 3.10 以降を想定しています。
- duckdb Python パッケージ

インストール例:

```bash
# 仮想環境の作成（推奨）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 必要なパッケージをインストール
pip install duckdb
```

（プロジェクトに requirements.txt や pyproject.toml がある場合はそちらからインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン／配置する
2. Python 3.10+ の仮想環境を作成して有効化
3. 依存パッケージをインストール（最低限 duckdb）
4. プロジェクトルートに `.env` を配置（自動読み込みされる）

.env の自動読み込みについて:
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化できます
- 自動読み込みはパッケージファイル位置から上位ディレクトリをたどり `.git` または `pyproject.toml` が見つかったディレクトリをプロジェクトルートと見なして行います

.env の例（必要最低限のキー）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
# KABU_API_BASE_URL は省略可（デフォルト: http://localhost:18080/kabusapi）

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（省略時はデフォルト値）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境 / ログレベル
KABUSYS_ENV=development         # development | paper_trading | live
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

---

## 使い方

以下は主要な API の使用例です。

- 設定値を取得する

```python
from kabusys.config import settings

# 必須キーが未設定なら ValueError が発生します
token = settings.jquants_refresh_token
kabu_base = settings.kabu_api_base_url
is_live = settings.is_live
```

- DuckDB スキーマを初期化して接続を取得する

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# settings.duckdb_path は Path を返します（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)

# 以降 conn.execute("SELECT ...") などで DB を利用
```

- 監査ログテーブルを既存接続に追加する

```python
from kabusys.data.audit import init_audit_schema

# conn は init_schema() で得た接続
init_audit_schema(conn)
```

- 監査用に専用 DB を初期化する（単独で監査 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- メモリ内 DB を使う（テスト用）

```python
conn = init_schema(":memory:")
audit_conn = init_audit_db(":memory:")
```

注意点:
- init_schema() は冪等（既存テーブルはそのまま）です。
- init_audit_schema() は与えた接続に監査テーブルを追加します（UTC タイムゾーンを設定します）。
- order_requests テーブルには冪等キー（order_request_id）があり、再送による重複発注を防ぐ設計になっています。

---

## 環境変数（主なキー）

必須（Settings で _require が使われているもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意／デフォルト付き:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると自動 .env ロードを無効化)

---

## ディレクトリ構成

以下は本パッケージの主要ファイル構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理（.env 自動ロード含む）
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義・初期化（init_schema, get_connection）
      - audit.py               # 監査ログスキーマ（signal_events, order_requests, executions）
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
    - strategy/
      - __init__.py            # 戦略用名前空間（拡張ポイント）
    - execution/
      - __init__.py            # 発注／接続用名前空間（拡張ポイント）
    - monitoring/
      - __init__.py            # モニタリング用名前空間（拡張ポイント）

（実際のリポジトリではさらにファイルが追加される想定です。ここに示したのは現在の主要モジュールの一覧です。）

---

## 開発メモ / 注意事項

- Python の型注釈や一部ロジックは Python 3.10+ を想定しています。古い Python では動作しません。
- DuckDB の SQL 制約を多用しているため、スキーマ設計は比較的厳密です。既存データや移行時は注意してください。
- 監査ログは削除しない前提です（FOREIGN KEY は ON DELETE RESTRICT 等でデータ保持を想定）。
- .env パーサはシェル風の表記（export, quoted values, inline comments）にある程度対応していますが、複雑なケースは避けるか明示的に環境変数を設定してください。
- 自動 .env ロードはテスト時に影響する場合があるため、テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に環境を構築することを推奨します。

---

## 参考

- この README は現行のコードベース（src/kabusys 以下）を参照して作成しています。戦略・実行ロジックの実装はこのライブラリを利用して別モジュールに実装してください。