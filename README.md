# KabuSys

日本株自動売買システムのコアライブラリ（ミニマル実装）

このリポジトリは、日本株のデータ取り込み・特徴量生成・発注監査を意識した内部ライブラリ群を提供します。DuckDB を用いた階層化されたデータスキーマ（Raw / Processed / Feature / Execution）や、発注フローの監査ログ（トレーサビリティ）を初期化するためのユーティリティが含まれます。

---

## 機能一覧

- 環境変数／設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須設定は取得時に検査して例外を送出
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - クォート・コメント・export 形式に対応した .env パーサ

- DuckDB ベースのデータスキーマ初期化
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義
  - インデックス作成
  - init_schema(db_path) により冪等にテーブル作成

- 監査ログ（Audit）スキーマ
  - signal_events / order_requests / executions を備えた監査用テーブル
  - 発注フローを UUID チェーンでトレース可能
  - init_audit_schema(conn) / init_audit_db(db_path) により初期化
  - 監査テーブルは TIMESTAMP を UTC で保存する設計

- パッケージ構成（モジュール分割）
  - data: データスキーマ・監査・ユーティリティ
  - strategy: 戦略関連（雛形）
  - execution: 発注関連（雛形）
  - monitoring: 監視・メトリクス（雛形）

---

## 必要要件（推奨）

- Python 3.10+
- duckdb
- （その他、戦略や execution 実装で追加パッケージが必要になることがあります）
- Slack や外部 API を使う場合はそれらのクレデンシャル

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# プロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. Python 仮想環境を作成し依存パッケージをインストール（上記参照）
3. プロジェクトルートに .env または .env.local を配置  
   - 自動読み込みはパッケージ import 時に行われます（プロジェクトルートは .git または pyproject.toml を基準に検出）
   - 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
4. 必要な環境変数（主要なもの）を設定

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env ファイルはクォートや export 形式、行内コメント等をある程度正しくパースします。未設定の必須変数はアプリ実行時に例外となります。

---

## 使い方（主要 API と例）

ここでは典型的な初期化／接続／設定参照の例を示します。

- 設定参照
```python
from kabusys.config import settings

# 必須値は取得時にチェックされます
token = settings.jquants_refresh_token
kabu_url = settings.kabu_api_base_url
is_live = settings.is_live
db_path = settings.duckdb_path  # pathlib.Path
```

- DuckDB スキーマ初期化（メイン DB）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# settings.duckdb_path のデフォルトは "data/kabusys.duckdb"
conn = init_schema(settings.duckdb_path)  # ファイルがなければディレクトリを作成して DB を生成
# 初期化済み接続を取得するだけなら:
conn2 = get_connection(settings.duckdb_path)
```

- 監査ログの初期化（既存接続に追記）
```python
from kabusys.data.audit import init_audit_schema

# 既に init_schema() で得た conn を使う場合
init_audit_schema(conn)
# または監査専用 DB を作成する場合
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 自動 .env 読み込みの挙動を無効化する（テスト等で）
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "import kabusys; print('auto env load disabled')"
```

注意点:
- init_schema は冪等（既にテーブルがあれば再作成しません）
- init_audit_schema は TIMESTAMP を UTC で保存するため接続に対して `SET TimeZone='UTC'` を実行します
- .env の読み込み順は OS 環境変数 > .env.local > .env（.env.local は上書き）

---

## ディレクトリ構成

主要ファイル／ディレクトリ（抜粋）
```
src/
  kabusys/
    __init__.py             # パッケージのエントリ。__version__ 等
    config.py               # 環境変数／設定管理（.env 自動読み込み含む）
    data/
      __init__.py
      schema.py             # DuckDB スキーマ定義・init_schema / get_connection
      audit.py              # 監査ログ（signal_events, order_requests, executions）の定義・初期化
      audit.py
      audit.py
    strategy/
      __init__.py           # 戦略関連モジュール（雛形）
    execution/
      __init__.py           # 発注関連モジュール（雛形）
    monitoring/
      __init__.py           # 監視・メトリクス関連（雛形）
```

主なモジュール説明:
- kabusys.config: .env のパースと自動ロード、必須設定チェックを行う Settings クラスを提供します。
- kabusys.data.schema: 全体的なデータスキーマ（Raw/Processed/Feature/Execution）とインデックスを定義。init_schema() で DB を初期化。
- kabusys.data.audit: 発注フローの監査テーブルを定義。init_audit_schema() / init_audit_db() を提供。

---

## 補足 / ベストプラクティス

- 機密情報は .env.local（.gitignore に追加）に置いて、リポジトリに公開しないでください。
- 本ライブラリはコアのスキーマと設定管理を提供するため、実際の取引ロジック（戦略・ブローカー連携・例外ハンドリング）は別モジュールで実装することを想定しています。
- 監査ログは削除しない方針（ON DELETE RESTRICT 等）なので、運用時はディスクサイズ・バックアップ方針を計画してください。
- DuckDB をファイルで使う場合、ファイルのアクセス競合に注意（複数プロセスからの同時書き込み設計を再検討してください）。

---

必要であれば、README に以下を追加できます:
- .env.example のサンプル
- CI / 開発用のセットアップ（pre-commit, linters）
- 実運用での DB マイグレーション方針
- 各テーブルの詳細（DataSchema.md 参照の旨）

追加してほしい項目があれば教えてください。