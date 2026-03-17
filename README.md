# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants API からの時系列データ取得、DuckDB ベースのスキーマ/ETL、RSS ニュース収集、データ品質チェック、監査ログ周りのユーティリティを提供します。

## 概要

KabuSys は次の目的を持つ内部ライブラリ群です。

- J-Quants API から株価日足・財務データ・マーケットカレンダーを安全に取得するクライアント
- DuckDB を用いたデータスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS フィードからのニュース収集と銘柄紐付け（SSRF 防止・サイズ制限・XML セキュリティ対応）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用のスキーマ初期化ユーティリティ
- カレンダー管理（営業日判定、前後営業日取得など）

設計上、API レート制限やリトライ、冪等性（ON CONFLICT 句）に配慮されています。

## 主な機能一覧

- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token、fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar
  - rate limiting（120 req/min）、再試行（指数バックオフ）、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存関数 save_* 系

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: カレンダー取得 → 株価差分取得＆保存 → 財務差分取得＆保存 → 品質チェック
  - 差分更新・backfill 機能、品質チェックとの連携

- データスキーマ（kabusys.data.schema）
  - DuckDB のテーブル定義（raw_prices, raw_financials, market_calendar, features, signals, orders, trades, positions, audit テーブル等）
  - init_schema / get_connection ユーティリティ

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（defusedxml 使用）、URL 正規化、記事ID（SHA-256 先頭32文字）生成、raw_news への冪等保存
  - SSRF 対策、レスポンスサイズ制限、gzip 解凍チェック、銘柄コード抽出

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日・期間内営業日取得、夜間カレンダー更新ジョブ

- 品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（前日比）・日付不整合の検出と QualityIssue 型での返却

- 監査ログ初期化（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの初期化、インデックス作成、UTC タイムゾーン設定

- 設定管理（kabusys.config）
  - .env 自動ロード（プロジェクトルート検出）、環境変数検証、settings オブジェクト経由の取得

## セットアップ手順

1. 前提
   - Python 3.9+（typing の | 型記法等を使用）
   - システムに pip と virtualenv 等がインストールされていること

2. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

3. 依存パッケージをインストール
   必要な主な外部依存:
   - duckdb
   - defusedxml
   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）
   ```bash
   pip install duckdb defusedxml
   ```

4. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動的に読み込まれます（読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   必須環境変数（例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_station_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   ```

   任意（デフォルト値あり）
   ```
   KABUSYS_ENV=development     # development | paper_trading | live
   LOG_LEVEL=INFO
   KABUS_API_BASE_URL=http://localhost:18080/kabusapi
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. DB 初期化（DuckDB）
   Python REPL かスクリプトで schema を初期化します。例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

   監査ログのみ別 DB に分けたい場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

## 使い方（代表的な呼び出し例）

以下は簡単な使用例です。

- J-Quants トークン取得（手動）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用
  ```

- 日次 ETL の実行
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 個別データ取得（株価をフェッチして保存）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, recs)
  ```

- RSS ニュースの収集と銘柄紐付け
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- 品質チェック（ETL 後に実行）
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

注意点:
- J-Quants API はレート制限 (120 req/min) を守るため、jquants_client は内部でスロットリングします。
- HTTP エラー（408/429/5xx）やネットワークエラーはリトライ（指数バックオフ）します。401 は refresh token から id_token を自動で再取得して 1 回リトライします。
- DuckDB への保存は各 save_* 関数で冪等（ON CONFLICT）となるよう設計されています。

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack bot token
- SLACK_CHANNEL_ID (必須) — Slack channel ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — set=1 で .env の自動読み込みを無効化

## 推奨ワークフロー（運用時）

- 開発: KABUSYS_ENV=development、ローカル DuckDB を使用して ETL 開発と品質チェックを行う。
- 本番（paper_trading / live）: 環境変数を適切にセット、監査ログは別 DB に切り出して保存。SLACK 通知など運用監視を組み合わせる。
- スケジューリング: 日次 ETL（run_daily_etl）を Cron や Airflow などで定期実行。ニュース収集は頻度に応じて複数回実行可能（RSS の負荷に注意）。
- バックフィル: データ欠損や過去データの修正があれば init_schema 後に run_prices_etl/run_financials_etl を日付レンジで実行して補填する。

## ディレクトリ構成

リポジトリ内の主なファイル・モジュール構成（抜粋）

- src/
  - kabusys/
    - __init__.py             # パッケージ定義（__version__ 等）
    - config.py               # 環境変数 / settings 管理（.env 自動ロード含む）
    - data/
      - __init__.py
      - jquants_client.py     # J-Quants API クライアント（fetch/save 等）
      - news_collector.py     # RSS ニュース収集・保存・銘柄抽出
      - schema.py             # DuckDB スキーマ定義・init_schema
      - pipeline.py           # ETL パイプライン（run_daily_etl 他）
      - calendar_management.py# カレンダー管理・営業日判定・更新ジョブ
      - audit.py              # 監査ログ用 DDL / 初期化
      - quality.py            # データ品質チェック
    - strategy/
      - __init__.py
      # （戦略ロジック用のプレースホルダ）
    - execution/
      - __init__.py
      # （発注・執行周りのプレースホルダ）
    - monitoring/
      - __init__.py
      # （監視・通知用のプレースホルダ）

## 開発・貢献

- コード品質: API 呼び出しはリトライ・レート制御・ログ出力を重視しているため、追加機能はこれらの方針に合わせてください。
- テスト: ネットワークを伴う部分はモック可能な設計（関数注入やモジュールレベルの hook）になっています。CI では外部 API 呼び出しをモックして単体テストを実行してください。

---

質問や README に追加して欲しい例（例: Dockerfile、CI 設定、より詳細な .env.example など）があれば教えてください。