# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
このリポジトリはデータ収集（J-Quants）、ETL、データ品質チェック、ニュースのNLPスコアリング、マーケットレジーム推定、監査ログなどを含む再現可能で安全性に配慮した実装を提供します。

## 概要
KabuSys は以下を目的とするモジュール群を含む Python パッケージです。

- J-Quants API を用いた株価・財務・カレンダーの差分取得と DuckDB への保存（ETL）
- ニュース収集（RSS）および OpenAI を用いたニュースセンチメント（ai_scores）算出
- 市場レジーム（bull/neutral/bear）判定（ETF / マクロニュースの合成）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 研究用ファクター計算・特徴量解析ユーティリティ

設計方針として、バックテストでのルックアヘッドバイアスを避ける実装、API 呼び出しのリトライ・レート制御、SSRF 対策、冪等性（idempotency）を重視しています。

---

## 主な機能一覧
- ETL パイプライン（kabusys.data.pipeline.run_daily_etl）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足、財務、マーケットカレンダーの取得・保存
  - トークン自動リフレッシュ、レート制限、リトライ
- ニュース収集（kabusys.data.news_collector.fetch_rss）
  - URL 正規化、SSRF 対策、前処理、冪等保存を想定
- ニュース NLP（kabusys.ai.news_nlp.score_news）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのセンチメント算出、ai_scores へ書き込み
- レジーム検出（kabusys.ai.regime_detector.score_regime）
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントの合成
- データ品質チェック（kabusys.data.quality）
- 監査ログ初期化・運用（kabusys.data.audit）

---

## セットアップ手順

1. 前提
   - Python 3.10+
   - DuckDB（Python パッケージ duckdb）
   - OpenAI Python SDK（openai）※ ai 機能を使う場合
   - （任意）ネットワークアクセス（J-Quants / RSS / OpenAI）

2. リポジトリを取得してインストール
   (リポジトリルートに setup/pyproject がある前提で)
   - 開発環境でのインストール例:
     - pip install -e . もしくは pip install -r requirements.txt
     ※ requirements.txt は本コードベースに含まれていませんが、少なくとも duckdb, openai, defusedxml 等が必要です。

3. 環境変数 / .env
   プロジェクトルートに `.env`（および環境固有で `.env.local`）を配置できます。パッケージ import 時に自動で読み込まれます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   重要な環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で利用）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
   - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
   - SQLITE_PATH: 監視用 sqlite データベース（デフォルト `data/monitoring.db`）
   - PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用
   - KABUSYS_ENV: 環境（`development` / `paper_trading` / `live`）。デフォルト `development`
   - LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト `INFO`）

   .env のパーシングはシェル風の export 句やクォート・コメントをある程度サポートします。

4. データディレクトリ
   - デフォルトでは `data/` 以下に DuckDB ファイルや PID/フラグファイルを置きます。必要に応じて `.env` の DUCKDB_PATH 等で変更してください。

---

## 使い方（簡単な例）

以下は Python スクリプトや REPL から呼び出す想定の例です。import することで .env 自動読み込みが走ります（無効化可能）。

- DuckDB 接続の作成（メモリ/ファイル）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアリング（OpenAI API キーが必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("written:", written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査ログ DB 初期化（DuckDB ファイルを作成してスキーマを投入）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- RSS フィード取得（news_collector）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

注意:
- OpenAI 系の関数は API 呼び出し時にリトライやフォールバック（失敗時は 0.0 など）を行う設計ですが、API キーが未設定だと ValueError が発生します。
- J-Quants 呼び出しは settings.jquants_refresh_token を使用。必ず設定してください。

---

## よく使うモジュールと関数（抜粋）
- kabusys.config.settings — 環境設定（.env 自動ロード、各種パス・しきい値の取得）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, save_daily_quotes, fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl, ETLResult
- kabusys.data.news_collector
  - fetch_rss, preprocess_text
- kabusys.ai.news_nlp
  - score_news
- kabusys.ai.regime_detector
  - score_regime
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.audit
  - init_audit_schema, init_audit_db

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数/設定管理
    - ai/
      - __init__.py
      - news_nlp.py                 — ニュースのセンチメント算出（OpenAI）
      - regime_detector.py          — 市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py           — J-Quants API クライアント（取得・保存）
      - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
      - quality.py                  — データ品質チェック
      - news_collector.py           — RSS 収集・前処理
      - calendar_management.py      — 市場カレンダー管理・営業日ロジック
      - audit.py                    — 監査ログスキーマ初期化
      - etl.py                      — ETLResult 再エクスポート
      - stats.py                    — 統計ユーティリティ（zscore_normalize 等）
    - research/
      - __init__.py
      - factor_research.py          — モメンタム / ボラティリティ / バリュー計算
      - feature_exploration.py      — 将来リターン・IC・統計サマリー等
    - ai/ (上に記載)
    - research/ (上に記載)

各モジュールは単体テストしやすいように設計されています（例: OpenAI 呼び出しやネットワーク I/O を差し替え可能）。

---

## 注意点・運用上のヒント
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）をベースに行います。テスト時に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants と OpenAI の API 利用にはそれぞれ API キーが必要です。キーは安全に管理し、CI や本番環境ではシークレット管理サービスを利用してください。
- DuckDB への INSERT は冪等（ON CONFLICT DO UPDATE）を意識して設計されていますが、DB スキーマおよびインデックスの初期化は目的に応じて行ってください（監査ログの初期化は init_audit_schema / init_audit_db）。
- ニュース収集は外部フィードの形式差異や文字コードに影響されます。RSS の取り込みや XML パースの失敗はログで把握できるようにしています。

---

## ライセンス / 貢献
この README はコードベース説明のためのものです。実際のパッケージライセンスやコントリビューションルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

不明点や README の追加項目（例: 実行用 CLI、Docker 化手順、CI 設定など）があれば教えてください。必要に応じて補足します。