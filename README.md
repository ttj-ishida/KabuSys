# KabuSys

日本株向けの自動売買データ基盤 / ETL / 監査用ライブラリです。J-Quants や RSS 等からデータを取得して DuckDB に格納し、品質チェック・カレンダー管理・監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価（日足）、財務データ、取引カレンダー取得
- RSS からのニュース収集と銘柄紐付け
- DuckDB を用いたスキーマ定義・ETL（差分取得 / 冪等保存）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- マーケットカレンダー管理（営業日判定、前後営業日の取得）
- 監査ログ（シグナル→発注→約定のトレースを可能にする監査スキーマ）

設計上の特徴:
- API レート制御（J-Quants: 120 req/min）
- リトライ（指数バックオフ）、401 の自動トークンリフレッシュ
- Look-ahead bias を避けるため取得時刻（UTC）を記録
- DuckDB への保存は冪等（ON CONFLICT）で実装
- RSS の SSRF / XML Bomb 対策（スキーム検証、defusedxml、最大受信サイズ等）

---

## 機能一覧

- データ取得
  - fetch_daily_quotes: 株価日足（OHLCV）取得（ページネーション対応）
  - fetch_financial_statements: 四半期財務データ取得
  - fetch_market_calendar: JPX マーケットカレンダー取得
- データ保存（DuckDB）
  - save_daily_quotes / save_financial_statements / save_market_calendar（冪等保存）
- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl: 日次 ETL（カレンダー取得→株価→財務→品質チェック）
- ニュース収集
  - fetch_rss, run_news_collection, save_raw_news, save_news_symbols
  - URL 正規化、トラッキングパラメータ削除、ID は SHA-256（先頭32文字）
- マーケットカレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job: 夜間のカレンダー差分更新ジョブ
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks: すべてのチェックをまとめて実行
- 監査ログ（Audit）
  - init_audit_schema / init_audit_db: signal_events, order_requests, executions などの監査スキーマ初期化

---

## セットアップ手順

前提
- Python 3.10 以上（Union 型表記 Path | None 等を使用）
- ネットワーク接続（J-Quants API や RSS 取得のため）

1. リポジトリをクローンし、パッケージをインストール（開発用）
   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 必要な追加依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
   - 他にプロジェクトで外部ライブラリを使う場合はそれらを追加してください（例: Slack 通知などを行う場合は slack-sdk 等）。

3. 環境変数（または .env）を設定
   - 自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabu API のパスワード
     - SLACK_BOT_TOKEN — Slack ボットトークン（Slack 通知を利用する場合）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（Slack を利用する場合）
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト "http://localhost:18080/kabusapi"
     - DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH — デフォルト "data/monitoring.db"

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下は代表的な利用例です。Python スクリプトや CLI ジョブから呼び出して使用します。

- DuckDB スキーマ初期化と接続取得
  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl

  # conn は init_schema の戻り値
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection

  # known_codes: 抽出対象の有効な銘柄コードセット（例: 上場銘柄リスト）
  known_codes = {"7203", "6758", "9984", ...}

  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: 新規保存件数}
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn)
  print(f"saved: {saved}")
  ```

- 監査スキーマ初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- J-Quants の個別フェッチ（テストやデバッグ）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes

  records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

ログ出力や例外は標準 logging を通して出ます。必要に応じてログレベルを設定してください。

---

## ディレクトリ構成

主要ファイル・モジュール構成（src 配下）:

- src/kabusys/
  - __init__.py (パッケージ定義、__version__ = "0.1.0")
  - config.py
    - 環境変数読み込み、Settings クラス（J-Quants トークン等）
    - 自動 .env ロード（.git または pyproject.toml を探索）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、レート制御、リトライ、保存ユーティリティ
    - news_collector.py
      - RSS 取得、前処理、保存、銘柄抽出（SSRF/サイズ制限/defusedxml 対策）
    - schema.py
      - DuckDB スキーマ定義（Raw / Processed / Feature / Execution）と init_schema
    - pipeline.py
      - ETL パイプライン（差分取得、バックフィル、品質チェック統合）
    - calendar_management.py
      - 市場カレンダー管理、営業日判定、calendar_update_job
    - audit.py
      - 監査ログ用スキーマ（signal_events, order_requests, executions）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py (戦略モジュール用プレースホルダ)
  - execution/
    - __init__.py (実行/発注層用プレースホルダ)
  - monitoring/
    - __init__.py (監視・メトリクス用プレースホルダ)

その他:
- .env / .env.local: 環境変数ファイル（プロジェクトルートに置くと自動ロードされます）

---

## 開発・運用上の注意

- 環境変数自動読み込みはプロジェクトルートの検出に .git または pyproject.toml を使用します。テスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants へのリクエストはモジュール内でレートリミットとリトライ制御を行いますが、長時間の大規模フェッチは API 利用規約を確認してください。
- DuckDB のファイルパスは Settings.duckdb_path で指定できます。初回は `init_schema()` を呼んでスキーマを作成してください。
- ニュース収集では外部 URL を取得するため SSRF 対策や受信サイズ制限が入っていますが、運用時にはホワイトリスト等の追加制御を検討してください。
- 監査スキーマは UTC タイムゾーンを前提としています（init_audit_schema は SET TimeZone='UTC' を実行します）。

---

## 参考（よく使う関数 / API）

- schema.init_schema(db_path)
- data.jquants_client.get_id_token(refresh_token=None)
- data.jquants_client.fetch_daily_quotes(...)
- data.jquants_client.save_daily_quotes(conn, records)
- data.pipeline.run_daily_etl(conn, target_date=None, ...)
- data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- data.calendar_management.calendar_update_job(conn)
- data.audit.init_audit_db(db_path)
- data.quality.run_all_checks(conn, target_date=None)

---

必要であれば、README に記載する具体的なコード例（CRON/airflow 用の簡易ワーカーサンプル、Dockerfile、CI 設定例、より詳細な .env.example）を追加します。どの部分を詳細化したいか教えてください。