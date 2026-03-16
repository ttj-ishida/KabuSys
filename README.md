# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETLパイプライン、DuckDB スキーマ、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株の自動売買プラットフォーム構築に必要な以下の機能をモジュール化して提供します。

- J-Quants API クライアント（株価日足・財務データ・市場カレンダー取得）
  - API レート制限（120 req/min）の厳守（固定間隔の RateLimiter）
  - リトライ（指数バックオフ、最大3回）、401 応答時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）
- DuckDB 用スキーマ定義と初期化（Raw / Processed / Feature / Execution レイヤー）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合検出）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 環境設定管理（.env 自動読み込み、Settings API）

設計方針として冪等性・トレーサビリティ・テスト容易性を重視しています。

---

## 機能一覧

- 環境設定
  - .env / .env.local を自動読み込み（プロジェクトルートの検出: .git / pyproject.toml）
  - 必須変数未設定時は明示的な例外を送出
  - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（refresh token から id token を取得）
  - レート制限・リトライ・ページネーション対応
- DuckDB スキーマ
  - raw_prices, raw_financials, market_calendar, features, signals, orders, trades, positions, portfolio_performance など多数のテーブルを定義
  - init_schema(db_path) でスキーマを一括作成
- ETL（data.pipeline）
  - run_daily_etl(conn, ...)：カレンダー取得 → 株価差分取得（backfill対応） → 財務差分取得 → 品質チェック
  - 差分更新ロジック（DBの最終取得日を参照）
- 品質チェック（data.quality）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合を検出
  - 各チェックは QualityIssue のリストを返し、重大度（error/warning）を付与
- 監査ログ（data.audit）
  - signal_events / order_requests / executions を定義
  - init_audit_schema(conn) / init_audit_db(path) を提供（UTC タイムゾーンで記録）

---

## 必要な環境・依存

- Python 3.10 以上（| 型、型注釈のため）
- 依存パッケージ（最低限）
  - duckdb

（プロジェクトの pyproject.toml / requirements.txt があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン／ダウンロードしてプロジェクトルートへ移動

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb
   - （ローカル開発用にパッケージを editable インストールする場合）
     - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を配置します。
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルト有り）
     - KABUSYS_ENV (development | paper_trading | live)  デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) デフォルト: INFO
     - KABU_API_BASE_URL デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH デフォルト: data/kabusys.duckdb
     - SQLITE_PATH デフォルト: data/monitoring.db
   - 自動 .env 読み込みを無効にする（テスト等）:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   .env のパースは POSIX 風で以下に対応しています:
   - コメント行（#）と export KEY=val 形式
   - シングル／ダブルクォートとバックスラッシュエスケープ
   - inline コメントはクォート外かつ直前が空白の場合に認識

5. DuckDB スキーマ初期化
   - Python から次を実行して DB を初期化します（parent ディレクトリがなければ自動作成されます）:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

6. 監査ログテーブル（必要に応じて）
   - from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)

---

## 使い方（サンプル）

- 設定値の取得

  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.is_live, settings.log_level)

- DuckDB スキーマを初期化

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL を実行（最も基本的な例）

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を省略すると今日（ローカル日）を使用
  print(result.to_dict())

- ETL をテスト用トークンで実行（id_token を注入してテスト可能）

  token = "テスト用のid_token"
  result = run_daily_etl(conn, id_token=token, run_quality_checks=True)

- J-Quants データ取得を直接呼ぶ（ページネーション・自動リフレッシュ対応）

  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  # duckdb の接続を渡して保存
  saved = jq.save_daily_quotes(conn, records)

- 品質チェックを個別に実行

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2023,1,31))
  for i in issues:
      print(i.check_name, i.severity, i.detail)

- 監査ログ初期化（別 DB にする場合）

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

注意点:
- J-Quants API のレート上限（120 req/min）に合わせたスリープ制御が組み込まれています。短時間に多数のリクエストを送る用途では注意してください。
- fetch 系関数はページネーションに対応しており、モジュール内で id_token をキャッシュします。401 を受けると自動で refresh（1回）して再試行します。
- 保存関数は冪等（ON CONFLICT DO UPDATE）になっているため、再実行しても安全です。

---

## よく使う API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url
  - settings.slack_bot_token / settings.slack_channel_id
  - settings.duckdb_path / settings.sqlite_path
  - settings.env / settings.is_live / settings.is_paper / settings.is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path) -> DuckDB connection

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...) -> ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## ディレクトリ構成（概要）

以下はこの README に基づく主要ファイルのツリー（抜粋）です。

src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      schema.py
      pipeline.py
      audit.py
      quality.py
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

主要なモジュール説明:
- config.py: 環境変数管理と Settings クラスの実装
- data/jquants_client.py: J-Quants API の呼び出し・保存（DuckDB 連携）
- data/schema.py: DuckDB スキーマ定義と初期化ロジック
- data/pipeline.py: ETL ワークフロー（差分取得・保存・品質チェック）
- data/quality.py: データ品質チェック
- data/audit.py: 監査ログ（発注→約定トレース）用テーブル定義

---

## 開発／運用に関する補足

- ロギング
  - settings.log_level で制御します。監査ログは UTC タイムスタンプで保存される想定です（data.audit は SET TimeZone='UTC' を実行します）。
- テスト
  - 自動 .env 読み込みが邪魔な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化してください。
  - ETL の関数は id_token を引数で渡せるため、ネットワーク呼び出しをモックして単体テストしやすく設計されています。
- 安全性
  - 保存処理は ON CONFLICT DO UPDATE を使い冪等化しています。
  - audit の order_request_id / broker_execution_id などは冪等キーとして扱われ、二重発注の防止設計を想定しています。

---

この README はコードベースの公開 API と利用手順の概要を示すものです。実環境での運用前に .env の設定内容、DB のバックアップ、証券会社 API（kabu ステーション等）との接続設定・検証を十分に行ってください。必要であれば README に含める実行例や追加の運用手順を追記します。