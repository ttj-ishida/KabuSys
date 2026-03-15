# KabuSys

日本株向けの自動売買基盤ライブラリ (KabuSys)。  
データ取得・永続化（DuckDB）・スキーマ定義・監査ログなど、アルゴリズム取引プラットフォームの基礎機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システムのための共通ライブラリ群です。主な目的は次のとおりです。

- J-Quants API からの市場データ取得（株価日足、財務データ、マーケットカレンダー）
- 取得データの DuckDB への永続化（冪等保存）
- DuckDB スキーマ（Raw / Processed / Feature / Execution 層）の定義・初期化
- 監査ログ（シグナル→発注→約定のトレーサビリティ）テーブルの定義・初期化
- 環境変数ベースの設定管理（.env 自動読み込み、テスト用フラグあり）

設計上のポイント:
- API レート制限（J-Quants: 120 req/min）を守るためのスロットリング
- 再試行（指数バックオフ）、401 時トークン自動リフレッシュ
- 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を抑制
- DuckDB への挿入は ON CONFLICT DO UPDATE で冪等性を担保

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN）
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（fetch_daily_quotes）
  - 財務データ（fetch_financial_statements）
  - マーケットカレンダー（fetch_market_calendar）
  - 取得データを DuckDB に保存するユーティリティ（save_* 系）
  - レート制御・リトライ・トークン管理
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義
  - init_schema(db_path) で全テーブルを作成
  - get_connection(db_path) で既存 DB に接続
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL
  - init_audit_schema(conn) / init_audit_db(path)
  - 監査用のインデックスを作成
- パッケージ構造（モジュール化された strategy / execution / monitoring / data）

---

## セットアップ手順

※プロジェクトに pyproject.toml / requirements.txt がある前提です。ここでは最低限の依存と初期化手順を示します。

1. Python 環境の準備（推奨: 3.9+）
   - 仮想環境を作る:
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb

   ※実運用では requests 等追加ライブラリや linters・CI 用の依存が必要になる場合があります。

3. リポジトリをローカルにクローンして editable install（任意）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）で `.env` と `.env.local` を利用できます。
   - 自動ロードはデフォルトで有効。テスト時などに無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID

   - その他（デフォルトあり）
     - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（モニタリング DB 用、デフォルト: data/monitoring.db）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）

   .env の簡易例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで schema を初期化します（デフォルトパスは settings.duckdb_path）。
   - 例（スクリプト）:
     from kabusys.data import schema
     from kabusys.config import settings
     schema.init_schema(settings.duckdb_path)

6. 監査ログの初期化（必要な場合）
   - 既に初期化した DuckDB 接続に対して監査テーブルを追加:
     conn = schema.get_connection(settings.duckdb_path)
     from kabusys.data import audit
     audit.init_audit_schema(conn)
   - 監査専用 DB を別で作る場合:
     audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方

ここでは主要なユースケースのコード例を示します。

- 設定の参照:
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)  # 必須 env を読み取り
  print(settings.duckdb_path)
  ```

- DuckDB スキーマの初期化:
  ```python
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)
  ```

- J-Quants から日足を取得して DuckDB に保存:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)  # 既に init_schema 済みを想定

  records = fetch_daily_quotes(code="7203")  # 例：トヨタ（7203）
  n = save_daily_quotes(conn, records)
  print(f"saved {n} daily quote rows")
  ```

- 財務データ・カレンダーの取得と保存:
  ```python
  from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
  from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

  fin = fetch_financial_statements(code="7203")
  save_financial_statements(conn, fin)

  cal = fetch_market_calendar()
  save_market_calendar(conn, cal)
  ```

- 監査テーブル初期化（既存接続に追加）:
  ```python
  from kabusys.data import audit
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  audit.init_audit_schema(conn)
  ```

備考（J-Quants クライアント）:
- 内部でレートリミット（120 req/min）を守る実装があり、複数ページ取得時でも安全に動作します。
- 408/429/5xx 系は最大 3 回の再試行を行います（指数バックオフ）。
- 401 はリフレッシュトークンを使って自動的に ID トークンを更新し 1 回再試行します。

---

## ディレクトリ構成（主なファイル）

プロジェクト内の主要なファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                - 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント + DuckDB 保存ユーティリティ
    - schema.py              - DuckDB スキーマ定義・初期化
    - audit.py               - 監査ログ（signal / order_request / execution）
    - (raw その他ファイル)
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

上記以外にプロジェクトルートには .env/.env.local を置くことを想定しています。

--- 

## 注意事項 / 運用メモ

- .env の自動読み込みは、プロジェクトルート（.git または pyproject.toml）を基準に行われます。CI やテストで自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 初期化は冪等です。既存テーブルがあれば上書きされません。
- 監査ログは原則削除しない前提で設計されています（外部キーは ON DELETE RESTRICT）。
- 本リポジトリはインフラ/運用用の認証情報（トークンやパスワード）を .env に格納することを想定しています。取り扱いには十分注意してください（バージョン管理にコミットしない等）。

---

もし README に追加したい内容（例：CI の設定方法、詳細なスキーマドキュメント、開発用の Makefile / tox / pre-commit 設定）があれば教えてください。必要に応じてサンプル .env.example やより詳細な使い方（戦略作成 / 発注フロー）も作成します。