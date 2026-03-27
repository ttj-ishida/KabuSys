# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のコアモジュール群です。J-Quants や RSS、OpenAI（LLM）等を組み合わせてデータ収集（ETL）・品質チェック・ニュース NLP（銘柄センチメント）・市場レジーム判定・ファクター計算・監査ログ（発注/約定のトレーサビリティ）などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない）
- DuckDB をデータストアに利用し高速な SQL 処理を行う
- OpenAI（gpt-4o-mini）を JSON mode で利用することで安定した出力を目指す
- 冪等性・トランザクション制御・フェイルセーフ（API失敗時のフォールバック）を重視

---

## 機能一覧

- 環境設定管理
  - .env/.env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 必須環境変数の検証（settings オブジェクト）

- データ ETL / Data Platform
  - J-Quants API クライアント（差分取得、ページネーション、トークン自動リフレッシュ、レート制御）
  - 日次 ETL パイプライン（株価、財務、マーケットカレンダー）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - RSS ニュース収集（SSRF対策・トラッキング除去・前処理）
  - 監査ログスキーマ（signal_events / order_requests / executions）の初期化・DB作成ヘルパー

- AI（ニュース NLP / レジーム判定）
  - ニュースを銘柄別に集約して LLM によるセンチメント評価を実行（ai_scores へ保存）
  - マクロ記事 + ETF 1321 の MA200 乖離を合成した市場レジーム判定（bull / neutral / bear）

- リサーチ / ファクター処理
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

---

## セットアップ手順

前提
- Python 3.9+（型アノテーションや一部の戻り値記述に合わせて調整してください）
- ネットワークアクセス可能（J-Quants / OpenAI / RSS）

1. リポジトリをクローン
   - git clone <repository>

2. 仮想環境作成と有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .  （setup / pyproject がある場合）
   - または最低限必要なライブラリを直接インストール:
     - pip install duckdb openai defusedxml

   （実際の requirements はプロジェクトの packaging に合わせて管理してください）

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（CWD 依存しない探索）
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - 任意: DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV / LOG_LEVEL

   例 .env（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

6. 監査用 DuckDB の初期化（オプション）
   - Python から:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主要なユースケース例）

以下は Python API のサンプル。DuckDB 接続には `duckdb.connect(path)` を用います。

- 設定値参照
  - from kabusys.config import settings
  - settings.jquants_refresh_token などで環境変数を取得

- 日次 ETL の実行
  - from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントスコア（銘柄別）生成
  - from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"written: {n_written}")

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))

- ファクター計算 / 研究用関数
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect(str(settings.duckdb_path))
    mom = calc_momentum(conn, target_date=date(2026,3,20))
    vol = calc_volatility(conn, target_date=date(2026,3,20))
    val = calc_value(conn, target_date=date(2026,3,20))

- カレンダー関連ヘルパー
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
    is_trading = is_trading_day(conn, date(2026,3,20))
    nxt = next_trading_day(conn, date(2026,3,20))

- RSS ニュース収集（個別フィード取得）
  - from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

- J-Quants API 直接呼び出し（fetch/save）
  - from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
    quotes = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
    # 保存は save_daily_quotes(conn, records)

- 監査スキーマの初期化（既存接続へ）
  - from kabusys.data.audit import init_audit_schema
    conn = duckdb.connect(str(settings.duckdb_path))
    init_audit_schema(conn, transactional=True)

注意点:
- OpenAI を利用する関数（score_news, score_regime）は api_key を引数で受け取れます（引数省略時は環境変数 OPENAI_API_KEY を参照）。
- LLM 呼び出しはリトライ・フォールバックの制御がありますが、APIキーやネットワークの設定は適切に行ってください。
- ETL / データ保存は DuckDB 側のスキーマを前提に作られているため、事前にスキーマ初期化（プロジェクト内の schema 初期化処理）を行ってください（プロジェクトの別モジュールで schema 定義がある想定）。

---

## ディレクトリ構成（主要ファイル）

概観: src/kabusys 以下にモジュール群が配置されています。主要ファイル・モジュールと概要は以下の通りです。

- src/kabusys/__init__.py
  - パッケージメタデータ（バージョン・公開モジュール）

- src/kabusys/config.py
  - 環境変数/設定管理、.env 自動読み込み、Settings オブジェクト

- src/kabusys/ai/
  - __init__.py
  - news_nlp.py：ニュースを銘柄別に集約し OpenAI でセンチメントを算出、ai_scores に保存
  - regime_detector.py：ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して市場レジーム判定

- src/kabusys/data/
  - __init__.py
  - calendar_management.py：マーケットカレンダーと営業日判定ロジック
  - etl.py：ETLResult 型の公開
  - pipeline.py：日次 ETL パイプライン（prices/financials/calendar + 品質チェック）
  - stats.py：Zスコア正規化などの統計ユーティリティ
  - quality.py：データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py：監査ログ（signal_events, order_requests, executions）スキーマ定義・初期化
  - jquants_client.py：J-Quants API クライアント（fetch/save、認証、レートリミット、リトライ）
  - news_collector.py：RSS 収集・前処理・SSRF 対策

- src/kabusys/research/
  - __init__.py
  - factor_research.py：Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py：将来リターン計算・IC・統計サマリ・ランク処理

その他:
- package の公開インターフェースは __all__ で制御されています。必要な機能をインポートして利用してください。

---

## 運用上の注意

- 環境変数の管理（特に API キー）は安全に行ってください（.env をリポジトリにコミットしない）。
- ETL は J-Quants のレート制限（120 req/min）を厳守する実装になっていますが、複数プロセス等で同時に叩く場合は注意してください。
- OpenAI の利用にはコストが発生します。バッチ化・トークン利用量の管理をしてください。
- DuckDB スキーマや初期化処理（テーブル定義）が別途ある前提です。プロジェクト内の schema 初期化スクリプトを併用してください。

---

必要であれば、README にサンプル .env.example、より詳細なスキーマ初期化手順、あるいは CLI/Makefile の使い方を追加できます。どの情報を優先して追加しますか？