# KabuSys

日本株自動売買システムのコアライブラリ（モジュール群）。データ収集・スキーマ管理、戦略・特徴量管理、発注・監査ログの基盤を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買プラットフォーム向けに設計された内部ライブラリです。本リポジトリは以下の役割を持ちます。

- データの永続化（DuckDB）用スキーマ定義と初期化
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマ
- 環境変数／設定管理（自動 .env ロード、必須値チェック）
- 戦略、発注、モニタリングのためのパッケージ骨組み

注：戦略（strategy）、発注（execution）、モニタリング（monitoring）パッケージは骨組みを提供します。実際の戦略ロジックや API クライアントは別途実装してください。

---

## 主な機能一覧

- 環境変数の読み込みと型チェック（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（.git または pyproject.toml を検出）
  - 必須環境変数の検査（未設定で ValueError）
  - 環境種別（development, paper_trading, live）とログレベルの検証
  - 自動読み込みを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .env のパースはクォート、エスケープ、インラインコメント等に対応

- DuckDB 用スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層データ設計
  - 各種テーブルの DDL を定義（銘柄別終値、財務、ニュース、特徴量、シグナル、注文、約定、ポジションなど）
  - インデックス作成、親ディレクトリの自動作成、":memory:" のサポート
  - API:
    - init_schema(db_path) → DuckDB 接続（スキーマ初期化：冪等）
    - get_connection(db_path) → 既存 DB へ接続（スキーマは作成しない）

- 監査ログ（kabusys.data.audit）
  - シグナル→発注要求→約定の監査テーブル定義
  - 冪等キー（order_request_id）や broker 提供の約定 ID を扱う設計
  - UTC タイムゾーンに固定して TIMESTAMP を保存
  - API:
    - init_audit_schema(conn) → 既存の DuckDB 接続に監査テーブルを追加
    - init_audit_db(db_path) → 監査専用 DB を初期化して接続を返す

---

## 必要条件

- Python 3.10+
  - ソース内で PEP 604（| を用いた型注釈）などを使っているため 3.10 以上を想定しています。
- 依存パッケージ（最低限）
  - duckdb

インストール例:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb
```

プロジェクトを開発モードでインストールする場合（setup がある前提）:
```bash
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／配置する

2. Python と依存パッケージをインストール
   - 例: pip install duckdb

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` を置くと自動で読み込まれます。
   - `.env.local` を配置すると `.env` を上書き（ただし OS 環境変数は保護される）します。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   その他オプション:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化

5. データベース初期化（DuckDB）
   - デフォルトの DuckDB パスは `data/kabusys.duckdb`（設定 `DUCKDB_PATH` で変更可）
   - 監査用 DB を分離する場合は別 path を使用

---

## .env の例

.env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_api_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
SQLITE_PATH="data/monitoring.db"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意点:
- export プレフィックス（export KEY=val）にも対応
- シングル／ダブルクォートとエスケープを考慮してパースされます
- インラインコメントはスペース直前の # をコメントとみなします（詳細は実装のパーサ参照）

---

## 使い方（簡単なコード例）

設定の参照:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token  # 必須値（未設定なら ValueError）
print(settings.env, settings.is_live, settings.log_level)
```

DuckDB スキーマを初期化して接続を得る:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path を返す
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

既存 DB へ接続する（スキーマ初期化は行わない）:
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

監査ログテーブルを既存接続に追加:
```python
from kabusys.data.audit import init_audit_schema

# conn は init_schema() による接続など
init_audit_schema(conn)
```

監査専用 DB を新規作成して初期化:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

発注・戦略・監視の流れはこのライブラリのスキーマを利用して実装します。シグナルを保存し、order_requests を登録、broker 返信（約定）を executions に入れる、という監査チェーンを踏襲してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義・初期化
      - audit.py               # 監査ログ（シグナル→発注→約定）
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
    - strategy/
      - __init__.py            # 戦略パッケージの骨組み
    - execution/
      - __init__.py            # 発注／ブローカー連携の骨組み
    - monitoring/
      - __init__.py            # モニタリング用の骨組み

（リポジトリルート）
- .env.example (想定)         # .env の雛形（プロジェクトに追加することを推奨）
- pyproject.toml / setup.cfg 等（プロジェクト構成ファイル、存在する場合はプロジェクトルート判定に使われる）

---

## 実運用時の注意点・設計上の指針

- 監査ログは削除しない設計です（監査性を重視）。FK は ON DELETE RESTRICT を基本としています。
- すべての TIMESTAMP は UTC で保存するようにしています（audit.init_audit_schema は `SET TimeZone='UTC'` を実行）。
- order_request_id を冪等キーとして扱うことで再送による二重発注を防止する設計です。
- .env の自動読み込みは便利ですが、CI／テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うことを検討してください。
- KABUSYS_ENV を "live" に設定すると実運用モード扱いになります（is_live プロパティで判定可能）。紙上取引（paper_trading）モードや開発モードでの挙動切替をアプリ側で実装してください。

---

必要であれば、README に環境変数の詳細説明（各変数の用途やサンプル値）や、duckdb によるクエリ例、監査ログの具体的な利用例（シグナル登録→order_requests→executions の一連操作）なども追加できます。どの情報をさらに詳しく載せたいか教えてください。