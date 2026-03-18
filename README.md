# KabuSys

バージョン: 0.1.0

日本株向けの自動売買基盤（ライブラリ群）。J‑Quants / kabuステーション 等からのデータ取得、DuckDB によるデータ永続化、ETL パイプライン、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

---

## 概要

KabuSys は日本株の自動売買システムを支える共通基盤ライブラリ群です。主な目的は以下の通りです。

- J‑Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新）
- DuckDB を用いたスキーマ定義と冪等なデータ保存
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・トラッキングパラメータ除去）
- マーケットカレンダーの管理と営業日判定ロジック
- 監査ログ（signal → order_request → execution のトレース）
- データ品質チェックモジュール（欠損、重複、スパイク、日付不整合）

設計上の特徴として、API レート制限やリトライ、Look‑ahead Bias 回避のための fetched_at 記録、DB 保存の冪等性（ON CONFLICT）やセキュリティ対策（SSRF、XML脆弱性対策）等を重視しています。

---

## 機能一覧

- J‑Quants クライアント
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - RateLimiter（120 req/min）、リトライ（指数バックオフ、401 のトークン自動更新）
  - DuckDB への idempotent な保存関数（save_daily_quotes 等）
- ETL（kabusys.data.pipeline）
  - run_daily_etl：カレンダー・株価・財務の差分取得と品質チェックをまとめて実行
  - 差分取得、バックフィル、品質チェック（quality モジュール）
- ニュース収集（kabusys.data.news_collector）
  - RSS から記事収集、URL 正規化、記事ID（SHA‑256 の先頭 32 文字）生成
  - SSRF/サイズ上限/defusedxml による安全な XML パース
  - raw_news / news_symbols への冪等保存
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - calendar_update_job（夜間バッチでの差分更新）
- スキーマ管理（kabusys.data.schema）
  - DuckDB の全テーブル / インデックス定義と init_schema 関数
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions 等の監査テーブルと初期化関数
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（前日比閾値）、将来日付/非営業日の検出

---

## 前提 / 必要環境

- Python 3.10 以上（コード中で | 型やパターンを使用）
- 必要な外部パッケージ（最低限）:
  - duckdb
  - defusedxml

インストール例:

- 仮想環境作成・有効化（例: venv）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- パッケージのインストール:
  - pip install duckdb defusedxml

（パッケージ配布/requirements.txt がある場合はそれに従って下さい）

---

## 環境変数（主なもの）

自動読み込み: パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env、.env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 環境 (development / paper_trading / live)。デフォルト "development"
- LOG_LEVEL — (DEBUG / INFO / WARNING / ERROR / CRITICAL)。デフォルト "INFO"
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト "data/kabusys.duckdb"
- SQLITE_PATH — SQLite（監視用）パス。デフォルト "data/monitoring.db"

未設定の必須値を参照すると ValueError が送出されます。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成・有効化
2. 依存パッケージをインストール（例: duckdb, defusedxml）
3. .env を作成して必要な環境変数を設定
   - 例: .env
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
4. DuckDB スキーマを初期化
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - (監査ログ専用 DB を使う場合)
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（代表的な例）

以下はライブラリを直接呼ぶ簡単なサンプルです。

- DuckDB スキーマ初期化:

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（デフォルトで今日を対象）:

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- J‑Quants トークン取得 / データ取得:

  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- ニュース収集ジョブ:

  from kabusys.data.news_collector import run_news_collection
  # known_codes は抽出に使う有効な銘柄コード集合（例: {"7203","6758"}）
  results = run_news_collection(conn, known_codes={"7203","6758"})
  print(results)  # {source_name: 新規保存件数}

- カレンダー夜間更新ジョブ:

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved: {saved}")

- 監査スキーマ初期化（既存 conn に追加）:

  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # transactional=False がデフォルト

- 設定参照:

  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.env, settings.is_live)

---

## 主要 API（抜粋）

- kabusys.config.Settings
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev

- kabusys.data.schema
  - init_schema(db_path) → DuckDB 接続
  - get_connection(db_path)

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements, save_market_calendar

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) → list[NewsArticle]
  - save_raw_news(conn, articles) → list[new_ids]
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.calendar_management
  - is_trading_day(conn, d), next_trading_day, prev_trading_day, get_trading_days, is_sq_day, calendar_update_job

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) → list[QualityIssue]

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False), init_audit_db(db_path)

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- __version__ = "0.1.0"

src/kabusys/config.py
- 環境変数の読み込み・Settings クラス（自動 .env ロード、必須チェック）

src/kabusys/data/
- __init__.py
- jquants_client.py — J‑Quants API クライアント、取得／保存ロジック
- news_collector.py — RSS 収集、前処理、SSRF 対策、保存
- schema.py — DuckDB スキーマ定義と init_schema/get_connection
- pipeline.py — ETL パイプライン（差分取得・品質チェック）
- calendar_management.py — マーケットカレンダー管理、営業日ロジック
- audit.py — 監査ログテーブル定義と初期化
- quality.py — データ品質チェック

src/kabusys/strategy/
- __init__.py （戦略層を設置するためのパッケージ）

src/kabusys/execution/
- __init__.py （発注・約定処理層）

src/kabusys/monitoring/
- __init__.py （監視・メトリクス関係）

---

## 開発時の注意点 / 補足

- Python の型表記や新しい構文（例: X | Y）を使用しているため、Python 3.10 以上を推奨します。
- DuckDB を使用しているため、ファイルパスの親ディレクトリは自動作成されます（init_schema 内で処理）。
- J‑Quants API のレート制限や 401 を含むエラーハンドリングは組み込まれていますが、運用時は適切なログ監視・再試行計画を用意してください。
- news_collector は外部 URL を扱うため SSRF/サイズ制限/XML 脆弱性に対する安全策を導入していますが、環境ごとのネットワークポリシーも確認してください。
- DB スキーマは既存のデータがあっても冪等に作成されます。監査スキーマ初期化時は transactional フラグに注意（DuckDB のトランザクションの仕様に起因）。

---

必要であれば、README にサンプル .env.example、より詳しい使い方（cron での ETL 実行、Slack 通知の連携、kabu ステーションとの通信実装例等）を追加します。どの部分を優先して詳しく記述しますか？