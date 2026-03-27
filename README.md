# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、データ品質チェック、ETL パイプライン、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（オーダー/約定トレーサビリティ）、リサーチ用ファクター計算などを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやデータプラットフォーム構築を支援する Python モジュール群です。主な目的は次のとおりです。

- J-Quants API を用いた株価・財務・カレンダー等の差分取得と DuckDB への冪等保存
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集・前処理・LLM による銘柄別センチメント算出（gpt-4o-mini など）
- ETF とマクロニュースを組み合わせた市場レジーム判定
- 監査ログスキーマ（signal → order_request → execution）の初期化と管理
- 研究（research）モジュール：ファクター算出、将来リターン・IC 計算、Z スコア正規化等

設計方針として、バックテスト時のルックアヘッドバイアス防止、API 呼び出し時のリトライとレート制御、DuckDB での効率的な SQL 処理、外部サービス呼び出しのフェイルセーフ化を重視しています。

---

## 機能一覧

- data
  - jquants_client: J-Quants API 呼び出し、ページネーション、トークン自動リフレッシュ、DuckDB への保存（raw_prices / raw_financials / market_calendar 等）
  - pipeline: 日次 ETL（calendar / prices / financials）と品質チェックの統合 run_daily_etl
  - quality: 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返す）
  - calendar_management: 営業日判定・次営業日/前営業日の算出、カレンダー更新ジョブ
  - news_collector: RSS 取得、安全対策（SSRF / Gzip / XML Bomb 対策）、raw_news 保存ロジック
  - audit: 監査ログテーブル DDL と初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄ごとニュースをまとめて LLM に送り ai_scores を更新
  - regime_detector.score_regime: ETF MA200 乖離 + マクロニュースで市場レジーム（bull/neutral/bear）を算出して保存
- research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - 環境変数管理（.env の自動ロード機能、必須 env の検査）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（typing の Union 表記や型ヒントを使用）
- 系列パッケージ: duckdb, openai, defusedxml（下記参照）

手順（開発環境向けの一例）

1. リポジトリをクローン
   - git clone ... (リポジトリ URL)

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - 追加で必要なら sqlite3 は標準ライブラリに同梱（外部インストール不要）

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を実行してください）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化できます）。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. DuckDB ファイル・ディレクトリ作成（必要に応じて）
   - デフォルトでは data/kabusys.duckdb を使用します。ディレクトリを作成しておくと便利です。

---

## 使い方（簡単な例）

以下はライブラリの代表的な API を用いた利用例です。実行前に環境変数（特に OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN）を設定してください。

1) DuckDB 接続を作って日次 ETL を実行する
- 例:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

2) ニュース NLP スコアリングを実行する
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")

3) 市場レジーム判定を実行する
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

4) 監査ログ DB を初期化する（監査用専用 DB）
- 例:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます

5) news_collector の RSS 取得（単体）
- 例:
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles[:5]:
      print(a["datetime"], a["title"])

注意点:
- OpenAI API を呼ぶ関数（score_news / regime_detector.score_regime）は OPENAI_API_KEY を参照します。api_key 引数で明示的に渡すことも可能です。
- DuckDB への書き込みは関数側で BEGIN/COMMIT/ROLLBACK を適切に扱っていますが、大きな処理を組む場合は呼び出し側でトランザクション設計を考慮してください。
- ETL / ニューススコアリング等は外部 API 呼び出しを行うため、API レートやコストに留意してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for LLM 呼出し) — OpenAI API キー（score_news / score_regime 等で使用）
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用（設定が必須の箇所があれば使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等で使用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）に .env / .env.local があれば自動で読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py (パッケージ初期化)
  - config.py (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - calendar_management.py (市場カレンダー管理)
    - etl.py (ETL 再エクスポート)
    - pipeline.py (日次 ETL パイプライン)
    - stats.py (統計ユーティリティ)
    - quality.py (データ品質チェック)
    - audit.py (監査ログスキーマ / 初期化)
    - jquants_client.py (J-Quants API クライアント / 保存関数)
    - news_collector.py (RSS 収集・前処理)
  - research/
    - __init__.py
    - factor_research.py (momentum/value/volatility)
    - feature_exploration.py (forward returns / IC / summary)
  - その他（strategy / execution / monitoring 等は __all__ に準備中）

---

## 注意事項・運用上のポイント

- Look-ahead Bias の防止:
  - 多くのモジュール（news_nlp, regime_detector, pipeline 等）は datetime.today()/date.today() を内部で直接参照しない設計になっています。外から target_date を渡して使うことを想定しています。
- 冪等性:
  - J-Quants からの保存は ON CONFLICT DO UPDATE、監査スキーマも冪等に作成するため再実行が安全な設計です。
- エラー耐性:
  - 外部 API 呼び出しはリトライとバックオフ、フェイルセーフ（失敗時はスキップして代替値を使う）を備えています。ログを必ず確認してください。
- テスト性:
  - OpenAI 呼び出し部分などは内部の _call_openai_api をパッチすることでモック可能な設計です（ユニットテスト容易化）。

---

もし README に追記したい具体的な使用フロー（例えば cron / Airflow / Fargate での運用例）や、requirements.txt・CI 設定、実行スクリプト（CLI）を追加したい場合は要件を教えてください。README をそれに合わせて拡張します。