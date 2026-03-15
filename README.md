# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（データ取得・スキーマ定義・監査ログなど）。  
このリポジトリは主にデータ取得・永続化、監査トレーサビリティ、データベーススキーマの初期化を提供します。取引エンジンや戦略本体は別モジュールで実装する想定です。

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API からの市場データ（株価日足、財務データ、JPX カレンダー）取得
- DuckDB によるデータ永続化（Raw / Processed / Feature / Execution 層）
- 取得データの冪等保存（重複上書きの回避）
- API レート制御（120 req/min 固定間隔スロットリング）とリトライ・トークン自動リフレッシュ
- 監査ログ（signal → order_request → execution のチェーンを UUID で追跡）
- 環境変数 / .env による設定管理

---

## 主な機能一覧

- data/jquants_client.py
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - get_id_token（リフレッシュトークンから ID トークンを取得）
  - save_* 関数で DuckDB に冪等保存（ON CONFLICT DO UPDATE）
  - レートリミッタ、指数バックオフリトライ、401 時の自動トークンリフレッシュなどの堅牢化
- data/schema.py
  - Raw / Processed / Feature / Execution 層のテーブル定義（DDL）
  - init_schema(db_path) で DuckDB を初期化して接続を取得
- data/audit.py
  - 監査ログ用テーブル（signal_events, order_requests, executions）とインデックス
  - init_audit_schema(conn) / init_audit_db(db_path)
- config.py
  - 環境変数の読み込み（プロジェクトルートの .env / .env.local を自動ロード）
  - settings オブジェクト経由で必須設定を取得（必須未設定時は ValueError）
  - KABUSYS_ENV / LOG_LEVEL 等の検証

---

## 前提・依存ライブラリ

- Python 3.10 以上（型アノテーションで `X | Y` を使用）
- duckdb
  - インストール例: pip install duckdb

（外部 HTTP は標準ライブラリ urllib を使用しています。その他の依存は現状不要です。）

---

## セットアップ手順

1. リポジトリをチェックアウト／インストール
   - 開発環境であれば editable install:
     pip install -e .

2. 依存ライブラリをインストール
   - 例: pip install duckdb

3. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を配置すると自動で読み込まれます。
   - 自動ロードは OS 環境変数 > .env.local > .env の順で解決され、.env.local は .env を上書きします。
   - 自動ロードを無効化したい場合:
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定してください。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知に用いる Bot トークン
   - SLACK_CHANNEL_ID (必須) — 通知送信先チャンネル ID
   - その他オプション:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live; デフォルト: development)
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL; デフォルト: INFO)

5. .env の例（プロジェクトルート）
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

---

## 使い方（簡易ガイド）

- settings から設定を参照する

  from kabusys.config import settings
  token = settings.jquants_refresh_token
  if settings.is_live:
      # 本番フロー

  注意: 必須値が未設定の場合は ValueError が発生します。

- DuckDB スキーマの初期化

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # conn は duckdb の接続オブジェクト（duckdb.DuckDBPyConnection）

  メモ: ":memory:" を指定するとインメモリ DB として初期化します。

- J-Quants からデータ取得して保存する（例: 日足を取得して保存）

  from datetime import date
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,2,1))
  saved = save_daily_quotes(conn, records)
  print(f"保存件数: {saved}")

  ポイント:
  - fetch_* 関数はページネーション対応
  - save_* 関数は ON CONFLICT DO UPDATE により冪等に保存

- ID トークンの取得（通常は自動でキャッシュされる）

  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を使用

- 監査ログの初期化

  from kabusys.data.schema import init_schema
  from kabusys.data.audit import init_audit_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn)  # 監査テーブルを既存 conn に追加

  または監査専用 DB を単独で初期化:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

- エラーハンドリングとロギング
  - jquants_client の HTTP 呼び出しは 408/429/5xx に対して指数バックオフで最大 3 回リトライします。
  - 401 受信時は自動で ID トークンを再取得して 1 回だけ再試行します。
  - リクエストは内部で 120 req/min のレート制限を守るようスロットリングされます。

---

## ディレクトリ構成

リポジトリの主要ファイルと説明（src/kabusys 以下）

- src/kabusys/__init__.py
  - パッケージ定義、バージョン（__version__ = "0.1.0"）

- src/kabusys/config.py
  - 環境変数の読み込み・検証・settings オブジェクト
  - 自動でプロジェクトルートの .env / .env.local をロードするロジック
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能

- src/kabusys/data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
  - schema.py
    - DuckDB の DDL 定義（Raw / Processed / Feature / Execution 層）
    - init_schema / get_connection
  - audit.py
    - 監査ログ（signal_events / order_requests / executions）
    - init_audit_schema / init_audit_db
  - その他:
    - raw テーブル、インデックス等の設計が含まれている

- src/kabusys/strategy/__init__.py
  - 戦略モジュール用のプレースホルダ（実装はここに追加）

- src/kabusys/execution/__init__.py
  - 発注実行関連のプレースホルダ（実装はここに追加）

- src/kabusys/monitoring/__init__.py
  - 監視・メトリクス関連プレースホルダ

---

## 注意事項 / 設計上のポイント

- 時刻は原則 UTC で扱う（fetch 時の fetched_at などは UTC で記録）。
- データ保存は可能な限り冪等（ON CONFLICT DO UPDATE）にしてあり、再取得で上書きされます。
- 監査ログは削除せず履歴として保持する前提（ON DELETE RESTRICT 等）。
- settings の検証により環境の誤設定早期発見を目指しています（KABUSYS_ENV / LOG_LEVEL の検証等）。
- J-Quants API の利用制限（120 req/min）に合わせてレート制御を実装しています。並列化する場合は上位でのさらなる制御が必要です。

---

必要であれば、README に含める例（CI 向けの起動スクリプト、より詳しい .env.example、DuckDB のクエリ例、CI 上でのテスト方法等）も追加できます。どの情報をより詳しく載せたいか教えてください。