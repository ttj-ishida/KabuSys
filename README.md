# KabuSys

日本株自動売買プラットフォームの一部を実装した Python パッケージ（プロトタイプ）。  
このリポジトリには主にデータ取得・ETL、データスキーマ、品質チェック、監査ログの初期化ロジックが含まれます。

> 注: 本 README は配布されたコードベースの説明を目的としており、ブローカー接続や実際の発注処理など本番稼働に必要な部分は別途実装が必要です。

## プロジェクト概要

- J-Quants API から株価（OHLCV）、財務指標、JPX マーケットカレンダーを取得するクライアント実装を含む。
- 取得データを DuckDB に階層化（Raw / Processed / Feature / Execution）されたスキーマで永続化するDDLを提供。
- ETL パイプライン（差分取得・バックフィル・保存）と品質チェック（欠損、スパイク、重複、日付不整合）を実行可能。
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）用のスキーマ初期化機能を提供。
- 環境変数（.env）経由で設定を管理するユーティリティを搭載（自動読み込み機能あり）。

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API の認証（refresh token → id_token）
  - 日足（fetch_daily_quotes）、財務（fetch_financial_statements）、市場カレンダー（fetch_market_calendar）の取得
  - 取得データを DuckDB に冪等的に保存する save_* 関数
  - API レート制御（120 req/min）、リトライ、トークン自動リフレッシュ、fetched_at 記録 等

- data/schema.py
  - Raw / Processed / Feature / Execution 層のテーブル DDL 定義
  - init_schema(db_path) により DuckDB を初期化（冪等）
  - get_connection(db_path) による既存 DB への接続取得

- data/pipeline.py
  - 差分 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 日次 ETL エントリポイント run_daily_etl（品質チェックを含む）
  - ETL 結果を収める ETLResult データクラス

- data/quality.py
  - 欠損データ、スパイク、重複、日付不整合のチェック
  - run_all_checks でまとめて実行し QualityIssue のリストを返却

- data/audit.py
  - 監査ログ用テーブル（signal_events / order_requests / executions）定義と初期化
  - init_audit_schema / init_audit_db を提供（UTC タイムスタンプ利用）

- config.py
  - .env 自動読み込み（プロジェクトルートの .git または pyproject.toml を探索）
  - 環境変数ラッパ（settings）で必須キー取得
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能

## 前提・依存

- Python 3.10+
  - （型アノテーションで `X | None` を利用しているため）
- 依存ライブラリ（最低限）
  - duckdb

必要に応じて以下をインストールしてください（仮の例）:

pip install duckdb

※ 本リポジトリの他の機能（Slack連携やkabuステーション連携等）を使う場合は別途依存ライブラリが必要になります。

## セットアップ手順

1. リポジトリをクローン / 展開

   git clone <repo-url>
   cd <repo>

2. Python 仮想環境を作成・有効化（任意だが推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install duckdb

   （追加の依存があれば requirements.txt / pyproject.toml からインストール）

4. 環境変数 (.env) の準備

   プロジェクトルートに .env（または .env.local）を作成してください。主要な環境変数:

   - JQUANTS_REFRESH_TOKEN (必須)  
     J-Quants のリフレッシュトークン。jquants_client の認証に使用。

   - KABU_API_PASSWORD (必須)  
     kabuステーション API のパスワード（将来の発注機能で使用想定）。

   - SLACK_BOT_TOKEN (必須)  
     Slack 通知用ボットトークン。

   - SLACK_CHANNEL_ID (必須)  
     Slack 通知先チャンネル ID。

   - DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)  
     DuckDB ファイルパス（":memory:" も可）。

   - SQLITE_PATH (任意、デフォルト: data/monitoring.db)  
     監視/モニタリング用途の SQLite ファイルパス（コードでは参照のみ）。

   - KABUSYS_ENV (任意、デフォルト: development)  
     有効値: development, paper_trading, live

   - LOG_LEVEL (任意)  
     有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

   自動読み込みを無効化したい場合:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境に設定

## 使い方（簡単な例）

以下は最小限の使用例です。DuckDB スキーマを初期化し、日次 ETL を実行する例です。

- スキーマ初期化（ファイル DB）

from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（取得 → 保存 → 品質チェック）

from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())  # ETL の結果概要

- テスト用にインメモリ DB を使う

from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
# 以降同様に run_daily_etl(conn)

- J-Quants のトークンを直接使ってデータを取得する（テスト用）

from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を利用
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,1,31))

- 監査用テーブルの初期化（既存 conn に追加）

from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

### 主な公開関数（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token / settings.kabu_api_password / settings.duckdb_path / settings.env / settings.log_level など

- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path) -> duckdb connection

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_prices_etl(conn, target_date, ...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(conn, target_date=None, ...)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

## 推奨運用メモ / 注意点

- J-Quants のレート制限（120 req/min）およびエラーハンドリングは jquants_client に実装されています。大量リクエストの場合は注意してください。
- get_id_token はリフレッシュトークンを使用して id_token を取得します。401 発生時には自動で1回リフレッシュしてリトライする設計です。
- DuckDB の初期化は冪等です（既存テーブルがあれば上書きは行いません）。監査ログを追加したい場合は init_audit_schema を併用してください。
- 品質チェックは Fail-Fast ではなく全件収集します。ETL 実行後の result.quality_issues を評価して運用側で停止等を決定してください。
- タイムスタンプは監査関連で UTC を前提としています（init_audit_schema は SET TimeZone='UTC' を実行）。

## ディレクトリ構成

下記はこのパッケージの主要ファイル・ディレクトリ構成（配布時の src 配下を想定）:

src/kabusys/
- __init__.py
- config.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py
- strategy/
  - __init__.py
- data/
  - __init__.py
  - jquants_client.py
  - schema.py
  - pipeline.py
  - quality.py
  - audit.py
  - (その他: pipeline/ETL・品質関連モジュール)

主要ファイルの説明:
- config.py: .env 自動読み込み・settings オブジェクトを提供
- data/jquants_client.py: J-Quants API クライアント（取得・保存ロジック）
- data/schema.py: DuckDB スキーマ定義 / 初期化
- data/pipeline.py: ETL パイプライン（差分取得・保存・品質チェック）
- data/quality.py: データ品質チェック
- data/audit.py: 監査ログ（トレーサビリティ）スキーマ

## 開発・テストについて

- テスト時は環境変数を直接設定するか、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを止め、テスト用の env をプロセスに注入してください。
- 単体テストでは DuckDB のインメモリ ":memory:" を使用するとディスク不要で早く実行できます。
- id_token の取得や API 呼び出しは外部通信を伴うため、ユニットテストではモック化・トークン注入を推奨します（jquants_client の関数は id_token を引数で注入可能）。

---

この README は現状のコードベースに基づく概要ドキュメントです。実運用する場合は接続先ブローカーの認証・注文フローの実装、Slack 等通知の実装、運用手順（CI/CD, バックアップ, ログ管理）を必ず整備してください。