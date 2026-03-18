# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（骨組み）。  
DuckDB を用いたデータ基盤、J-Quants からのデータ取得クライアント、ETL パイプライン、品質チェック、ニュース収集、ファクター計算（リサーチ向け）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的で設計されています。

- J-Quants API などから株価・財務・マーケットカレンダー・ニュースを取得して DuckDB に保存する ETL 基盤
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理（営業日判定、前後営業日検索）
- ニュース収集（RSS）と銘柄タグ付け
- 研究用途のファクター計算（モメンタム、ボラティリティ、バリュー等）と IC 計算・統計サマリー
- 監査ログ（order/signal/exec のトレーサビリティ）用スキーマ

設計方針の一部:
- DuckDB を中核 DB とし、ETL は冪等（ON CONFLICT）で安全に実行
- ネットワーク呼び出しはレートリミット・リトライ・トークン自動更新を備える
- 本番の発注 API など外部リソースへの依存を最小化し、研究モジュールは安全にローカルで動作する

---

## 機能一覧

- data/jquants_client
  - J-Quants API クライアント（ID トークン取得、自動リフレッシュ、ページネーション、レート制御、リトライ）
  - fetch / save 関数（株価日足、財務、マーケットカレンダー）
- data/schema
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) で初期化
- data/pipeline
  - 差分 ETL（prices / financials / calendar）の処理と run_daily_etl()
  - バックフィル / 品質チェック統合
- data/quality
  - 欠損・重複・スパイク・日付不整合などのチェック群
  - run_all_checks() でまとめ実行
- data/news_collector
  - RSS 取得（SSRF 対策、gzip 対応、受信サイズ制限）
  - 記事正規化、SHA256 ベース ID、raw_news 保存、news_symbols の紐付け
- data/calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job() による夜間カレンダー更新
- data/audit
  - 監査用スキーマ（signal_events / order_requests / executions）と初期化補助
- research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats.zscore_normalize を利用した正規化ユーティリティ
- config
  - 環境変数・.env ロード、Settings クラスによる設定アクセス

---

## 必要な環境変数

以下は Settings クラスで必須またはデフォルト設定として参照される環境変数です。

必須（未設定だと起動時に例外）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト `INFO`
- DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト `data/monitoring.db`

自動 .env ロードの無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます。

自動 .env ロードの挙動:
- プロジェクトルートを .git または pyproject.toml から特定し、優先順に `.env` (override=False)、`.env.local` (override=True) を読み込みます。既存の OS 環境変数は保護されます。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - このコードベースは少なくとも以下を必要とします:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   ※ 実際の requirements.txt がある場合はそれを使用してください。

4. 環境変数を設定
   - .env をプロジェクトルートに配置するか、OS 環境変数を設定します。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

5. DuckDB スキーマ初期化
   - Python から実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```

---

## 基本的な使い方（例）

- DuckDB スキーマの初期化

  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ディレクトリ自動作成
  ```

- 日次 ETL の実行（J-Quants トークンは環境変数で供給）

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を省略すると本日
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行

  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes に銘柄コード集合を渡すと記事 -> 銘柄の紐付けを行う
  known_codes = {"7203", "6758", "9984"}
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)
  ```

- 研究用ファクター計算（例: モメンタム）

  ```python
  from kabusys.data.schema import get_connection
  from kabusys.research import calc_momentum, calc_forward_returns

  conn = get_connection("data/kabusys.duckdb")
  from datetime import date
  target = date(2025, 1, 31)

  momentum = calc_momentum(conn, target)
  forwards = calc_forward_returns(conn, target, horizons=[1,5,21])
  ```

- IC（Information Coefficient）計算例

  ```python
  from kabusys.research import calc_ic
  # factor_records は calc_momentum 等の結果、forward_records は calc_forward_returns
  ic = calc_ic(factor_records=momentum, forward_records=forwards, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- 設定参照（Settings）

  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

---

## よく使う API / 関数一覧

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.jquants_client
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - get_id_token(refresh_token=None)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=[1,5,21])
  - calc_ic(factor_records, forward_records, factor_col, return_col)
  - factor_summary(records, columns)
  - zscore_normalize(records, columns)  (re-exported from data.stats)

---

## 注意点 / 運用上のポイント

- 自動 .env 読み込み:
  - パッケージは起動時にプロジェクトルート（.git または pyproject.toml）を探索し `.env` / `.env.local` を読み込みます。テスト等でこれを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB ファイルの配置:
  - デフォルトは data/kabusys.duckdb。init_schema() は親ディレクトリが存在しない場合は自動作成します。
- ネットワーク呼び出し:
  - J-Quants クライアントには固定レート制限（120 req/min）と自動リトライが実装されていますが、実運用時は API 使用量に注意してください。
- リサーチモジュール:
  - 研究用関数は外部の取引・発注には影響しないよう設計されています（読み取り専用、prices_daily/raw_financials のみ参照）。
- トランザクション管理:
  - news_collector の保存や ETL の一部はトランザクションでまとめられます。失敗時はロールバックされます。

---

## ディレクトリ構成

主要なファイル・モジュールのツリー（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - execution/            (発注・execution 関連のプレースホルダ)
  - strategy/             (戦略層のプレースホルダ)
  - monitoring/           (監視用モジュールのプレースホルダ)
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - etl.py
    - quality.py
  - research/
    - __init__.py
    - feature_exploration.py
    - factor_research.py

---

## 開発 / テストについて

- 単体テストや CI のためには、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して環境変数の自動ロードを抑制するとテストの再現性が向上します。
- ネットワーク依存の部分（jquants_client, fetch_rss など）はモック可能な実装になっており、_urlopen や ID トークン取得の挙動を差し替えてテストできます。

---

## 参考

- 環境変数の取得は kabusys.config.settings を通じて行ってください。未設定の必須キーは _require() により ValueError が発生します。
- DuckDB スキーマのディテールは kabusys.data.schema にコメント付きで定義されています。必要に応じてスキーマを拡張してください。

---

ご不明点や README に追加したい使用例（CLI、サービス化手順、systemd / cron 実行例など）があれば教えてください。必要に応じて README を拡張します。