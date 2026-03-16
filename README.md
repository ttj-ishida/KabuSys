# KabuSys

日本株向けの自動売買／データプラットフォームのコアライブラリです。  
J-Quants API から市場データを取得して DuckDB に格納・整備し、品質チェックや監査ログの仕組みを提供します。戦略・実行・モニタリング層と連携するための基盤コンポーネント群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つモジュール群で構成されています。

- J-Quants API から株価（OHLCV）・財務データ・JPXマーケットカレンダーを取得
- 取得データを DuckDB に冪等（idempotent）に格納（ON CONFLICT DO UPDATE）
- ETL（差分取得・バックフィル）パイプラインの提供
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ

設計上の特徴：
- API レート制御（J-Quants: 120 req/min の固定間隔スロットリング）
- リトライ・トークン自動リフレッシュ
- Look-ahead bias 回避のため取得日時（UTC）を記録
- DuckDB を用いたシンプルで高速なローカルデータストア

---

## 機能一覧

- data.jquants_client
  - J-Quants からのデータ取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - 認証トークン自動取得（get_id_token）
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
  - レートリミット、リトライ、401 の自動リフレッシュ対応

- data.schema
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution レイヤ）
  - init_schema(db_path) による初期化（冪等）

- data.pipeline
  - 差分ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 日次バッチ統合入口 run_daily_etl（品質チェック実行オプション付き）
  - backfill やカレンダー先読みの自動処理

- data.quality
  - 欠損チェック / スパイク検出 / 重複チェック / 日付不整合チェック
  - QualityIssue データクラスにより問題の一覧を返却

- data.audit
  - 監査ログ用スキーマ（signal_events / order_requests / executions）
  - init_audit_schema / init_audit_db によるセットアップ

- config
  - .env や環境変数から設定を自動ロード
  - settings オブジェクト経由で設定項目にアクセス可能

---

## 必要条件

- Python 3.10 以上（型記法に "|" を使用）
- 依存パッケージ（最低限）
  - duckdb

（注）パッケージ化時に追加のライブラリが必要になる可能性があります（例: Slack 通知等）。本リポジトリ内の他モジュールを利用する場合は該当モジュールの依存も確認してください。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成

   ```
   git clone <this-repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール

   最小：
   ```
   pip install duckdb
   ```

   （開発用）
   ```
   pip install -e .
   ```

3. 環境変数の設定

   プロジェクトルートに `.env` または `.env.local` を置くことで自動読み込みされます（自動読み込みはデフォルトで有効）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須となる主な環境変数（settings 参照）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意 / デフォルトあり:
   - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
   - LOG_LEVEL (DEBUG / INFO / ...)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)

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

4. DuckDB スキーマの初期化

   Python REPL やスクリプトから初期化できます。DB ファイルの親ディレクトリがなければ自動作成されます。

   例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

   監査ログテーブルを追加する場合:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```
   または別DBとして初期化:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（基本例）

以下は代表的な利用パターンです。

- J-Quants の ID トークン取得（単独利用）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して POST で取得
  ```

- データ取得と保存（例：日足を取得して DuckDB に保存）
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved:", saved)
  ```

- 日次ETL の実行（カレンダー・株価・財務・品質チェックを統合）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2023,3,10))
  for i in issues:
      print(i)
  ```

- audit スキーマの初期化（既存接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  ```

注意点：
- run_daily_etl は内部で各ステップを独立して実行し、エラーが発生したステップはロギングして結果オブジェクトにエラーメッセージを残します。致命的な品質問題は run_daily_etl の戻り値（ETLResult）で確認してください。
- J-Quants API はレート制限およびリトライ挙動に従います。大量取得時は注意してください。

---

## 設定 (config) の挙動

- settings オブジェクト経由で必要設定にアクセスできます（例: settings.jquants_refresh_token）。
- パッケージインポート時にプロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` → `.env.local` を自動ロードします（OS 環境変数が優先、.env.local は上書き可）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント / 保存処理
    - schema.py — DuckDB スキーマ定義と初期化
    - pipeline.py — ETL パイプライン（差分更新・品質チェック等）
    - quality.py — データ品質チェック
    - audit.py — 監査ログスキーマ・初期化
    - pipeline.py — ETL 実行ロジック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記以外にドキュメントファイルや追加モジュールが含まれることがあります）

---

## ロギング・デバッグ

- settings.log_level (環境変数 LOG_LEVEL) でログレベルを制御できます（デフォルト: INFO）。
- ETL や API クライアントは例外発生時に logger.exception を出します。自己環境に合わせてログ設定（ハンドラーやフォーマッタ）を行ってください。

---

## 注意事項 / ベストプラクティス

- 実運用での「live」モードに切り替える場合は KABUSYS_ENV=live を設定し、認証情報・資金管理・テストを十分に行ってください。
- DuckDB ファイルはローカルに保存されるためバックアップやアクセス管理を検討してください（特に監査ログを含むDBは機密性が高い）。
- API トークンやパスワードは `.env` や CI のシークレットストアで安全に管理してください。
- J-Quants API の利用規約・レート制限に従ってください。

---

必要であれば、README に載せるサンプル .env.example ファイルや、CI / デプロイ手順、実行スクリプト (cron / Airflow / Prefect 等) のテンプレートも作成します。どの形式が良いか教えてください。