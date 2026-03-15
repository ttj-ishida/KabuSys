# KabuSys

日本株自動売買システムのライブラリ基盤（バージョン 0.1.0）

簡潔な説明:
- 市場データ取得・整形・特徴量作成・シグナル生成・発注／約定監査までを想定したモジュール群を含む骨組み。
- データ永続化には DuckDB を用いるスキーマ定義と初期化ロジックを提供。
- 環境変数による設定管理、監査ログ（order→execution のトレーサビリティ）機能を備える。

---

## 主な機能

- 環境変数／.env ファイル自動読み込み（package 配布後でも正しく動作するプロジェクトルート探索）
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- アプリケーション設定の取得（settings オブジェクト経由）
  - J-Quants, kabuステーション, Slack, DB パスなどの必須／デフォルト値管理
  - KABUSYS_ENV のバリデーション（development / paper_trading / live）
  - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DuckDB スキーマ定義および初期化（data.schema）
  - Raw / Processed / Feature / Execution の多層テーブル群を作成
  - インデックスの作成
  - init_schema(db_path) で DB を初期化して接続を返す
- 監査ログ（audit）スキーマ（order_requests / executions / signal_events）
  - 冪等キー、状態遷移、UTC タイムゾーンの運用ポリシーを想定
  - init_audit_schema(conn) / init_audit_db(db_path) を提供

---

## 要求環境 / 依存

- Python 3.10+（Union 演算子や型ヒントを使用）
- ライブラリ: duckdb
  - インストール例: pip install duckdb

（プロジェクト全体の依存は pyproject.toml / requirements.txt に従ってください。ここではソースから読み取れる主要依存のみ記載しています）

---

## 環境変数（主なもの）

必須（Settings._require により未設定時はエラー）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化
- KABUSYS 用の DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）

.env の読み込み優先順位:
1. OS 環境変数（保護）
2. .env.local（存在すれば上書き）
3. .env

.env のパースはシェル風:
- export KEY=val に対応
- シングル／ダブルクォート内部でのバックスラッシュエスケープを考慮
- 非クォート値では「#」の前に空白がある場合はコメント扱い

例（.env）:
KEY=val
JQUANTS_REFRESH_TOKEN="your-refresh-token"
KABU_API_PASSWORD='password'
SLACK_BOT_TOKEN=xxxxxx
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを取得）
   - git clone ...（プロジェクトルートには .git または pyproject.toml がある必要があります）

2. 仮想環境を作成 & 有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存をインストール
   - pip install duckdb
   - （プロジェクト配布形態に応じて）pip install -e . または pip install -r requirements.txt

4. 環境変数を設定
   - プロジェクトルートに .env を作成（上記の例を参照）
   - 自動読み込みを無効にしたい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（簡単なサンプル）

設定値取得:
- Python コード内で settings を使って設定を取得できます。

例:
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
if settings.is_live:
    print("ライブモードです")

DuckDB スキーマ初期化:
- 永続ファイルを使う例（デフォルトパスを settings から取得）:
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
# conn は duckdb 接続オブジェクト（duckdb.DuckDBPyConnection）

- インメモリ DB を使うテスト例:
conn = schema.init_schema(":memory:")

既存 DB 接続を取得するだけ（スキーマ初期化は行わない）:
conn = schema.get_connection(settings.duckdb_path)

監査ログの初期化:
- 既存の接続に監査テーブルを追加する:
from kabusys.data import audit
audit.init_audit_schema(conn)

- 監査専用 DB を新規作成する:
audit_conn = audit.init_audit_db("data/audit.duckdb")

自動 .env 読み込みを無効化して手動で設定したい場合:
import os
os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"
# その後に必要な環境変数を設定する

API の注意点:
- settings の必須プロパティを参照するとき、該当環境変数が未設定だと ValueError が発生します。
- init_schema は冪等（既存テーブルがあればスキップ）で、親ディレクトリがなければ自動作成します。

---

## ディレクトリ構成

（src 配下の主要ファイル・モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py                （パッケージ初期化、__version__ = "0.1.0"）
    - config.py                  （環境変数・設定管理、.env 自動読み込み）
    - data/
      - __init__.py
      - schema.py                （DuckDB スキーマ定義 / init_schema / get_connection）
      - audit.py                 （監査ログスキーマ / init_audit_schema / init_audit_db）
      - audit.py
      - audit.py
      - audit.py
      - audit.py
    - strategy/
      - __init__.py               （戦略層のプレースホルダ）
    - execution/
      - __init__.py               （発注・約定・ブローカー連携のプレースホルダ）
    - monitoring/
      - __init__.py               （監視・メトリクスのプレースホルダ）

（上記以外に README、pyproject.toml 等がプロジェクトルートに存在する想定）

---

## 実装上のポイント / 運用ガイド

- 環境管理:
  - OS 環境変数は最優先で保護され、.env/.env.local はそれを上書きしない設計（.env.local は OS 環境変数を上書きしない範囲で .env を上書き）。
- タイムゾーン:
  - 監査ログ（audit）は初期化時に TimeZone='UTC' をセットし、TIMESTAMP は UTC で保存する前提。
- 冪等:
  - order_request_id や broker_execution_id 等は冪等キー設計を考慮。二重発注防止の設計が施されています。
- スキーマ運用:
  - init_schema / init_audit_schema は冪等であり、既存テーブルがあれば何度実行しても安全です。
- テスト:
  - ":memory:" を使ったインメモリ DuckDB によりユニットテストが容易です。
  - 自動 .env 読み込みをテストで制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

この README はコードベースから抽出した説明を元に作成しています。利用時はプロジェクトの pyproject.toml / ドキュメント（DataSchema.md / DataPlatform.md 等）が存在する場合、それらも合わせて参照してください。