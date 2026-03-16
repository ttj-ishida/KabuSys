# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ。データ取得（J-Quants）、ETL、データ品質チェック、DuckDB スキーマ定義、監査ログ（発注→約定のトレーサビリティ）等の基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための基盤モジュール群です。主に以下を提供します。

- J-Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）
- DuckDB を用いたスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit レイヤ）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

設計上のポイント:
- J-Quants のレート制限（120 req/min）に合わせた RateLimiter を実装
- リトライ（指数バックオフ）、401 の自動リフレッシュ対応
- DuckDB への保存は冪等性（ON CONFLICT DO UPDATE）を担保
- すべての TIMESTAMP は UTC を想定（監査テーブル初期化時に SET TimeZone='UTC'）

---

## 主な機能一覧

- data/jquants_client.py
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（refresh token から id token を取得）
  - save_* 系で DuckDB へ冪等保存

- data/schema.py
  - init_schema(db_path) : 全テーブルを作成（Raw / Processed / Feature / Execution）
  - get_connection(db_path)

- data/pipeline.py
  - run_daily_etl(conn, target_date=None, ...) : 日次 ETL（calendar → prices → financials → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）

- data/quality.py
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks

- data/audit.py
  - init_audit_schema(conn) / init_audit_db(db_path) : 監査ログテーブルの初期化

- config.py
  - 環境変数からの設定管理（.env の自動読み込み、必須変数チェック、env 判定など）

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（typing の構文を使用）
- DuckDB を利用するため `duckdb` パッケージが必要

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

3. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション等のパスワード
   - SLACK_BOT_TOKEN: Slack 通知に使う Bot token
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   オプション / デフォルト:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

例（.env）
    JQUANTS_REFRESH_TOKEN=your_refresh_token_here
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

---

## 使い方

以下は基本的な利用例（Python スクリプトや REPL で実行）。

1) DuckDB スキーマ初期化（初回のみ）

    from kabusys.config import settings
    from kabusys.data import schema

    conn = schema.init_schema(settings.duckdb_path)
    # conn は duckdb.DuckDBPyConnection

2) 監査ログテーブルの初期化（必要に応じて）

    from kabusys.data import audit
    audit.init_audit_schema(conn)
    # または別 DB に分ける:
    # audit_conn = audit.init_audit_db("data/audit.duckdb")

3) J-Quants の id token を取得（任意にトークン注入してテスト可能）

    from kabusys.data.jquants_client import get_id_token
    token = get_id_token()  # settings.jquants_refresh_token を使用

4) 日次 ETL を実行

    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)
    print(result.to_dict())

    主な引数:
    - target_date: ETL 対象日（省略時は今日）
    - id_token: テスト用に注入可能
    - run_quality_checks: 品質チェックを行うか（デフォルト True）
    - backfill_days: 最終取得日から何日前まで再取得して後出し修正を吸収するか（デフォルト 3）

5) 品質チェックを個別に実行

    from kabusys.data import quality
    issues = quality.run_all_checks(conn, target_date=None)
    for i in issues:
        print(i)

注意点:
- J-Quants へのリクエストは内部でレート制限・リトライ処理が行われます。
- save_* 関数は ON CONFLICT DO UPDATE により冪等性を確保しています。
- ETL は各ステップごとに例外を捕捉して続行するため、結果オブジェクト（ETLResult）の errors / quality_issues を確認してください。

---

## ディレクトリ構成

プロジェクトの主要ファイル・ディレクトリ構成（要約）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - execution/               # 発注・約定等の実装予定（パッケージ）
      - __init__.py
    - strategy/                # 戦略関連（パッケージ）
      - __init__.py
    - monitoring/              # 監視モジュール（パッケージ）
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得 + 保存）
      - schema.py              # DuckDB スキーマ定義・初期化
      - pipeline.py            # ETL パイプライン
      - audit.py               # 監査ログ（signal/order_request/execution）
      - quality.py             # データ品質チェック

- pyproject.toml / setup.py / README.md（存在すれば）

（実際のリポジトリに合わせてツリーを補完してください）

---

## 実運用・運用上の注意

- 本ライブラリは「基盤」機能を提供します。実際の戦略、ブローカーAPIのアダプタ、リスク管理、ジョブスケジューリング（cron / Airflow など）は上位層で実装してください。
- 本番（live）運用時は KABUSYS_ENV=live を設定し、テスト・ペーパーと区別してください。
- 監査ログ（audit テーブル群）は基本的に削除しない運用を想定しています。order_request_id 等は冪等キーになります。
- DuckDB ファイルは単一ファイルで永続化されます。バックアップやアクセス制御に注意してください。
- J-Quants の API 利用制限や契約条件を遵守してください。

---

## 開発・拡張

- strategy、execution、monitoring パッケージは空の __init__ が配置されており、ここに戦略ロジック・発注アダプタ・監視処理を実装していきます。
- テストを書く際は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動 .env 読み込みを抑止し、テスト用の環境を注入してください。
- jquants_client の各 fetch 関数は id_token を引数で受け取れるため、テスト時は偽トークンやモックを注入しやすく設計されています。

---

もし README に追加したい点（例: 実際の .env.example、CI の設定、動作デモスクリプト、サンプル戦略など）があれば教えてください。README をリポジトリの実際のファイル構成や運用フローに合わせてさらに詳細化できます。