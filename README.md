# KabuSys

日本株自動売買システムのライブラリ / コア実装群です。データ収集（J‑Quants、RSS）、ETL、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定トレース）など、運用に必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けに設計されたモジュール群です。主な目的は次のとおりです。

- J‑Quants API 等からのデータ収集（株価、財務、マーケットカレンダー）
- RSS フィードからニュース記事を収集・前処理し DB に保存
- DuckDB を用いたデータ格納（Raw / Processed / Feature / Execution の多層スキーマ）
- ETL パイプライン（差分更新、backfill、品質チェック）
- マーケットカレンダー管理（営業日判定、次/前営業日取得）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）
- 設定・環境変数管理（.env 自動読み込み機能付き）

設計方針として、冪等性（ON CONFLICT による更新）、Look‑ahead バイアス防止（fetched_at の記録）、レートリミット遵守、堅牢なエラーハンドリングを重視しています。

---

## 主な機能一覧

- 環境設定読み込み（.env / .env.local）と型付き Settings（`kabusys.config.settings`）
- J‑Quants API クライアント（トークン自動リフレッシュ、リトライ、レート制御）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_* 系関数で DuckDB に冪等保存
- RSS ニュース収集（URL 正規化、トラッキング除去、SSRF 対策、gzip 対応）
  - fetch_rss, save_raw_news, run_news_collection
  - 銘柄コード抽出（正規表現ベース）
- DuckDB スキーマ定義・初期化（raw/processed/feature/execution レイヤ）
  - init_schema, get_connection
- ETL パイプライン（差分更新・backfill・品質チェック）
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
- マーケットカレンダー管理ユーティリティ
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- データ品質チェック（欠損、重複、スパイク、日付不整合）
  - run_all_checks 等
- 監査ログスキーマ（signal_events, order_requests, executions）と初期化
  - init_audit_schema, init_audit_db

---

## 動作環境・依存

- Python 3.10 以上（型注釈に `|` を使用しているため）
- 主な依存ライブラリ（インストール時に requirements に加えてください）
  - duckdb
  - defusedxml

プロジェクトルートに `pyproject.toml` / `.git` があれば、自動で `.env` / `.env.local` を読み込みます（無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

---

## 環境変数（主なもの）

以下はコードで参照される主要な環境変数です。必須のものは README 内で明示します。

必須:
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（`kabusys.config.settings.jquants_refresh_token`）
- KABU_API_PASSWORD: kabuステーション API のパスワード（`kabusys.config.settings.kabu_api_password`）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV: `development` / `paper_trading` / `live`（デフォルト `development`）
- LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト `INFO`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: `1` を設定すると .env 自動読み込みを無効化
- KABUSYS による DB パス:
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
  - SQLITE_PATH: 監視用 SQLite のパス（デフォルト `data/monitoring.db`）
- KABUS_API_BASE_URL: kabu API のベース URL（デフォルト `http://localhost:18080/kabusapi`）

例 (.env):
DOTENV の読み込みは `.env` → `.env.local` の順で行われ、OS 環境変数を上書きしません（`.env.local` は override=True で上書き可能ですが、OS の環境変数は保護されます）。

---

## セットアップ手順（ローカルでの開発向け）

1. レポジトリをクローン / チェックアウト

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （パッケージを editable にする場合）pip install -e .

   ※ プロジェクトで pyproject / requirements.txt があればそれに従ってください。

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。例:

     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     DUCKDB_PATH=data/kabusys.duckdb
     ```

   - テスト時に自動読み込みを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB スキーマの初期化
   - Python から実行例:

     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```

   - これにより必要なテーブルとインデックスが作成されます。

---

## 使い方（主なユースケース）

以下はライブラリの主な関数を呼び出す簡単な使用例です。実運用ではエラーハンドリングやログ設定を追加してください。

- J‑Quants の ID トークン取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  ```

- 株価・財務・カレンダーの取得と保存（個別）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- 日次 ETL を一括実行
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- RSS ニュース収集（1ソース）
  ```python
  from kabusys.data.news_collector import fetch_rss, save_raw_news
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  new_ids = save_raw_news(conn, articles)
  ```

- ニュース一括収集（既知銘柄との紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例：有効銘柄セット
  results = run_news_collection(conn, known_codes=known_codes)
  ```

- マーケットカレンダーの夜間更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  ```

- 品質チェック（ETL 後）
  ```python
  from kabusys.data.quality import run_all_checks
  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

- 監査ログスキーマの初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/kabusys_audit.duckdb")
  ```

---

## 設計上の注意点 / 実装のポイント

- J‑Quants クライアントは API レート制限（120 req/min）を守るために固定間隔スロットリングを採用しています。大量取得は間隔に注意してください。
- リトライは指数バックオフ（最大 3 回）、408/429/5xx を考慮し、401 は自動トークンリフレッシュ（1 回のみ）を試みます。
- データ保存は原則的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）です。重複挿入での副作用を最小化しています。
- NewsCollector は SSRF 対策（スキーム検証、プライベートIP拒否、リダイレクト検査）や XML のハードニング（defusedxml）を実装しています。
- DuckDB スキーマは Raw / Processed / Feature / Execution レイヤに分かれており、監査ログ用の別スキーマ（または別 DB）を用意できます。
- データ品質チェックは Fail‑Fast ではなく全チェックを収集し、呼び出し元で判断できるように設計されています。

---

## ディレクトリ構成

以下は主要ファイルのツリー（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/               # 発注・ブローカー連携関連（未実装のプレースホルダ）
      - __init__.py
    - strategy/                # 戦略ロジック（未実装のプレースホルダ）
      - __init__.py
    - monitoring/              # モニタリング関連（未実装のプレースホルダ）
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py      # J‑Quants API クライアント（取得・保存）
      - news_collector.py      # RSS ニュース収集・前処理・保存
      - schema.py              # DuckDB スキーマ定義・初期化
      - pipeline.py            # ETL パイプライン（差分取得・backfill・品質チェック）
      - calendar_management.py # マーケットカレンダー管理
      - audit.py               # 監査ログスキーマ初期化
      - quality.py             # データ品質チェック
- pyproject.toml / setup.cfg / README.md (本ファイル)

---

## 貢献 / 開発メモ

- 自動環境読み込みはプロジェクトルートを `.git` または `pyproject.toml` を基準に探します。テスト時などで自動読み込みを抑制するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を使用しているため、データ操作は SQL を直接投げる形で拡張しやすく、ETL の効率化や分析にも向きます。
- strategy / execution / monitoring パッケージは拡張ポイントとして用意しています。実際の発注ロジックや戦略はこの層に実装してください。
- ロギングは各モジュールで logger を取得しているので、アプリ側でハンドラやフォーマッタを設定すると運用しやすくなります。

---

その他の質問（例: 特定の ETL ワークフロー例、DB スキーマの詳細、監査ログの利用例等）があれば、用途に合わせた具体的な README の追記やサンプルコードを作成します。