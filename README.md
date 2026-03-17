# KabuSys

日本株の自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
J-Quants / RSS などから市場データ・ニュースを収集し、DuckDB に格納、品質チェック、監査ログ管理、ETL パイプラインを提供します。

現在のバージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム向けのデータ基盤コンポーネント群です。主に以下を提供します。

- J-Quants API クライアント（株価日足・財務データ・マーケットカレンダー取得）
- RSS ベースのニュース収集（正規化、SSRF対策、トラッキングパラメータ除去）
- DuckDB スキーマ定義と初期化
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定・次/前営業日取得）
- 監査ログ（シグナル→発注→約定のトレース可能なテーブル群）
- 環境設定管理（.env 自動ロード、必須環境変数のラッパー）

設計上の特徴:
- API レート制限・リトライ・トークン自動リフレッシュに対応
- DuckDB への冪等保存（ON CONFLICT 句を利用）
- セキュリティ対策（defusedxml、SSRF リダイレクトブロック、受信サイズ制限）
- 品質チェック（欠損、スパイク、重複、日付不整合検出）

---

## 機能一覧

- data/jquants_client.py
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への保存）
- data/news_collector.py
  - RSS フィード取得（gzip 対応）、前処理、記事 ID 生成、DuckDB への保存（raw_news, news_symbols）
  - SSRF / gzip-bomb / トラッキングパラメータ除去等の安全対策
- data/schema.py
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution 層）と初期化関数 init_schema()
- data/pipeline.py
  - 差分 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）、統合 run_daily_etl()
  - バックフィル・品質チェック呼び出し（quality モジュール）
- data/calendar_management.py
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- data/audit.py
  - 監査ログ用テーブル定義と初期化（init_audit_schema / init_audit_db）
- data/quality.py
  - 欠損・スパイク・重複・日付不整合チェックと総合実行 run_all_checks()
- config.py
  - .env 自動読み込み（プロジェクトルート検出）と Settings クラス（環境変数ラッパー）
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## セットアップ手順

1. Python 環境の準備（推奨: venv）
   - Python 3.9+ を想定
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # Windows: .venv\Scripts\activate
     ```

2. 依存パッケージのインストール（プロジェクトに依存管理ファイルがある前提）
   - 主要依存:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```

   （実際のプロジェクトでは pyproject.toml / requirements.txt に依存を記載してください）

3. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（config.Settings で参照されるもの）:

     - J-Quants / API
       - JQUANTS_REFRESH_TOKEN (必須)
     - kabuステーション API
       - KABU_API_PASSWORD (必須)
       - KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
     - Slack
       - SLACK_BOT_TOKEN (必須)
       - SLACK_CHANNEL_ID (必須)
     - データベース
       - DUCKDB_PATH (省略時: data/kabusys.duckdb)
       - SQLITE_PATH (省略時: data/monitoring.db)
     - システム
       - KABUSYS_ENV (development | paper_trading | live) (省略時: development)
       - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (省略時: INFO)

   - サンプル .env:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データベース初期化
   - DuckDB スキーマを作成:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログを別 DB に作る場合:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/audit.duckdb")
     ```
---

## 使い方（主要な例）

- 日次 ETL の実行（市場カレンダー取得 → 株価/財務差分取得 → 品質チェック）

  ```python
  from datetime import date
  import logging
  from kabusys.data import schema, pipeline

  logging.basicConfig(level=logging.INFO)

  # DB 初期化（既に初期化済みの場合はスキップして接続を返す）
  conn = schema.init_schema("data/kabusys.duckdb")

  # 当日分の ETL を実行
  result = pipeline.run_daily_etl(conn, target_date=date.today())

  print(result.to_dict())
  ```

- RSS ニュース収集と保存（既に schema.init_schema() を実行している前提）

  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
  # 既知銘柄セットを渡すと銘柄紐付けが行われる
  known_codes = {"7203", "6758", "9984"}
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- J-Quants から株価を個別取得して保存

  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  jq.save_daily_quotes(conn, records)
  ```

- マーケットカレンダーの営業日判定

  ```python
  from datetime import date
  from kabusys.data import calendar_management as cal, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  cal.is_trading_day(conn, date(2024,1,2))
  cal.next_trading_day(conn, date(2024,1,2))
  ```

- 品質チェック手動実行

  ```python
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 自動環境変数読み込みについて

- config._find_project_root() により、.git または pyproject.toml を基準にプロジェクトルートを探索して `.env` / `.env.local` を自動ロードします。これにより CWD に依存せずパッケージ配布後も動作します。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に有用）。
- ロード順序: OS 環境 > .env.local > .env。`.env.local` は .env の値を上書きします。ただし既存の OS 環境変数は保護されます。

---

## ディレクトリ構成

以下は主要なファイル・モジュールの一覧（提供コードベースに基づく）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント（fetch/save）
    - news_collector.py       # RSS ニュース収集・保存
    - schema.py               # DuckDB スキーマ定義・初期化
    - pipeline.py             # ETL パイプライン（差分更新・統合）
    - calendar_management.py  # マーケットカレンダー管理
    - audit.py                # 監査ログ（signal / order_request / executions）
    - quality.py              # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（実際のプロジェクトでは tests/、scripts/、docs/ 等が追加されることが多いです）

---

## ログ出力

- 各モジュールは Python の logging を利用しています。実行環境で logging.basicConfig などを設定してください（LOG_LEVEL 環境変数に基づく振る舞いを行う上位設定を用意することを推奨）。

---

## 注意点 / 実運用上の考慮

- J-Quants のレート制限（120 req/min）を厳守するため内部で固定間隔のレートリミッタとリトライを実装しています。大規模取得時は制限に注意してください。
- RSS 取得は SSRF やメモリ DoS に対する防御を含みますが、外部フィードの種類により想定外の入力があるため運用時は監視を強化してください。
- DuckDB ファイルは適切にバックアップを取得してください。監査ログは削除しない前提の設計です。
- 本リポジトリのコードはデータ基盤・ETL の役割にフォーカスしており、ブローカーへの実際の送信ロジック（kabu ステーションとの完全な発注処理等）は別モジュールで実装することを想定しています。

---

## 貢献・ライセンス

この README では明示していませんが、実プロジェクト化する場合は CONTRIBUTING.md、LICENSE を用意してください。

---

README は以上です。必要であれば「導入用の小さな CLI スクリプト例」や「CI 用の DB 初期化ジョブ例」など追記します。どの情報を追加しますか？