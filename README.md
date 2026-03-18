# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）。  
J-Quants API や RSS を用いたデータ収集、DuckDB を用いたスキーマ管理、特徴量計算、ETL パイプライン、品質チェック、ニュース収集、監査ログ等の機能群を備えています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants からの株価・財務・市場カレンダーの差分取得（ページネーション・認証リフレッシュ・レート制御対応）
- DuckDB を用いたデータスキーマ定義・永続化（Raw/Processed/Feature/Execution 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄抽出（SSRF/サイズ制限/トラッキング除去対応）
- 研究（Research）向けのファクター計算（モメンタム、ボラティリティ、バリュー等）と評価指標（IC など）
- 監査ログ（signal → order → execution をトレースする監査スキーマ）
- 簡易的な設定管理（.env 自動ロード等）

設計方針は「外部 API に対して安全かつ冪等にデータを収集・保存し、研究・戦略開発に必要なデータ基盤を提供する」ことです。

---

## 主な機能一覧

- 環境/設定管理
  - .env / .env.local 自動ロード（プロジェクトルート自動検出）
  - 必須環境変数の明示と検証
- データ取得（J-Quants）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - レート制御（120 req/min 固定スロットリング）
  - 401 自動トークンリフレッシュ、リトライ（指数バックオフ）
  - DuckDB への冪等保存（ON CONFLICT）
- データベーススキーマ（DuckDB）
  - Raw / Processed / Feature / Execution / Audit レイヤーのテーブル定義
  - インデックス定義、初期化ユーティリティ（init_schema, init_audit_schema）
- ETL パイプライン
  - 差分取得（最終取得日からの差分、自動バックフィル）
  - 日次 ETL エントリ（run_daily_etl）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip / サイズ制限）
  - 前処理 + 重複排除 + raw_news 保存 + 銘柄抽出（4桁銘柄コード）
- 研究用ユーティリティ
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（クロスセクション正規化）
- カレンダー管理
  - 営業日判定、前後営業日の取得、カレンダー更新ジョブ
- 監査ログ
  - signal_events / order_requests / executions の監査スキーマと初期化

---

## 必要環境 / 依存

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - defusedxml

インストール例:

pip install duckdb defusedxml

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意して管理してください。）

---

## 環境変数

主に以下の環境変数が利用されます（必須は README 内で明示）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — =1 にすると .env 自動読み込みを無効化

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に `.env` → `.env.local` の順で読み込みます。
- OS 環境変数が優先され、.env.local は既存環境変数を上書きする（ただし OS のキーは保護される）。
- 自動読み込みを止めたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. Python と依存パッケージのインストール
   - Python 3.10+
   - pip install duckdb defusedxml

2. 環境変数の準備
   - リポジトリルートに `.env`（または `.env.local`）を作成。
   - 必須キーを設定:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 必要に応じて DUCKDB_PATH 等を設定。

3. DuckDB スキーマの初期化
   - 以下のようにスクリプト/REPL から実行します:

     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)

   - 監査ログ用のスキーマを別 DB に作る場合:

     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")

   - 既存接続に監査テーブルを追加する場合:

     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

4. （オプション）プロジェクトローカル設定
   - .env.example がある場合はそれを参考に .env を作成してください（実装内で .env.example を期待しているメッセージあり）。

---

## 使い方（例）

以下は主要な操作の簡単なサンプルコードです。

- DuckDB 接続とスキーマ初期化

  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）

  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)
  print(result.to_dict())

- 株価差分 ETL のみ

  from datetime import date
  from kabusys.data.pipeline import run_prices_etl

  fetched, saved = run_prices_etl(conn, target_date=date.today())

- 市場カレンダー更新ジョブ

  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn, lookahead_days=90)

- ニュース収集ジョブ（RSS -> raw_news, news_symbols）

  from kabusys.data.news_collector import run_news_collection

  # known_codes: 抽出時に有効とする銘柄コードセット
  stats = run_news_collection(conn, known_codes={"7203", "6758", "9984"})
  print(stats)

