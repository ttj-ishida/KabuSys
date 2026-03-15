# KabuSys

日本株自動売買システムのコアライブラリ（内部モジュール群）の README。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けのコアコンポーネント群です。本リポジトリは以下の責務を持ちます。

- 市場データ・ファンダメンタル・ニュース等のデータレイヤを定義・永続化（DuckDB）
- 戦略／特徴量（Feature）層のためのスキーマ定義
- 発注・約定・ポジションなどの実行（Execution）層のスキーマと監査ログ
- 環境変数／設定管理（自動 .env 読み込み、バリデーション）
- 監査ログ（トレーサビリティ）用スキーマの初期化ユーティリティ

設計上、
- DuckDB を永続化／分析用のローカル DB として利用
- 監査ログは削除しない前提で設計（FK は ON DELETE RESTRICT）
- すべての TIMESTAMP は UTC で保存（監査スキーマ）

---

## 主な機能一覧

- 環境変数読み込み・管理（kabusys.config.Settings）
  - 自動的にプロジェクトルートの `.env` / `.env.local` を読み込む仕組み
  - 必須変数のチェック（例: JQUANTS_REFRESH_TOKEN 等）
  - 環境（development / paper_trading / live）とログレベルの検証
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを提供
  - インデックス作成、親ディレクトリ自動作成、メモリ DB 対応（":memory:"）
  - get_connection / init_schema API
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブルを定義
  - 冪等キー（order_request_id / broker_execution_id 等）の考慮
  - UTC タイムゾーン固定、インデックス作成
  - init_audit_schema / init_audit_db API

---

## 要求環境

- Python 3.10+
- 依存ライブラリ（最低限）:
  - duckdb
- 推奨: 仮想環境（venv / venvwrapper / poetry 等）

（詳細な requirements.txt / pyproject.toml はプロジェクト側の設定に従ってください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストールします（例: duckdb）。

   ```bash
   pip install duckdb
   # またはプロジェクトの pyproject / requirements を使う
   # pip install -e .
   ```

3. 環境変数を準備します。プロジェクトルート（.git または pyproject.toml のある親）に `.env` / `.env.local` を配置すると自動で読み込まれます（詳細は下記）。

---

## 環境変数 / 設定

kabusys.config.Settings が参照する主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN - J-Quants API 用のリフレッシュトークン
- KABU_API_PASSWORD - kabuステーション API のパスワード
- SLACK_BOT_TOKEN - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID - Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - 監視用 sqlite path（デフォルト: data/monitoring.db）
- KABUSYS_ENV - 実行環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL - ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）デフォルト: INFO

自動 .env 読み込み:
- プロジェクトルートが検出される場合、起動時に `.env` → `.env.local` の順で読み込みます。
- OS 環境変数は `.env` によって上書きされません（.env.local は上書き可能）。
- 自動ロードを無効化したい場合（テスト等）:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

.env の簡易テンプレート例:

```
# .env.example
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定値はアプリから以下のように取得できます:

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path
```

未設定の必須項目にアクセスすると ValueError が発生します。

---

## データベース（DuckDB）初期化と使い方

kabusys.data.schema にスキーマ初期化関数が用意されています。

- 全スキーマを初期化して接続を取得する:

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

- 既存 DB へ接続する（スキーマ初期化は行わない）:

```python
conn = schema.get_connection("data/kabusys.duckdb")
```

- 監査ログ用スキーマ（signal_events, order_requests, executions）を既存接続に追加する:

```python
from kabusys.data import audit
audit.init_audit_schema(conn)
```

- 監査ログ専用 DB を新規に作る:

```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

注意:
- init_schema / init_audit_db は冪等（既存テーブルはスキップ）です。
- ファイルパスの親ディレクトリが存在しない場合、自動で作成します。
- ":memory:" を指定するとインメモリ DB を使用します（テスト時に便利）。

---

## サンプルコード

環境設定の確認と DB 初期化の簡易スクリプト例:

```python
from kabusys.config import settings
from kabusys.data import schema, audit

print("env:", settings.env)
print("duckdb path:", settings.duckdb_path)

# メイン DB 初期化
conn = schema.init_schema(settings.duckdb_path)

# 監査ログテーブルを追加
audit.init_audit_schema(conn)
```

---

## 開発・テスト時のヒント

- 自動で .env を読み込ませたくない場合:
  - 起動前に `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1`（Unix）または Windows では適宜環境変数を設定してください。
- 型システム・文法上、Python 3.10+ の型アノテーション（`Path | None` など）を使用しています。環境は Python 3.10 以上を推奨します。

---

## ディレクトリ構成

リポジトリの主要なファイル・ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py      - パッケージ初期化、__version__ = "0.1.0"
  - config.py        - 環境変数／設定管理（Settings クラス、自動 .env 読み込み）
  - data/
    - __init__.py
    - schema.py      - DuckDB スキーマ定義・init_schema / get_connection
    - audit.py       - 監査ログ（signal_events / order_requests / executions）、init_audit_schema / init_audit_db
    - audit.py は監査用の独立スキーマを追加するユーティリティを提供
    - (その他データ関連モジュール)
  - strategy/
    - __init__.py     - 戦略関連モジュール（未実装スタブ）
  - execution/
    - __init__.py     - 発注/実行関連（未実装スタブ）
  - monitoring/
    - __init__.py     - 監視用モジュール（未実装スタブ）

DuckDB スキーマは層構造（Raw / Processed / Feature / Execution）で定義されています。監査ログは別途初期化可能です。

---

必要であれば README に含める追加情報（CI、テスト方法、ライセンス、依存パッケージ一覧、より詳細な .env.example、開発フローなど）を追記できます。どの情報を追加しますか？