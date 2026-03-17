# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants API や RSS ニュースを取り込み、DuckDB に保存して ETL、品質チェック、監査トレースまでをカバーすることを目的としています。

バージョン: 0.1.0

---

## 概要

主な目的:
- J-Quants から株価（日足）・財務・マーケットカレンダーを安全かつ冪等に取得して保存
- RSS からニュースを収集して記事と銘柄紐付けを行う
- DuckDB 上にデータスキーマを定義・初期化する（Raw / Processed / Feature / Execution / Audit）
- 日次 ETL（差分取得／バックフィル／品質チェック）を実行
- マーケットカレンダー管理（営業日判定、前後営業日取得）
- 監査ログ（signal → order → execution のトレーサビリティ）
- データ品質チェック（欠損、重複、スパイク、日付不整合）

設計上の特徴:
- API レート制限の遵守（J-Quants: 120 req/min のスロットリング）
- リトライ、指数バックオフ、401 応答時のトークン自動リフレッシュ
- DuckDB への保存は冪等処理（ON CONFLICT ... DO UPDATE / DO NOTHING）
- RSS 収集は SSRF 対策、gzip サイズ制限、xml 安全パーサを使用
- ETL は差分更新とバックフィルをサポートし、品質チェックは Fail-Fast とせず問題を収集

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - Settings クラス経由で設定値を取得

- J-Quants API クライアント（kabusys.data.jquants_client）
  - token リフレッシュ（get_id_token）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系関数で DuckDB に冪等保存
  - レートリミッタ、リトライ、401 自動リフレッシュ、fetched_at 記録

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（gzip 対応、XML パース保護）
  - URL 正規化・トラッキングパラメータ除去・記事 ID は SHA-256（先頭32文字）
  - SSRF・プライベートアドレス検査・サイズ制限・DB へのバルク保存
  - 銘柄コード抽出と news_symbols 紐付け

- データスキーマ管理（kabusys.data.schema）
  - DuckDB 上のテーブル定義（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, signals, orders, trades, positions, など）
  - init_schema / get_connection

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl（カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分／バックフィルロジック

- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - calendar_update_job（夜間バッチでのカレンダー更新）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルと初期化関数（init_audit_schema / init_audit_db）
  - UTC 固定、冪等キー、インデックス定義

- データ品質チェック（kabusys.data.quality）
  - 欠損チェック、重複チェック、スパイク検出、日付整合性チェック
  - run_all_checks により一覧で問題を取得

---

## セットアップ手順

前提:
- Python 3.9+（typing の Union | 型等を使用しているため Python 3.10+ を推奨）
- duckdb, defusedxml などのサードパーティパッケージ

例:

1. リポジトリをクローンし、仮想環境を作成する
   - Unix/macOS:
     ```bash
     git clone <repo-url>
     cd <repo-dir>
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows Powershell:
     ```powershell
     git clone <repo-url>
     cd <repo-dir>
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール
   - 最低限:
     ```bash
     pip install duckdb defusedxml
     ```
   - パッケージ化されている場合はプロジェクトルートで:
     ```bash
     pip install -e .
     ```
   - （必要に応じて logging/Slack 連携用ライブラリ等を追加）

3. 環境変数を設定
   - プロジェクトルートに `.env`（および `.env.local`）を置くと、自動で読み込まれます（デフォルト）。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知（必要な場合）
     - SLACK_CHANNEL_ID — Slack 通知先
   - 任意/デフォルト:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト "development"
     - LOG_LEVEL — デフォルト "INFO"
     - DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH — デフォルト "data/monitoring.db"

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマ初期化
   - Python スクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査DB 初期化（監査専用DBを別で用意する場合）:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（基本的な例）

- 日次 ETL を実行する最小例:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
  print(result.to_dict())
  ```

- RSS ニュース収集ジョブを実行:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema("data/kabusys.duckdb")
  # known_codes を渡すと記事と銘柄の紐付けも行う
  known_codes = {"7203", "6758"}
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(stats)
  ```

- カレンダー更新バッチ:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 品質チェック単体実行:
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

- J-Quants の ID トークンを手動取得:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token が環境変数から読み込まれます
  ```

注意点:
- run_daily_etl 等は内部で例外を捕捉して継続する設計ですが、戻り値の ETLResult.errors や quality_issues をチェックして運用フローを判断してください。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py  -- 環境変数読み込みと Settings
    - data/
      - __init__.py
      - jquants_client.py      -- J-Quants API クライアント（取得 / 保存ロジック）
      - news_collector.py      -- RSS 収集と記事保存、銘柄抽出
      - schema.py              -- DuckDB スキーマ定義と init_schema
      - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py -- カレンダー管理・バッチ
      - audit.py               -- 監査ログスキーマ / 初期化
      - quality.py             -- データ品質チェック
    - strategy/
      - __init__.py
      (戦略モジュールの土台)
    - execution/
      - __init__.py
      (発注／執行関連の土台)
    - monitoring/
      - __init__.py
      (監視・メトリクス等の土台)

この README に記載されていない小さなユーティリティや内部関数は各ファイル内の docstring を参照してください。

---

## 運用上の注意 / ベストプラクティス

- 機密情報（トークン・パスワード）は .env.local に置き、リポジトリには絶対コミットしないでください。
- DuckDB はファイルベースの DB なのでバックアップ戦略（定期コピー等）を用意してください。
- run_daily_etl は品質チェックの結果（error/warning）を返すため、監視系（Slack 通知など）に連携すると良いです。
- API レート・リトライの動作は jquants_client 内に定義されていますが、大量取得時は処理間隔やリトライの影響を考慮してください。
- RSS フィード取得では外部 URL の扱いに注意（SSRF 対策済みですが、運用上のホワイトリスト化等も検討ください）。

---

必要に応じて README に追記します。特定の利用例（戦略の実装、kabu ステーションへの接続、Slack 通知の組み込みなど）を追加したい場合は用途を教えてください。