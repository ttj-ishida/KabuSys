KabuSys
=======

日本株自動売買を想定した軽量フレームワーク（ライブラリ）です。  
データレイヤ（DuckDB スキーマ）、監査ログ、環境設定、戦略・発注・モニタリングのための骨組みを提供します。

プロジェクト概要
--------------
KabuSys は日本株の自動売買システムを構築するための基盤モジュール群を提供します。  
主に以下を備えています。

- DuckDB を利用したデータスキーマ（Raw / Processed / Feature / Execution 層）
- 監査ログ用スキーマ（シグナル → 発注要求 → 約定のトレーサビリティ）
- 環境変数ベースの設定管理（.env/.env.local の自動ロード機能）
- strategy / execution / monitoring といったサブパッケージのプレースホルダ

機能一覧
--------
- data.schema.init_schema(db_path): DuckDB データベースの初期化（全テーブル作成）
- data.schema.get_connection(db_path): 既存 DuckDB への接続取得（初期化は行わない）
- data.audit.init_audit_schema(conn): 既存接続へ監査ログテーブルを追加
- data.audit.init_audit_db(db_path): 監査ログ専用 DB を作成して接続を返す
- config.Settings: 環境変数から設定を取得する高レベル API（必須変数は取得時にチェック）
- 環境変数の自動ロード: プロジェクトルートの .env を自動読み込み、.env.local が .env を上書き

動作環境（推奨）
----------------
- Python 3.10 以上（型ヒントに PEP 604 の表記を使用）
- duckdb（DuckDB Python パッケージ）
- その他、利用する外部 API クライアント（J-Quants / kabuステーション / Slack 等）は別途導入

セットアップ手順
---------------
1. リポジトリをクローン／取得
   - 開発時: pip install -e . を推奨（セットアップツールに依存します）

2. 仮想環境を作成・アクティベート（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール（例）
   - pip install duckdb

   （プロジェクトの配布方法に合わせて requirements または pyproject.toml を使用してください）

4. 環境変数の準備
   - プロジェクトルートに .env を用意してください（.env.example を参照する想定）。  
   - 自動ロードはデフォルトで有効です（.env を読み込み、.env.local があれば上書き）。  
   - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（config.Settings が参照）
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API のパスワード
  - SLACK_BOT_TOKEN       : Slack ボットトークン
  - SLACK_CHANNEL_ID      : Slack チャネル ID
- 任意（デフォルトあり）
  - KABUSYS_ENV           : 実行環境 (development | paper_trading | live)。デフォルト: development
  - LOG_LEVEL             : ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)。デフォルト: INFO
  - KABU_API_BASE_URL     : kabuAPI のベース URL。デフォルト: http://localhost:18080/kabusapi
  - DUCKDB_PATH           : DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
  - SQLITE_PATH           : SQLite（モニタリング用）パス。デフォルト: data/monitoring.db

.env の自動ロード挙動（補足）
- プロジェクトルートは __file__ を起点に .git または pyproject.toml を探して決定します（CWD に依存しない）。
- 読み込み順序: OS 環境変数 > .env.local > .env
- .env のパースはシェル風の簡易パーサを実装。引用符、エスケープ、行末コメント（条件付き）に対応。

使い方（簡易例）
----------------

1) 設定の参照
- settings オブジェクトから各種値を取得できます。

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
db_path = settings.duckdb_path  # Path オブジェクト
if settings.is_live:
    print("LIVE モードで動作中")
```

2) DuckDB スキーマの初期化（全テーブルを作成）
- 初めて DB を作る際は init_schema を使います（冪等）。parent ディレクトリがなければ自動作成されます。

```python
from kabusys.data import schema
from pathlib import Path

db_path = Path("data/kabusys.duckdb")
conn = schema.init_schema(db_path)
# conn は duckdb.DuckDBPyConnection
```

- メモリ上 DB を使う場合:
```python
conn = schema.init_schema(":memory:")
```

3) 既存 DB への接続
```python
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
```

4) 監査ログスキーマの初期化（既存接続へ追加）
```python
from kabusys.data import audit, schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema で初期化済みの接続
audit.init_audit_schema(conn)
```

または監査専用 DB を作る:
```python
conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

ディレクトリ構成
----------------
（リポジトリの src 配下を基準にした主要ファイル / モジュール）

- src/
  - kabusys/
    - __init__.py                 # パッケージ初期化（__version__, __all__）
    - config.py                   # 環境変数・設定管理（Settings）
    - data/
      - __init__.py
      - schema.py                 # DuckDB スキーマ定義・初期化（init_schema / get_connection）
      - audit.py                  # 監査ログスキーマ（init_audit_schema / init_audit_db）
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
    - strategy/
      - __init__.py               # 戦略関連モジュール（プレースホルダ）
    - execution/
      - __init__.py               # 発注関連（プレースホルダ）
    - monitoring/
      - __init__.py               # モニタリング関連（プレースホルダ）

（注）README 用に簡略化しています。実プロジェクトでは strategy / execution / monitoring に具体的なモジュールが入ります。

設計上のポイント・注意事項
-------------------------
- data.schema.init_schema は冪等であり、既存テーブルがある場合は変更しません。
- 監査ログは削除しないことを前提に設計されており、外部キーは ON DELETE RESTRICT を用いています。
- 監査ログのタイムスタンプは UTC で記録されます（init_audit_schema 内で TimeZone を設定）。
- order_requests テーブルは order_request_id を冪等キーとして想定しており、再送に対する安全性を担保します。
- .env の自動ロードは便利ですが、テスト環境や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して無効化できます。

次のステップ（開発者向け提案）
-----------------------------
- strategy 層に具体的なシグナル生成ロジックを実装する
- execution 層でブローカー API（kabuステーション等）との接続処理を実装する
- monitoring 層で SQLite / Prometheus / Slack 通知の連携を追加する
- CI / テスト環境向けに KABUSYS_DISABLE_AUTO_ENV_LOAD を用いたテストケース準備

ライセンス / コントリビュート
-----------------------------
本 README では省略しています。実際のリポジトリでは LICENSE ファイル、貢献手順を追加してください。

お問い合わせ・補足
-------------------
追加で README に書きたい内容（例: サンプル戦略、マイグレーション手順、運用手順、 .env.example のテンプレートなど）があれば教えてください。README を拡張して作成します。