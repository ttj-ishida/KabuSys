# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買システムのコアライブラリです。市場データ取得から特徴量整備、シグナル生成、発注・約定の監査ログまでを扱うデータ層・実行層の基盤を提供します。

## 概要
- DuckDB を用いたローカルデータベーススキーマ（Raw / Processed / Feature / Execution 層）を定義・初期化します。
- 発注〜約定に関する監査ログ（トレーサビリティ）用のスキーマも提供します。
- 環境変数管理（.env の自動読み込み、必須設定の検証）を行います。
- 実際の戦略・実行・監視モジュールのためのパッケージ構成を備えています（strategy、execution、monitoring はプレースホルダ）。

## 主な機能一覧
- 環境設定管理
  - .env / .env.local の自動読み込み（OS 環境変数が最優先）
  - 必須環境変数の取得と検証（例: JQUANTS_REFRESH_TOKEN、SLACK_BOT_TOKEN）
  - KABUSYS_ENV / LOG_LEVEL の値検証（有効値を限定）
  - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）
- DuckDB スキーマ管理
  - data.schema.init_schema(db_path) による一括テーブル作成（冪等）
  - get_connection(db_path) で既存 DB に接続
  - 多層（Raw / Processed / Feature / Execution）のテーブル DDL とインデックス
- 監査ログ（トレーサビリティ）
  - data.audit.init_audit_schema(conn) による監査テーブル追加（冪等）
  - 監査用専用 DB を作る init_audit_db(db_path)
  - 発注要求（冪等キー）、約定ログ等を含む堅牢な設計

## 動作環境（推奨）
- Python 3.10 以上（型注釈に | を使用しているため）
- duckdb（DuckDB Python パッケージ）

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install duckdb
   - パッケージを開発モードでインストールする場合:
     - pip install -e .

   （プロジェクトに requirements ファイルがある場合はそれを使用してください）

4. 環境変数を設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと、自動的にロードされます。
   - 自動ロードを停止したい場合は環境変数を設定:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必須環境変数（.env の例）
   - 以下を参考に .env を作成してください（値は適宜置き換え）。

例: .env.example
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
# KABU_API_BASE_URL は省略可（デフォルト: http://localhost:18080/kabusapi）
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development   # (development | paper_trading | live)
LOG_LEVEL=INFO
```

## 使い方（簡単な例）

- 環境設定の取得
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
base_url = settings.kabu_api_base_url
print(settings.env, settings.log_level)
```

- DuckDB スキーマの初期化（ファイル DB）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path 型を返します
conn = init_schema(settings.duckdb_path)
# conn を使ってクエリ実行
conn.execute("SELECT count(*) FROM prices_daily").fetchall()
```

- DuckDB をメモリで初期化（テスト用）
```python
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")
```

- 監査ログスキーマを既存接続に追加
```python
from kabusys.data.audit import init_audit_schema
# conn: duckdb connection（init_schema の戻り値など）
init_audit_schema(conn)
```

- 監査用専用 DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

- 自動 .env 読み込みの挙動
  - プロジェクトルートの検出は、モジュールファイルの親ディレクトリを起点に `.git` または `pyproject.toml` が見つかったディレクトリをプロジェクトルートとみなします（CWD に依存しません）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - `.env` のパースは `export KEY=val`、クォート、インラインコメント等に対応しています。

## 主要 API（要点）
- kabusys.__version__ — パッケージバージョン（0.1.0）
- kabusys.config.settings — 設定オブジェクト
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev
- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection（全テーブル作成）
  - get_connection(db_path) -> duckdb connection（スキーマ初期化なし）
- kabusys.data.audit
  - init_audit_schema(conn) — 既存接続に監査テーブルを追加
  - init_audit_db(db_path) -> duckdb connection（監査専用 DB 初期化）

## ディレクトリ構成
以下は主要ファイルのみを抜粋した構成例です。

```
src/
└─ kabusys/
   ├─ __init__.py            # パッケージ定義（__version__, __all__）
   ├─ config.py              # 環境変数・設定管理
   ├─ data/
   │  ├─ __init__.py
   │  ├─ schema.py           # DuckDB スキーマ定義 / init_schema / get_connection
   │  └─ audit.py            # 監査ログスキーマ（order_requests / executions 等）
   ├─ strategy/
   │  └─ __init__.py         # 戦略用パッケージ（プレースホルダ）
   ├─ execution/
   │  └─ __init__.py         # 実行層パッケージ（プレースホルダ）
   └─ monitoring/
      └─ __init__.py         # 監視・メトリクス（プレースホルダ）
```

## 注意事項 / 実装上のポイント
- Python の型注釈で PEP 604 の `|` を使用しているため Python 3.10 以上を想定しています。
- init_schema / init_audit_schema は冪等（既存テーブルがある場合はスキップ）です。DB パスの親ディレクトリが存在しない場合は自動で作成されます。
- 監査ログのタイムゾーンは UTC に揃える設計です（init_audit_schema 内で `SET TimeZone='UTC'` を実行します）。
- order_requests は冪等キー（order_request_id）を持ち、limit/stop/market のチェック制約が付与されています。
- 環境変数の自動読み込みは便利ですが、テストや CI で不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

この README は現在のコードベース（データスキーマ、監査スキーマ、設定ロード周り）に基づく導入・使用ガイドです。戦略・実行のビジネスロジックや外部 API 呼び出しの実装は各モジュールに追加していく想定です。必要であれば、セットアップの CI やサンプル戦略、発注フローの具体例などの追記も対応します。