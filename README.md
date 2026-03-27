# KabuSys

日本株向けの自動売買 / 研究プラットフォーム用ライブラリ群。  
データETL、ニュース収集・AIセンチメント評価、ファクター計算、監査ログなどを提供します。

> 注意: 本リポジトリは実運用を想定したユーティリティ群を含みます。発注機能や本番環境での使用前には十分なテストと安全確認を行ってください。

---

## 主な概要

KabuSys は次のような機能を備えた Python モジュール群です。

- J-Quants API からのデータ取得（株価日足 / 財務 / 上場銘柄情報 / 市場カレンダー）
- DuckDB を用いた ETL（差分取得・冪等保存・品質チェック）
- RSS ニュース収集と前処理（SSRF/サイズ制限対策付き）
- OpenAI（gpt-4o-mini 等）を使ったニュース NLP（銘柄別センチメント）と市場レジーム判定
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と統計ユーティリティ
- 監査ログ（signal / order_request / executions）用のスキーマ初期化ユーティリティ
- 環境変数ベースの設定管理（.env 自動読み込み機能あり）

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（fetch_rss, raw_news 前処理・保存ロジック）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None)：銘柄ごとのニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime(conn, target_date, api_key=None)：マクロセンチメントと ETF MA 乖離を合成して market_regime に保存
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- 設定
  - kabusys.config.Settings: 環境変数から各種設定を取得（.env の自動読み込みあり）

---

## 必要条件

- Python 3.10+
- 必須 Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml

実行環境に応じて追加パッケージが必要になる場合があります（例: ネットワーク/HTTPS を使う標準ライブラリのみで実装されていますが、実運用では requests 等を使う場合もあります）。

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repository-url>
   cd <repository>

2. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install --upgrade pip
   pip install duckdb openai defusedxml

   （プロジェクトに setup/pyproject があれば）
   pip install -e .

4. 環境変数の設定
   プロジェクトルートに `.env` または `.env.local` を配置すると、自動的に読み込まれます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化できます）。

   必要な環境変数（一例）:
   - JQUANTS_REFRESH_TOKEN=...   # J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD=...       # kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN=...         # Slack 通知用（必須）
   - SLACK_CHANNEL_ID=...        # Slack チャンネル ID（必須）
   - OPENAI_API_KEY=...          # OpenAI を使う場合（score_news/score_regime で未指定時に参照）
   - DUCKDB_PATH=data/kabusys.duckdb  # データベースパス（任意）
   - SQLITE_PATH=data/monitoring.db    # 監視用 SQLite（任意）
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   例（.env）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

5. データディレクトリの作成（任意）
   mkdir -p data

---

## 使い方（簡単な例）

以下は Python REPL やスクリプト内からの呼び出し例です。いずれも DuckDB の接続オブジェクト（duckdb.connect(...)）を渡して使用します。

- ETL（日次パイプライン）を実行する
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースセンチメントを評価して ai_scores に保存
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"wrote {n_written} scores")

  - OpenAI API キーを明示的に渡すことも可能:
    score_news(conn, date(2026,3,20), api_key="sk-...")

- 市場レジームをスコアリングして保存
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))

- 監査ログ用 DB を初期化する
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # 以降 conn に対して監査テーブルを使える

- 研究用ファクター計算（例：モメンタム）
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
  recs = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(recs))

注意点:
- OpenAI を呼ぶ関数は api_key 引数を受け取ります。未指定時は環境変数 OPENAI_API_KEY を参照します。
- データベースのパスは Settings.duckdb_path（.env で DUCKDB_PATH を指定）から取得できます。
- これらの処理は外部 API を呼び出します。実行前にネットワーク・API キー・レート制限などを確認してください。

---

## 環境変数・設定（主要項目）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須): Slack 通知設定
- DUCKDB_PATH, SQLITE_PATH: データ保存先
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` が自動で読み込まれます。テストや特殊用途で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

リポジトリ（src/kabusys レイアウト）の主要構成:

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数・設定管理（.env 自動読み込み等）
  - ai/
    - __init__.py
    - news_nlp.py                  # ニュースセンチメント解析（score_news）
    - regime_detector.py           # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント（fetch/save 等）
    - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
    - etl.py                       # ETL 主要エクスポート（ETLResult）
    - news_collector.py            # RSS 収集・前処理
    - calendar_management.py       # 市場カレンダー管理
    - quality.py                   # データ品質チェック
    - stats.py                      # 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                      # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           # ファクター計算
    - feature_exploration.py       # 将来リターン / IC / summary
  - monitoring/ (存在する場合の監視コード)
  - strategy/, execution/ (戦略・約定関連モジュール—本リポジトリのスコープによる)

---

## 開発・テストについて（簡易メモ）

- モジュール内の外部 API 呼び出しはリトライ・フェイルセーフ設計です。ユニットテストでは外部呼び出しをモック（patch）してください（例: kabusys.ai.news_nlp._call_openai_api 等）。
- DuckDB を使ったテストは ":memory:" を渡せます（init_audit_db(":memory:") など）。
- .env 自動読み込みをテストで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## ライセンス・貢献

- ライセンス情報・貢献方法はリポジトリのトップレベルドキュメント（LICENSE / CONTRIBUTING.md 等）を参照してください。

---

必要であれば README に例の .env.example や、より詳細な API 使用例（各関数のサンプルスクリプト）を追加します。どの部分を詳しく書くか教えてください。