# KabuSys

日本株自動売買システムのライブラリ（KabuSys）。データ収集、ETL、データ品質チェック、マーケットカレンダー管理、ニュース収集、監査ログ（トレーサビリティ）など、アルゴリズム取引プラットフォームに必要な基盤機能を提供します。

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを安全かつ冪等に取得・保存
- RSS からのニュース収集と銘柄（4桁コード）抽出、DuckDB への保存
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ETL（差分更新、バックフィル、先読みカレンダー）
- マーケットカレンダーの営業日判定・検索ユーティリティ
- 監査ログ（シグナル→発注→約定のトレース可能なスキーマ）
- DuckDB を用いたローカルデータレイク構成

設計上の重点：
- 冪等性（ON CONFLICT / DO UPDATE / DO NOTHING）
- API レートリミット順守（J-Quants: 120 req/min）
- リトライ・トークン自動リフレッシュ
- セキュリティ対策（RSS の XML Bomb / SSRF / 圧縮爆弾対策 等）
- テストしやすさ（id_token の注入など）

---

## 機能一覧

主な機能（モジュール単位）

- kabusys.config
  - .env または環境変数の自動読み込み（プロジェクトルート探索）
  - 必須設定の検査（settings オブジェクト）
  - 有効な環境: `development`, `paper_trading`, `live`
  - ログレベル検証（DEBUG/INFO/...）

- kabusys.data.jquants_client
  - J-Quants 認証（refresh token → idToken）
  - fetch_daily_quotes（株価日足、ページネーション対応）
  - fetch_financial_statements（四半期財務）
  - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ保存する save_* 関数（raw_prices, raw_financials, market_calendar）
  - レートリミティング、リトライ、401 自動リフレッシュ、fetched_at 記録

- kabusys.data.news_collector
  - RSS フィード取得（gzip 対応、最大受信バイト数制限）
  - XML の安全パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去・記事ID（SHA-256 先頭32文字）
  - SSRF/プライベートホスト対策（リダイレクト検査、IP 判定）
  - raw_news / news_symbols の冪等保存（INSERT ... RETURNING）
  - 銘柄コード抽出（4桁、known_codes によるフィルタ）

- kabusys.data.schema
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - インデックス作成と依存順を考慮した DDL 実行

- kabusys.data.pipeline
  - 差分 ETL（prices / financials / calendar）
  - run_daily_etl: 日次パイプライン（カレンダー先読み・差分取得・品質チェック）
  - 品質チェックの呼び出し（quality モジュール）

- kabusys.data.calendar_management
  - 営業日判定 / next/prev_trading_day / get_trading_days
  - カレンダー夜間更新ジョブ（calendar_update_job）

- kabusys.data.quality
  - 欠損データ / スパイク（前日比） / 重複 / 日付不整合チェック
  - QualityIssue 型で問題を返却（severity: error|warning）

- kabusys.data.audit
  - 戦略→シグナル→発注→約定を完全トレースする監査スキーマ
  - init_audit_db / init_audit_schema（UTC タイムゾーン固定）

---

## セットアップ手順

前提: Python 3.10+（型注釈に Union 型の省略表記等を使用）

1. リポジトリをクローンしてパッケージをインストール（例: pip editable）
   - 例:
     ```
     git clone <repo-url>
     cd <repo>
     pip install -e .
     ```
   - 依存（代表的なもの）: duckdb, defusedxml
     （pyproject.toml / requirements.txt がある場合はそちらを利用してください）

2. 環境変数 / .env を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（settings から確認）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL) — default: INFO
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

3. DuckDB 初期化
   - 例（Python REPL / スクリプト）:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```

4. 監査用 DB 初期化（任意）
   - 例:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方

ここでは主要なユースケースの最小限の使用例を示します。

- settings を読む（環境変数）
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)  # 未設定なら ValueError が発生
  ```

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL の実行（J-Quants トークンは settings から自動使用）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄コードセット（例: {'7203', '6758', ...}）
  stats = run_news_collection(conn, known_codes=known_codes_set)
  print(stats)  # {source_name: saved_count}
  ```

- マーケットカレンダー更新（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved", saved)
  ```

- J-Quants API を直接使う（トークン取得・フェッチ）
  ```python
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
  records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  jq.save_daily_quotes(conn, records)
  ```

- 品質チェックの実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意点（実運用）
- run_daily_etl は複数ステップを独立して実行し、各ステップで例外を捕捉してログと ETLResult.errors に記録します。
- J-Quants API はレート制限（120 req/min）に合わせたスロットリングとリトライを内部で行います。
- news_collector は SSRF・XML bomb・gzip 解凍サイズチェック等のセキュリティ対策が組み込まれています。

---

## ディレクトリ構成

リポジトリの主要ファイル・モジュール構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     --- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            --- J-Quants API クライアント（取得・保存）
    - news_collector.py            --- RSS ニュース収集・保存・銘柄抽出
    - schema.py                    --- DuckDB スキーマ定義・初期化
    - pipeline.py                  --- ETL パイプライン（差分・品質チェック）
    - calendar_management.py       --- カレンダー管理（営業日判定等）
    - audit.py                     --- 監査ログ用スキーマ・初期化
    - quality.py                   --- データ品質チェック
  - strategy/
    - __init__.py                  --- 戦略層（拡張用プレースホルダ）
  - execution/
    - __init__.py                  --- 発注・ブローカー連携（拡張用プレースホルダ）
  - monitoring/
    - __init__.py                  --- モニタリング（拡張用プレースホルダ）

補足:
- DuckDB スキーマは Raw / Processed / Feature / Execution の複数層に分かれ、外部キー・インデックスを考慮して順に作成されます。
- news_collector の既定 RSS ソースは DEFAULT_RSS_SOURCES に定義されています（現状は Yahoo Finance のビジネスカテゴリが例として登録）。

---

## 環境変数一覧（主なもの）

必須：
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルトあり：
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL) — default: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動ロードを無効化)

---

## ログ・トラブルシューティング

- 各モジュールは標準 logging を利用しています。LOG_LEVEL を環境変数で調整してください。
- J-Quants API 呼び出しで 401 が返った場合、ライブラリは自動的に refresh token から id_token を再取得して 1 回リトライします。
- RSS 取得時の XML 解析失敗やサイズ超過は警告ログ出力の上で該当ソースをスキップします（run_news_collection は他ソースへ継続）。

---

必要に応じて README の具体的なインストール手順（pyproject.toml や CI の設定）やサンプル .env.example、運用ガイド（cron ジョブ / Airflow / systemd タイマー設定）を追加できます。追加したい内容があれば教えてください。