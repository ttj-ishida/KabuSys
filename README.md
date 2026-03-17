# KabuSys

日本株自動売買システム用ライブラリ（KabuSys）。  
データ取得・ETL・品質チェック・監査ログ・ニュース収集など、アルゴリズムトレーディング基盤に必要な機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームの基盤ライブラリ群です。主に以下を提供します。

- J-Quants API からの市場データ取得（株価日足・四半期財務・市場カレンダー）
- DuckDB を用いたデータスキーマ定義と永続化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース（RSS）収集と銘柄紐付け
- マーケットカレンダー管理（営業日判定・翌日/前日検索）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針は「冪等性」「トレーサビリティ」「外部入力の安全性（SSRF・XML攻撃対策等）」を重視しています。

---

## 主な機能一覧

- 環境変数管理
  - .env / .env.local を自動読み込み（必要に応じて無効化可能）
  - 必須環境変数の明示的チェック

- J-Quants クライアント
  - 株価日足 / 財務 / マーケットカレンダー取得
  - レート制限（120 req/min）順守（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大3回）、401 の場合は自動トークンリフレッシュ（1回）
  - fetched_at によるデータ取得時刻の記録（Look-ahead Bias 対策）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS 取得 → 前処理（URL除去・空白正規化）→ raw_news に冪等保存
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256 の先頭32文字を記事IDとする
  - XML パースに defusedxml を使用（XML Bomb 等の防御）
  - SSRF 対策（スキーム検証・リダイレクト先のプライベートIPチェック・受信サイズ制限）
  - 銘柄コード抽出（本文中の4桁数字）と news_symbols 保存

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution / Audit（監査） 層のテーブル定義
  - インデックス定義・外部キー制約を含む初期化 API

- ETL パイプライン
  - 差分取得、バックフィル、品質チェックの統合（run_daily_etl）
  - 市場カレンダーの先読み取得
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- カレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等のユーティリティ
  - 夜間バッチ更新ジョブ（calendar_update_job）

- 監査ログ
  - signal_events, order_requests, executions 等を使った完全なトレーサビリティ
  - UUID ベースの冪等キー・タイムスタンプ（UTC）

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（ソースは typing | Path | duckdb を使用）
- DuckDB（Python パッケージ版）を使用
- ネットワーク経由の API 呼び出しが可能であること

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   - duckdb
   - defusedxml
   - （その他：logging 等は標準ライブラリ）

   例:
   ```
   pip install duckdb defusedxml
   ```

   実際のプロジェクトでは requirements.txt / pyproject.toml で管理してください。

4. 環境変数設定
   プロジェクトルートに `.env`（および任意で `.env.local`）を配置すると、自動的にロードされます。
   自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（少なくともこれらを設定してください）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意/デフォルト:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db

   `.env` の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化（例）
   Python でスキーマを初期化します（親ディレクトリがなければ自動作成）。
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   # 監査テーブルを追加する場合
   from kabusys.data import audit
   audit.init_audit_schema(conn)
   ```

---

## 使い方（簡易サンプル）

- J-Quants トークン取得:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を参照して取得
  ```

- 日次 ETL 実行（DB 接続済みを渡す）
  ```python
  from kabusys.data import pipeline, schema
  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集（既知銘柄 set を渡して紐付け）
  ```python
  from kabusys.data import news_collector, schema
  conn = schema.init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 例
  stats = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: saved_count}
  ```

- DuckDB の既存 DB に接続
  ```python
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  ```

- 品質チェックを個別に実行
  ```python
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意:
- J-Quants API 呼び出しは内部でレート制御・リトライを行いますが、ETL を大量に回す際はアプリ側でもスケジューリングに注意してください。
- news_collector は外部 URL を扱うため、ネットワーク／セキュリティ設定に注意（SSRF 保護等は実装済み）。

---

## 主要モジュール API 概要

- kabusys.config
  - settings: Settings オブジェクト（環境変数取得メソッドを提供）
  - 自動 .env 読み込み（.git または pyproject.toml を起点にプロジェクトルートを検出）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list[str] (新規挿入ID)
  - save_news_symbols(conn, news_id, codes) -> int
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30) -> dict

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続（全テーブル作成）
  - get_connection(db_path) -> DuckDB 接続（初期化は行わない）

- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl(conn, target_date=None, ... ) -> ETLResult

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, s, e)
  - calendar_update_job(conn, lookahead_days=...)

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)

（strategy, execution, monitoring パッケージは初期パッケージ構成として存在します）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）
- src/kabusys/
  - __init__.py
  - config.py
  - execution/ (パッケージ（空の __init__） — 発注周り用)
  - strategy/ (パッケージ（空の __init__） — 戦略実装用)
  - monitoring/ (パッケージ（空の __init__）)
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py        # RSS 収集・保存・銘柄抽出
    - pipeline.py              # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   # カレンダー管理・夜間更新
    - schema.py                # DuckDB スキーマ定義・初期化
    - audit.py                 # 監査ログ（signal/order/execution）スキーマ
    - quality.py               # データ品質チェック

---

## 運用上の注意点・設計上のポイント

- 環境自動ロード:
  - パッケージ起点で .env/.env.local を自動読み込みします。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- API レート制御:
  - J-Quants には 120 req/min の制限があるため固定間隔のスロットリングを実装しています。複数プロセス／複数ホストから同じ API を叩く場合は追加の調整が必要です。

- 冪等性:
  - raw テーブルへの保存は ON CONFLICT を利用して冪等にできます（重複更新）。

- セキュリティ:
  - news_collector は defusedxml と SSRF チェック、受信バイト数の上限を実装しています。外部 URL を扱うため、さらにネットワークレベルでの制限や監査を行うことを推奨します。

- 時刻:
  - 監査ログ等の TIMESTAMP は UTC 保存が前提です（audit.init_audit_schema が SET TimeZone='UTC' を実行）。

---

ご不明点や README に追加したい使用例（例えば docker 化、CI/CD スクリプト、具体的な ETL スケジュール例 等）があれば教えてください。必要に応じて運用手順やサンプルスクリプトを追記します。