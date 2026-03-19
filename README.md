# KabuSys

日本株自動売買プラットフォーム（ライブラリ）  
バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants などの外部データソースから市場データや財務データ、RSS ニュースを取得して DuckDB に保存し、特徴量生成・リサーチ・戦略実行・監査ログなどを支援するモジュール群を提供します。

設計上のポイント
- DuckDB をストレージとして利用（ローカルファイル / in-memory 両対応）
- J-Quants API からの差分取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- ETL は冪等（INSERT ... ON CONFLICT）で実装
- News Collector は SSRF / XML Bomb 等のセキュリティ対策を実装
- Research / factor 計算は外部 API に依存せず DuckDB の prices_daily/raw_financials を参照して完結
- 簡易的なデータ品質チェックおよび監査テーブル群を提供

主な機能
---------
- データ取得・永続化
  - J-Quants からの日足（OHLCV）、財務データ、マーケットカレンダーの取得と DuckDB 保存
  - RSS フィードからのニュース収集と銘柄紐付け
- ETL
  - 差分更新（バックフィル対応）、品質チェック、daily ETL ワークフロー
- データスキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化ユーティリティ
  - 監査ログ用スキーマ（signal / order_request / executions）
- リサーチ / ファクター計算
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- カレンダー管理
  - 営業日判定、前後営業日の取得、カレンダー更新ジョブ
- 品質チェック
  - 欠損・重複・スパイク・日付不整合チェック

前提（推奨）
------------
- Python 3.10 以上（型アノテーションに | 演算子を使用）
- DuckDB
- defusedxml
（必要な依存は実プロジェクトの requirements.txt を参照してください。ここでは主要なものを列挙しています。）

セットアップ手順
----------------
1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   例（最小）:
   ```bash
   pip install duckdb defusedxml
   ```
   実運用では requests 等や Slack クライアント、kabu API 用の依存が必要になる場合があります。

4. 環境変数の設定
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   必須環境変数（config.Settings で参照）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション等の API パスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack 投稿先チャンネル ID

   任意/デフォルト
   - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
   - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db

   例 `.env`
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx-xxxx-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

基本的な使い方（コード例）
------------------------

- 設定の読み取り
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  ```

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")  # ファイルを自動作成
  # またはメモリ DB:
  # conn = init_schema(":memory:")
  ```

- 監査ログ DB 初期化（専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants から日足取得して保存（直接呼ぶ場合）
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- 日次 ETL 実行（pipeline）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知銘柄セット
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)
  ```

- リサーチ用ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2024, 1, 31)

  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- Z スコア正規化（data.stats）
  ```python
  from kabusys.data.stats import zscore_normalize

  normalized = zscore_normalize(records, ["mom_1m", "mom_3m"])
  ```

運用に関する注意
----------------
- J-Quants API のレート制限（120 req/min）を守るため内部に RateLimiter を実装済みです。大量ページングを伴う処理では時間がかかる可能性があります。
- save_ 系関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で設計されていますが、スキーマ変更時や外部からの直書きがある場合は品質チェックを定期的に実行してください。
- ニュース収集は外部 URL を取得するため SSRF 対策やサイズ制限（10MB）を行っています。追加のフィードを登録する際は信頼できるソースを使用してください。
- 実口座での運用はリスクを伴います。KABUSYS_ENV を適切に設定して paper_trading / live の切り替えを行ってください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                 : パッケージ定義（__version__ = "0.1.0"）
- config.py                   : 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py         : J-Quants API クライアント + 保存ユーティリティ
  - news_collector.py        : RSS ニュース収集・前処理・DB 保存
  - schema.py                : DuckDB スキーマ定義と init_schema
  - stats.py                 : 統計ユーティリティ（zscore_normalize 等）
  - pipeline.py              : ETL パイプライン（run_daily_etl 等）
  - quality.py               : データ品質チェック
  - calendar_management.py   : マーケットカレンダー管理
  - audit.py                 : 監査ログスキーマ初期化
  - features.py              : 特徴量公開インターフェース
  - etl.py                   : ETLResult の再エクスポート
- research/
  - __init__.py
  - feature_exploration.py   : 将来リターン・IC・統計サマリー等
  - factor_research.py       : momentum / volatility / value の実装
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

（上記は主要モジュールのみ。細かい補助モジュールはリポジトリ内を参照してください。）

貢献方法
--------
- バグ修正・改善提案は Issue を作成してください。
- プルリクエストでは、変更の目的・挙動・関連するテスト（可能な限り）を明記してください。

ライセンス
---------
（リポジトリに付与されているライセンスファイルを参照してください）

付録: よく使う関数一覧（抜粋）
--------------------------------
- data.schema.init_schema(db_path)
- data.audit.init_audit_db(db_path)
- data.jquants_client.fetch_daily_quotes(...)
- data.jquants_client.save_daily_quotes(conn, records)
- data.pipeline.run_daily_etl(conn, target_date=...)
- data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- research.calc_momentum(conn, date), calc_volatility(...), calc_value(...)
- research.calc_forward_returns(conn, date, horizons=[1,5,21])
- data.stats.zscore_normalize(records, columns)
- data.quality.run_all_checks(conn, target_date=..., reference_date=...)

お問い合わせ
----------
不明点やサポートが必要な箇所があれば Issue を立てるか、リポジトリのメンテナに連絡してください。