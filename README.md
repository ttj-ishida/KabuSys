# KabuSys

日本株向けの自動売買基盤ライブラリ（プロトタイプ）。データ収集（J-Quants / RSS）、ETL、データ品質チェック、マーケットカレンダー管理、監査ログスキーマなどを提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。主に以下の役割を持ちます。

- J-Quants API からの市場データ取得（株価日足、財務データ、マーケットカレンダー）
- RSS フィードからのニュース収集と銘柄紐付け
- DuckDB によるスキーマ定義・永続化（Raw / Processed / Feature / Execution / Audit 層）
- ETL（差分取得・バックフィル）とデータ品質チェック
- マーケットカレンダーの営業日ロジック
- 監査ログ（シグナル→発注→約定のトレース）スキーマ

設計上の特徴：
- API レート制御・リトライ・トークン自動リフレッシュ
- データ保存は冪等（ON CONFLICT による上書き/排除）
- Look-ahead bias を避けるための fetched_at / UTC の扱い
- セキュリティ考慮（RSS の SSRF防止、defusedxml の利用、受信サイズ制限など）

---

## 主な機能一覧

- data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(...), save_market_calendar(...)

- data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - extract_stock_codes(text, known_codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- data.schema
  - init_schema(db_path)  -- DuckDB スキーマ初期化（Raw/Processed/Feature/Execution）
  - get_connection(db_path)

- data.pipeline
  - run_prices_etl(...), run_financials_etl(...), run_calendar_etl(...)
  - run_daily_etl(conn, target_date=None, ...)  -- 日次 ETL の入口

- data.calendar_management
  - is_trading_day(conn, d), next_trading_day(...), prev_trading_day(...), get_trading_days(...)
  - calendar_update_job(conn, lookahead_days=90)

- data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency

- data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- config
  - settings: 環境変数を参照する Settings オブジェクト（自動 .env ロード機能あり）

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部で | が使われているため 3.10 以上を推奨）
- pip, virtualenv 等

1. リポジトリを取得、仮想環境を作成して有効化
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - defusedxml
   - 実際の requirements.txt はプロジェクトに合わせて作成してください。例:
     pip install duckdb defusedxml

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config モジュールがプロジェクトルートを検出して読み込みます）。
   - 自動ロードを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用（必須）
   - その他（任意/デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live), LOG_LEVEL (DEBUG|INFO|...)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   例 .env（サンプル）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要な操作例）

README 内では Python スクリプトや REPL から使う例を示します。

1) DuckDB スキーマの初期化
- Python から:
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")  # ファイルがなければ作成
  ```

2) 日次 ETL（株価 / 財務 / カレンダー 取得 + 品質チェック）
- Python から:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection, init_schema
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を省略すると本日
  print(result.to_dict())
  ```

3) 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved: {saved}")
  ```

4) ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は既知の銘柄コード集合（例: 全上場銘柄の 4 桁コード）
  results = run_news_collection(conn, known_codes={"7203","6758"})
  print(results)
  ```

5) 監査ログスキーマ初期化（signal_events / order_requests / executions）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

6) J-Quants API を直接呼ぶ（テスト用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

ログや例外は各モジュールで適切に記録されます。ETL は各ステップを独立して実行し、問題があっても可能な範囲で処理を続行する設計です。

---

## 注意点 / 実運用に向けたポイント

- API レート制限（J-Quants: 120 req/min）に従う設計（内部で RateLimiter を使用）。
- get_id_token は 401 に対して自動リフレッシュ処理を行う（1 回まで）。
- DuckDB に対する INSERT は冪等化（ON CONFLICT ... DO UPDATE / DO NOTHING）されています。
- news_collector は SSRF や XML Bomb に配慮（スキーム検証、プライベートアドレスチェック、defusedxml、最大受信バイト数制限）。
- 品質チェック（data.quality）はエラー/警告レベルを返すため、呼び出し元で応じた対処が必要です（例: エラーがあれば運用中断やアラートを出す等）。
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml の存在）を基準に行われます。テスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## ディレクトリ構成

以下はパッケージの主要ファイル・モジュール構成の抜粋（src/kabusys 以下）です。

- src/kabusys/
  - __init__.py
  - config.py                  -- 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（取得＋保存）
    - news_collector.py        -- RSS からのニュース取得・保存・銘柄抽出
    - schema.py                -- DuckDB スキーマ定義・初期化
    - pipeline.py              -- ETL パイプライン（差分取得 / 品質チェック）
    - calendar_management.py   -- マーケットカレンダー管理 / 営業日ロジック
    - audit.py                 -- 監査ログ（signal/order/execution）スキーマ
    - quality.py               -- データ品質チェック
  - strategy/
    - __init__.py              -- 戦略関連（拡張領域）
  - execution/
    - __init__.py              -- 発注・実行関連（拡張領域）
  - monitoring/
    - __init__.py              -- 監視・メトリクス（拡張領域）

---

## 開発 / 貢献

- コードはモジュール単位で責務を分離しています。新しい機能（戦略、実行層、監視）を追加する場合は該当パッケージにモジュールを追加してください。
- DB スキーマを変更する場合は schema.py を更新し、後方互換性を考慮したマイグレーション戦略を採ることを推奨します（現状は init_schema による初期化のみ）。

---

## ライセンス

本リポジトリにライセンス表記がない場合、利用前にプロジェクトポリシーを確認してください。

---

README はここまでです。必要に応じて「サンプル .env.example」や「簡易起動スクリプト例（systemd / cron / Airflow 等）」、CI 用のセットアップ手順などを追加できます。どの情報を優先して追記しますか？