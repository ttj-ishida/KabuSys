# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants API から市場データ・財務データ・マーケットカレンダー等を取得して DuckDB に保存し、ETL（差分更新）、品質チェック、監査ログスキーマを提供します。取引実行・戦略・監視のための基盤モジュール群を含みます。

バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を用いた 3 層データスキーマ（Raw / Processed / Feature）および実行・監査テーブルの定義・初期化
- 差分 ETL パイプライン（差分取得、バックフィル、保存、品質チェック）
- 品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 設定は環境変数 / .env ファイルで管理し、自動読み込みに対応

設計上の注目点:
- API レート制限（120 req/min）をモジュールで順守
- リトライ（指数バックオフ、最大 3 回）、401 受信時は自動でトークンをリフレッシュ
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- すべてのタイムスタンプは UTC を想定している箇所がある（監査テーブル等）

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（OS 環境変数を優先）
  - 必須環境変数チェック
  - KABUSYS_ENV / LOG_LEVEL 等の検証
- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - レートリミット、リトライ、ページネーション対応、トークンキャッシュ
  - DuckDB へ保存する save_* 関数（冪等）
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(), get_connection()
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック、バックフィル、品質チェック実行（run_daily_etl 等）
  - ETL 実行結果を ETLResult で返す
- 品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合チェック
  - run_all_checks() でまとめて実行
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions のテーブル定義
  - init_audit_schema(), init_audit_db()
- プレースホルダ：strategy / execution / monitoring パッケージ（拡張ポイント）

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントに `X | None` などを使用）
- pip、仮想環境の利用を推奨

例（UNIX 系）:

1. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存ライブラリのインストール（最低: duckdb）
   ```
   pip install duckdb
   ```
   （本レポジトリをパッケージとして扱う場合）
   ```
   pip install -e .
   ```

3. 環境変数の用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動読み込みされます。
   - 読み込み優先度: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

必須環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注などに使用）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意 / デフォルト:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

.example の .env はプロジェクト配布に合わせて用意してください（config._require は .env.example を参照する旨のエラーメッセージを出します）。

---

## 使い方（基本例）

以下は Python REPL やスクリプトからの利用例です。

- 設定値を参照する:
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.is_live, settings.is_paper, settings.is_dev)
  ```

- DuckDB スキーマ初期化:
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)  # db ファイルを自動生成しスキーマ作成
  ```

  - インメモリ DB を使う場合:
    ```python
    conn = init_schema(":memory:")
    ```

- 監査スキーマの初期化（既存接続に追加）:
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # conn は init_schema で得た接続など
  ```

- J-Quants からデータ取得（低レベル）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  token = get_id_token()  # settings.jquants_refresh_token を使って id_token を取得
  records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,2,1))
  ```

- 日次 ETL 実行（差分取得 + 品質チェック）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ今日を対象に実行
  print(result.to_dict())
  ```

- 品質チェックのみ実行:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

注意点:
- J-Quants クライアントは内部でレート制御とリトライを行います。大量に並列で叩かないでください。
- get_id_token() はリフレッシュトークンから idToken を取得し、モジュールキャッシュを持っています。401 の際に自動リフレッシュするロジックがあります。

---

## よく使う API（抜粋）

- kabusys.config.settings
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続（スキーマ作成）
  - get_connection(db_path) -> 既存 DB への接続

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date: date | None = None, ... ) -> ETLResult
  - run_prices_etl, run_financials_etl, run_calendar_etl（個別ジョブ）

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## ディレクトリ構成

プロジェクトは src レイアウトで配置されています（主なファイルのみ抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - schema.py
      - pipeline.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

各ファイルの役割:
- config.py: 環境変数の読み込み・検証・Settings クラス
- data/jquants_client.py: J-Quants API クライアント + DuckDB 保存ユーティリティ
- data/schema.py: DuckDB テーブル定義と初期化ロジック
- data/pipeline.py: ETL パイプライン（差分更新・品質チェック）
- data/audit.py: 発注〜約定の監査ログスキーマ
- data/quality.py: 品質チェックロジック
- strategy/, execution/, monitoring/: 今後の戦略・発注・監視ロジックのためのパッケージ（拡張領域）

---

## 運用上の注意 / 補足

- .env のパースはシェル風（export 対応、クォート・エスケープ対応、コメント処理）ですが完璧ではない場合があります。機密情報の管理は適切に行ってください。
- DuckDB のスキーマは冪等に作成されます。初回のみ init_schema() を呼ぶ運用を推奨します。
- ETL の差分ロジックは最終取得日を基に自動算出します。バックフィル日数はパラメータで変更可能です。
- 品質チェックはデフォルトで Fail-Fast ではなく、問題をリストアップして呼び出し側が判断できるように設計されています。
- J-Quants API はレート制限があるため、他のクライアントと合わせて利用する場合は注意してください（120 req/min）。
- ロギングは環境変数 LOG_LEVEL で制御します。実行環境に応じて INFO / DEBUG 等を設定してください。

---

もし README にサンプル .env.example、pyproject.toml、あるいは戦略・発注の具体的な使い方（戦略の実装例や発注フローのサンプル）が必要であれば、その内容を教えてください。README をそれに合わせて拡張します。