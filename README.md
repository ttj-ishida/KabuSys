# KabuSys

日本株のデータ収集・品質管理・監査・ETL・ニュース収集・（将来的な）自動売買を想定した内部ライブラリ群です。  
主に J-Quants API と RSS をデータソースとし、DuckDB に冪等（idempotent）保存してパイプライン処理・品質チェック・監査ログを提供します。

概要・機能・使い方・セットアップ方法を以下にまとめます。

---

## プロジェクト概要

KabuSys は日本株を対象にしたデータ基盤／ETL ライブラリ群です。  
設計上のポイント：

- J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたローカルデータベース（スキーマ定義と初期化）
- 日次 ETL（差分取得・バックフィル・品質チェック）
- ニュース（RSS）収集と銘柄紐付け（SSRF対策・XML脆弱性対策・トラッキング除去）
- マーケットカレンダー管理（営業日判定・次/前営業日検索など）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 各所で冪等性を重視（ON CONFLICT や一意IDを用いた保存）

パッケージ: `kabusys`（ソースフォルダ: `src/kabusys`）

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API から株価日足・財務情報・マーケットカレンダー取得
  - レート制御（120 req/min）、再試行（指数バックオフ）、401時のトークン自動リフレッシュ
  - DuckDB への冪等保存関数（save_daily_quotes 等）

- data.schema
  - DuckDB のフルスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - スキーマ初期化 API: `init_schema(db_path)`、および接続取得 `get_connection`

- data.pipeline
  - 日次 ETL（差分取得・backfill・品質チェック）の実行: `run_daily_etl(...)`
  - 個別 ETL: `run_prices_etl`, `run_financials_etl`, `run_calendar_etl`

- data.news_collector
  - RSS フィードの取得 / 前処理 / 記事保存（raw_news） / 銘柄抽出・紐付け
  - SSRF 対策（リダイレクト検査・プライベートIP拒否）、XML の安全パース（defusedxml）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で冪等性確保

- data.calendar_management
  - market_calendar の管理、営業日判定、next/prev_trading_day、期間の営業日一覧取得、夜間更新ジョブ

- data.quality
  - 欠損検出、スパイク（急騰/急落）検出、重複チェック、日付不整合チェック
  - 各チェックは QualityIssue のリストを返す（エラー/警告で分類）

- data.audit
  - 監査ログ用スキーマ（signal_events, order_requests, executions）と初期化 API
  - トレーサビリティ確保のための設計とインデックス

- config
  - .env / 環境変数の自動ロード（プロジェクトルートの .env / .env.local）
  - 必須設定の取得ラッパ（Settings クラス）
  - 自動ロードを無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## 必要条件

- Python 3.10+
  - （コードは型注釈に `|` を使用しているため少なくとも Python 3.10 以上を想定）
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt があればその内容を利用してください。ここでは主要依存のみ記載しています）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （プロジェクトを package として扱う場合）
     - pip install -e .

4. 環境変数（.env）を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれる（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すれば無効化可能）。
   - 必須環境変数（Settings が必須扱いするもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意／デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマの初期化（例）
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     # 監査スキーマを追加する場合
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（主要な API＆実行例）

以下は簡単な利用例です。実運用ではログやエラーハンドリングを追加してください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（差分更新・品質チェック込み）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を与えなければ今日
  print(result.to_dict())
  ```

- 個別ジョブ
  - 株価差分 ETL:
    ```python
    from kabusys.data.pipeline import run_prices_etl
    from datetime import date
    run_prices_etl(conn, target_date=date.today())
    ```
  - カレンダー更新ジョブ（夜間バッチ相当）:
    ```python
    from kabusys.data.calendar_management import calendar_update_job
    calendar_update_job(conn)
    ```

- ニュース収集
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に用いる有効コード集合（例: {"7203","6758",...}）
  results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
  print(results)
  ```

- J-Quants トークン取得（必要に応じて）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を参照して自動で取得
  ```

- 監査ログ用 DB を別ファイルで初期化する（必要に応じて）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 環境設定確認
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env, settings.is_live)
  ```

---

## 実行環境・運用上の注意

- API レートとリトライ
  - J-Quants クライアントは 120 req/min を想定しており、モジュール内で簡易レート制御を行っています。複数プロセスで同時に API を叩く場合は注意してください。

- 環境変数の自動読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動で読み込みます。テストや特殊用途では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます。

- DuckDB のファイルパス
  - デフォルトは `data/kabusys.duckdb`。パスの親ディレクトリは自動作成されます。

- セキュリティ考慮
  - news_collector は SSRF や XML Bomb に対する対策を実装していますが、外部フィードの扱いには引き続き注意してください。
  - 秘密情報（API トークン等）は .env に平文で置くことになるため、適切なアクセス制御を行ってください。

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境設定 / .env 自動読み込み
    - data/
      - __init__.py
      - jquants_client.py          — J-Quants API クライアント（取得 + 保存）
      - news_collector.py          — RSS ニュース収集・前処理・保存・銘柄紐付け
      - schema.py                  — DuckDB スキーマ定義 & 初期化
      - pipeline.py                — ETL パイプライン（差分取得 / 日次ETL）
      - calendar_management.py     — 市場カレンダー管理、営業日判定
      - audit.py                   — 監査ログスキーマと初期化
      - quality.py                 — データ品質チェック
    - strategy/
      - __init__.py                — （戦略モジュール用のプレースホルダ）
    - execution/
      - __init__.py                — （発注/実行管理用のプレースホルダ）
    - monitoring/
      - __init__.py                — （監視・モニタリング用プレースホルダ）

この README はコードベースから抽出した機能に基づくドキュメントです。  
実際の運用／拡張ではログ設定、エラーハンドリング、ジョブスケジューラ（cron / Airflow / Kubernetes CronJob など）、監視（Slack 通知等）を組み合わせて使ってください。

---

もし README に追加したい内容（例: CI/CD、テストの実行、より具体的な .env.example、サンプルスクリプト等）があれば教えてください。必要に応じて追記します。