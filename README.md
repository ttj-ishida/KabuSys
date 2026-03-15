# KabuSys

日本株向け自動売買基盤（ライブラリ部分）

バージョン: 0.1.0

概要:
KabuSys は日本株のデータ収集、加工、特徴量生成、シグナル生成、発注・約定管理までを想定した自動売買システムのコアライブラリ群です。本リポジトリには設定管理、DuckDB を用いたスキーマ定義・初期化、監査ログ（トレーサビリティ）関連の実装が含まれます。

主な目的:
- データ層（Raw / Processed / Feature / Execution）のスキーマを定義・初期化する
- 発注から約定までの監査ログを記録するためのスキーマを提供する
- 環境変数を安全に読み込む設定管理機能を提供する

---

## 機能一覧

- 環境変数・設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（OS 環境変数を優先）
  - 必須設定の取得とバリデーション（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）
  - KABUSYS_ENV, LOG_LEVEL の妥当性検査
  - 自動ロードの無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD）

- DuckDB スキーマ管理（data/schema.py）
  - Raw / Processed / Feature / Execution の多層スキーマを作成
  - 各種インデックスを同時に作成（クエリ性能を想定）
  - init_schema() でファイルベースまたはインメモリ DB を初期化

- 監査ログ（data/audit.py）
  - signal_events, order_requests, executions など監査用テーブルを定義
  - 冪等キー（order_request_id、broker_execution_id）を考慮
  - UTC タイムゾーン保存方針を適用（init_audit_schema は SET TimeZone='UTC' を実行）
  - init_audit_db / init_audit_schema による初期化を提供

---

## 動作要件

- Python >= 3.10（型アノテーションで `X | Y` を使用）
- duckdb Python パッケージ
- （実運用で）各種外部 API トークン等（下記参照）

インストール例:
pip install duckdb

（このリポジトリはライブラリ実装のため、別途依存管理ファイルがある場合はそちらに従ってください。）

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. Python 環境を準備（推奨: venv / Poetry 等）

   例:
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある位置）に `.env`（および必要なら `.env.local`）を配置します。
   - 自動ロードの挙動:
     - OS 環境変数 > .env.local > .env の順で優先
     - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセット

   例 `.env`（最小例、実運用では値を設定してください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   必須環境変数（get すると ValueError を投げます）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意（デフォルトあり）:
   - KABUSYS_ENV (development | paper_trading | live) — default: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
   - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
   - DUCKDB_PATH — default: data/kabusys.duckdb
   - SQLITE_PATH — default: data/monitoring.db

4. データベース初期化
   - DuckDB スキーマを作成します（ファイルパスを指定）
   - 監査用スキーマは別途初期化できます（既存 conn に追加することも可能）

---

## 使い方（簡単なコード例）

設定の参照:
```python
from kabusys.config import settings

# 環境変数取得
token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path  # Path 型
```

DuckDB スキーマの初期化:
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.audit import init_audit_schema

# ファイル DB を初期化（必要に応じて ":memory:" を指定してインメモリ）
conn = init_schema(settings.duckdb_path)

# 監査ログテーブルを同一接続に追加する場合
init_audit_schema(conn)

# 既存の DB に接続するだけ
conn2 = get_connection(settings.duckdb_path)
```

監査用に専用 DB を作る場合:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

注記:
- init_schema は冪等（既にテーブルが存在すればスキップ）です
- init_audit_schema はすべての TIMESTAMP を UTC で扱うよう SET TimeZone='UTC' を実行します

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py              # パッケージ初期化、__version__ 等
    - config.py                # 環境変数 / 設定管理
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ（Raw / Processed / Feature / Execution）
      - audit.py               # 監査ログ（signal_events / order_requests / executions）
      - audit.py
      - audit.py
- pyproject.toml (想定)
- .git/ (プロジェクトルート判定に使用)
- .env, .env.local (推奨)

（注）実際のリポジトリには上記以外のファイルやディレクトリが存在する可能性があります。

---

## 設計上のポイント / 注意事項

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml で判定）を起点に `.env` と `.env.local` を読み込みます。OS の既存環境変数は保護され、上書きされません（`.env.local` は override=True で読み込まれるが OS キーは protected）。
- .env のパーシングはクォート、エスケープ、インラインコメント、`export KEY=val` 形式に対応しています。
- DuckDB スキーマは多層（Raw / Processed / Feature / Execution）で、頻出クエリ向けにインデックスを作成します。
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT など）で設計されています。order_request_id は冪等キーとして機能する設計です。
- 監査ログのタイムスタンプは UTC で保存されます（init_audit_schema が SET TimeZone='UTC' を実行）。

---

## よくある運用フロー（概略）

1. データ取得モジュールが取得した生データを raw_* テーブルに格納
2. ETL/処理パイプラインで processed / features テーブルを更新
3. 戦略層が features / ai_scores を参照しシグナルを生成 -> signal_events に記録
4. 発注要求を出す際に order_requests に記録（order_request_id を冪等キーとして使用）
5. ブローカー応答（broker_order_id・約定）を executions に記録しトレーサビリティを完結

---

## 開発・テスト補助

- 自動環境読み込みを無効化してユニットテストを実行する場合:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして起動すると .env 自動ロードをスキップします。

---

README の内容は現状のコードベース（config.py / data/schema.py / data/audit.py 等）から生成しています。実運用での外部 API 実装（J-Quants や kabu ステーション・Slack 通知 等）は本リポジトリの別モジュールまたは上位アプリ側で実装する想定です。必要であれば、追加の使い方（戦略実装例、発注フローサンプル、CI 設定例）を追記します。