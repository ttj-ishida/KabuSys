# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）の内部モジュール群です。  
本リポジトリは主に下記を提供します。

- J-Quants / JPX 等からのデータ取得クライアントと ETL パイプライン
- DuckDB ベースのスキーマ定義・初期化
- ニュース収集（RSS）・記事の正規化と銘柄紐付け
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）および研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査（オーダー／約定トレース）用スキーマ

目的：Look-ahead biasの管理や冪等性、APIレート制御等を考慮した安全なデータ基盤と研究・発注の基礎コンポーネントを提供します。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - DuckDB への冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- スキーマ管理
  - DuckDB の全スキーマ初期化（init_schema）
  - 監査ログ専用スキーマ初期化（init_audit_db / init_audit_schema）
- ニュース収集
  - RSS 取得（fetch_rss）、前処理（URL除去・空白正規化）、記事保存（save_raw_news）、銘柄抽出・紐付け（extract_stock_codes / save_news_symbols）
  - SSRF や XML Bomb 対策、サイズ制限等のセーフガード実装
- 研究用・特徴量
  - モメンタム / ボラティリティ / バリューのファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン / IC 計算（calc_forward_returns / calc_ic / rank）
  - Zスコア正規化ユーティリティ（zscore_normalize）
- データ品質チェック
  - 欠損 / 重複 / スパイク / 日付不整合チェック（run_all_checks 等）
- 設定管理
  - .env/.env.local 自動読み込み（パッケージ配布後も cwd 非依存）／無効化用フラグ

---

## 必要な環境・依存パッケージ

最低限必要な Python モジュール（pip でインストール）:

- duckdb
- defusedxml

（その他は標準ライブラリのみで多くが実装されています。実行環境に応じて追加のロギングや Slack 通知等を用意してください。）

例:
```
pip install duckdb defusedxml
```

---

## 環境変数（重要）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)。デフォルト development
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)。デフォルト INFO

.env の例:
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

## セットアップ手順

1. Python のインストール（推奨: 3.9+）
2. 必要パッケージのインストール:
   ```
   pip install duckdb defusedxml
   ```
3. プロジェクトルートに `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマ初期化（例: Python REPL やスクリプトから）:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ファイルパスは任意
   ```
5. （監査DBが別に必要な場合）
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な例）

- ETL（J-Quants からのデータフェッチと保存）を日次で実行:
  ```python
  from datetime import date
  import logging
  from kabusys.data import schema, pipeline

  logging.basicConfig(level=logging.INFO)

  conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema を実行済みの想定
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）:
  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes は有効な銘柄コードセットを渡すと抽出して紐付けする
  known_codes = {"7203", "6758", "9984"}
  stats = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(stats)
  ```

- ファクター計算（研究用途）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  ```

- 将来リターン・IC の計算:
  ```python
  from kabusys.research import calc_forward_returns, calc_ic, rank
  fwd = calc_forward_returns(conn, target_date)
  # factor_records は各種ファクターを含む dict のリスト
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

---

## 注意点 / 設計指針（抜粋）

- J-Quants クライアントはレート制限（120 req/min）を守るため内部にスロットリングを実装しています。
- API 呼び出しはリトライ・指数バックオフ・401 時の自動トークンリフレッシュを備えます。
- DuckDB への保存は冪等（ON CONFLICT ... DO UPDATE / DO NOTHING）で実装されています。
- ニュース取得は SSRF / XML Bomb / レスポンスサイズの保護を行っています。
- 研究モジュールは外部ライブラリ非依存で、DuckDB の prices_daily / raw_financials テーブルのみを参照します（発注APIにはアクセスしません）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を基準に行われます。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

（src/kabusys 以下の主なファイル・モジュール）

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env ロード・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（fetch/save 系）
    - news_collector.py  — RSS 取得・記事保存・銘柄抽出
    - schema.py  — DuckDB スキーマ定義・init_schema / get_connection
    - stats.py  — zscore_normalize 等の統計ユーティリティ
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - features.py  — 公開インターフェース（zscore_normalize 再エクスポート）
    - calendar_management.py — マーケットカレンダー管理 / バッチ更新
    - audit.py — 監査ログスキーマ / init_audit_db
    - etl.py — ETLResult 再エクスポート
    - quality.py — データ品質チェック（check_missing_data, check_spike, ...）
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン / IC / summary / rank
    - factor_research.py — calc_momentum / calc_volatility / calc_value
  - strategy/  — 戦略関連（未実装のプレースホルダ）
  - execution/ — 発注関連（未実装のプレースホルダ）
  - monitoring/ — 監視用モジュール（プレースホルダ）

各モジュールの詳細はソースコード内の docstring を参照してください。

---

## 開発者向けメモ

- DuckDB の SQL 文はパラメータバインド（?）を用いており SQL インジェクション対策が組み込まれています。
- 一部の関数はトランザクションを明示的に開始（conn.begin() / conn.commit() / conn.rollback()）します。呼び出し側でトランザクション管理に注意してください（DuckDB はネストトランザクションに制限あり）。
- テストや CI では環境変数の自動読み込みを無効化して isolate された環境を作ることを推奨します（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

必要であれば、README にサンプル .env.example、docker-compose での実行例、より詳細な API 使用例（各 fetch/save の具体的なパラメータ）や運用フロー（cron・Airflow での運用推奨）を追加します。どの情報を優先して追加したいか教えてください。