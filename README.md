# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群。データ取得（J-Quants 等）、ETL、データ品質チェック、ニュース収集、監査ログ（発注→約定のトレーサビリティ）など、取引システムの基盤処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような機能を持つモジュール群です。

- J-Quants API からの市場データ（株価日足、財務データ、マーケットカレンダー）取得と DuckDB への保存
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- RSS ベースのニュース収集と記事→銘柄の紐付け
- マーケットカレンダー管理（営業日判定、次営業日／前営業日取得）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル／発注要求／約定）の初期化と管理

設計上のポイント:
- API レート制限、リトライ、トークン自動更新に対応
- DuckDB を用いた冪等な保存（ON CONFLICT を利用）
- SSRF や XML Bomb などのセキュリティ対策を考慮した実装
- ロギングと品質チェックによりデータ健全性を担保

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants からの fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レートリミッタ、指数バックオフリトライ、401 時のトークン自動リフレッシュ
  - DuckDB への save_* 関数（冪等）

- data/pipeline.py
  - run_daily_etl: 市場カレンダー→株価→財務→品質チェックの一括 ETL
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・バックフィル対応）

- data/news_collector.py
  - RSS フィード取得（gzip 対応、SSRF/プライベートホストチェック、受信サイズ制御）
  - 記事 ID を URL 正規化→SHA-256（先頭32文字）で生成し raw_news へ冪等保存
  - 銘柄コード抽出・ニュースと銘柄の紐付け保存

- data/schema.py
  - DuckDB のスキーマ定義と init_schema（Raw/Processed/Feature/Execution 層のテーブル）
  - インデックス作成

- data/quality.py
  - 欠損、スパイク、重複、日付不整合のチェックと QualityIssue 型での報告
  - run_all_checks でまとめて実行

- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間カレンダー差分更新）

- data/audit.py
  - 監査ログ用テーブル（signal_events, order_requests, executions）定義と init_audit_db
  - すべてのタイムスタンプは UTC を前提

- config.py
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 環境変数アクセス用 Settings（必須変数のチェック、env / log_level 等）

---

## 必要条件（依存ライブラリ）

本 README で明示したコードを動かす際に必要な代表的パッケージ:

- Python 3.9+
- duckdb
- defusedxml

（実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン／ワークスペースに配置

2. 仮想環境を作成して依存をインストール
   - 例（venv + pip）:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb defusedxml
     ```

3. 環境変数の設定
   - プロジェクトルートに `.env`（および開発用に `.env.local`）を置くと config モジュールが自動読み込みします。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（Settings が参照するもの）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (省略可, デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (省略可, デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live)
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python スクリプトで schema.init_schema を呼び出します:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ用 DB を別途初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（簡単な例）

以下は基本的な操作例です。各関数は duckdb の接続オブジェクトを受け取ります。

- 日次 ETL を実行する（J-Quants トークンは Settings から取得される）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 単独で株価 ETL を実行（差分更新）:
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_prices_etl

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")
  ```

- RSS ニュース収集ジョブを実行して保存・銘柄紐付け:
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 事前に用意した銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新ジョブを夜間に実行:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved calendar records:", saved)
  ```

- 品質チェックを個別実行:
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date.today(), reference_date=date.today())
  for i in issues:
      print(i)
  ```

注意:
- jquants_client の HTTP リトライや rate-limit を内部で実施します。高頻度での同時実行は避けてください。
- get_id_token は refresh token を基に ID トークンを取得します。401 の際は自動リフレッシュ処理があります。

---

## .env 自動読み込みの挙動

- 実行時に config モジュールがプロジェクトルート（.git または pyproject.toml を親階層から探索）を検出すると、自動で以下を読み込みます（優先度順）:
  1. OS 環境変数
  2. .env.local（存在する場合、既存 OS 環境変数を保護しつつ上書き）
  3. .env（未設定のキーのみセット）

- 自動ロードを無効化するには環境変数を設定:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

- 必須環境変数が未設定の場合、Settings のプロパティアクセス時に ValueError が送出されます。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント + DuckDB 保存
    - news_collector.py        # RSS 収集・前処理・保存・銘柄抽出
    - schema.py                # DuckDB スキーマ定義・初期化
    - pipeline.py              # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   # 市場カレンダー管理・ジョブ
    - audit.py                 # 監査ログ用スキーマと初期化
    - quality.py               # データ品質チェック
  - strategy/                   # 戦略関連（雛形）
    - __init__.py
  - execution/                  # 発注・約定関連（雛形）
    - __init__.py
  - monitoring/                 # 監視・メトリクス（雛形）
    - __init__.py

---

## 開発上の注意点

- テスト実行時は自動 .env 読み込みを無効にするか、テスト専用の .env を使用してください（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- DuckDB の接続はスレッド／プロセス間で扱う際に注意が必要です。マルチプロセスで使う場合は個別の接続を推奨します。
- NewsCollector は外部 URL にアクセスするため、環境（プロキシ、ネットワーク制限）に依存します。SSL/TLS やファイアウォールの設定を確認してください。
- 監査ログは削除を想定していません（ON DELETE RESTRICT 等）。運用設計に沿ったローテーションやアーカイブを検討してください。

---

## 追加情報 / 今後の拡張候補

- 実際の発注実行（kabuステーション API 連携）や Webhook コールバックの受信処理の実装
- Slack 通知やモニタリング（Prometheus / Grafana）統合
- Strategy 層の実装とバックテスト用ユーティリティ
- CI/CD 用のテスト・型チェックの整備

---

参考、問い合わせ:
- ソース内ドキュメント（docstring）を参照してください。API の使い方・引数仕様は各モジュールの docstring に詳細があります。