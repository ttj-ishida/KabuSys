# KabuSys

日本株向けの自動売買プラットフォーム向けユーティリティ群です。  
データ収集（J-Quants）、ETLパイプライン、ニュース収集、データ品質チェック、マーケットカレンダー管理、監査ログスキーマなど、取引システムの基盤機能を提供します。

---

## 概要

KabuSys は以下を目的としたライブラリ群です。

- J-Quants API から日本株の時系列・財務・カレンダーを取得して DuckDB に保存する
- RSS からニュース記事を収集し前処理・銘柄抽出して保存する
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）を実行する
- JPX の市場カレンダー管理と営業日判定を行う
- データ品質チェック（欠損・スパイク・重複・日付不整合）を行う
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマを提供する

設計上の特徴：
- J-Quants API のレート制限 (120 req/min) に合わせたスロットリングとリトライ（指数バックオフ）を備えています
- トークン自動リフレッシュ、Look-ahead バイアス対策（fetched_at の記録）、DuckDB への冪等保存（ON CONFLICT）を実施
- ニュース収集は SSRF 対策、XML インジェクション対策（defusedxml）、レスポンスサイズ制限などセキュアに設計

---

## 主な機能一覧

- kabusys.config
  - 環境変数読み込み（.env, .env.local 自動ロード）と型安全な設定取得
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
  - レート制御、リトライ、401 時のトークンリフレッシュ対応

- kabusys.data.schema
  - init_schema(db_path) : DuckDB スキーマを初期化して接続を返す
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
    - 市場カレンダー取得 → 株価差分ETL → 財務差分ETL → 品質チェック

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)
  - URL 正規化・記事ID生成、SSRF/サイズ/Gzip/XML のセキュリティ対策、銘柄コード抽出

- kabusys.data.calendar_management
  - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks(...)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## セットアップ手順

1. 必要な Python バージョン
   - Python 3.10 以上（型注釈に | 演算子を使用）

2. 必要な依存パッケージ（例）
   - duckdb
   - defusedxml
   - （その他プロジェクト依存のパッケージがあれば pyproject.toml / requirements.txt を参照）

   pip の例:
   ```
   pip install duckdb defusedxml
   ```

3. リポジトリをチェックアウトしてインストール（開発環境）
   ```
   git clone <repo_url>
   cd <repo_root>
   pip install -e .
   ```
   （パッケージ化がない場合は直接 PYTHONPATH を通すか、プロジェクトルートで実行してください）

4. 環境変数の準備
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（.git または pyproject.toml を基準にルートを検出）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   必須の主な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   任意（デフォルトあり）:
   - KABUSYS_ENV: development / paper_trading / live （default: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL （default: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
   
   config の詳細は kabusys.config.Settings を参照してください。

5. データベース初期化
   - DuckDB スキーマを作成します（例）:
     ```
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```

---

## 使い方（簡単な例）

- 設定読み込み
  ```
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB スキーマ初期化
  ```
  from kabusys.data import schema
  conn = schema.init_schema(settings.duckdb_path)
  ```

- 日次 ETL 実行
  ```
  from kabusys.data import pipeline
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集ジョブ
  ```
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758"}  # 有効な銘柄コードのセット
  counts = run_news_collection(conn, known_codes=known_codes)
  print(counts)
  ```

- J-Quants トークン取得 / 直接データ取得
  ```
  from kabusys.data import jquants_client as jq
  token = jq.get_id_token()  # settings.jquants_refresh_token を使う
  quotes = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 監査スキーマ初期化（監査用 DB）
  ```
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- マーケットカレンダー判定
  ```
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_open = is_trading_day(conn, date.today())
  nxt = next_trading_day(conn, date.today())
  ```

- データ品質チェック
  ```
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for issue in issues:
      print(issue.check_name, issue.severity, issue.detail)
  ```

---

## 注意点 / 運用メモ

- J-Quants API 呼び出しは内部でレート制御（120 req/min）とリトライを行いますが、大量の並列リクエストは避けてください。
- fetch 系関数はページネーションに対応しています。ID トークンはモジュール内でキャッシュされ、401 発生時に自動リフレッシュします（1 回のみリトライ）。
- news_collector は外部 URL を扱うため SSRF 対策、XML コード注入対策、最大受信サイズチェック等を行っています。テスト時は _urlopen をモックすることで HTTP を差し替え可能です。
- DuckDB に対する書き込みは多くが ON CONFLICT を用いた冪等処理になっています（ETL を繰り返し実行しても安全）。
- 環境毎の挙動は KABUSYS_ENV に依存します（development / paper_trading / live）。運用時は live を指定して慎重に。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定・.env 自動ロード
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集・前処理・DB 保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（daily_etl 等）
    - calendar_management.py — マーケットカレンダー操作・バッチ
    - audit.py               — 監査ログスキーマの初期化
    - quality.py             — データ品質チェック
  - strategy/                — 戦略関連（パッケージ用の枠組み）
  - execution/               — 発注/実行関連（枠組み）
  - monitoring/              — 監視関連（枠組み）

---

## 開発・テスト

- config は .env 自動ロードを行いますが、ユニットテストや CI では
  `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- news_collector._urlopen や jquants_client の HTTP 呼び出しは外部通信をモックしてテスト可能に設計されています。
- DuckDB のインメモリ接続は `":memory:"` を指定して使用できます（テスト向け）。

---

## ライセンス / 貢献

- 本リポジトリのライセンスや貢献方法はリポジトリルートの LICENSE / CONTRIBUTING ファイルを参照してください。

---

必要であれば README に具体的な .env.example のテンプレートや、CI 用ワークフロー、より詳細な API 使用例（関数シグネチャの説明、返り値のサンプル）を追加します。どの情報を優先して追記しましょうか？