# KabuSys

日本株自動売買システムのコアライブラリ（初期バージョン）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を支える内部ライブラリ群です。データ収集・保存（DuckDB）、特徴量生成、シグナル管理、発注監査ログ（トレーサビリティ）のためのスキーマとユーティリティを提供します。外部 API（J-Quants、kabuステーション等）や Slack 通知と連携するための設定管理も含まれます。

設計上のポイント:
- DuckDB を用いた3層（Raw / Processed / Feature）＋ Execution 層のデータモデル
- 発注から約定までの監査ログ（UUIDチェーン）を別モジュールで管理
- .env ファイルと環境変数による柔軟な設定

---

## 主な機能一覧

- 環境設定読み込み・管理（settings）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可能）
  - 必須設定は取得時にエラーを出す（例: JQUANTS_REFRESH_TOKEN 等）
  - 環境モード（development / paper_trading / live）とログレベル検証

- DuckDB スキーマ初期化（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - init_schema(db_path) で全テーブルを冪等に作成
  - get_connection(db_path) で既存 DB に接続

- 監査ログ（data.audit）
  - signal_events / order_requests / executions など、発注フローの完全トレース用テーブル
  - init_audit_schema(conn) で既存接続に監査テーブルを追加
  - init_audit_db(db_path) で監査専用 DB を初期化して接続を返す
  - すべての TIMESTAMP は UTC で保存されるように設定

- （骨組み）strategy、execution、monitoring 用のパッケージプレースホルダ

---

## セットアップ手順

前提:
- Python 3.9+（typing | Path 型注釈でのユニオン等を使用）
- pip が利用可能

1. リポジトリをクローン / パッケージを配置
2. 依存パッケージをインストール
   - requirements.txt が用意されている場合:
     ```
     pip install -r requirements.txt
     ```
   - 必要最小限（DuckDB）のみ手動で:
     ```
     pip install duckdb
     ```
3. 開発インストール（任意）
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を置くと自動読み込みされます。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（代表例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト有り
     - KABUS_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

.env のパース挙動（主なポイント）:
- コメント行は `#` または先頭の `#` で無視
- `export KEY=val` 形式をサポート
- 値をシングル/ダブルクォートで囲んだ場合はエスケープを考慮して閉じクォートまでを値として扱う
- クォートなしの場合、`#` の直前がスペース/タブなら以降をコメントとして扱う

---

## 使い方（簡易ガイド）

1. settings を使って設定を参照する
```python
from kabusys.config import settings

token = settings.jquants_refresh_token  # 未設定なら ValueError
db_path = settings.duckdb_path
```

2. DuckDB スキーマを初期化して接続を得る
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリを自動作成）
conn = init_schema(settings.duckdb_path)

# またはインメモリ DB
conn_mem = init_schema(":memory:")
```

3. 既存 DB に接続する（スキーマの初期化は行わない）
```python
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
```

4. 監査ログを既存接続に追加する
```python
from kabusys.data.audit import init_audit_schema

# init_schema で得た conn を渡す
init_audit_schema(conn)
```

5. 監査専用 DB を初期化する（独立させたい場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意:
- init_schema / init_audit_schema は冪等（既存のテーブルがあればスキップ）です。
- init_audit_schema は実行時に `SET TimeZone='UTC'` を行い、TIMESTAMP を UTC で扱います。

---

## 設定項目の一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live、デフォルト: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動ロードを無効化

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py               # パッケージメタ（__version__=0.1.0）
    - config.py                 # 環境変数 / 設定管理（自動 .env ロード・Settings）
    - data/
      - __init__.py
      - schema.py               # DuckDB スキーマ定義、init_schema, get_connection
      - audit.py                # 監査ログ（signal_events / order_requests / executions）
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
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
      - __init__.py             # 戦略モジュールのプレースホルダ
    - execution/
      - __init__.py             # 発注/ブローカー連携のプレースホルダ
    - monitoring/
      - __init__.py             # モニタリングのプレースホルダ

（注）リポジトリの実際のファイル数や追加モジュールにより構成は変わります。上記は提供されたコードベースに基づく主要ファイルの一覧です。

---

## 開発・運用時の補足

- テストや CI で .env 自動読み込みを妨げたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のファイルパスに `:memory:` を与えるとインメモリ DB を使用します（テストや一時実行に便利）。
- 監査ログは削除しない前提の設計（ON DELETE RESTRICT 等）です。運用時のデータ保持ポリシーに注意してください。
- KABUSYS_ENV による挙動切替（開発・ペーパー・本番）を想定しています。実運用では is_live 等プロパティを使用して安全制御を入れてください。

---

## ライセンス / 貢献

（ここにプロジェクトのライセンスや貢献方法を記載してください。コードベースに指定がない場合は適切なライセンスを追加することを推奨します）

---

不明点や README に追加したいサンプル（戦略の実装例や監査ログの参照クエリなど）があれば教えてください。必要に応じて具体例を追加します。