- J-Quants から日足を直接取得して保存

  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)

- 研究用ファクター計算

  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

  target = date(2024, 1, 31)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(mom, ["mom_1m", "ma200_dev"])
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

---

## よく使う API（概要）

- 設定
  - kabusys.config.settings — アプリケーション設定（環境変数読み取り）

- データ取得 / 保存
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.fetch_financial_statements(...)
  - kabusys.data.jquants_client.fetch_market_calendar(...)
  - kabusys.data.jquants_client.save_daily_quotes(conn, records)
  - kabusys.data.jquants_client.save_financial_statements(conn, records)
  - kabusys.data.jquants_client.save_market_calendar(conn, records)

- DB スキーマ
  - kabusys.data.schema.init_schema(db_path)
  - kabusys.data.audit.init_audit_db(db_path)
  - kabusys.data.audit.init_audit_schema(conn, transactional=False)

- ETL / Pipeline
  - kabusys.data.pipeline.run_daily_etl(conn, ...)
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.pipeline.run_financials_etl(...)
  - kabusys.data.pipeline.run_calendar_etl(...)

- ニュース
  - kabusys.data.news_collector.fetch_rss(url, source)
  - kabusys.data.news_collector.save_raw_news(conn, articles)
  - kabusys.data.news_collector.run_news_collection(conn, ...)

- 研究 / ファクター
  - kabusys.research.calc_momentum(...)
  - kabusys.research.calc_volatility(...)
  - kabusys.research.calc_value(...)
  - kabusys.research.calc_forward_returns(...)
  - kabusys.research.calc_ic(...)
  - kabusys.data.stats.zscore_normalize(...)

- 品質チェック
  - kabusys.data.quality.run_all_checks(conn, target_date=..., ...)

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得 / 保存）
    - news_collector.py            — RSS ニュース収集・保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - pipeline.py                  — ETL パイプライン
    - features.py                  — 特徴量ユーティリティの公開
    - calendar_management.py       — 市場カレンダー管理（営業日判定、更新ジョブ）
    - audit.py                     — 監査ログスキーマ（signal/order/execution）
    - etl.py                       — ETL 公開インターフェース（ETLResult 再エクスポート）
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - feature_exploration.py       — 将来リターン・IC・統計サマリー等
    - factor_research.py           — モメンタム / ボラティリティ / バリュー計算
  - strategy/
    - __init__.py
    — （戦略実装用のプレースホルダ）
  - execution/
    - __init__.py
    — （発注 / 約定処理のプレースホルダ）
  - monitoring/
    - __init__.py
    — （監視/アラート用のプレースホルダ）

---

## 注意点 / 運用上のポイント

- トークン・機密情報は .env に保存する場合は適切なアクセス制御を行ってください。
- J-Quants の API 制限（120 req/min）を遵守するため、jquants_client 内で固定間隔のスロットリングを実装しています。大量取得はスロットリングとリトライの影響を受ける点に注意してください。
- DuckDB の DDL は ON CONFLICT 等で冪等性を担保していますが、外部からの直接挿入や古いスキーマとの兼ね合いに注意してください。監査スキーマ初期化は transactional オプションがあります（DuckDB のトランザクション挙動に注意）。
- ニュース収集は SSRF 対策、圧縮解凍・サイズチェック、XML パースの安全対策（defusedxml）を組み込んでいますが、信頼できないフィードを無制限に追加する場合は追加の運用ルールを設けてください。
- 研究モジュールでは pandas 等依存を排して純粋 Python + SQL で実装しています。大規模データでのパフォーマンス評価は環境に依存します。

---

## 開発 / 貢献

- バグ・機能提案は Issue を作成してください。
- テストや CI の設定（pytest 等）は別途追加を推奨します。
- コードスタイルや型チェック（mypy）を導入すると保守性が向上します。

---

必要ならば README に含めるサンプルスクリプトや .env.example のテンプレート、より詳しい API リファレンス（各関数の引数/戻り値/例外）を追記します。どの情報を優先して追加しますか？