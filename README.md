# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（KabuSys）。  
データ収集（J-Quants / RSS）、ETL、品質チェック、マーケットカレンダー管理、監査ログの初期化など、戦略実行の基盤となるコンポーネントを提供します。

---

## プロジェクト概要

KabuSys は以下を目的とする内部モジュール群です。

- J-Quants API からの市場データ（株価日足、四半期財務、JPX カレンダー）の取得と DuckDB への保存（冪等性を担保）
- RSS ベースのニュース収集と本文前処理、銘柄コード抽出・DB保存（SSRF / XML 攻撃等の保護を実装）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定／次/前営業日取得）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレース用スキーマ）

設計上の注目点：
- J-Quants API のレート制限を尊重（120 req/min）し、リトライ・トークン自動更新を備えています。
- DuckDB を主要な永続ストアとして利用。DDL は冪等に作成されます。
- ニュース収集はセキュリティ（defusedxml、SSRF対策、レスポンスサイズ制限）を強化しています。

---

## 主な機能一覧

- data/jquants_client.py
  - ID トークン取得（リフレッシュ）、日足・財務・カレンダー取得（ページネーション対応）
  - レートリミッタ、指数バックオフ・リトライ、401 時トークン自動更新
  - DuckDB への冪等保存（ON CONFLICT を使用）

- data/news_collector.py
  - RSS フィード取得・XML パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去・記事ID 作成（SHA-256）
  - SSRF/内部アドレス対策、gzip サイズ検査、DuckDB バルク保存（INSERT ... RETURNING）

- data/schema.py
  - Raw / Processed / Feature / Execution 層のテーブル DDL と初期化関数（init_schema, get_connection）

- data/pipeline.py
  - 差分 ETL（prices, financials, calendar）、メインエントリ run_daily_etl
  - バックフィル、品質チェック統合

- data/calendar_management.py
  - 営業日判定、next/prev_trading_day、期間内営業日取得、夜間カレンダー更新ジョブ

- data/quality.py
  - 欠損検出、スパイク検出（前日比閾値）、重複チェック、日付不整合チェック
  - QualityIssue データクラスと run_all_checks

- data/audit.py
  - 監査ログ用テーブル（signal_events, order_requests, executions）初期化関数（init_audit_schema, init_audit_db）

- config.py
  - 環境変数読み込み（.env / .env.local の自動読み込み、無効化フラグあり）
  - 必須変数チェックと settings オブジェクト（JQUANTS_REFRESH_TOKEN 等）

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo_url>

2. Python 環境を準備
   - 推奨: Python 3.9+（型注釈の Union 省略表記や型ヒントを使用）
   - 仮想環境の作成例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS/Linux
     .venv\Scripts\activate     # Windows
     ```

3. 依存ライブラリをインストール
   - 主な依存：duckdb, defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - （プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）

4. 環境変数の設定
   - .env ファイルをプロジェクトルートに作成するか、OS 環境変数で設定します。
   - 自動ロードはデフォルトで有効。無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   推奨 .env の例（.env.example 相当）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development  # development / paper_trading / live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. データベースの初期化
   - DuckDB スキーマの初期化例（Python REPL またはスクリプト）:
     ```
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - 監査ログを別DBで管理する場合:
     ```
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（簡易例）

- ETL（日次パイプライン）を実行する
  ```
  from kabusys.config import settings
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.pipeline import run_daily_etl

  # 初回のみスキーマ初期化
  conn = init_schema(settings.duckdb_path)

  # 日次 ETL を実行（戻り値は ETLResult）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 個別 ETL（株価のみ）を実行する
  ```
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")
  ```

- RSS ニュース収集を実行する
  ```
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)  # {source_name: 新規保存数}
  ```

- 市場カレンダー更新ジョブ
  ```
  from kabusys.data.calendar_management import calendar_update_job
  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved {saved} records")
  ```

- 品質チェックの実行
  ```
  from kabusys.data.quality import run_all_checks
  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

- J-Quants から直接データを取得して保存
  ```
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes()
  jq.save_daily_quotes(conn, records)
  ```

---

## 環境変数一覧（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
  - KABU_API_PASSWORD: kabu API パスワード
  - SLACK_BOT_TOKEN: Slack ボットトークン（通知等で利用する場合）
  - SLACK_CHANNEL_ID: Slack チャンネル ID

- 任意（デフォルトあり）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite ファイルパス（デフォルト: data/monitoring.db）

- 自動ロード制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化します（テスト用途等）。

---

## ディレクトリ構成

（主要ファイル・モジュールの一覧）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py        # J-Quants API クライアント（取得・保存ロジック）
      - news_collector.py       # RSS ニュース収集・前処理・保存
      - schema.py               # DuckDB スキーマ定義・初期化
      - pipeline.py             # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py  # マーケットカレンダー管理
      - audit.py                # 監査ログスキーマ初期化
      - quality.py              # データ品質チェック

---

## 実運用・注意点

- J-Quants API のレート制限（120 req/min）を守るため、連続呼び出し時の挙動に注意してください。jquants_client は内部でレート制御・リトライを行いますが、過度な同時実行は避けてください。
- DuckDB のファイルパスは並列プロセスからの同時書き込みに注意が必要です（ロックやコネクション管理）。
- news_collector は外部 URL を扱うため SSRF 対策・XML パースの安全化（defusedxml）・最大受信バイト数制限を実装していますが、運用時のログと監視を推奨します。
- 設定は .env / 環境変数で管理します。機密情報（トークン・パスワード）は安全に保管してください。
- 監査ログ（audit）は UTC タイムスタンプ保持を前提としています。DB の TimeZone 設定等に注意してください。

---

## 開発・拡張

- 新しい ETL ジョブ、データソース、戦略ロジック（strategy パッケージ）や発注実装（execution パッケージ）はモジュール分離されているため、既存のスキーマ・ユーティリティを活用して拡張できます。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い、環境の汚染を防いでください。
- jquants_client 内の _urlopen や news_collector の HTTP 層はモック可能な設計になっており、単体テストを書きやすくなっています。

---

README の内容はコードベースから抜粋した要点です。さらに実行スクリプト、CI 設定、依存関係や packaging の手順を追加する場合は pyproject.toml / requirements.txt の内容に合わせて追記してください。必要であれば README に実運用ガイド（systemd/cron ジョブ例、監視アラート例等）も作成します。要望があればお知らせください。