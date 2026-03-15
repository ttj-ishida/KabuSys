# KabuSys

日本株向けの自動売買基盤ライブラリ（初期バージョン）
バージョン: 0.1.0

このリポジトリは、データレイヤ（Raw / Processed / Feature / Execution）と監査ログを含む DuckDB スキーマ管理、環境設定の読み込みロジック、及び自動売買に必要な設定インターフェースを提供します。実際の戦略実装、発注インターフェース、外部連携は別モジュール（strategy / execution / monitoring 等）で実装することを想定しています。

---

## 主な機能

- 環境設定管理
  - .env / .env.local の自動読み込み（OS 環境変数を優先）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証

- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution の4層に分かれたテーブル群を定義・作成
  - 典型的なインデックスを自動作成
  - init_schema(db_path) による冪等な初期化
  - get_connection(db_path) による接続取得

- 監査ログ（data.audit）
  - シグナル → 発注要求 → 約定 までをトレースする監査テーブル群
  - 冪等キー（order_request_id）や broker_execution_id を扱う設計
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化
  - すべての TIMESTAMP を UTC で保存する設定をサポート

---

## セットアップ手順

前提:
- Python 3.10+（型注釈で `|` を使っているため）
- 任意の仮想環境（venv / pyenv 等）

1. リポジトリをクローンして仮想環境を作成・有効化
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   - このコードベースで明示的に使われている外部依存は `duckdb` のみです:
   ```
   pip install duckdb
   ```
   - （プロジェクトをパッケージとして使う場合は pyproject.toml / setup.py があれば `pip install -e .` を利用してください）

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（.git または pyproject.toml を探索してプロジェクトルートを検出）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   サンプル（.env）:
   ```
   JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
   KABU_API_PASSWORD="your_kabu_api_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   # 任意
   DUCKDB_PATH="data/kabusys.duckdb"
   SQLITE_PATH="data/monitoring.db"
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

- 設定オブジェクトを取得する:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path  # Path オブジェクト
```

- DuckDB スキーマを初期化する（ファイル DB またはメモリ）:
```python
from kabusys.data.schema import init_schema, get_connection

# ファイル DB を初期化して接続を取得
conn = init_schema("data/kabusys.duckdb")

# またはインメモリ
mem_conn = init_schema(":memory:")

# 既存 DB へ接続のみ（スキーマ初期化は行わない）
conn2 = get_connection("data/kabusys.duckdb")
```

- 監査ログテーブルを既存接続に追加:
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # conn は duckdb 接続
```

- 監査専用 DB を初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- init_schema / init_audit_schema は冪等（存在するテーブルは作成しない）です。
- init_audit_schema は実行時に `SET TimeZone='UTC'` を実行し、監査用 TIMESTAMP を UTC で保存するようにします。

---

## 環境変数の自動読み込み挙動

- 検索されるプロジェクトルートは、現在ファイルの親階層から `.git` または `pyproject.toml` を探索して決定します。プロジェクトルートが見つからない場合は自動ロードをスキップします。
- 読み込み順序（優先度高 → 低）:
  1. OS 環境変数
  2. .env.local （存在すれば上書き）
  3. .env
- `.env` のパーシング:
  - コメント行や空行をスキップ
  - export KEY=val 形式に対応
  - シングルクオート / ダブルクオートを扱い、バックスラッシュエスケープ対応
  - クォート無しの場合、直前がスペース／タブの `#` をコメント開始とみなす
- 自動ロードを無効化する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py                 : パッケージ定義（version 等）
  - config.py                   : 環境変数・設定管理
  - data/
    - __init__.py
    - schema.py                 : DuckDB のスキーマ定義・初期化（init_schema, get_connection）
    - audit.py                  : 監査ログ（signal / order_request / execution）定義・初期化
    - (その他: audit.py に対応するテーブル・インデックス定義)
  - strategy/
    - __init__.py               : 戦略モジュールのプレースホルダ
  - execution/
    - __init__.py               : 発注実行モジュールのプレースホルダ
  - monitoring/
    - __init__.py               : 監視系モジュールのプレースホルダ

その他:
- .env / .env.local（プロジェクトルートに配置して自動読み込み）
- pyproject.toml / requirements.txt（このリポジトリでは未提示。ただし duckdb が必要）

---

## 備考 / 今後の拡張点

- strategy / execution / monitoring パッケージはプレースホルダです。実際の売買ロジック・ブローカー連携・監視ロジックはこれらに実装してください。
- 外部 API（J-Quants, kabuステーション, Slack 等）のクライアント実装は含まれていませんが、config の settings を利用してトークン等を渡す設計です。
- 単体テスト実行時は自動 .env ロードを無効にすることで環境依存を排除できます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

必要であれば、README に含める .env.example のテンプレート作成、初期化スクリプト（簡易 CLI）の追加、pip パッケージ化手順の追記なども対応します。どの情報を追加したいか教えてください。