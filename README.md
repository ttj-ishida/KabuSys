# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants や RSS などからデータを取得して DuckDB に保存し、ETL／品質チェック／マーケットカレンダー管理／ニュース収集／監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムに必要なデータ基盤とユーティリティを集めた Python パッケージです。主に以下を提供します。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新）
- DuckDB ベースのスキーマ定義・初期化・接続ヘルパー
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- ニュース（RSS）収集器（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
- JPX マーケットカレンダー管理（営業日判定、前後営業日取得）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上の特徴として、API レート制御・指数バックオフ付きリトライ・冪等（ON CONFLICT）保存・UTC 時刻保存・安全な XML パース等を重視しています。

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存: save_daily_quotes, save_financial_statements, save_market_calendar
  - レート制御、リトライ、401 時のトークン自動リフレッシュ、fetched_at の記録
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) による初期化
- data.pipeline
  - run_daily_etl(conn, target_date, ...) による日次 ETL（差分更新・品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl 単体ジョブ
- data.news_collector
  - RSS 取得（fetch_rss）、記事保存（save_raw_news）、銘柄紐付け（save_news_symbols）
  - URL の正規化、記事ID の SHA-256 ハッシュ化、SSRF 対策、gzip / サイズ制限
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による夜間カレンダー更新
- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks によるまとめ実行
- data.audit
  - 監査用テーブル（signal_events / order_requests / executions）の初期化と管理
- 設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルートの .env / .env.local を順に読み込む）
  - settings オブジェクト経由で環境変数取得・バリデーション

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションに `X | None` を使用）
- pip が利用可能

1. リポジトリをクローンしてパッケージをインストール（開発モード）:

   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

   （プロジェクトが src レイアウトなので pip install -e . が推奨です）

2. 依存パッケージの一部（例）:
   - duckdb
   - defusedxml

   必要に応じて次を実行してください:

   ```bash
   pip install duckdb defusedxml
   ```

   （requirements.txt があればそれを利用してください）

3. 環境変数を設定
   - プロジェクトルート（pyproject.toml または .git のある場所）に `.env` として必要な変数を定義できます。
   - 自動ロードはデフォルトで有効。テスト等で無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須 / デフォルト）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - KABU_API_BASE_URL (省略可) — デフォルト: http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN (必須) — Slack ボットトークン
   - SLACK_CHANNEL_ID (必須) — Slack チャンネルID
   - DUCKDB_PATH (省略可) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (省略可) — デフォルト: data/monitoring.db
   - KABUSYS_ENV (省略可) — development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL (省略可) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例（.env）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は主要機能の利用例です。実運用では適切な例外処理・ログ設定を行ってください。

- DuckDB スキーマ初期化:

  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行:

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")  # 既に init_schema 済みを想定
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants: トークン取得・株価取得（トークンは settings を自動参照）:

  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を利用
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- ニュース収集（RSS）と保存:

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 例: 有効銘柄コードセット
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)  # 各ソースごとの新規保存数を返す
  ```

- カレンダー更新ジョブ（夜間バッチ）:

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 監査スキーマ初期化（監査専用 DB）:

  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit_duckdb.duckdb")
  ```

---

## 設定の自動読み込みについて

- kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を自動読み込みします。
- 読み込み優先順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にする: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用など）。

---

## ディレクトリ構成

以下はパッケージ内の主要ファイルとモジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - news_collector.py        — RSS ニュース収集器（SSRF対策等）
    - schema.py                — DuckDB スキーマ定義・初期化
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — マーケットカレンダー管理（営業日判定等）
    - quality.py               — データ品質チェック
    - audit.py                 — 監査ログスキーマ（signal/order/execution）
  - strategy/
    - __init__.py              — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py              — 発注・実行関連（拡張ポイント）
  - monitoring/
    - __init__.py              — 監視関連（拡張ポイント）

この README は現状のコードベース（src 下）を基に作成しています。戦略や発注の実装はパッケージの拡張ポイントとして空の __init__.py が置かれており、プロジェクト固有のロジックを追加していくことを想定しています。

---

## 注意点 / 運用上のヒント

- Python バージョンは 3.10 以上を推奨（型ヒントの構文依存）。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。別パスを使用する場合は環境変数 DUCKDB_PATH を設定するか、init_schema にパスを渡してください。
- J-Quants API はレート制限（120 req/min）やレスポンスのページネーションに対応しています。大量取得時は制限に注意してください。
- RSS 収集では SSRF 対策や受信サイズ制限を実装していますが、外部フィードの品質に依存するため例外ハンドリングを適切に行ってください。
- ETL の品質チェックは警告／エラーを返します。運用ではエラー検出時の通知（Slack 等）や自動ロールバック方針を検討してください。
- 監査ログ（audit）はトレースに重要です。order_request_id を冪等キーとして再送対策を行うことが前提です。

---

必要であれば README に含めるサンプル .env.example、CI 実行方法、より詳細な API リファレンスやユースケース（戦略の追加例、発注フローの実装例）も作成します。どのセクションを拡張したいか教えてください。