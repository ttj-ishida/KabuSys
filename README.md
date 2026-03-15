# KabuSys

日本株自動売買プラットフォーム用のライブラリ群（KabuSys）。データ取得・DBスキーマ管理・監査ログ・APIクライアント等、戦略実行に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。主な目的は以下です。

- J-Quants や kabuステーション等の外部APIからデータを取得するクライアントを提供
- DuckDB を用いた層別データスキーマ（Raw / Processed / Feature / Execution）を定義・初期化
- 発注・約定に関する監査（トレーサビリティ）テーブルを提供
- 環境変数ベースの設定管理（.env 自動読み込み、必須変数チェック）
- API レート制御やリトライ等を組み込んだ堅牢なデータ取得処理

設計上のポイント：
- J-Quants API のレート制限（120 req/min）を厳守（固定間隔スロットリング）
- 401 時のトークン自動リフレッシュ、ネットワークエラーに対する再試行（指数バックオフ）
- データ取得時の fetched_at 記録で Look-ahead Bias の抑止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）を採用

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）
  - KABUSYS_ENV / LOG_LEVEL の検証
  - 自動ロード無効化環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD

- データ取得（kabusys.data.jquants_client）
  - 日足（OHLCV）取得: fetch_daily_quotes(...)
  - 財務データ（四半期 BS/PL）取得: fetch_financial_statements(...)
  - JPX マーケットカレンダー取得: fetch_market_calendar(...)
  - 認証トークン取得/自動リフレッシュ: get_id_token(...)
  - レート制御、リトライ、401 自動リフレッシュを実装

- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) で全テーブル（Raw/Processed/Feature/Execution）を作成
  - get_connection(db_path) で既存DBに接続
  - テーブル定義・インデックスを含む冪等な初期化

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions 等の監査テーブルを初期化
  - init_audit_schema(conn) / init_audit_db(db_path) を提供

- （将来的に）戦略/実行/モニタリング用パッケージ骨子（kabusys.strategy, kabusys.execution, kabusys.monitoring）

---

## セットアップ手順

前提:
- Python 3.9+（型アノテーションや一部記法で 3.9 以降を想定）
- DuckDB を利用するため duckdb パッケージが必要

1. リポジトリをクローン / ソースを配置
   - 例: git clone <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install duckdb
   - （必要に応じて他ライブラリを追加）

   ※ プロジェクトがパッケージ化されている場合:
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必須例（.env に設定する主なキー）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...

   任意（デフォルトあり）:
   - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
   - LOG_LEVEL=INFO|DEBUG|...
   - DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
   - SQLITE_PATH=data/monitoring.db  （デフォルト）

5. DB スキーマの初期化（例）
   - Python REPL やスクリプトから:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
   - 監査用テーブルを追加する場合:
     from kabusys.data import audit
     audit.init_audit_schema(conn)
   - 監査専用 DB を作る場合:
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（簡易例）

- J-Quants トークン取得（明示的に）
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って POST で取得

- 日足を取得して DuckDB に保存
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 事前に init_schema を実行しておく
  records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  saved = save_daily_quotes(conn, records)
  print(f"{saved} 件保存しました")

- 財務データ / カレンダーも同様
  records = fetch_financial_statements(...)
  saved = save_financial_statements(conn, records)

- 監査DBの初期化（別DBを使う場合）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

- .env 自動ロードを無効にしてテストから手動で環境をセットする
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

注意点：
- fetch_* 系はページネーションに対応しており、内部で id_token をキャッシュして共有します。
- レートリミッタによる待ちが入るため大量リクエストは時間がかかります。
- ネットワーク/HTTP エラー時は指数バックオフで自動リトライを行います（最大 3 回）。401 は一度だけトークンをリフレッシュして再試行します。

---

## 主要 API（要約）

- kabusys.config.settings
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url
  - settings.slack_bot_token
  - settings.slack_channel_id
  - settings.duckdb_path / settings.sqlite_path
  - settings.env / settings.log_level / settings.is_live / settings.is_paper / settings.is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(id_token: str|None, code: str|None, date_from: date|None, date_to: date|None) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path) -> duckdb connection

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path) -> duckdb connection

---

## ディレクトリ構成

リポジトリ内の主要ファイル・モジュール（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理（.env 自動読み込み、Settings クラス）
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック、レート制御、リトライ）
      - schema.py              # DuckDB スキーマ定義と初期化
      - audit.py               # 監査ログ（signal_events, order_requests, executions）
      - (その他: audit/util 等)
    - strategy/
      - __init__.py            # 戦略関連（骨子）
    - execution/
      - __init__.py            # 発注実行関連（骨子）
    - monitoring/
      - __init__.py            # モニタリング関連（骨子）

その他:
- .env.example (想定) — プロジェクトルートに置いて .env を作成するためのテンプレート（存在する場合）
- pyproject.toml / setup.cfg 等（パッケージ化されている場合）

---

## 運用上の注意

- システム時刻は UTC を前提に扱う箇所があります（特に監査ログ）。
- DuckDB ファイルの保存先は settings.duckdb_path（デフォルト: data/kabusys.duckdb）。運用前にバックアップ方針を決めてください。
- KABUSYS_ENV により動作モードを切替できます（development / paper_trading / live）。live モードでは発注フローなどに特別な扱いを実装する想定です。
- 監査テーブルは削除しない前提（ON DELETE RESTRICT）。監査ログの扱いは慎重に行ってください。

---

必要であれば README に含めるサンプル .env.example、より詳細な API 使用例、ユニットテスト実行手順、CI/CD やデプロイ手順のテンプレートなども作成します。どの情報を追加しますか？