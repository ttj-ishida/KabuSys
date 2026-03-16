# KabuSys

日本株自動売買システムのコアライブラリ（ライブラリ部分のみ）。  
このリポジトリはデータ取得・ETL、データ品質チェック、DuckDBスキーマ定義、監査ログ基盤などを提供します。戦略実装や発注実行ロジックは別モジュール（strategy / execution）に分離できる設計です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム構築のための基盤ライブラリです。主に以下を提供します。

- J-Quants API からの時系列・財務・マーケットカレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた三層データレイヤ（Raw / Processed / Feature）と Execution/Audit テーブル定義
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal → order_request → execution に渡る UUID ベースのトレーサビリティ）

設計方針としては「冪等性」「トレーサビリティ」「Look-ahead-bias の回避」を重視しています。

---

## 機能一覧

- 環境設定管理（.env 自動ロード、必須値チェック）
  - 必須環境変数の取得・検証を行う Settings クラスを提供
- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、四半期財務、マーケットカレンダー取得
  - レート制限（120 req/min）を守る RateLimiter
  - 401 の場合の自動トークンリフレッシュ（1 回）とリトライ（指数バックオフ）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL
  - インデックス定義と初期化ユーティリティ
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル（デフォルト backfill_days=3）
  - ETL 実行結果を ETLResult で返却（品質問題・エラー情報含む）
- データ品質チェック（src/kabusys/data/quality.py）
  - 欠損データ、スパイク（前日比）、主キー重複、日付不整合の検出
  - 問題は QualityIssue リストで返す（severity: error / warning）
- 監査ログ（src/kabusys/data/audit.py）
  - signal_events, order_requests, executions テーブルなど
  - 発注フローのトレーサビリティを保証
- placeholder モジュール: strategy, execution, monitoring（将来の拡張用）

---

## 必要条件 / 依存

- Python 3.10+
  - 型注釈に `X | None` 形式を使用しているため 3.10 以上を推奨します
- 依存パッケージ
  - duckdb

インストール例:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate (macOS/Linux) / .venv\Scripts\activate (Windows)
- duckdb インストール:
  - pip install duckdb

（setup.py / pyproject.toml がある場合は pip install -e . 等でパッケージとしてインストールしてください）

---

## 環境変数

自動でルートプロジェクトの `.env` / `.env.local` を読み込みます（優先順位: OS > .env.local > .env）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（Settings により要求されます）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API のパスワード
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack チャンネル ID

任意 / デフォルト値あり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   - git clone <repo>
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存をインストール
   - pip install duckdb

3. 環境変数を用意
   - プロジェクトルートに `.env` を作成し、必要な環境変数を設定

4. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで schema を初期化する:
     - from kabusys.data.schema import init_schema
     - from kabusys.config import settings
     - conn = init_schema(settings.duckdb_path)

5. 監査ログ（オプション）
   - from kabusys.data.audit import init_audit_schema
   - init_audit_schema(conn)  # 既存の conn に監査テーブルを追加

---

## 使い方（サンプル）

- J-Quants トークンの取得:
  - from kabusys.data import jquants_client as jq
  - id_token = jq.get_id_token()  # settings.jquants_refresh_token を使って POST

- DuckDB 初期化:
  - from kabusys.data.schema import init_schema
  - from kabusys.config import settings
  - conn = init_schema(settings.duckdb_path)

- 日次 ETL を実行（当日分）:
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - print(result.to_dict())  # ETLの結果・品質問題等を確認

- 特定日（例: 2024-01-01）に対して ETL 実行:
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2024, 1, 1))

- 部分的な処理（価格データのみ）:
  - from kabusys.data.pipeline import run_prices_etl
  - fetched, saved = run_prices_etl(conn, target_date=date.today())

- 監査ログ初期化（独立DBを使う場合）:
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

注意点:
- J-Quants API に対するリクエストは内部でレート制御・リトライを行います。アプリ側で追加のスロットリングを行う必要は基本的にはありませんが、大量の並列リクエストは避けてください。
- ETL は各ステップが独立してエラーハンドリングされ、1ステップ失敗でも残りのステップは継続します。結果の `ETLResult.errors` を確認してください。
- 品質チェックは Fail-Fast ではなく、検出結果を一覧で返します。重大な問題があれば呼び出し側で停止を検討してください。

---

## API / 主要モジュール概要

- kabusys.config
  - settings: Settings インスタンス（環境変数取得）
  - 自動 .env ロード（.git または pyproject.toml をルート判別）

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) / save_financial_statements(...) / save_market_calendar(...)

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...)

- kabusys.data.quality
  - run_all_checks(...)
  - check_missing_data(...)
  - check_spike(...)
  - check_duplicates(...)
  - check_date_consistency(...)

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## ディレクトリ構成

リポジトリ内の主要ファイル / 位置は以下の通りです（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                             # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py                   # J-Quants API クライアント（取得・保存）
      - schema.py                           # DuckDB スキーマ定義・初期化
      - pipeline.py                         # ETL パイプライン
      - audit.py                            # 監査ログ定義・初期化
      - quality.py                          # データ品質チェック
    - strategy/
      - __init__.py                          # 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py                          # 発注実行モジュール（拡張ポイント）
    - monitoring/
      - __init__.py                          # 監視関連（拡張ポイント）

---

## 開発上の注意 / 設計ノート

- J-Quants のレート制限（120 req/min）を遵守するため、内部的に固定間隔のスロットリングを行っています。
- HTTPエラー時のリトライ戦略:
  - 408 / 429 / 5xx 系は指数バックオフで最大 3 回リトライ
  - 401 はトークン自動リフレッシュを行い 1 回リトライ
- データ保存は冪等に実装されており、DuckDB 側で ON CONFLICT DO UPDATE を使用して更新します。
- 全ての監査ログ（audit）テーブルは UTC タイムスタンプを前提としています（init_audit_schema は SET TimeZone='UTC' を実行します）。
- ETL は差分更新を行い、バックフィル日数を指定して後出し修正（API の修正等）を吸収します。

---

## 今後の拡張案

- execution モジュールに具体的な broker 接続（kabuステーション）実装
- strategy レイヤのサンプル戦略やハイパーパラメータ管理
- モニタリング用ダッシュボード / アラート実装
- 並列 ETL 実行時の分散レート制御

---

## ライセンス / 貢献

このドキュメントではライセンスは明記していません。実装コードのライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください。

---

README で補足してほしい点（例: 具体的な起動スクリプト、CI 設定、追加の依存追記など）があれば教えてください。必要に応じてサンプル .env.example やスニペットを追加します。