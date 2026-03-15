# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けのコアライブラリです。市場データの保存（DuckDB）、特徴量抽出、シグナル管理、発注・約定監査ログなどを扱うためのスキーマ定義および設定管理を提供します。

主にライブラリとして他の戦略・実行コンポーネントから利用されることを想定しています。

---

## 主な機能

- 環境変数 / .env ファイルの自動読み込み（プロジェクトルート検出）
  - 優先順位: OS環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能
- アプリケーション設定ラッパー（settings）
  - 必須・任意の環境変数をプロパティとして提供
  - 環境（development / paper_trading / live）やログレベルの検証
- DuckDB 用のデータスキーマ定義
  - Raw / Processed / Feature / Execution 層のテーブル群を定義
  - インデックス定義、冪等（id）や制約を含むDDL
  - init_schema() で簡単に初期化できる（:memory: も可）
- 監査用スキーマ（トレーサビリティ）
  - signal_events, order_requests, executions の監査テーブル
  - 冪等キー、ステータス管理、UTC タイムゾーン保存ポリシー
  - init_audit_schema()/init_audit_db() による初期化

---

## 必須（および主要）環境変数

下記は Settings クラス内で必須として取得されるキーの例です（未設定時は ValueError を送出します）。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)

その他の設定（任意またはデフォルトあり）:

- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）

サンプル .env（README 用例）
```
# .env.example
JQUANTS_REFRESH_TOKEN="your-jquants-refresh-token"
KABU_API_PASSWORD="your-kabu-api-password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"

# 任意
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
KABU_API_BASE_URL=http://localhost:18080/kabusapi
```

.env のパースについて:
- export KEY=val 形式をサポート
- シングル/ダブルクォート内はエスケープ処理を考慮して読み込み
- クォートなしの場合、コメント（#）は直前がスペースまたはタブのときのみコメント扱い

---

## セットアップ手順

前提:
- Python 3.8+（型注釈に Path | None 等を使用）
- pip が利用可能

1. リポジトリをクローン / 取得

2. 仮想環境を作成（任意）
```
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

3. 必要なパッケージをインストール（最低限）
```
pip install duckdb
```
（実際のプロジェクトでは他に依存パッケージがある可能性があります。パッケージ配布用の pyproject.toml / requirements.txt があればそちらを利用してください）

4. 環境変数を設定
- プロジェクトルートに .env または .env.local を配置
- もしくは OS 環境変数として設定

自動の .env 読み込みを無効にする場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（基本例）

- settings の利用例:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token  # 未設定だと ValueError
base_url = settings.kabu_api_base_url
if settings.is_live:
    print("本番モードです")
```

- DuckDB スキーマの初期化:
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# デフォルトパスを使う場合
db_path = settings.duckdb_path  # Path オブジェクト
conn = init_schema(db_path)     # テーブルをすべて作成して接続を返す

# メモリ内 DB を使う場合
conn_mem = init_schema(":memory:")

# 既存 DB に接続するだけなら
conn2 = get_connection(db_path)
```

- 監査ログ（Audit）スキーマの初期化:
```python
from kabusys.data.audit import init_audit_schema, init_audit_db

# 既存の DuckDB 接続に追加する場合
init_audit_schema(conn)  # conn は init_schema() で得た接続など

# 監査専用 DB を作る場合
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- init_schema/init_audit_schema は冪等（既存テーブルは変更しない）なので何度呼んでも安全です。
- init_audit_schema は接続に対して "SET TimeZone='UTC'" を実行し、TIMESTAMP を UTC として扱うことを要求します。

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル・パッケージ構成は次のようになっています（提供されたコードに基づく）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数 / 設定管理
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
      - audit.py               # 監査ログ（信号→発注→約定のトレーサビリティ）
      - audit.py
      - audit.py
      - audit.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（実際のリポジトリでは tests、cli、docs などが追加される可能性があります）

---

## 補足 / 設計上のポイント

- データレイヤーは 3 層（Raw → Processed → Feature）＋Execution 層で設計されており、パイプラインの各段階で永続化を行います。
- 監査ログは UUID 連鎖でシグナル発生から最終約定までのトレーサビリティを保証します。order_request_id は冪等キーとして機能し、二重発注を防ぎます。
- スキーマには多くの CHECK 制約とインデックスが定義され、データ整合性と問い合わせ性能を考慮しています。
- settings の検証により、実行時の設定ミス（無効な KABUSYS_ENV や LOG_LEVEL 等）を早期に検出します。

---

必要に応じて、README に加える情報（インストール用の pyproject.toml 説明、CI / テスト実行方法、具体的な SQL クエリ例、戦略開発のガイドライン等）を指定してください。