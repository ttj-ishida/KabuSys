# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（ミニマム実装）。  
データレイヤ（Raw / Processed / Feature / Execution）、監査ログ、環境設定管理を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムに必要なデータスキーマ、環境設定、監査ログ機構をまとめたパッケージです。  
主に以下を提供します。

- DuckDB ベースのデータスキーマ（Raw / Processed / Feature / Execution）
- 発注・約定に関する監査ログ（冪等キー・ステータス管理付き）
- 環境変数（.env）を扱う Settings ラッパー
- 各種初期化ユーティリティ（スキーマの生成、接続取得）

このリポジトリはライブラリ部分の骨格を提供しており、実際のデータ取得・戦略実装・ブローカー連携等はユーザー側で実装します。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動ロード（プロジェクトルートは .git または pyproject.toml により決定）
  - 必須設定値の取得（例: JQUANTS_REFRESH_TOKEN 等）
  - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）

- DuckDB スキーマ（data.schema）
  - Raw / Processed / Feature / Execution のテーブルを定義・初期化
  - 頻出クエリに合わせたインデックス作成
  - init_schema(db_path) で冪等的に初期化

- 監査ログ（data.audit）
  - signal_events / order_requests / executions を定義
  - order_request_id（冪等キー）による二重発注防止
  - UTC タイムスタンプ保存の設定
  - init_audit_schema(conn) / init_audit_db(db_path)

- モジュール分割
  - data, strategy, execution, monitoring といった領域別パッケージ構成（拡張しやすい）

---

## セットアップ手順

前提
- Python 3.8+（`from __future__ import annotations` を使用）
- pip が利用できる環境

1. リポジトリをクローン / 作業ディレクトリへ移動

2. 依存ライブラリ（最小）
   - duckdb

   例:
   ```
   pip install duckdb
   ```

   （プロジェクト配布形態に応じて `pip install -e .` 等を利用してください）

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` と `.env.local` を置けます。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (省略可、デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (省略可、デフォルト: data/monitoring.db)
   - KABUSYS_ENV (省略可、デフォルト: development) — 有効値: development, paper_trading, live
   - LOG_LEVEL (省略可、デフォルト: INFO) — 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

   .env のフォーマットは一般的な KEY=VALUE 形式（`export KEY=val` にも対応）。クォートやコメントも適切に扱います。

---

## 使い方

以下は代表的な利用例です。

- Settings の取得（環境変数ラッパー）

```python
from kabusys.config import settings

# 必須値の取得例（未設定時は ValueError）
token = settings.jquants_refresh_token

# DB パスや実行環境フラグ
db_path = settings.duckdb_path
is_live = settings.is_live
log_level = settings.log_level
```

- DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# settings.duckdb_path に基づきファイルを作成してスキーマを初期化
conn = init_schema(settings.duckdb_path)

# 既存 DB に接続するだけ
conn2 = get_connection(settings.duckdb_path)
```

- 監査ログスキーマの初期化（既存接続へ追加）

```python
from kabusys.data.audit import init_audit_schema

# 既に init_schema() で得た conn を渡す
init_audit_schema(conn)
```

- 監査ログ専用 DB を作る

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意:
- init_schema / init_audit_db は親ディレクトリが存在しない場合、自動で作成します。
- init_schema は冪等（既存テーブルがあれば上書きしない）です。
- audit スキーマではタイムゾーンを UTC に固定します（`SET TimeZone='UTC'` を実行）。

---

## ディレクトリ構成

パッケージの主要ファイル構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - schema.py         # DuckDB のメインスキーマ定義と初期化 (init_schema, get_connection)
    - audit.py          # 監査ログ（signal_events, order_requests, executions）定義と初期化
    - audit.py
    - audit.py
    - audit.py
    - audit.py
    - audit.py
    - audit.py
    - audit.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（README 用の抜粋表示です。実際のファイルはリポジトリを参照してください）

主要モジュール概要:
- kabusys.config
  - Settings クラス（settings インスタンス）で環境変数を参照
  - 自動 .env ロード機能（プロジェクトルート検出、.env/.env.local 読込）
- kabusys.data.schema
  - init_schema(db_path) / get_connection(db_path)
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
- kabusys.data.audit
  - init_audit_schema(conn) / init_audit_db(db_path)
  - 発注〜約定の監査テーブル（冪等・トレーサビリティ設計）

---

## 注意点・運用上のヒント

- 環境（KABUSYS_ENV）は開発 / ペーパートレード / 本番（live）を区別するために重要です。live 運用時は十分な注意と検証を行ってください。
- order_requests テーブルの order_request_id は冪等キーとして機能します。再送やリトライ時に重複発注を防ぐため、クライアント側でも同一処理に同一 order_request_id を付与してください。
- 監査ログは削除しない前提で設計されています（FK は ON DELETE RESTRICT）。履歴・トレースの保存を優先する運用を想定しています。
- .env の自動ロードは便利ですが、CI やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用し明示的に環境をセットすることを推奨します。

---

必要に応じて README の追加情報（例: テスト手順、CI 設定、具体的な戦略テンプレート等）を作成できます。追加したい内容を教えてください。