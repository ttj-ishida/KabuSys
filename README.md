# KabuSys

日本株自動売買プラットフォームのライブラリ（KabuSys）。データ取得・ETL、ニュース収集とAIによる記事センチメント・市場レジーム判定、リサーチ用ファクター計算、監査ログ / 発注トレーサビリティなどを含むモジュール群を提供します。

主な設計方針の概要:
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を不用意に参照しない）
- ETL / DB 書き込みは冪等性を意識（ON CONFLICT / DELETE→INSERT 等）
- 外部 API 呼び出しにはリトライ・レート制御を実装
- DuckDB をデータプラットフォームとして利用

---

## 主要機能一覧
- データ / ETL
  - J-Quants からの株価日足・財務データ・市場カレンダーの差分取得と DuckDB 保存（jquants_client, pipeline）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 市場カレンダー管理・営業日判定ユーティリティ
- ニュース収集
  - RSS フィード収集（SSRF 対策、サイズ制限、URL 正規化、トラッキングパラメータ削除）
  - raw_news / news_symbols への冪等保存ロジック
- AI（OpenAI）
  - ニュースセンチメント集計（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（ETF 1321 の MA 乖離 + マクロ記事の LLM センチメント合成; kabusys.ai.regime_detector.score_regime）
  - API 呼び出しは JSON Mode を利用、リトライとフォールバック実装
- 研究（research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算（zscore 正規化含む）
  - 将来リターン計算、IC（Spearman）等の統計分析ユーティリティ
- 監査ログ（audit）
  - signal → order_request → execution までを UUID で追跡する監査テーブル定義と初期化ユーティリティ
- 設定管理
  - .env / .env.local / OS 環境変数から設定を自動ロード（プロジェクトルート検出）

---

## システム要件
- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の依存は setup.py / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン／取得

2. 仮想環境を作成・有効化（推奨）

   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール

   - pip install -r requirements.txt
   - またはローカル開発インストール:
     - pip install -e .

   （requirements.txt / pyproject.toml に記載の依存を使用してください）

4. 環境変数の準備

   - プロジェクトルート（.git または pyproject.toml のある階層）から .env/.env.local を自動読み込みします。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   重要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合は必須）
   - KABU_API_PASSWORD: kabu API のパスワード（API 経由の実行機能を使う場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack 通知を使う場合
   - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"（任意）
   - SQLITE_PATH: デフォルト "data/monitoring.db"（任意）
   - KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト development）
   - LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト INFO）

   .env の書き方は shell の KEY=VALUE 形式に準拠しています。自動読み込みのパースは .env/.env.local に対応（クォート・コメント処理あり）。

---

## 使い方（基本例）

以下は代表的なユースケースの簡単な例です。実行は Python スクリプトや REPL で行います。

- DuckDB 接続を開く（データ格納用ファイル例）
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する（pipeline.run_daily_etl）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

  run_daily_etl は market calendar → prices → financials の順で差分取得・保存し、品質チェックを実行します。戻り値は ETLResult。

- ニュースセンチメントを算出して ai_scores に保存する
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key を渡さない場合は OPENAI_API_KEY を参照
    print(f"Wrote {written} codes")

- 市場レジーム判定（regime score を market_regime に書き込む）
  - from datetime import date
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ DB を初期化する（監査用独立 DB）
  - from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")
    # conn_audit を使用して監査テーブルに書き込みや検索を行う

- ニュース RSS を取得する（単体）
  - from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
    for a in articles:
        print(a["id"], a["datetime"], a["title"])

注意事項・設計上の振る舞い:
- many functions are idempotent: ETL 保存や audit 初期化は再実行可能。
- AI 呼び出しはリトライ・フォールバック（エラー時は中立スコア等）を採用。
- 多くの関数は外部 API キーを引数で受け取れるため、テスト時に注入可能です。

---

## 主要モジュールと API（抜粋）

- kabusys.config
  - settings: 環境設定プロパティ（jquants_refresh_token, kabu_api_base_url, slack_bot_token, duckdb_path など）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult dataclass
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.news_collector
  - fetch_rss, preprocess_text, URL 正規化/ID 生成等
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None) → ai_scores へ保存
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None) → market_regime へ保存
- kabusys.research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(path)

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - calendar_management.py
    - stats.py
    - quality.py
    - news_collector.py
    - audit.py
    - (その他: pipeline に関連する補助モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*：ファクター計算・特徴量探索
  - ai/*：OpenAI を用いた NLP/判定ロジック
  - data/*：ETL、J-Quants クライアント、品質チェック、監査スキーマ

---

## 開発・テスト時の注意点
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行います。CI やテストで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出しはテスト時にモックできるよう _call_openai_api を内部でラップしています（ユニットテストでは patch 可能）。
- DuckDB に対する executemany の挙動（空リスト不可など）を考慮した実装が含まれます。テスト DB には ":memory:" も利用可能です。

---

もし README に追加したい具体的な実行例（cron ジョブ、Dockerfile、CI ワークフロー、.env.example のテンプレートなど）があれば、それに合わせてサンプル内容を追記します。