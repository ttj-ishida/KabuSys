# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants / RSS 等から市場データ・ニュースを取得して DuckDB に蓄積し、ETL・品質チェック・監査ログ・カレンダー管理・ニュース収集などの基盤処理を提供します。

## 概要
- J-Quants API を通じて株価日足（OHLCV）、財務データ、JPX のマーケットカレンダーを取得・保存します。
- RSS フィードからニュース記事を収集して正規化・DB保存・銘柄紐付けを行います。
- DuckDB をデータレイクとして利用するスキーマ定義（Raw / Processed / Feature / Execution / Audit）を提供します。
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）を実行可能です。
- カレンダー管理（営業日判定、next/prev trading day 等）やデータ品質チェック（欠損、スパイク、重複、日付不整合）を備えます。
- セキュリティ・堅牢性に配慮した実装（レート制限、リトライ、トークン自動リフレッシュ、SSRF対策、XML防御、Gzip上限など）。

## 主な機能一覧
- 環境設定管理
  - .env（.env.local）自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得とバリデーション
- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制限（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大3回、408/429/5xx 対応）
  - 401 時のリフレッシュトークンによる自動トークン更新（1回のみ）
  - ページネーション対応、取得日時（fetched_at）記録
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- RSS ニュース収集（kabusys.data.news_collector）
  - RSS 取得・XML パース（defusedxml で安全に）
  - URL 正規化とトラッキングパラメータ除去
  - SSRF 対策（スキーム検証、プライベートホスト排除、リダイレクト検査）
  - 受信バイト数上限（メモリ DoS 対策）、gzip 解凍上限
  - 記事ID：URL 正規化後の SHA-256 ハッシュ（先頭32文字）で冪等性
  - DuckDB へのバルク保存（INSERT ... RETURNING、トランザクション）
  - テキスト前処理・銘柄コード（4桁）抽出と銘柄紐付け
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層の DDL を提供
  - init_schema(db_path) で初期化（冪等）、get_connection で接続取得
  - 監査ログ用 init_audit_db / init_audit_schema（UTC タイムゾーン固定）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（DB の最終取得日を基に差分取得）
  - backfill による後出し修正吸収
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一括実行
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による差分更新（バックフィル・健全性チェック）
- データ品質チェック（kabusys.data.quality）
  - 欠損（missing_data）、スパイク（spike）、重複（duplicates）、日付不整合（future_date / non_trading_day）
  - run_all_checks でまとめて実行し QualityIssue を返却

## セットアップ手順

前提:
- Python 3.10+（型注釈に | を使用しているため）
- duckdb、defusedxml などが必要

1. リポジトリをクローンしてインストール（開発環境）
   - pipenv / poetry / venv 等お好みの環境で仮想環境を作成してください。
   - 例（pip）:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -U pip
     - pip install duckdb defusedxml

   - パッケージとして利用する場合は、プロジェクトの setup/pyproject があれば pip install -e . を使ってください。

2. 環境変数の設定
   - プロジェクトルートの .env または .env.local に必要な環境変数を設定します。
   - 自動読み込みは、.git または pyproject.toml を含むディレクトリをプロジェクトルートとして探索して行われます。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 必須の環境変数（kabusys.config.Settings が参照）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API パスワード（kabu ステーション向け）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID

   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）

   - サンプル .env（README 用）
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - KABU_API_PASSWORD=your_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C0123456789
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO
     - DUCKDB_PATH=data/kabusys.duckdb

3. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")
   - 監査用 DB を別に作る場合:
     - from kabusys.data import audit
     - audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

## 使い方（代表的な例）

- 日次 ETL 実行（単純な呼び出し例）
  - from kabusys.data import schema, pipeline
  - conn = schema.init_schema("data/kabusys.duckdb")
  - result = pipeline.run_daily_etl(conn)
  - print(result.to_dict())

- ニュース収集ジョブ（RSS 取得→DB 保存→銘柄紐付け）
  - from kabusys.data import schema, news_collector
  - conn = schema.init_schema("data/kabusys.duckdb")
  - known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードのセット
  - results = news_collector.run_news_collection(conn, known_codes=known_codes)
  - print(results)

- カレンダー更新バッチ
  - from kabusys.data import schema, calendar_management
  - conn = schema.init_schema("data/kabusys.duckdb")
  - saved = calendar_management.calendar_update_job(conn)
  - print(f"saved={saved}")

- J-Quants データ取得（低レベル）
  - from kabusys.data import jquants_client as jq
  - token = jq.get_id_token()  # settings.jquants_refresh_token を使用
  - quotes = jq.fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))

- 品質チェックを個別実行
  - from kabusys.data import quality, schema
  - conn = schema.get_connection("data/kabusys.duckdb")
  - issues = quality.run_all_checks(conn)
  - for i in issues: print(i)

注意:
- run_daily_etl 等の関数は内部で例外を捕捉しつつ継続する設計です。戻り値（ETLResult）を参照してエラーや品質問題の有無を確認してください。
- J-Quants API のレート制限やリトライは内部で制御されますが、長時間・大規模なバッチ実行では監視を行ってください。

## 主要モジュール（要点）
- kabusys.config: 環境変数・設定の管理、自動 .env ロード（無効化可能）
- kabusys.data.jquants_client: J-Quants API クライアント（取得 / 保存）
- kabusys.data.news_collector: RSS 収集・正規化・保存・銘柄抽出
- kabusys.data.schema: DuckDB スキーマ定義・初期化
- kabusys.data.pipeline: ETL パイプライン（差分取得・保存・品質チェック）
- kabusys.data.calendar_management: 市場カレンダー関連ユーティリティ
- kabusys.data.quality: データ品質チェック
- kabusys.data.audit: 監査ログ用スキーマと初期化

## ディレクトリ構成
プロジェクトの主要ファイル／ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（実リポジトリに pyproject.toml / requirements.txt / .env.example 等があれば合わせて参照してください）

## 注意事項・設計上のポイント
- DuckDB の DDL は冪等（CREATE TABLE IF NOT EXISTS）で定義されています。init_schema は既存テーブルを上書きせず安全に実行できます。
- ニュース収集は外部 HTTP を扱うため SSRF 対策、受信サイズ上限、gzip 解凍上限など複数の安全策を実装しています。
- J-Quants API はページネーション・トークン管理を行い、トークン期限切れ時の自動リフレッシュをサポートします。リトライポリシーとレート制御が組み込まれています。
- 監査ログ（audit）は UTC タイムゾーン固定で保存し、冪等キー（order_request_id / broker_execution_id 等）を活用して二重発注や重複挿入の影響を最小化する設計です。
- 品質チェックは Fail-Fast ではなく全件検査して問題を列挙する方式です。呼び出し元が結果に基づき運用判断を行ってください。

---

不明点や README に追加したいサンプルや CI / デプロイ手順があれば教えてください。必要に応じて .env.example や簡易運用スクリプトのテンプレートも作成します。