# KabuSys

日本株向け自動売買システムのコアライブラリ（プロトタイプ）。  
DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）と監査ログ（audit）を提供し、環境変数ベースの設定管理、取引戦略／発注／監視モジュールの雛形を含みます。

---

## プロジェクト概要

- 名前: KabuSys
- 目的: 日本株の自動売買に必要なデータ基盤（市場データ、財務データ、ニュース、特徴量）、発注・約定・ポジション管理、および監査ログを提供するライブラリ。
- 設計思想:
  - データは層 (Raw → Processed → Feature → Execution) に分離して保管。
  - 監査ログは発生したイベントを冪等かつトレース可能に保管（UUID ベースのチェーン）。
  - 環境変数(.env) を用いた設定管理。自動で .env / .env.local を読み込む機能あり（無効化可能）。

---

## 機能一覧

- 環境変数 / 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で特定）
  - export KEY=val、引用符やエスケープ、コメントに対応したパーサ
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_ENV / LOG_LEVEL のバリデーション
- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - init_schema(db_path) による初期化（冪等）
  - get_connection(db_path) による接続取得
- 監査ログ（data.audit）
  - signal_events, order_requests, executions を含む監査用テーブル定義とインデックス
  - init_audit_schema(conn) / init_audit_db(db_path)
  - タイムゾーンは UTC（監査テーブル初期化時に SET TimeZone='UTC' を実行）
- パッケージ構成の雛形
  - strategy / execution / monitoring 用のパッケージ骨子（拡張用）

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈に `X | Y` 構文を使用）
- pip が利用可能

1. リポジトリをクローン（またはソースを用意）
2. 必要パッケージをインストール（最低限 duckdb）
   - 開発時に editable インストールする想定:
     ```
     pip install -e .
     ```
   - 依存が明示されていない場合は最低限:
     ```
     pip install duckdb
     ```
3. 環境変数を準備
   - プロジェクトルートに `.env` または `.env.local` を置く。
   - 自動読み込みはデフォルトで有効。無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

.env（例 — 必須キー）
```
# J-Quants API
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス（省略時はデフォルト）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# システム
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

注意:
- .env のパースは export プレフィックス、引用符、エスケープ、コメントを考慮して行われます。
- OS 環境変数は .env より優先されます。.env.local は .env の上書き用に読み込まれます。

---

## 使い方（基本例）

設定読み込み:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print("env:", settings.env)
print("is_live:", settings.is_live)
```

DuckDB スキーマ初期化（メイン DB）:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path オブジェクト
# conn は duckdb.DuckDBPyConnection
```

監査ログの初期化（既存接続に追加）:
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # conn は init_schema で取得した接続
```

監査ログ専用 DB を作る:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

注意点:
- 初回は init_schema() でスキーマを作成してください。get_connection() は既存 DB への単なる接続取得です。
- 監査テーブルのタイムゾーンは UTC にセットされます。
- 環境 (KABUSYS_ENV) によって実行モード（本番 / ペーパー等）を切り替えてください。

---

## ディレクトリ構成

（リポジトリのルートに README.md 等がある想定。以下は src 内の構成抜粋）

```
src/
└─ kabusys/
   ├─ __init__.py            # パッケージ定義、バージョン
   ├─ config.py              # 環境変数 / 設定管理
   ├─ data/
   │  ├─ __init__.py
   │  ├─ schema.py           # DuckDB スキーマ定義・init_schema / get_connection
   │  └─ audit.py            # 監査ログ（signal_events, order_requests, executions）
   ├─ strategy/
   │  └─ __init__.py         # 戦略モジュール用のエントリ（拡張用）
   ├─ execution/
   │  └─ __init__.py         # 発注エンジン / broker 接続のエントリ（拡張用）
   └─ monitoring/
      └─ __init__.py         # 監視・監査用モジュール（拡張用）
```

---

## 追加情報 / 注意事項

- KABUSYS_ENV で許容される値:
  - development, paper_trading, live
- LOG_LEVEL は標準ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から行うため、CWD に依存しません。プロジェクト配布後も正しく動作するように設計されています。
- 監査ログは削除しない前提で設計され、FK は ON DELETE RESTRICT を使用します。
- order_requests テーブルは order_request_id を冪等キーとして二重発注防止を想定しています。

---

必要であれば、README に以下を追加できます:
- 開発フロー（テスト、Lint、CI）
- API ドキュメント（各テーブル・カラムの詳細）
- 具体的な戦略実装テンプレート
- 運用手順（ペーパートレード→本番切替、監査ログの参照方法）

追加したい項目があれば教えてください。