# KabuSys

KabuSys は日本株の自動売買プラットフォームのコアライブラリです。  
J-Quants API から市場データを取得して DuckDB に格納する ETL、RSS ニュース収集、データ品質チェック、監査ログ用スキーマなどを提供します。

現在のバージョン: 0.1.0

---

## 目次

- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（簡単なコード例）
- 環境変数一覧（.env）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は次の目的で設計されています。

- J-Quants API から株価（日足）・財務情報・市場カレンダーを取得して DuckDB に保存する（差分更新・バックフィル対応）
- RSS フィードからニュース記事を収集し、記事と銘柄コードの紐付けを行う
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレース）用のスキーマ定義
- カレンダー管理（営業日判定・翌営業日/前営業日取得）

設計上のポイント:
- API レート制限（J-Quants: 120 req/min）を尊重する仕組み
- リトライ（指数バックオフ）や認証トークン自動リフレッシュを実装
- DuckDB へは冪等的（ON CONFLICT）に保存
- SSRF や XML Bomb 等に対する防御（news_collector）

---

## 主な機能一覧

- データ取得 / 保存
  - jquants_client.fetch_daily_quotes / save_daily_quotes
  - jquants_client.fetch_financial_statements / save_financial_statements
  - jquants_client.fetch_market_calendar / save_market_calendar
- ETL パイプライン
  - data.pipeline.run_daily_etl（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
- ニュース収集
  - data.news_collector.fetch_rss / save_raw_news / run_news_collection
  - URL 正規化、トラッキングパラメータ除去、SSRF対策、gzip制限、XMLの安全パースなど
- データ品質チェック
  - data.quality.run_all_checks（欠損・重複・スパイク・日付不整合）
- カレンダー管理
  - data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチ）
- スキーマ初期化 / 監査ログ
  - data.schema.init_schema / get_connection
  - data.audit.init_audit_schema / init_audit_db

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントで `|` を使用しているため 3.10+ を想定する場合もありますが、コードは 3.9+ で動作するように書かれています）
- DuckDB を利用します（Python パッケージ duckdb）

1. リポジトリをクローンして開発環境にインストール（またはパッケージ化してインストール）

   ```
   git clone <repo-url>
   cd <repo-dir>
   pip install -e ".[dev]"   # setup.cfg/pyproject に extras があれば
   ```

   ※ minimal な依存が分かっている場合は直接インストールでも可:

   ```
   pip install duckdb defusedxml
   ```

2. 環境変数の設定

   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必要な環境変数例は下記セクション「環境変数一覧」を参照してください。

3. DuckDB スキーマの初期化

   Python シェルまたはスクリプトで:

   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   # settings.duckdb_path は .env の DUCKDB_PATH を参照（デフォルト "data/kabusys.duckdb"）
   conn = init_schema(settings.duckdb_path)
   ```

4. 監査ログ DB を別途用意する場合:

   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（簡単なコード例）

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得と品質チェック）

  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ（既定の RSS ソースを使用し DuckDB に保存）

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # known_codes に銘柄コードのセットを渡すと、記事と銘柄の紐付けを行う
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- J-Quants から直接データ取得（トークン自動管理）

  ```python
  from kabusys.data import jquants_client as jq
  # ID トークンは settings.jquants_refresh_token を使って自動取得・リフレッシュされる
  quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- データ品質チェックの実行

  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 環境変数一覧（.env）

KabuSys は起動時にプロジェクトルートの `.env` / `.env.local` を自動読込します（OS 環境変数が優先）。主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。jquants_client が ID トークンを取得するために使用。
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード（execution 関連で使用）。
- KABU_API_BASE_URL (任意)
  - kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot Token
- SLACK_CHANNEL_ID (必須)
  - 通知先の Slack チャンネル ID
- DUCKDB_PATH (任意)
  - メイン DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)
  - 監視用 SQLite パス（モジュールで使用する場合）
- KABUSYS_ENV (任意)
  - 動作モード。`development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL (任意)
  - ログレベル。`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まない

サンプル .env（例）:

```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 注意点・運用メモ

- J-Quants API のレート制限（120 req/min）を守るためモジュール内で固定間隔のレートリミッタを実装しています。過度な同時呼び出しは避けてください。
- HTTP エラーに対してリトライ（指数バックオフ）を行います。401（認証切れ）の場合はリフレッシュトークンで自動取得して 1 回再試行します。
- news_collector は RSS の XML を defusedxml で安全にパースし、SSRF 対策としてリダイレクト先の検査・プライベートアドレスの排除・gzip サイズ制限を行います。
- DuckDB スキーマは冪等的に作成されるため、init_schema を複数回呼んでも安全です。
- audit スキーマは init_audit_schema / init_audit_db を使って別 DB（または同一 DB）に初期化できます。init_audit_schema はオプションでトランザクションを使った初期化も可能です（DuckDB のトランザクション制約に注意）。

---

## ディレクトリ構成

（主要ファイル / モジュール）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント / 取得・保存ロジック
    - news_collector.py        — RSS ニュース収集・前処理・DB 保存
    - schema.py                — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — マーケットカレンダー管理・判定ユーティリティ
    - quality.py               — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                 — 監査ログスキーマ（signal/order/execution トレーサビリティ）
    - (その他)
  - strategy/
    - __init__.py             — 戦略層（拡張ポイント）
  - execution/
    - __init__.py             — 発注 / ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py             — モニタリング周り（拡張ポイント）

---

## 今後の拡張案（参考）

- execution モジュールに kabuステーション連携の実装（注文送信 / コールバック処理）
- strategy 層（複数戦略・バージョン管理・シグナル生成ロジック）
- Slack 通知や監視ダッシュボードの統合
- テストスイート・CI ワークフローの整備

---

もし README に追記したい利用シナリオ（例: cron ジョブ化、Docker 化、CI ワークフロー）や、README に含めたい具体的なコード例があれば教えてください。必要に応じてサンプル .env.example やデプロイ手順も作成します。