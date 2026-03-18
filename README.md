# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）  
このリポジトリはデータ収集・ETL、財務/価格データの保存、特徴量計算、ニュース収集、品質チェック、監査ログなどを備えた日本株自動売買基盤のコア実装を含みます。

---

## プロジェクト概要

KabuSys は以下の層を持つデータ・オートメーション基盤です。

- データ取得（J-Quants API 経由の株価・財務・カレンダー）
- 生データ（Raw）→ 整形データ（Processed）→ 特徴量（Feature） の ETL パイプライン
- ニュース RSS 収集と銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用ユーティリティ（ファクター計算、将来リターン計算、IC 評価、Zスコア正規化）
- DuckDB を前提としたデータベーススキーマと監査ログ（発注・約定のトレーサビリティ）
- J-Quants API クライアント（レートリミット、リトライ、トークンリフレッシュ対応）

実運用の発注 API（kabuステーション等）や戦略実行層はモジュール分離されており、ライブラリとして組み込んで利用します。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（ページネーション、レート制御、再試行、トークン自動更新）
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar

- data/schema.py, data/audit.py
  - DuckDB のスキーマ定義（Raw/Processed/Feature/Execution/Audit）
  - init_schema(), init_audit_schema(), init_audit_db()

- data/pipeline.py
  - 差分 ETL（run_daily_etl/run_prices_etl/run_financials_etl/run_calendar_etl）
  - 品質チェック呼び出しとの統合

- data/news_collector.py
  - RSS 収集、記事正規化、記事ID生成、DuckDB への冪等保存、銘柄抽出（4桁コード）

- data/quality.py
  - 欠損、スパイク、重複、日付不整合などのチェック（QualityIssue オブジェクトで返却）

- research/*（feature_exploration.py, factor_research.py）
  - 将来リターン計算、IC（Spearman ρ）計算、モメンタム/バリュー/ボラティリティ等のファクター計算
  - data.stats.zscore_normalize を使った正規化ユーティリティ

- config.py
  - 環境変数読み込み（.env / .env.local の自動読み込み機能）
  - 必須設定のラッパー（settings オブジェクト）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントの | 演算子やアノテーションを使用）
- duckdb, defusedxml など一部外部ライブラリを利用

インストール（例）
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクト依存の追加パッケージがある場合は requirements.txt を用意して pip install -r する）

3. 環境変数設定
   - プロジェクトルート（このパッケージの .py ファイルが含まれるツリーのルート）に `.env` / `.env.local` を作成すると自動で読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（settings で _require されるもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API 用パスワード（発注等を使う場合）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack チャンネル ID

任意（デフォルトあり）
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると自動 .env ロードを無効化

例 .env
- .env.example を参考に必要なキーを設定してください（リポジトリに .env.example がある想定）。

---

## 使い方（簡単なクイックスタート）

以下は Python REPL / スクリプトでの基本的な使い方例です。

1) DuckDB スキーマ初期化
- メモリ DB で試す場合:
  - from kabusys.data.schema import init_schema
  - conn = init_schema(":memory:")

- ファイル DB を使う場合（settings からパスを取得する例）:
  - from kabusys.data.schema import init_schema
  - from kabusys.config import settings
  - conn = init_schema(settings.duckdb_path)

2) 日次 ETL を実行する
- J-Quants トークンなどが環境変数で設定済みである前提:
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.data.schema import init_schema
  - conn = init_schema(":memory:")  # 実運用ではファイルパスを指定
  - result = run_daily_etl(conn)
  - print(result.to_dict())

3) ニュース収集ジョブ
- RSS から記事を取得して DB に保存:
  - from kabusys.data.news_collector import run_news_collection
  - from kabusys.data.schema import init_schema
  - conn = init_schema(":memory:")
  - results = run_news_collection(conn, known_codes={"7203", "6758"})  # known_codes を渡すと銘柄紐付けを行う

4) 研究/ファクター計算の利用例
- DuckDB 接続を渡してファクターを計算:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - res = calc_momentum(conn, target_date)
  - 利用例: zscore 正規化 -> from kabusys.data.stats import zscore_normalize

5) 監査ログスキーマ初期化（発注トレーサビリティ用）
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")

注意点
- settings の必須値が未設定だと ValueError が発生します。テスト時は :memory: を使うなどして settings の要求する値に注意してください。
- J-Quants 取得はレート制御・リトライを行いますが、実行前に API 利用ルールを必ず確認してください。

---

## 主な API / 関数一覧（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token / kabu_api_password / slack_bot_token / slack_channel_id / duckdb_path / env / log_level / is_live など

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- kabusys.data.news_collector
  - fetch_rss(url, source) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list[str]
  - run_news_collection(conn, sources=None, known_codes=None)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=[1,5,21])
  - calc_ic(factor_records, forward_records, factor_col, return_col)
  - factor_summary(records, columns)
  - zscore_normalize(records, columns) （data.stats から再エクスポート）

---

## ディレクトリ構成

簡易的なソースツリー（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数・設定読み込み
  - data/
    - __init__.py
    - jquants_client.py           # J-Quants API クライアント & 保存ユーティリティ
    - news_collector.py           # RSS 収集・記事保存・銘柄抽出
    - schema.py                   # DuckDB スキーマ・初期化
    - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
    - quality.py                  # データ品質チェック
    - stats.py                    # 統計ユーティリティ（zscore_normalize）
    - features.py                 # 公開インターフェース（再エクスポート）
    - calendar_management.py      # 市場カレンダー管理
    - audit.py                    # 監査ログ（発注・約定トレーサビリティ）
    - etl.py                      # ETL 用型/再エクスポート
  - research/
    - __init__.py                 # 研究用ユーティリティの再エクスポート
    - feature_exploration.py      # 将来リターン / IC / summary 等
    - factor_research.py          # momentum/value/volatility 等の factor 計算
  - strategy/                      # 戦略ロジック用（空の __init__ あり）
  - execution/                     # 発注/約定制御用（空の __init__ あり）
  - monitoring/                    # 監視用（空の __init__ あり）

---

## 運用上の注意・設計方針（抜粋）

- DuckDB を永続層として想定。init_schema() は冪等でテーブルを作成します。
- J-Quants API クライアントは内部でレート制御（120 req/min）と再試行・トークン自動更新を行います。
- ETL は差分処理を行い、backfill により直近数日を再取得して API の後出し修正を吸収します。
- ニュース収集では SSRF 対策、受信サイズ制限、XML パースの安全化（defusedxml）等を取り入れています。
- データ品質チェックは Fail-Fast ではなく全チェックを行い、重大度に応じて上位で判断します。
- 監査ログは発注→約定のトレーサビリティを UUID 連鎖で保証します。

---

## 追加情報 / 開発者向け

- テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env 自動読み込みを止め、テスト特有の環境変数注入を推奨します。
- DB の初期化やマイグレーションが必要な場合は data/schema.py の DDL を参照してください。
- 研究用途の計算は DuckDB 接続と prices_daily / raw_financials テーブルが必要です。実行前に ETL を通じてデータを用意してください。

---

必要であれば、README に「サンプル .env.example」や「よくあるエラーと対処法（例：認証失敗、DuckDB ファイル権限、ネットワーク制限）」などの追記も作成できます。追記希望があれば教えてください。