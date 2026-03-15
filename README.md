# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ（プロトタイプ）
バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株のデータ管理、特徴量生成、シグナル管理、発注・約定の監査ログを備えた自動売買システムのコアライブラリです。  
主に以下の目的を持ちます。

- 市場データ・ファンダメンタル・ニュース等の永続化（DuckDB）
- 日次・特徴量・AIスコア等の層別データ管理（Raw / Processed / Feature / Execution）
- 発注フローの監査ログ（UUID によるトレース）
- 環境変数を用いた設定管理

このリポジトリはライブラリ本体のスキーマ定義・設定読み込み・監査ログ等の基盤を提供します。実際のデータ取得、戦略、証券会社接続は各モジュール（strategy / execution 等）に実装します。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得 API（Settings クラス）
  - 環境（development / paper_trading / live）とログレベル検証
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - 頻出クエリ向けのインデックス作成
  - init_schema(db_path) による冪等な初期化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル群
  - 冪等キー（order_request_id / broker_execution_id）を想定
  - init_audit_schema(conn) / init_audit_db(path) を提供
- モジュール分割
  - data, strategy, execution, monitoring といった役割別パッケージ構成

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントで `|` を使用）
- pip が使用可能

1. リポジトリをクローン / ダウンロード
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv && source .venv/bin/activate
3. 依存のインストール
   - 最低限: duckdb
   - 例:
     - pip install duckdb
     - （パッケージとして配布する場合）pip install -e .

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` と/または `.env.local` を配置すると自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

推奨パッケージ例（requirements.txt を用意している場合）:
- duckdb

---

## 環境変数（.env）例

以下は必要となる代表的な環境変数（キー名はコード内定義）:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO

.env の簡単な例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意:
- 自動読み込みの優先順位は OS 環境変数 > .env.local > .env です。
- .env のパースは `export KEY=val`、引用符、インラインコメント等の基本的なパターンに対応します。

---

## 使い方（簡単なコード例）

以下は主要な API の利用例です。

- 設定値を取得する:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path  # Path オブジェクト
```

- DuckDB スキーマを初期化する（ファイル DB）:
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# conn は duckdb の接続オブジェクト。以降 SQL 実行可能。
```

- インメモリ DB を使う場合:
```python
conn = schema.init_schema(":memory:")
```

- 監査ログ用スキーマを既存接続に追加:
```python
from kabusys.data import audit

# 既存の DuckDB 接続 (schema.init_schema が返す conn 等)
audit.init_audit_schema(conn)
```

- 監査ログ用途に専用 DB を初期化:
```python
conn_audit = audit.init_audit_db("data/audit.duckdb")
```

これらの関数は冪等であり、既にテーブルが存在する場合はスキップします。

---

## ディレクトリ構成（主要ファイル説明）

リポジトリ内の主要なファイル / モジュール:

- src/kabusys/
  - __init__.py
    - パッケージメタ（__version__ 等）
  - config.py
    - 環境変数読み込み・Settings クラスを提供
    - 自動でプロジェクトルートを探索し .env/.env.local を読み込む
  - data/
    - __init__.py
    - schema.py
      - DuckDB のテーブル定義（Raw / Processed / Feature / Execution）と初期化関数:
        - init_schema(db_path)
        - get_connection(db_path)
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）の定義と初期化関数:
        - init_audit_schema(conn)
        - init_audit_db(db_path)
    - other data modules...
  - strategy/
    - __init__.py
    - （戦略関連コードを配置するための場所）
  - execution/
    - __init__.py
    - （発注・ブローカ連携ロジックを配置するための場所）
  - monitoring/
    - __init__.py
    - （監視・メトリクス関連を配置するための場所）

ファイル群の役割:
- schema.py は主要なデータモデル（DDL）を網羅しており、インデックスやテーブル作成順も管理しています。
- audit.py は発注フローのトレーサビリティを目的とした監査専用スキーマを提供します。
- config.py はプロジェクト配布後も動作するよう、__file__ を起点にプロジェクトルートを探索して環境変数を読み込みます。

---

## 注意点 / 補足

- タイムスタンプは監査ログ初期化時に UTC に固定される（audit.init_audit_schema は `SET TimeZone='UTC'` を実行）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を探して行います。CWD（カレントディレクトリ）に依存しません。
- 自動読み込みをテスト等で無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 実際の証券会社 API との接続や Slack 通知などの実装は本パッケージに含める想定ですが、現状は基盤（スキーマ・設定）を中心に実装されています。

---

もし README に追加したい情報（例えば、依存パッケージ一覧、CI 設定、開発ルール、テスト方法、実際の戦略テンプレートなど）があれば教えてください。必要に応じて追記します。