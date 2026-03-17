# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。J-Quants API から市場データ（株価・財務・マーケットカレンダー）を取得して DuckDB に保存する ETL パイプライン、RSS ベースのニュース収集、データ品質チェック、マーケットカレンダー管理、監査ログ用スキーマなどを備えています。

## 主な概要・設計方針
- データ取得は J-Quants API を利用（レート制限・リトライ・トークン自動リフレッシュ対応）
- データは DuckDB に 3 層（Raw / Processed / Feature）＋ Execution / Audit を保存
- ETL は差分更新・バックフィル対応で冪等性（ON CONFLICT）を重視
- ニュース収集は RSS を正規化・前処理して保存、SSRF / XML攻撃 / 大容量レスポンス対策あり
- 品質チェック（欠損・スパイク・重複・日付不整合）を提供
- マーケットカレンダーの営業日判定・前後営業日検索をサポート
- 監査ログ（signal → order_request → execution）のテーブルを別途初期化可能

---

## 機能一覧
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - レート制限（120 req/min）とリトライ（指数バックオフ、401 時はトークン自動更新）
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl（calendar → prices → financials → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分更新・バックフィル）
- DuckDB スキーマ初期化（kabusys.data.schema）
  - init_schema / get_connection（Raw/Processed/Feature/Execution テーブル、インデックス）
- ニュース収集（kabusys.data.news_collector）
  - fetch_rss（defusedxml, SSRF/リダイレクト検証, gzip 対応, レスポンス上限）
  - save_raw_news / save_news_symbols / run_news_collection
  - 記事 ID は URL 正規化後の SHA-256（先頭32文字）で冪等性を確保
  - 銘柄コード抽出（4桁数字, known_codes フィルタ）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチで差分更新）
- データ品質チェック（kabusys.data.quality）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（まとめて実行、QualityIssue オブジェクトで返却）
- 監査ログ初期化（kabusys.data.audit）
  - init_audit_schema / init_audit_db（監査用テーブル・インデックス、UTC タイムゾーン設定）
- 設定管理（kabusys.config）
  - .env / .env.local を自動ロード（プロジェクトルートは .git または pyproject.toml で判定）
  - Settings 経由で環境変数を型安全に取得

---

## 必要条件（推奨）
- Python 3.10+
- 依存パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリの urllib, hashlib, logging 等を使用）

（実際の requirements はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
   - プロジェクトルートには .git または pyproject.toml があることを想定します（自動 .env ロードのため）。

2. 仮想環境を作成して依存をインストール
   - 例:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     pip install duckdb defusedxml
     # またはパッケージのインストール手順に従う
     ```

3. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で .env.local）を置くと自動で読み込まれます。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必要な環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABU_API_BASE_URL（省略可、デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN（必須）
     - SLACK_CHANNEL_ID（必須）
     - DUCKDB_PATH（省略可、デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（省略可、デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化
   - Python から:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ":memory:" 指定でインメモリ DB
     ```
   - 監査ログ用スキーマの初期化:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

---

## 使い方（主要な API・例）

- 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # 引数で target_date や id_token を指定可能
  print(result.to_dict())
  ```

- 特定の ETL ジョブを個別に実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

  conn = init_schema("data/kabusys.duckdb")
  target = date.today()
  run_calendar_etl(conn, target)
  run_prices_etl(conn, target)
  run_financials_etl(conn, target)
  ```

- J-Quants トークン取得（必要な場合）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings が JQUANTS_REFRESH_TOKEN を読む
  ```

- ニュース収集ジョブを実行
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コード集合
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- カレンダー関連ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  d = date(2026, 3, 17)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 品質チェックを個別に実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

---

## 実装上の主な注意点・セキュリティ
- J-Quants API クライアントはレート制限（120 req/min）を守るため固定間隔スロットリングを使用します。
- HTTP エラー（408, 429, 5xx）やネットワークエラーに対して指数バックオフで最大3回リトライします。
- 401 受信時は refresh token から id_token を自動でリフレッシュして再試行します（1 回のみ）。
- RSS フィードの取得は defusedxml、レスポンスサイズ上限（10MB）、SSRF 対策（スキーム検証・プライベートIP拒否）を行います。
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）にしています。
- 環境変数の自動ロードはプロジェクトルート (.git または pyproject.toml) を検出して .env/.env.local を読み込みます。テスト等で自動ロードを停止したければ KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）
以下はリポジトリ内の主要モジュール／ファイル構成です（src/kabusys 以下）。

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py          # J-Quants API クライアント（fetch/save）
  - news_collector.py         # RSS ニュース収集・保存
  - pipeline.py               # ETL パイプライン（run_daily_etl 等）
  - schema.py                 # DuckDB スキーマ初期化
  - calendar_management.py    # マーケットカレンダー管理ユーティリティ
  - audit.py                  # 監査ログスキーマ初期化
  - quality.py                # データ品質チェック
- src/kabusys/strategy/
  - __init__.py (将来的な戦略モジュール用)
- src/kabusys/execution/
  - __init__.py (発注・約定処理用)
- src/kabusys/monitoring/
  - __init__.py (監視用)

---

## 追加情報・今後
- strategy / execution / monitoring の詳細実装はそれぞれのモジュールで拡張可能です。
- テスト、CI、パッケージ化（pyproject.toml）を整備すると運用がスムーズになります。
- 実環境での発注機能を有効化する際は、KABUSYS_ENV を paper_trading / live に切り替え、十分な検証を行ってください。

---

もし README に追加したい「例: cron での ETL スケジューリング方法」「Docker 化の手順」「テストの実行方法」などがあれば、用途に合わせて追記できます。どの部分を詳しく書くか指示ください。