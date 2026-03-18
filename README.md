# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants API や RSS フィードからデータを収集し、DuckDB に格納・品質チェック・ETL を行い、監査ログや発注関連のスキーマを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つライブラリ群です。

- J-Quants API から株価・財務・マーケットカレンダー等を安全に取得・保存する
- RSS フィードからニュースを収集し、記事→銘柄の紐付けを行う
- DuckDB 上にデータレイヤ（Raw / Processed / Feature / Execution / Audit）を構築・初期化する
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）を提供する
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマを提供する

設計上の特徴:
- API レート制限・リトライ・トークン自動リフレッシュを備えた J-Quants クライアント
- DuckDB への冪等保存（ON CONFLICT）を保証
- RSS 収集における SSRF 防止、XML 攻撃対策、レスポンスサイズ制限
- 品質チェック（欠損・重複・スパイク・日付不整合）を実装

---

## 機能一覧

- 環境変数/設定管理（.env 自動読み込み、強制無効化可能）
- J-Quants API クライアント（fetch + save）
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - レート制御、リトライ、401 自動リフレッシュ、fetched_at 記録
- RSS ニュース収集（fetch_rss / save_raw_news / run_news_collection）
  - URL 正規化、記事 ID (SHA-256 の先頭32文字)、SSRF 防御、gzip 対応
  - 銘柄コード抽出と news_symbols 保存
- DuckDB スキーマ管理（init_schema / get_connection）
  - Raw / Processed / Feature / Execution のテーブル・インデックスを定義
- ETL パイプライン（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
  - 差分取得、バックフィル、品質チェックの統合
- カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
- 監査ログ（audit）スキーマと初期化（init_audit_schema / init_audit_db）
- データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）

---

## 前提条件 / 必要パッケージ

- Python 3.9+
- duckdb
- defusedxml

（環境や用途に応じて追加パッケージが必要な場合があります）

インストール例（仮想環境推奨）:
- venv を作成してアクティベート
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール
  - pip install duckdb defusedxml

※ 本リポジトリに setup/requirements がある場合はそれに従ってください。

---

## 環境変数

自動でプロジェクトルート（.git または pyproject.toml がある場所）から `.env` と `.env.local` を読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabuAPI のベース URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意) — 監視用 SQLite パス (デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live (デフォルト: development)
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL (デフォルト: INFO)

settings オブジェクト経由でアクセス可能:
from kabusys.config import settings
例: settings.jquants_refresh_token

---

## セットアップ手順（ローカル実行向け）

1. リポジトリをクローンしワークディレクトリへ
2. 仮想環境作成・アクティベート
3. 必要パッケージをインストール（duckdb, defusedxml など）
4. プロジェクトルートに `.env`（および開発用に `.env.local`）を作成し、上記必須環境変数を設定
5. DuckDB スキーマを初期化
   - Python REPL またはスクリプト内で:
     from kabusys.data import schema
     conn = schema.init_schema(settings.duckdb_path)
   - これにより `data/kabusys.duckdb`（デフォルト）が作成され、テーブルが作られます

---

## 使い方（簡単なコード例）

以下は主要な操作の最小例です。実際はログ設定や例外処理を追加してください。

- DuckDB スキーマ初期化:
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants トークンは settings から自動的に利用されます）:
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- 個別 ETL（株価のみ）:
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())

- RSS ニュース収集（既定ソースから収集）:
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)

- J-Quants 生データ取得（直接呼び出す例）:
  from kabusys.data.jquants_client import fetch_daily_quotes
  quotes = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))

- カレンダー更新バッチ:
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

- 監査ログスキーマの初期化（audit 用）:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- 品質チェック:
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)

注意点:
- J-Quants API のレート制限（120 req/min）を尊重してください。クライアントは内部で制御しますが、多数の並列実行は避けてください。
- run_daily_etl は複数ステップを実行し、各ステップは個別にエラーハンドリングされます。ETLResult に詳細が入ります。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数管理・自動 .env 読み込み
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py  — RSS フィード収集・保存・銘柄紐付け
  - schema.py          — DuckDB スキーマ定義 / 初期化
  - pipeline.py        — ETL パイプライン（日次 ETL を含む）
  - calendar_management.py — マーケットカレンダー管理（営業日判定等）
  - audit.py           — 監査ログ（signal / order_request / executions）スキーマ
  - quality.py         — データ品質チェック
- strategy/
  - __init__.py  — 戦略関連モジュール（拡張ポイント）
- execution/
  - __init__.py  — 発注・実行周り（ブローカー連携の拡張ポイント）
- monitoring/
  - __init__.py  — 監視・メトリクス関連（拡張ポイント）

備考:
- strategy / execution / monitoring はプラグイン的に拡張するための領域です（本コードベースでは初期化ファイルのみ）。
- schema.py により Raw / Processed / Feature / Execution 層のテーブルがすべて作られます。
- audit.py は監査トレーサビリティ用スキーマを個別に初期化する関数を持ちます。

---

## 運用上の注意・設計上のポイント

- 環境変数は .env/.env.local を通じ自動で読み込まれますが、CI/本番では OS 環境変数を使うことを推奨します。
- ニュース収集では SSRF・XML 攻撃・レスポンスサイズ上限などの防御策を講じていますが、外部ソースの安全性は常に監視してください。
- DuckDB への保存は基本的に冪等（ON CONFLICT）を担保していますが、手動での DB 操作やスキーマ変更には注意してください。
- run_daily_etl 等はログ出力と品質チェックの結果を元に運用判断（通知・ロールバックなど）を行ってください。

---

必要であれば、README に以下の追記も可能です:
- 具体的な .env.example のテンプレート
- CI/CD での運用フロー例（スケジューラー、Slack 通知のサンプル）
- strategy / execution の実装ガイドライン

ご希望があれば追加します。