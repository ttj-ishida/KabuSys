# KabuSys

日本株向け自動売買システムのコアライブラリ（骨組み）。  
DuckDB を用いたデータ層、監査ログ、環境設定管理、戦略／発注／モニタリングのための名前空間を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援するライブラリ群です。  
主な目的は次のとおりです。

- 市場データ・ファンダメンタル・ニュースなどの生データ（Raw）から整形済みデータ（Processed）、戦略用特徴量（Feature）までのデータレイヤを DuckDB に保存するスキーマを提供
- 発注フローの監査（トレーサビリティ）用テーブル群を提供し、シグナル→発注→約定までを UUID 連鎖で完全追跡可能にする
- 環境変数／.env の自動読み込みとアプリ設定 API を提供
- 将来的に strategy / execution / monitoring のモジュールを収容する名前空間を提供

---

## 機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み
  - 必須設定は Settings クラス経由で取得し、未設定時は例外を送出
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - スキーマ初期化関数: data.schema.init_schema(db_path)
  - 既存 DB への接続: data.schema.get_connection(db_path)

- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査用テーブルとインデックス
  - 初期化関数: data.audit.init_audit_schema(conn) または data.audit.init_audit_db(db_path)
  - すべての TIMESTAMP は UTC で保存されるように設定

- 名前空間の準備
  - kabusys.strategy, kabusys.execution, kabusys.monitoring（将来的な実装）

---

## セットアップ手順

1. Python のセットアップ（例: 3.9+ 推奨）
   - 仮想環境の作成と有効化（任意）
     - python -m venv .venv
     - Unix/macOS: source .venv/bin/activate
     - Windows: .venv\Scripts\activate

2. 依存パッケージのインストール
   - 最低限必要: duckdb
   - 例:
     - pip install duckdb

   ※ プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。

3. レポジトリルートに .env を作成（次節を参照）

4. スキーマ初期化（使用例は後述）

---

## 環境変数 (.env) と設定

KabuSys は .env / .env.local をプロジェクトルートから自動で読み込みます（OS 環境変数が優先）。  
自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（Settings で参照されるもの）:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants API のリフレッシュトークン

- KABU_API_PASSWORD (必須)  
  kabuステーション API 用パスワード

- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)  
  kabuAPI のベース URL

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン

- SLACK_CHANNEL_ID (必須)  
  通知先 Slack チャンネル ID

- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)  
  DuckDB のファイルパス。":memory:" でインメモリ DB も可

- SQLITE_PATH (任意、デフォルト: data/monitoring.db)  
  監視用 SQLite パス（将来的な用途）

- KABUSYS_ENV (任意、デフォルト: development)  
  有効値: development, paper_trading, live

- LOG_LEVEL (任意、デフォルト: INFO)  
  有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env の読み込みルール:
- コメント、export プレフィックス、シングル/ダブルクォート、エスケープに対応
- .env が読み込まれた後 .env.local を読み込み（.env.local は上書き可能）
- OS 環境変数は保護され .env で上書きされない（ただし .env.local は override=True で上書き可能）

---

## 使い方（簡単な例）

- Settings を使って環境設定を取得する:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print("ENV:", settings.env)
print("DuckDB path:", settings.duckdb_path)
```

- DuckDB スキーマの初期化:
```python
from kabusys.data import schema
from kabusys.config import settings

# ファイル DB を初期化して接続を取得
conn = schema.init_schema(settings.duckdb_path)

# 以後 conn.execute(...) でクエリ実行可能
```

- 監査ログスキーマの初期化（既存接続へ追加）:
```python
from kabusys.data import audit
# conn は init_schema が返した接続
audit.init_audit_schema(conn)
```

- 監査用専用 DB を新規作成する場合:
```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

- インメモリ DB（テスト用）:
```python
conn = schema.init_schema(":memory:")
audit.init_audit_schema(conn)
```

- 自動 .env 読み込みをテスト中に無効化する:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print('disabled')"
```

---

## ディレクトリ構成

プロジェクトの主要なファイル／ディレクトリは以下の通りです（src 配下）:

- src/kabusys/
  - __init__.py                : パッケージ定義（バージョン等）
  - config.py                  : 環境変数 / 設定管理（Settings クラス）
  - execution/
    - __init__.py              : 発注関連モジュールの名前空間（未実装）
  - strategy/
    - __init__.py              : 戦略関連モジュールの名前空間（未実装）
  - monitoring/
    - __init__.py              : モニタリング関連モジュール（未実装）
  - data/
    - __init__.py
    - schema.py                : DuckDB スキーマ定義と初期化（raw / processed / feature / execution）
    - audit.py                 : 監査ログ（signal_events, order_requests, executions）定義と初期化

プロジェクトルートに以下があることを想定:
- .git または pyproject.toml（.env 自動読み込みの基準）
- .env / .env.local（ローカル設定）

---

## 注意事項 / 設計上のポイント

- data.schema.init_schema は冪等（既にテーブルがあればスキップ）です。
- audit.init_audit_schema は全ての TIMESTAMP を UTC で扱う設定（SET TimeZone='UTC'）を行います。
- order_requests などの監査テーブルは冪等性・二重発注防止のためのチェックや index を備えています（order_request_id は冪等キー）。
- 環境変数が必須なキーは Settings プロパティを通してアクセスすると未設定時に ValueError が送出されます。
- DuckDB ファイルの親ディレクトリが存在しない場合、init_* 関数は自動でディレクトリを作成します。

---

もし README に追加したい具体的な使い方（例: サンプル戦略、発注ワークフロー、CI 設定、Dockerfile）や、requirements やパッケージの配布方法（pyproject.toml / setup.cfg の内容）などがあれば教えてください。それに合わせて README を拡張します。