# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、DuckDB によるデータ管理、品質チェック、特徴量生成、リサーチ用ユーティリティ、ニュース収集、監査ログ等を含む設計です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／データ基盤向けモジュール群です。主に以下を提供します：

- J-Quants API 経由での OHLCV・財務・マーケットカレンダーの取得（ページネーション・レート制御・リトライ・トークン自動更新）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution / Audit）の初期化・操作
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース（RSS）収集と銘柄抽出
- リサーチ向けファクター計算（モメンタム・ボラティリティ・バリュー、将来リターン計算、IC 計算等）
- 汎用統計ユーティリティ（Zスコア正規化 等）
- マーケットカレンダー管理（営業日判定・次/前営業日取得）
- 監査ログ（シグナル→発注→約定のトレース用テーブル群）

設計上、本ライブラリは「DuckDB に格納された時系列データ（prices_daily 等）」を主要なデータソースとし、直接発注 API を呼ぶモジュールとは分離されています（発注関連は Execution / Audit スキーマを提供）。

---

## 主な機能一覧

- data/jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB への冪等保存）
  - レートリミッタ、リトライ、トークン自動リフレッシュ
- data/schema
  - DuckDB のスキーマ定義と init_schema（Raw / Processed / Feature / Execution 層など）
- data/pipeline
  - run_daily_etl: 日次 ETL（カレンダー→株価→財務＋品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl 単独ジョブ
- data/news_collector
  - RSS フィード取得、前処理、raw_news への保存、銘柄コード抽出
  - SSRF 対策、gzip 制限、XML の安全パースなど
- data/quality
  - 欠損 / スパイク / 重複 / 日付不整合の検出（QualityIssue オブジェクト）
- research
  - calc_momentum, calc_volatility, calc_value（DuckDB を入力に各種ファクターを計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索）
  - zscore_normalize（data.stats を通じて提供）
- data/calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- data/audit
  - 監査ログ用テーブル群と初期化ユーティリティ（init_audit_schema / init_audit_db）

---

## 前提・依存関係

最低限必要なライブラリ（例）:

- Python 3.9+
- duckdb
- defusedxml

（その他、標準ライブラリを多用。J-Quants API の利用にはネットワーク接続と認証トークンが必要です。）

インストール例（仮）:
```
pip install duckdb defusedxml
# このリポジトリを editable にインストールする場合
pip install -e .
```

---

## セットアップ手順

1. リポジトリを取得 / パッケージをインストール
   - ソースから: git clone して pip install -e するなど。

2. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` を作成すると自動で読み込まれます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   必須環境変数（Settings 参照）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD      : kabu ステーション API パスワード（必須）
   - SLACK_BOT_TOKEN       : Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID（必須）

   任意 / デフォルトあり:
   - KABU_API_BASE_URL     : kabu API エンドポイント（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

3. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ディレクトリが無ければ自動作成
     ```
   - 監査ログ専用 DB を別に作成する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

4. ログ設定
   - LOG_LEVEL を環境変数で設定するか、アプリ側で logging.basicConfig を設定してください。

---

## 使い方（代表的な例）

- 日次 ETL（J-Quants からデータ取得→保存→品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # 初回は init_schema を使う
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から株価データを個別取得して保存
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31), code="7203")
  saved = jq.save_daily_quotes(conn, records)
  ```

- ニュース収集の実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes は銘柄抽出に使用（例: DB から取得した全銘柄コードセット）
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- リサーチ用ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  from kabusys.data.stats import zscore_normalize
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2024, 1, 4)
  mom = calc_momentum(conn, d)
  vol = calc_volatility(conn, d)
  val = calc_value(conn, d)

  # 例: mom の一部カラムを Z スコア正規化
  mom_norm = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 特徴量の有用性評価（IC 計算）
  ```python
  from kabusys.research import calc_forward_returns, calc_ic
  fwd = calc_forward_returns(conn, date(2024,1,4), horizons=[1,5])
  ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

---

## よく使う API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.duckdb_path, settings.env, settings.is_live 等

- DuckDB スキーマ
  - init_schema(db_path)
  - get_connection(db_path)

- ETL
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- J-Quants クライアント
  - fetch_daily_quotes(...), save_daily_quotes(conn, records)
  - fetch_financial_statements(...), save_financial_statements(conn, records)
  - fetch_market_calendar(...), save_market_calendar(conn, records)

- News
  - fetch_rss(url, source), run_news_collection(conn, sources=None, known_codes=None)

- Research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=[1,5,21])
  - calc_ic(...), factor_summary(...), rank(...)

---

## ディレクトリ構成

（主要なファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得/保存/リトライ/レート制御）
    - news_collector.py     — RSS 収集・前処理・DB 保存・銘柄抽出
    - schema.py             — DuckDB スキーマ定義＆初期化（init_schema）
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - features.py           — 特徴量ユーティリティのエクスポート
    - calendar_management.py— マーケットカレンダー管理（営業日判定等）
    - audit.py              — 監査ログ（signal/order/execution 用テーブル）
    - etl.py                — ETL 用の公開型再エクスポート（ETLResult）
    - quality.py            — データ品質チェック（QualityIssue）
  - research/
    - __init__.py
    - feature_exploration.py— 将来リターン計算、IC、統計サマリー等
    - factor_research.py    — Momentum/Volatility/Value ファクター計算
  - strategy/
    - __init__.py           — 戦略モジュール格納場所（拡張向け）
  - execution/
    - __init__.py           — 発注管理 / ブローカー連携（拡張向け）
  - monitoring/
    - __init__.py           — 監視・アラート関連（拡張向け）

---

## 注意点・設計上の留意事項

- DuckDB スキーマ定義は冪等（IF NOT EXISTS / ON CONFLICT 等）を重視しています。初回のみ init_schema を実行してください。
- J-Quants クライアントは 120 req/min のレート制限、最大 3 回の指数バックオフリトライ、401 時はトークン自動更新の仕組みを持っています。
- news_collector には SSRF や XML インジェクション対策、gzip 解凍制限、受信サイズ上限など安全対策が組み込まれています。
- research モジュールは DuckDB の prices_daily / raw_financials テーブルのみを参照する設計で、本番発注 API にはアクセスしません（リサーチ専用）。
- 環境（KABUSYS_ENV）は "development", "paper_trading", "live" のいずれかを指定してください（それ以外は ValueError）。

---

## 貢献 / 拡張

- strategy/ や execution/ 以下に独自の戦略・発注ロジックを実装して組み込めます。
- ETL pipeline, news_collector のデータソースや品質チェックを必要に応じて拡張してください。
- モジュールは外部依存を最小化する方針で実装されていますが、実運用ではログ集約やメトリクス・監視、CI/CD、テストカバレッジの整備を推奨します。

---

README に書かれている操作はサンプルです。実運用前に必ずローカル環境で動作確認を行い、認証情報・シークレットは安全に管理してください。質問や追加ドキュメントが必要であれば教えてください。