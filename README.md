# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース NLP（LLM を用いたセンチメント）・市場レジーム判定・監査ログ管理など、トレーディングシステムの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は次のような目的で設計されたモジュール群です。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL と DuckDB への保存（冪等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- RSS ニュース収集と銘柄紐付け（SSRF 対策・正規化済み ID）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別、マクロ）
- ETF（1321）MA とマクロセンチメントを合成した市場レジーム判定
- トレーサビリティ用の監査ログ（signal / order_request / execution）テーブル管理

設計上の注意点として、バックテストやモデル評価におけるルックアヘッドバイアスを避けるために多くの関数は内部で datetime.today()/date.today() に依存せず、呼び出し側から対象日を明示的に渡すことを想定しています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（ID トークン管理・リトライ・レート制御）
  - カレンダー管理（is_trading_day / next_trading_day / get_trading_days）
  - ニュース収集（RSS 取得、SSRF 対策、前処理、raw_news 保存）
  - データ品質チェック（missing / duplicates / spike / date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（銘柄別センチメントを OpenAI へ送信して ai_scores に保存）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）
- research
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（将来リターン計算 / IC / 統計サマリー）
- config
  - 環境変数管理（.env 自動読み込み、Settings クラス）

---

## セットアップ手順

前提: Python 3.9+（コードは typing の Union | を使っているため 3.10+ を推奨）および pip が利用可能であること。

1. リポジトリをクローン
   git clone <repository-url>
   cd <repository-root>

2. 仮想環境（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクト配布に setup/pyproject があれば pip install -e . でも可）

4. 環境変数設定
   プロジェクトルート（.git か pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると、kabusys.config が自動で読み込みます（自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください）。

   必須環境変数（少なくとも ETL / AI を使う場合）:
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
   - SLACK_BOT_TOKEN        : （通知機能を使う場合の Slack Bot Token）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - KABU_API_PASSWORD     : kabu ステーション API パスワード（発注連携を行う場合）

   その他のオプション:
   - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 sqlite パス（デフォルト data/monitoring.db）
   - PID_FILE_PATH         : 実行プロセス PID ファイルパス（デフォルト data/execution.pid）
   - CPU_THRESHOLD_PCT 等 : 監視しきい値
   - KABUSYS_ENV, LOG_LEVEL

   LLM/API 用:
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime の api_key 引数を省略した場合に参照）

5. DuckDB 用ディレクトリ作成（必要時）
   mkdir -p data

---

## 使い方（基本例）

以下はライブラリをインポートして機能を呼ぶ簡単な例です。実行前に必要な環境変数が設定されていることを確認してください。

- 日次 ETL 実行（prices / financials / calendar を差分取得）
  ```
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア取得（指定日）
  ```
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（ETF 1321 の MA200 と LLM）
  ```
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  res = score_regime(conn, target_date=date(2026, 3, 20))
  print("完了:", res)
  ```

- RSS フィード取得（一例）
  ```
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

- 監査 DB 初期化
  ```
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブルが作成されます
  ```

注意:
- OpenAI の呼び出しはネットワーク/課金が伴います。テスト時は score_news/_call_openai_api をモックしてください（README 内のモジュールコメントにある想定どおりに patch 可能）。
- J-Quants へのリクエストはレート制限（120 req/min）やリトライ・トークンリフレッシュを内部で行います。JQUANTS_REFRESH_TOKEN の設定が必要です。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須 for J-Quants)
- KABU_API_PASSWORD (必須 if kabu 発注)
- KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (必須 if score_news/score_regime を実行)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (通知が必要な場合)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動ロードを無効化

---

## ディレクトリ構成（主要ファイル説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（自動 .env 読み込みロジック含む）
  - ai/
    - __init__.py
    - news_nlp.py
      - 銘柄別ニュースセンチメント評価、OpenAI 呼び出し、レスポンス検証、ai_scores への書き込み
    - regime_detector.py
      - ETF 1321 の MA200 乖離とマクロニュース LLM を合成し market_regime に書き込む
  - data/
    - __init__.py
    - calendar_management.py
      - JPX 市場カレンダーの判定 / 取得更新ロジック
    - etl.py
      - ETLResult を再エクスポート（pipeline.ETLResult）
    - pipeline.py
      - 日次 ETL パイプライン、個別 ETL ジョブ（prices/financials/calendar）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py
      - 監査ログ用テーブル定義・初期化関数（冪等）
    - jquants_client.py
      - J-Quants API の HTTP リクエスト、トークン取得、fetch/save ユーティリティ
    - news_collector.py
      - RSS 収集・前処理・SSRF 対策・raw_news 保存
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials を参照）
    - feature_exploration.py
      - 将来リターン・IC・統計サマリー等
  - その他: strategy/ execution/ monitoring 等のパッケージが __all__ にある想定（コードベース全体による）

---

## テスト／開発上の注意

- LLM や外部 API を直接叩くテストはコストやレート制限の問題があるため、モック（unittest.mock.patch）で置き換えて実行してください。モジュール内で _call_openai_api を明示的に別関数化してあるため差し替えやすく設計されています。
- DuckDB の executemany はバージョン差により空リストを受け付けないなどの挙動差があるため、コード内で空リストチェックを行っています。DuckDB バージョンとの整合性に注意してください。
- 監査スキーマの作成は transactional オプションに留意（既にトランザクション中で呼ぶとネストトランザクションの扱いに注意）。

---

## ライセンス / コントリビュート

（ここにライセンスとコントリビュート方法を追記してください。）

---

README に記載した以外のユーティリティや API については、各モジュールの docstring を参照してください。さらに詳しい使用例やデプロイ手順（kabu ステーションとの連携、Slack 通知、監視デーモンの運用等）が必要であればお知らせください。