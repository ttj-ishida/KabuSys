# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤のライブラリ（KabuSys）。  
DuckDB をデータレイクとして用い、J-Quants からのマーケットデータ収集、品質チェック、特徴量生成、監査ログ、ニュース収集などを提供します。戦略・発注・モニタリングの各層を分離して実装しています。

---

## 概要

このプロジェクトは以下の機能を持つモジュール群を提供します。

- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB を用いたスキーマ定義・初期化・接続ユーティリティ
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- 財務・価格データからのファクター（モメンタム／バリュー／ボラティリティ）計算
- ニュース（RSS）収集・正規化・記事 → 銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- ユーティリティ（Z スコア正規化等）

設計上、Research/Feature 計算は本番発注 API にアクセスしないようになっており、ETL・データ処理系は冪等（重複挿入回避）を意図しています。

---

## 主な機能一覧

- data/jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - RateLimiter、リトライ、401 時のトークン自動更新
- data/schema
  - DuckDB のテーブル定義と init_schema(db_path) による初期化
- data/pipeline
  - run_daily_etl：カレンダー → 株価 → 財務の差分 ETL と品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
- data/news_collector
  - RSS フィード取得、URL 正規化、記事ID生成、raw_news 保存、銘柄抽出と紐付け
  - SSRF 対策、受信サイズ制限、gzip 対応、XML 危険対策（defusedxml）
- data/quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（まとめ実行）
- research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
  - zscore_normalize（data.stats 経由で再エクスポート）
- audit
  - 監査ログテーブルの初期化（init_audit_schema / init_audit_db）

---

## 要求環境（目安）

- Python 3.10+
- 依存ライブラリ（主なもの）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード）

pip 等でインストールしてください（例: pip install duckdb defusedxml）。

---

## 環境変数 / 設定

config.Settings が環境変数から設定を読み込みます。プロジェクトルートの `.env` / `.env.local` を自動ロードする仕組みがあります（`.git` または `pyproject.toml` をプロジェクトルート検出に使用）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（名前はコード内と一致）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション等の API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）

例: `.env`（.env.example 的な内容）

export JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （開発パッケージ／テストがあれば別途インストール）

3. リポジトリルートに `.env` を作成し、必要な環境変数を設定

4. DuckDB スキーマ初期化
   - Python から init_schema を呼ぶ例（以下は簡易例）:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

   - 監査ログ専用 DB が必要な場合:

     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/kabusys_audit.duckdb")
     conn.close()

---

## 使い方（例）

- 日次 ETL を実行する（Python スクリプト例）

  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # テーブル作成と接続取得
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()

- ニュース収集ジョブを実行する

  from kabusys.data.news_collector import run_news_collection
  import duckdb
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット（例）
  res = run_news_collection(conn, sources=None, known_codes=known_codes, timeout=30)
  print(res)
  conn.close()

- 研究用ファクター計算（Research）

  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2024, 1, 31))
  # z-score 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  conn.close()

- J-Quants クライアントを直接呼ぶ（トークンは自動管理）

  from kabusys.data.jquants_client import fetch_daily_quotes
  data = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  # 取得後は save_daily_quotes を用いて DuckDB に保存可能

---

## 注意点 / 運用メモ

- J-Quants API はレート制限（120 req/min）を想定しており、ライブラリ内で固定間隔スロットリングを行います。
- get_id_token はリフレッシュトークン（JQUANTS_REFRESH_TOKEN）からの ID トークン取得を行います。401 発生時は自動で一度リフレッシュして再試行します。
- news_collector は SSRF 対策、受信サイズ上限、XML パースの安全化（defusedxml）等を実装しています。
- ETL は差分更新かつ backfill を行い、API の後出し修正にもある程度耐える設計です。
- データ品質チェック（data.quality）は Fail-Fast ではなく、すべてのチェック結果を返して呼び出し元で対応を決める方式です。
- duckdb に対する INSERT は可能な限り冪等（ON CONFLICT）を活用しています。
- 環境は KABUSYS_ENV によって development / paper_trading / live を切り替えできます。is_live 等で判定可能です。発注ロジックを組む際は必ず環境設定と安全スイッチを確認してください。

---

## ディレクトリ構成

（リポジトリの src/kabusys 以下の主要ファイル構成を抜粋）

src/kabusys/
- __init__.py
- config.py
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
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

主要な公開 API:
- kabusys.config.settings
- kabusys.data.schema.init_schema / get_connection
- kabusys.data.pipeline.run_daily_etl 等
- kabusys.data.jquants_client.*（fetch_* / save_*）
- kabusys.data.news_collector.run_news_collection
- kabusys.research.*（calc_momentum 等）

---

## 付録：よくある操作コマンド例

- パッケージを開発モードでインストール（プロジェクトルートで）

  pip install -e .

- DuckDB スキーマの初期化（対話的）

  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- 日次 ETL を cron から呼ぶ（簡易例）

  /path/to/venv/bin/python - <<'PY'
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  conn = init_schema('data/kabusys.duckdb')
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())
  conn.close()
  PY

---

README の内容や使い方で不明点があれば、どの操作を詳しく知りたいか（例: ETL スケジュール化、監査ログの運用、戦略層の実装テンプレート）を教えてください。さらに具体的な使い方例やテンプレートを用意します。