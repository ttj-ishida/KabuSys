# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（データ収集・ETL・品質チェック・監査スキーマなど）。

このリポジトリは、J-Quants API や RSS を用いたデータ取得・DuckDB への格納・ETL パイプライン・データ品質チェック・監査ログ（発注〜約定のトレーサビリティ）を提供します。

主な設計方針：
- API レート制御・リトライ・トークンリフレッシュを備えた堅牢な取得ロジック
- DuckDB を使った冪等なデータ保存（ON CONFLICT / INSERT ... RETURNING）
- 品質チェックを出力することで ETL の可観測性を確保
- SSRF / XML Bomb 等の外部入力に対する安全策を実装

---

## 機能一覧
- 環境変数／設定管理（自動で .env / .env.local をプロジェクトルートから読み込み）
- J-Quants クライアント
  - 株価日足（OHLCV）取得（ページネーション対応・レート制御・リトライ）
  - 財務諸表（四半期）取得
  - JPX マーケットカレンダー取得
  - トークン自動リフレッシュ
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 市場カレンダー管理（営業日判定、next/prev_trading_day、夜間更新ジョブ）
- ニュース収集（RSS → raw_news、URL 正規化、SSRF/サイズ制限、防御的 XML パース）
- ニュースと銘柄コードの紐付け（テキスト中の 4 桁銘柄コード抽出）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（signal/events/order_requests/executions 等）と初期化ユーティリティ

---

## 動作環境 / 依存
- Python 3.10 以上（型注釈に `X | None` 形式を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- インストール例（仮に pyproject.toml がある前提）:
  - pip install -e .
  - pip install duckdb defusedxml

---

## 必要な環境変数
以下は Settings で必須となっているか、またはデフォルトがある主要な環境変数です（.env/.env.local で設定可能）。

必須（未設定だと起動時にエラー）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意／デフォルトあり:
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に `1` を設定
- KABUS_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

※ .env 自動ロードの挙動:
- プロジェクトルート（.git または pyproject.toml を基準）から `.env` → `.env.local` を読み込みます。
- OS 環境変数は保護され、`.env.local` の override を受けても上書きされない（必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使う）。

---

## セットアップ手順（基本例）

1. リポジトリをクローン、作業ディレクトリへ移動

   git clone <repo-url>
   cd <repo>

2. Python 仮想環境を作成・有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install -e .
   pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

4. 環境変数を設定
   - プロジェクトルートに `.env`（およびローカル用に `.env.local`）を作成して必須値を設定してください。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     KABUSYS_ENV=development

5. DuckDB スキーマ初期化（Python REPL またはスクリプト）

   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)
   # 監査ログ専用 DB を初期化する場合:
   # from kabusys.data import audit
   # audit_conn = audit.init_audit_db("data/audit.duckdb")

---

## 使い方（代表的な API・実行例）

以下はライブラリを使った基本的な操作例です。実運用ではログ設定や例外処理を適宜追加してください。

- 日次 ETL を実行する（市場カレンダー取得・株価/財務の差分取得・品質チェック）

  from kabusys.data import schema, pipeline
  from kabusys.config import settings
  conn = schema.init_schema(settings.duckdb_path)
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

- ニュース収集（RSS 取得→raw_news 保存→銘柄紐付け）

  from kabusys.data import schema, news_collector
  conn = schema.get_connection(settings.duckdb_path)
  # sources をカスタム指定可 (source_name: rss_url)
  res = news_collector.run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(res)  # {source_name: 新規レコード数}

- カレンダー夜間更新ジョブ（calendar_update_job）

  from kabusys.data import schema, calendar_management
  conn = schema.get_connection(settings.duckdb_path)
  saved = calendar_management.calendar_update_job(conn)
  print(f"saved: {saved}")

- 監査スキーマの初期化

  from kabusys.data import schema, audit
  conn = schema.get_connection(settings.duckdb_path)
  audit.init_audit_schema(conn, transactional=True)

- J-Quants の個別 API 呼び出し（トークンは自動管理）

  from kabusys.data import jquants_client as jq
  # 全銘柄の当日分データを取得する例
  records = jq.fetch_daily_quotes(date_from=date.today(), date_to=date.today())
  # DuckDB に保存する場合は save_daily_quotes を使用

注意点:
- run_daily_etl や run_prices_etl などは内部で差分算出やバックフィルを行います。引数で date 範囲や backfill_days, id_token を指定可能です。
- NewsCollector は SSRF や大容量レスポンスへの防御を備えています。外部 RSS ソースの指定は http/https のみ許可されます。

---

## ディレクトリ構成（要約）
（プロジェクトのトップは pyproject.toml/.git に依存して自動 .env 読み込みが行われます）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py      — RSS 収集 / 正規化 / 保存 / 銘柄抽出
    - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py            — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py — 市場カレンダー管理・営業日判定・夜間更新ジョブ
    - audit.py               — 監査ログ（発注〜約定のトレーサビリティ）スキーマ初期化
    - quality.py             — データ品質チェック
  - strategy/                 — 戦略関連モジュール（パッケージ構成のみ）
  - execution/                — 発注実行関連モジュール（パッケージ構成のみ）
  - monitoring/               — 監視関連（パッケージ構成のみ）

---

## 運用上の注意 / セキュリティ
- .env ファイルには機密情報（トークン・パスワード）を含めるため、git にコミットしないでください。
- news_collector は SSRF 等への対策を実装していますが、外部ソースは慎重に追加してください。
- J-Quants API のレート制限（120 req/min）を守るため、クライアント側でも RateLimiter が動作します。過度な並列取得は避けてください。
- DuckDB のファイルに対しては適切なバックアップ / 排他制御（複数プロセスからのアクセス）を考慮してください。
- 監査ログは削除しない前提で設計されています（トレーサビリティ確保）。

---

## 開発 / 貢献
- テスト時に .env の自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 型・引数はユニットテストしやすいよう id_token 注入、タイムアウトや chunk サイズ等が引数により調整可能です。
- バグ報告や改善提案は issue を作成してください。

---

この README はコードベース（src/kabusys 以下）の主要機能と導入手順をまとめたものです。より詳細な動作仕様やデータモデル（DataPlatform.md, DataSchema.md 等）が別途ある想定ですので、運用時はそれらのドキュメントも参照してください。