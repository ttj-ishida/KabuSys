# KabuSys

日本株自動売買システム向けの小規模ライブラリ群。データ取得・永続化、スキーマ管理、監査ログなどを含み、戦略・発注層の基盤を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の役割を持つモジュール群を含むパッケージです。

- J-Quants API からの市場データ・財務データ・マーケットカレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB に対するスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（signal → order_request → executions のトレース用テーブル群）初期化
- 環境変数経由の設定管理（.env 自動ロード機能）

設計上のポイント:
- API レート制限とリトライ（指数バックオフ）を考慮
- 取得時刻（fetched_at）での Look-ahead Bias 防止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）を意識
- 監査ログは削除せず、UUID ベースのチェーンで完全トレーサビリティを確保

---

## 機能一覧

- 環境設定管理（settings オブジェクト）
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可能）
  - 必須項目のチェック（未設定時は例外を発生）
- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - トークン取得（get_id_token）
  - 日足（fetch_daily_quotes）、財務（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）の取得（ページネーション対応）
  - DuckDB へ保存するユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）
  - レート制御（120 req/min）、リトライ、401 時の自動リフレッシュ
- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - init_schema(db_path) で全テーブル/インデックスを作成（冪等）
  - get_connection(db_path) で接続を取得（既存 DB 用）
- 監査ログスキーマ（src/kabusys/data/audit.py）
  - init_audit_schema(conn) / init_audit_db(db_path) により監査用テーブル・インデックスを初期化

---

## セットアップ手順

必要条件:
- Python 3.10 以上（型記法 Path | None を利用）
- pip

1. リポジトリをクローン／配置
   - 例: git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリのインストール
   - 本コードベースで明示的に必要となるのは duckdb（J-Quants クライアントは標準ライブラリの urllib を使用）
   - pip install duckdb

   （将来的に Slack や kabu API 等のクライアントを追加する場合は別途ライブラリが必要になる可能性があります）

4. 環境変数の準備
   - プロジェクトルートに `.env` を配置すると、自動で読み込まれます（優先順位: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

5. 必須環境変数（settings が参照するキー）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN : Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - （任意）KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
   - （任意）LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - データベースパス（デフォルト値を .env で上書き可能）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

   例: .env（最低限の例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方

以下は典型的な利用シナリオの例です。Python スクリプト内で直接インポートして使用します。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

2) J-Quants から日足を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)  # トークンは settings から自動取得
n = save_daily_quotes(conn, records)
print(f"{n} 件保存しました")
```

3) 財務データ取得と保存
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements

records = fetch_financial_statements(code="7203")
save_financial_statements(conn, records)
```

4) マーケットカレンダー取得と保存
```python
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

5) 監査ログテーブルの初期化（既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```
または監査専用 DB を作る:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

注意点:
- J-Quants API はレート制限（120 req/min）を厳守します。fetch_* 関数は内部でレート制御とリトライを行います。
- トークン期限切れで 401 を受けた場合、内部で1回だけトークンを自動リフレッシュして再試行します。
- DuckDB への保存は ON CONFLICT DO UPDATE により冪等化されています（既存レコードは更新されます）。
- 全てのタイムスタンプはロジック内で UTC を使用する（fetched_at 等）。

---

## ディレクトリ構成

ルート（例）:
- pyproject.toml / setup.cfg / .git/ など（プロジェクトルート判定に使用）
- .env, .env.local など（環境設定）

ソース:
- src/
  - kabusys/
    - __init__.py
    - config.py                -- 環境変数・設定管理（settings オブジェクト）
    - data/
      - __init__.py
      - jquants_client.py     -- J-Quants API クライアント（取得・保存ロジック）
      - schema.py             -- DuckDB スキーマ定義・初期化
      - audit.py              -- 監査ログ用スキーマ定義・初期化
      - (others...)           
    - strategy/
      - __init__.py           -- 戦略関連（将来的拡張）
    - execution/
      - __init__.py           -- 発注・約定管理（将来的拡張）
    - monitoring/
      - __init__.py           -- 監視関連（将来的拡張）

主要ファイルの概要:
- src/kabusys/config.py
  - settings オブジェクトを通じて設定値を取得
  - プロジェクトルートを自動探索して .env/.env.local をロード
- src/kabusys/data/jquants_client.py
  - API 呼び出しユーティリティ（_request）
  - fetch_* / save_* 関数群
- src/kabusys/data/schema.py
  - 各種テーブル（Raw, Processed, Feature, Execution）およびインデックスの DDL を管理
  - init_schema()/get_connection() を提供
- src/kabusys/data/audit.py
  - 監査ログ用 DDL と init_audit_schema()/init_audit_db()

---

## 補足 / トラブルシューティング

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に行われます。パッケージ配布後やテスト時に自動ロードを行いたくない場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- settings による必須環境変数が未設定だと ValueError が発生します。エラーメッセージの指示に従い .env を用意してください。
- DuckDB ファイルパスはデフォルトで data/kabusys.duckdb（相対パス）です。init_schema は親ディレクトリが無ければ自動作成します。
- J-Quants API のレート制御やリトライ挙動は jquants_client.py 内で定義されています。必要に応じてログレベルを DEBUG にして詳細を確認してください（LOG_LEVEL 環境変数）。

---

必要であれば README を README.md ファイルとして整形してお渡しします。追加で「サンプル .env.example」や「よくあるエラー対処集」などを含めたい場合は教えてください。