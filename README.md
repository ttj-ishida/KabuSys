# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ群です。データ取得（J-Quants）、ETL、品質チェック、ニュース収集、マーケットカレンダー管理、監査ログといった基盤機能を提供します。

この README ではプロジェクトの概要、主な機能、セットアップ手順、使い方の例、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株自動売買システムの基盤ライブラリです。主に以下を目的とします。

- J-Quants API からの市場データ（株価・財務・マーケットカレンダー）取得
- DuckDB を用いたデータ格納（Raw / Processed / Feature / Execution 層）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集・前処理・銘柄紐付け
- マーケットカレンダー管理（営業日判定、next/prev/trading day）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）
- ETL パイプライン（差分取得・バックフィル・品質チェック）

設計上のポイント:

- J-Quants API のレート制限（120 req/min）を遵守するレートリミッタとリトライ（指数バックオフ）
- トークンの自動リフレッシュ（401 時に1回リトライ）
- DuckDB への保存は冪等（ON CONFLICT による更新）
- RSS 取得時の SSRF や XML 攻撃に対する防御（リダイレクト検査、defusedxml、受信サイズ上限など）

---

## 機能一覧

- data.jquants_client
  - 株価日足、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar）
  - ID トークン取得／キャッシュ・自動リフレッシュ
  - レートリミッティングとリトライロジック

- data.pipeline
  - 日次 ETL パイプライン（run_daily_etl）
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 差分更新、バックフィル、品質チェック統合（quality モジュール）

- data.news_collector
  - RSS フィード取得／パース／前処理（URL除去・空白正規化）
  - 記事 ID の生成（正規化 URL の SHA-256 の先頭 32 文字）
  - raw_news への冪等保存、news_symbols への銘柄紐付け
  - SSRF 防止、gzip サイズチェック、XML パースの安全化

- data.calendar_management
  - market_calendar の夜間差分更新ジョブ（calendar_update_job）
  - 営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）

- data.quality
  - 欠損、スパイク（急騰・急落）、主キー重複、日付不整合チェック
  - QualityIssue 型で詳細を返す（severity: error | warning）

- data.schema / data.audit
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - スキーマ初期化関数（init_schema / init_audit_schema / init_audit_db）

- config
  - .env ファイルまたは OS 環境変数から設定を読み込む（自動ロード機構）
  - 必須環境変数の検査、環境モード判定（development / paper_trading / live）

---

## 前提・依存

- Python 3.10 以上（型注記で `X | Y` を使用しているため）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml

実運用では追加依存（requests や Slack ライブラリ等）を導入することがあります。本リポジトリのコードは標準ライブラリを多用していますが、DuckDB と defusedxml は必須です。

インストール例:

pip install duckdb defusedxml

（プロジェクト配布時は requirements.txt を用意して `pip install -r requirements.txt` を推奨します）

---

## 環境変数（主なもの）

このモジュールは .env（および .env.local）をプロジェクトルートから自動読み込みします（CWD 依存しない）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（コード内で _require() を呼んでいるもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード停止

.env の例（.env.example を参照する想定）:

JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意: .env.local は .env を上書きする（OS 環境変数は保護され上書きされない）。

---

## セットアップ手順

1. Python のセットアップ
   - Python 3.10+ をインストールしてください。

2. パッケージのインストール
   - 最小例:
     pip install duckdb defusedxml

   - 実プロジェクトでは仮想環境を作成してからインストールすることを推奨します:
     python -m venv .venv
     source .venv/bin/activate  # Windows: .venv\Scripts\activate
     pip install --upgrade pip
     pip install duckdb defusedxml

3. 環境変数の設定
   - プロジェクトルートに .env を作成する（.env.example を参考に）。
   - または OS 環境変数として設定してください。

4. DuckDB スキーマ初期化
   - 初回はスキーマを作成します。以下は Python REPL またはスクリプトでの例:

     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # デフォルトパスに作成
     # 監査スキーマを追加する場合:
     from kabusys.data import audit
     audit.init_audit_schema(conn)

   - :memory: を渡すことでインメモリ DB が利用可能です（テスト用途）。

