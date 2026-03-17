# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けのライブラリ群です。  
データ収集（J-Quants / RSS）、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、DuckDB ベースのスキーマ、監査ログ（発注→約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

主な目的は、J-Quants 等から取得したマーケットデータを安定して収集・保存し、戦略層や実行層に利用可能な状態に整備することです。設計上の特徴：

- API レート制御・リトライ・トークン自動リフレッシュ（J-Quants クライアント）
- DuckDB を用いた冪等（idempotent）保存（ON CONFLICT 処理）
- RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事 ID は正規化 URL の SHA-256）
- 日次 ETL（差分更新・バックフィル）と品質チェック（欠損、スパイク、重複、日付不整合）
- 市場カレンダー管理（営業日判定・前後営業日の計算・週末フォールバック）
- 監査ログ用スキーマ（シグナル → 発注 → 約定のトレーサビリティ）

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（ID トークン取得・ページネーション・レート制御・リトライ）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存用関数 save_daily_quotes, save_financial_statements, save_market_calendar

- data/news_collector.py
  - RSS フィード取得、記事前処理、記事の冪等保存（raw_news）
  - 記事 → 銘柄コード抽出、news_symbols への紐付け

- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) でテーブル作成（冪等）

- data/pipeline.py
  - 日次 ETL（run_daily_etl）：カレンダー、株価、財務データの差分取得・保存・品質チェック
  - 個別 ETL：run_prices_etl, run_financials_etl, run_calendar_etl

- data/calendar_management.py
  - 市場カレンダーの判定 helper（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - calendar_update_job（夜間バッチでカレンダー差分更新）

- data/quality.py
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - run_all_checks() でまとめて実行

- data/audit.py
  - 監査ログ用テーブル（signal_events, order_requests, executions）と初期化関数
  - init_audit_schema / init_audit_db

- config.py
  - .env または環境変数から設定を自動読み込み（プロジェクトルート検出）
  - Settings オブジェクト経由で設定取得（JQUANTS_REFRESH_TOKEN 等）
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## セットアップ手順

前提: Python 3.10+（typing のユニオン表記などを使用）

1. リポジトリをクローン / プロジェクトに配置

2. 依存ライブラリをインストール（例: pip）
   - 必要な主なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     pip install duckdb defusedxml
     # 追加でテストやツールがあれば requirements.txt / pyproject からインストール
     ```

3. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（config.py）。
   - 自動ロードの無効化（テスト等）:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード
     - SLACK_BOT_TOKEN: Slack ボットトークン（通知用途）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 推奨/任意:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD（1で無効化）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

4. データベース初期化（DuckDB）
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成してテーブル初期化
     ```
   - 監査ログの初期化（既存接続に追加）:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

---

## 使い方

ここでは主要な利用シナリオの簡単な例を示します。

- 日次 ETL（株価 / 財務 / カレンダー取得 + 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から株価を個別に取得して保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  token = get_id_token()  # settings.jquants_refresh_token が使われる
  records = fetch_daily_quotes(id_token=token, code="7203", date_from=None, date_to=None)
  saved = save_daily_quotes(conn, records)
  ```

- RSS ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は抽出に使う有効な銘柄コードのセット（省略すると紐付けはスキップ）
  results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(results)  # {source_name: saved_count}
  ```

- カレンダー関連ユーティリティ
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  # conn は DuckDB 接続
  print(is_trading_day(conn, date(2026, 1, 1)))
  print(next_trading_day(conn, date.today()))
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意:
- 設定値は Settings オブジェクト（kabusys.config.settings）で取得できます。
- 自動的に .env ファイルをロードしますが、テスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・モジュール（src/kabusys ベース）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント、保存ユーティリティ
    - news_collector.py      — RSS ニュース収集・前処理・保存・銘柄紐付け
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py — 市場カレンダー管理（判定・夜間更新ジョブ）
    - audit.py               — 監査ログ（signal/order/execution）スキーマ
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略層（拡張ポイント）
  - execution/
    - __init__.py            — 注文実行層（拡張ポイント）
  - monitoring/
    - __init__.py            — モニタリング（拡張ポイント）

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1: 自動 .env ロードを無効化)

.env.sample（プロジェクトルート）を用意しておくと便利です。

---

## 開発・運用時メモ

- DuckDB のファイルはデフォルトで data/kabusys.duckdb に作成されます。別パスを使う場合は DUCKDB_PATH を設定してください。
- J-Quants API のレート制限（120 req/min）に対応するためクライアントは内部でスロットリングを行います。
- ニュース収集では SSRF、XML Bomb、巨大レスポンスなどに対する防御を実装しています。
- schema.init_schema は冪等（IF NOT EXISTS）なので何度でも呼べます。監査テーブルは init_audit_schema で追加できます。
- テストでは settings の自動 .env 読み込みを無効化して、意図した環境を注入してください。

---

問題や拡張のご要望があれば、使用目的（バックテスト・ライブ運用・通知要件 など）を教えてください。README の改善やサンプルの追加を行います。