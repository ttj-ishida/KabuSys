# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants / kabuステーション 等の外部APIから市場データ・財務データ・ニュースを取得し、DuckDB に保持、ETL・品質チェック・監査ログの仕組みを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたライブラリです。

- J-Quants API からの株価・財務データ・マーケットカレンダー取得（ページネーション・レート制御・リトライ・自動トークン更新対応）
- RSS ベースのニュース収集と記事 → 銘柄コード紐付け（SSRF対策・XML攻撃対策・受信サイズ制限）
- DuckDB ベースのスキーマ定義・初期化、冪等なデータ保存（ON CONFLICT / DO UPDATE）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェックの統合）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）

設計上の注目点：
- API レート制限順守（J-Quants：120 req/min、固定間隔スロットリング）
- 冪等性とトレーサビリティ重視（DB の ON CONFLICT、監査用テーブル群）
- セキュアな外部入力処理（defusedxml、SSRFガード、受信サイズ制限等）

---

## 機能一覧

- 環境設定管理（.env 自動ロード、必須値チェック）
- J-Quants クライアント
  - get_id_token（リフレッシュトークンからIDトークン取得、401時の自動リフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - save_* 系関数（DuckDB への冪等保存）
- ニュース収集
  - fetch_rss：RSS → Article リスト（SSRF対策、gzip対応、XML脆弱性対策）
  - save_raw_news / save_news_symbols：DuckDB へ冪等保存（INSERT ... RETURNING）
  - 銘柄抽出ロジック（4桁コード抽出、既知銘柄でフィルタ）
- スキーマ管理
  - init_schema：DuckDB の全テーブル・インデックス作成（Raw / Processed / Feature / Execution 層）
  - init_audit_schema / init_audit_db：監査ログ用テーブル初期化
- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl（統合：カレンダー取得 → 株価 → 財務 → 品質チェック）
  - ETLResult 型で結果・品質問題・エラーを取得
- 品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（まとめて実行）

---

## 必要条件（依存）

主な Python ライブラリ（実際の requirements はプロジェクトの依存管理に従ってください）:

- Python 3.9+
- duckdb
- defusedxml

その他、実行環境によって urllib, logging 等標準ライブラリを使用。

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージおよび依存をインストール
   - pip install -e .        （プロジェクトが setuptools / pyproject を持つ想定）
   - pip install duckdb defusedxml

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` として設定可能。
   - 自動ロードはデフォルトで有効。無効化する場合は環境変数を設定：
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   サンプル `.env`（必要なキー）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_password
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 任意（デフォルト）
   - SLACK_BOT_TOKEN=your_slack_token
   - SLACK_CHANNEL_ID=your_channel_id
   - DUCKDB_PATH=data/kabusys.duckdb   # 任意（デフォルト）
   - SQLITE_PATH=data/monitoring.db    # 任意（デフォルト）
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   note: Settings で必須とされる項目は、未設定時に ValueError を投げます。

5. データベース初期化（例）
   - Python REPL またはスクリプト内で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   監査ログのみ分離して初期化する場合:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要な例）

- 日次 ETL を実行する（基本例）
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # 戻り値は ETLResult（fetched/saved/quality_issues 等を含む）
  print(result.to_dict())

- J-Quants から日足データを取得して保存
  from kabusys.data.schema import init_schema
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)

- RSS ニュース収集の実行
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203","6758", ...}  # 事前に用意した銘柄コード集合
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}

- 監査ログ初期化（既存 conn に追加）
  from kabusys.data.schema import init_schema
  from kabusys.data.audit import init_audit_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn)

---

## 設定・動作上のポイント

- .env 自動ロード
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を探索し、`.env` → `.env.local` の順で読み込みます。
  - OS 環境変数が優先され、`.env.local` は既存OS環境変数を上書きするが OS 側で定義されているキーは保護されます。
  - 無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- Settings API
  - settings.jquants_refresh_token (必須)
  - settings.kabu_api_password (必須)
  - settings.kabu_api_base_url (既定: http://localhost:18080/kabusapi)
  - settings.slack_bot_token (必須)
  - settings.slack_channel_id (必須)
  - settings.duckdb_path / settings.sqlite_path（デフォルト値あり）
  - settings.env: development / paper_trading / live のみ有効
  - settings.log_level: DEBUG/INFO/WARNING/ERROR/CRITICAL のみ有効

- J-Quants クライアントの耐障害設計
  - レート制限: 120 req/min を固定間隔で遵守
  - リトライ: 408/429/5xx 等を対象に指数バックオフ（最大3回）
  - 401 はリフレッシュトークンで自動リフレッシュ -> 1 回だけ再試行
  - ページネーション対応（pagination_key）
  - 保存時に fetched_at を UTC ISO 形式で記録

- ニュース収集のセキュリティ
  - defusedxml で XML 脆弱性対策
  - リダイレクト先のスキーム検証・プライベートIP排除（SSRF対策）
  - 受信サイズ上限（例: 10MB）を超えるレスポンスは拒否
  - URL 正規化 → SHA-256 部分を記事IDとして冪等性を確保

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution 層を定義
  - 多数のインデックスと制約（FK, CHECK）を用意
  - init_schema は冪等に全テーブルを作成

---

## ディレクトリ構成

（主要ファイルのみを抜粋）

src/
  kabusys/
    __init__.py                   # パッケージ初期化（__version__）
    config.py                     # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py           # J-Quants API クライアント（fetch/save 関数）
      news_collector.py           # RSS ニュース収集・保存
      pipeline.py                 # ETL パイプライン（run_daily_etl 等）
      schema.py                   # DuckDB スキーマ定義・init_schema
      audit.py                    # 監査ログ（signal/order/execution）初期化
      quality.py                  # データ品質チェック
      pipeline.py                 # ETL パイプライン
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

---

## 開発・テスト時のヒント

- 自動 .env ロードを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してパッケージ読み込み時の自動ロードをスキップできます（ユニットテスト等で利用）。
- DuckDB のインメモリ利用:
  - init_schema(":memory:") でテスト用インメモリDBを使用可能。
- ロギング:
  - 環境変数 `LOG_LEVEL` で制御（例: export LOG_LEVEL=DEBUG）

---

## 参考・運用上の注意

- 実際の売買（ライブ運用）を行う場合は、kabuステーション API パスワードや証券会社側のレート制限、注文の冪等性/失敗時の再試行ロジック、リスク管理を十分に検証してください。
- データ品質チェックは ETL の継続動作を前提に全件検出を行います。検出された QualityIssue の重大度に応じて運用側でアラート/停止判断を行ってください。
- 監査ログは削除しない前提の設計です。監査データの保持方針は運用ポリシーに従ってください。

---

必要であれば、この README をベースに導入ガイド（日本語）や API リファレンス、運用手順書（運用 runbook）をさらに作成します。どの部分を詳しくしたいか教えてください。