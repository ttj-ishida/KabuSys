# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ（データ基盤・ETL・監査・ニュース収集など）

このリポジトリは、J-Quants や kabu ステーション等からのデータ取得、DuckDB を用いたスキーマ管理、ETL パイプライン、ニュース収集、監査ログ機能などを提供するモジュール群です。戦略層・実行層・監視層と組み合わせて自動売買システムの基盤を構築する目的で設計されています。

バージョン: 0.1.0

---

## 主な機能

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限・リトライ・401 によるトークン自動リフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead を防止
- DuckDB ベースのスキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル群を定義・初期化
  - インデックスや外部キーなどの整備
- ETL パイプライン
  - 差分更新（最終取得日からの差分）・バックフィル対応
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL の統合エントリポイント
- ニュース収集モジュール
  - RSS フィードの安全な取得（SSRF 対策、gzip/サイズチェック、XML の安全パース）
  - 記事の正規化・トラッキングパラメータ除去・SHA-256 ベースの記事 ID（冪等）
  - raw_news / news_symbols への冪等保存
- マーケットカレンダー管理（営業日判定、next/prev/trading_days）
- 監査ログ（signal / order_request / execution）テーブルの初期化と管理
- データ品質チェックモジュール（独立して呼び出せる）

---

## 要求環境

- Python 3.10+
  - 型注釈で `|`（PEP 604）を使用しているため Python 3.10 以上を想定しています。
- 主な依存ライブラリ
  - duckdb
  - defusedxml

（実行環境や追加機能に応じて標準ライブラリ外のパッケージが必要になります。本プロジェクトをパッケージ化する際は requirements.txt / pyproject.toml を参照してください。）

---

## セットアップ手順

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS) または .venv\Scripts\activate (Windows)

2. 必要なパッケージをインストール
   - pip install duckdb defusedxml
   - （追加でロギングやテストツールなどがあれば別途インストール）

3. 環境変数 / .env の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必要な環境変数（主要なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu API 用パスワード（必須）
     - KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID: Slack 送信先チャンネル（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）

   - 例（.env.example）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データベーススキーマの初期化
   - DuckDB スキーマを作成します（ファイルは自動作成されます）。
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB を初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要 API / 例）

このライブラリは CLI ではなく Python API として利用する想定です。以下は典型的な使い方例です。

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # 引数を指定して振ることも可
  print(result.to_dict())
  ```

- 個別 ETL ジョブ
  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  # conn は init_schema で得た DuckDB 接続、target_date は datetime.date
  fetched, saved = run_prices_etl(conn, target_date)
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に使う有効な銘柄コードのセット
  results = run_news_collection(conn, known_codes={"7203","6758"})
  print(results)  # {source_name: saved_count}
  ```

- カレンダー夜間バッチ更新
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved", saved)
  ```

- J-Quants からの取得（低レベル）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()
  records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
  ```

- 設定値参照（環境変数ラッパ）
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.kabu_api_base_url)
  ```

---

## 主要モジュール説明

- kabusys.config
  - 環境変数の自動読み込み（.env/.env.local）、設定値アクセス用 Settings オブジェクト
  - 必須値が不足していると ValueError を送出

- kabusys.data.jquants_client
  - J-Quants API との HTTP 通信処理（レート制限・リトライ・トークンリフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存関数: save_daily_quotes / save_financial_statements / save_market_calendar

- kabusys.data.news_collector
  - RSS フィードの安全な取得と整形、raw_news / news_symbols への冪等保存
  - URL の正規化、記事 ID の生成、SSRF 対策、gzip サイズチェック など

- kabusys.data.schema
  - DuckDB のスキーマ DDL を定義して init_schema によりテーブル作成を行う

- kabusys.data.pipeline
  - 差分ETL（prices/financials/calendar）の実装、日次 ETL の統合
  - 品質チェック連携（kabusys.data.quality）

- kabusys.data.calendar_management
  - market_calendar を用いた営業日判定や next/prev_trading_day、カレンダーの差分更新ジョブ

- kabusys.data.audit
  - 監査ログ用のテーブル群（signal_events / order_requests / executions）の初期化関数

- kabusys.data.quality
  - データ品質チェック（欠損・重複・スパイク・日付不整合）を実行するユーティリティ

- その他
  - strategy, execution, monitoring パッケージは将来の戦略実装・実行系・監視ロジックのために用意

---

## ディレクトリ構成

（主なファイルとモジュール）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - calendar_management.py
  - audit.py
  - quality.py
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

補足:
- スキーマ定義や DDL は data/schema.py にまとまっています。
- ETL ロジックは data/pipeline.py、ニュース収集は data/news_collector.py にあります。

---

## トラブルシューティング / 注意点

- 必須の環境変数が未設定の場合、settings の該当プロパティ呼び出しで ValueError が発生します。
- 自動で .env を読ませたくないテスト等の場面では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は init_schema を使って行ってください（ファイルの親ディレクトリを自動作成します）。
- J-Quants API のレート制限（120 req/min）を守る設計です。大量の同時リクエストを行う使い方には注意してください。
- ニュース収集は外部ネットワークにアクセスします。SSRF や XML の安全性を考慮した実装ですが、本番ネットワークポリシーに注意して運用してください。

---

この README はコードベースの概要と主要な使い方を示したものです。詳細な API 仕様や運用手順（スケジューラ設定、Slack 通知フロー、証券会社 API の接続方法など）は別途ドキュメントとして追加することを推奨します。質問や補足があれば教えてください。