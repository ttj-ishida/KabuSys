# KabuSys

日本株自動売買プラットフォーム（ライブラリ）  
このリポジトリは、データ取得・スキーマ管理・品質検査・監査ログ等を備えた日本株向けの自動売買基盤コンポーネント群です。主に以下を提供します。

- J-Quants API からのデータ取得（株価日足、財務データ、JPX カレンダー）
- DuckDB によるスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 環境変数による設定管理（.env 自動読み込み機能）

バージョン: 0.1.0

---

## 主な機能一覧

- config
  - .env / .env.local をプロジェクトルートから自動読み込み（OS 環境変数を保護）
  - 必須環境変数の取得ラッパ（未設定時は ValueError）
  - 環境（development / paper_trading / live）とログレベルのバリデーション
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- data.jquants_client
  - J-Quants API クライアント（token 自動リフレッシュ、ページネーション対応）
  - レート制限（120 req/min）制御（固定間隔スロットリング）
  - 再試行（指数バックオフ、最大 3 回、408/429/5xx 対象、401 の場合はトークン再取得を 1 回実施）
  - fetch_* 系関数:
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
  - DuckDB へ保存する save_* 関数（ON CONFLICT DO UPDATE により冪等）

- data.schema
  - DuckDB における包括的スキーマ定義（Raw / Processed / Feature / Execution 層）
  - テーブル初期化関数: `init_schema(db_path)`
  - 既存 DB への接続取得: `get_connection(db_path)`

- data.audit
  - シグナル → 発注 → 約定 を追跡する監査テーブル定義
  - order_request_id を冪等キーとして二重発注防止
  - 初期化関数: `init_audit_schema(conn)` / `init_audit_db(db_path)`

- data.quality
  - データ品質チェック関数群:
    - 欠損チェック: check_missing_data(...)
    - スパイク検出: check_spike(...)
    - 重複チェック: check_duplicates(...)
    - 日付整合性: check_date_consistency(...)
    - 全チェック実行: run_all_checks(...)

---

## 要件

- Python >= 3.10（A | B 型注釈を使用）
- 依存パッケージ（抜粋）
  - duckdb
- 標準ライブラリ: urllib, json, logging, datetime, pathlib など

requirements.txt / pyproject.toml がある場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   - 例（Unix/macOS）:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 依存パッケージをインストールします（例: duckdb）。

   - pip install duckdb

   開発用やパッケージ化されている場合は、`pip install -e .` や `pip install -r requirements.txt` を使用してください。

3. 環境変数を設定します（.env を推奨）。

   - ルートに .env または .env.local を配置すると、自動で読み込まれます（ただしテスト時等は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。

   必須変数（コード内 Settings を参照）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   任意/デフォルト付き:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1（自動ロード無効化）
   - KABUSYS_API_BASE_URL: kabu API のベース URL（デフォルト実装では KABU_API_BASE_URL）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマの初期化:

   - Python REPL やスクリプトで:
     ```
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```

---

## 使い方（簡単な例）

- J-Quants から日足を取得して DuckDB に保存するサンプル:

  ```
  from kabusys.data.jquants_client import (
      fetch_daily_quotes,
      save_daily_quotes,
      get_id_token,
  )
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")

  # 必要に応じて id_token を手動取得／キャッシュを利用
  id_token = get_id_token()  # settings.jquants_refresh_token を利用して取得

  records = fetch_daily_quotes(id_token=id_token, code="7203", date_from=None, date_to=None)
  n = save_daily_quotes(conn, records)
  print(f"保存されたレコード数: {n}")
  ```

- 監査スキーマ初期化:

  ```
  from kabusys.data.audit import init_audit_schema
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn)
  ```

- データ品質チェックの実行:

  ```
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=None)
  for issue in issues:
      print(issue.check_name, issue.table, issue.severity, issue.detail)
  ```

- 設定値取得の例:

  ```
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

---

## 注意点 / 設計上の考慮

- J-Quants API はレート制限（120 req/min）に従う必要があります。本クライアントは固定間隔のスロットリングを用いて順守します。
- ネットワークエラーや 5xx/429 等に対するリトライを実装しています（指数バックオフ）。401 の場合はトークンを再取得して 1 回リトライします。
- データ取得時に fetched_at を UTC で記録しており、Look-ahead Bias を防ぐために「データをいつ取得したか」をトレースできます。
- DuckDB の INSERT 操作は ON CONFLICT DO UPDATE を用いて冪等性を担保しています。
- 監査ログは削除しない前提になっており、すべての TIMESTAMP を UTC で保存します（init_audit_schema 時に SET TimeZone='UTC' を実行）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から行われます。プロジェクトルートが特定できない場合は自動ロードをスキップします。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - schema.py              — DuckDB スキーマ定義・初期化
    - audit.py               — 監査ログスキーマ（signal → order → execution）
    - quality.py             — データ品質チェック
    - (その他: audit/quality 用補助モジュール)
  - strategy/
    - __init__.py            — 戦略関連（拡張想定）
  - execution/
    - __init__.py            — 発注/実行関連（拡張想定）
  - monitoring/
    - __init__.py            — 監視・メトリクス用（拡張想定）

ルート:
- pyproject.toml / setup.py（存在すればパッケージ情報）
- .env / .env.local（プロジェクトルートに配置して自動読み込み）

---

## 開発・拡張のヒント

- 新しいデータ取得 API を追加する場合は、fetch_*/save_* のペアを実装し、DuckDB のスキーマと合わせてテーブルを追加してください。
- strategy / execution / monitoring パッケージは軽量に抑えてあるため、戦略の実装や証券会社接続（kabuステーション）ロジックは各自拡張して組み込んでください。
- テスト実行時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して環境の自動汚染を防ぐことを推奨します。
- DuckDB のスキーマ定義は SQL 文字列で管理しているため、DDL を編集したら init_schema の idempotence（既存テーブルを壊さないこと）を意識して変更してください。

---

もし README に追加したい使用例、CI 設定、パッケージ化手順、あるいは別の言語（英語）版が必要であればお知らせください。