---

## 基本的な使い方

以下は代表的な利用例です。プロダクション運用ではこれらを Cron / Airflow / Job スケジューラから呼ぶ想定です。

1) 日次 ETL を実行する（株価・財務・カレンダーの差分取得＋品質チェック）:

from datetime import date
from kabusys.data import schema, pipeline

# DB 初期化（既に作成済みなら単に接続する）
conn = schema.init_schema("data/kabusys.duckdb")

# ETL 実行（target_date を指定しないと今日）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())

2) マーケットカレンダーの夜間更新ジョブ（calendar_update_job）:

from kabusys.data import schema, calendar_management
conn = schema.init_schema("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved calendar rows:", saved)

3) RSS ニュース収集（ニュース保存と銘柄紐付け）:

from kabusys.data import schema, news_collector
conn = schema.init_schema("data/kabusys.duckdb")

# 既知の銘柄コードセット（例: 取引銘柄一覧）
known_codes = {"7203", "6758", "9432", ...}

results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}

4) J-Quants から指定期間の株価を取得して保存する（テスト）:

from kabusys.data import jquants_client as jq
from kabusys.data import schema
conn = schema.init_schema(":memory:")
# 明示的にリフレッシュトークンを渡すことも可能
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("fetched:", len(records), "saved:", saved)

---

## 注意点 / 運用上のヒント

- API レート制限: jquants_client は 120 req/min に合わせた固定間隔スロットリングを行います。大量データ取得時はその制約を考慮してください。
- トークン自動リフレッシュ: 内部で ID トークンをキャッシュし、401 を受け取ったときは自動で一度リフレッシュしてリトライします。
- .env 自動読み込み: プロジェクトルート（.git または pyproject.toml のある場所）を基準に .env/.env.local を自動で読み込みます。テストで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- ニュース収集の安全性: RSS のリダイレクト先検査や受信サイズ上限、defusedxml による XML の安全化などを行っていますが、不特定多数の外部フィードを登録する場合は追加監査を推奨します。
- DuckDB の取り扱い: ファイルパスの親ディレクトリは自動作成されます。バックアップや世代管理は運用で対処してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイルと簡単な説明は以下の通りです。

src/kabusys/
- __init__.py
  - パッケージのバージョンと公開モジュール定義
- config.py
  - 環境変数読み込み、Settings クラス（必須設定の検査、自動 .env ロード）
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・リトライ・保存）
  - pipeline.py
    - ETL パイプライン（差分取得、バックフィル、品質チェック統合）
  - news_collector.py
    - RSS フィード取得・前処理・raw_news 保存・銘柄紐付け
  - schema.py
    - DuckDB スキーマ定義と init_schema / get_connection
  - calendar_management.py
    - マーケットカレンダーの管理・営業日判定ロジック・更新ジョブ
  - audit.py
    - 監査ログ（signal_events, order_requests, executions）定義と初期化
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
- strategy/
  - __init__.py
  - （戦略関連モジュールを配置するための名前空間）
- execution/
  - __init__.py
  - （発注・ブローカー連携モジュールを配置するための名前空間）
- monitoring/
  - __init__.py
  - （監視・メトリクス関連モジュールを配置するための名前空間）

その他:
- .env.example（存在が想定されているがリポジトリに合わせて作成してください）

---

## テスト・開発メモ

- 多くの関数は依存注入（例: id_token, DuckDB 接続）をサポートしており、ユニットテストで外部呼び出しのモック化がしやすく設計されています。
- news_collector._urlopen 等はテスト時に差し替え（モック）可能です。
- 設定読み込みはプロジェクトルートを基準にするため、テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して明示的にテスト用環境変数を注入すると安定します。

---

必要であれば README にサンプルの .env.example、requirements.txt、あるいは CLI ラッパー（コマンドラインから ETL を起動する簡単なスクリプト）の追加も作成できます。どの追加が欲しいか教えてください。