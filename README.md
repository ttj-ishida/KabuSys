KabuSys — 日本株自動売買基盤
========================

概要
----
KabuSys は日本株向けのデータプラットフォーム＋研究・自動売買コンポーネント群です。本リポジトリは以下の機能を持つモジュール群を提供します。

- J-Quants からのデータ取得（株価日足・財務・市場カレンダー）
- DuckDB を用いた ETL パイプライン・データ保存（冪等性を考慮）
- ニュース収集・NLP（OpenAI を使った銘柄別センチメント評価）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック・監査ログ（トレーサビリティ）
- kabuステーション / Slack などとの連携設定を想定

主な設計方針は「ルックアヘッドバイアスの排除」「DB への冪等保存」「API 呼び出しのフェイルセーフ（失敗時は部分的に続行）」です。

主な機能一覧
-------------
- data.jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークンリフレッシュ対応）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- data.pipeline: ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- data.news_collector: RSS 取得と raw_news への保存補助（URL 正規化・SSRF 対策・gzip/サイズ制限）
- data.quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
- data.calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
- data.audit: 監査ログ（signal_events / order_requests / executions）初期化ユーティリティ
- research: ファクター計算（calc_momentum / calc_value / calc_volatility）と探索（calc_forward_returns / calc_ic / factor_summary / rank）
- ai.news_nlp: ニュースを LLM で評価して ai_scores に保存する score_news()
- ai.regime_detector: ETF(1321)のMA乖離とマクロニュースのセンチメントを合成して市場レジームを判定する score_regime()
- config: 環境変数読み込み・Settings（自動 .env ロード、必須キー検査）

セットアップ手順
----------------

前提
- Python 3.10+（typing の Union | 等を使用）
- インターネット接続（J-Quants / OpenAI 等の API へアクセスする場合）

1. リポジトリをクローンしてパッケージをインストール
   - 推奨: 仮想環境を作成してからインストール
   - 例:
     python -m venv .venv
     source .venv/bin/activate   # Windows: .venv\Scripts\activate
     pip install -e .

2. 依存パッケージ（代表例）
   - duckdb
   - openai
   - defusedxml
   - （必要に応じて requests 等）
   実際の requirements.txt / pyproject.toml を参照してください。

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から自動的に .env を読み込みます（config モジュール）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必要な環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - SLACK_BOT_TOKEN: Slack ボットトークン（必須、通知等で使用）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - KABU_API_PASSWORD: kabu API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に指定するか環境変数に設定）
   - オプション / デフォルト値
     - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - KABUSYS_ENV: development | paper_trading | live （デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...

   - .env のパース仕様（参考）
     - export KEY=val 形式にも対応
     - クォート／エスケープやインラインコメントの処理あり

使い方（代表的な例）
-------------------

- DuckDB 接続を用意して ETL を実行する（簡易例）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースを LLM で評価して ai_scores に書き込む
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 19), api_key="sk-...")
  print("written:", n_written)

- 市場レジームの判定（score_regime）を実行
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 19), api_key="sk-...")

- 監査ログ DB を初期化する
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成して接続を返す

- ニュース RSS を取得する（単体ユーティリティ）
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

注意点 / 運用時のヒント
- OpenAI 呼び出し
  - score_news / score_regime は OpenAI クライアントを用います。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
  - API 呼び出しはリトライや JSON パースの堅牢化が組み込まれていますが、レート制限とコストに注意してください。
- ETL の堅牢性
  - run_daily_etl は各ステップで例外をキャッチして処理を継続する設計です。戻り値の ETLResult で品質問題・エラー状況を確認して運用判断してください。
- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動的に読み込みます。テスト時などで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テスト容易性
  - OpenAI など外部 API 呼び出しは内部で差し替え可能（ユニットテストではモックすることを想定）。例: kabusys.ai.news_nlp._call_openai_api を patch。

ディレクトリ構成（主要ファイル）
-----------------------------

- src/kabusys/
  - __init__.py  (パッケージ定義)
  - config.py    (環境変数・Settings)
  - ai/
    - __init__.py
    - news_nlp.py         (ニュースセンチメント→ai_scores 書込)
    - regime_detector.py  (市場レジーム判定→market_regime 書込)
  - data/
    - __init__.py
    - jquants_client.py   (J-Quants API クライアント & DuckDB 保存)
    - pipeline.py         (ETL パイプライン: run_daily_etl 等)
    - etl.py              (ETLResult 再エクスポート)
    - news_collector.py   (RSS 取得・テキスト前処理)
    - quality.py          (データ品質チェック)
    - stats.py            (zscore_normalize 等の統計ユーティリティ)
    - calendar_management.py (市場カレンダー管理・営業日判定)
    - audit.py            (監査ログテーブルの DDL/初期化)
  - research/
    - __init__.py
    - factor_research.py  (calc_momentum, calc_value, calc_volatility)
    - feature_exploration.py (calc_forward_returns, calc_ic, factor_summary, rank)
  - ai/__init__.py
  - research/__init__.py

共通の実装・設計メモ
-------------------
- DuckDB をデータ格納に使用（ファイルパスは設定で変更可能）
- 外部 API 呼び出しはリトライ・指数バックオフ・ステータスコード対応を実装
- ETL は差分取得（最終取得日からの再取得）とバックフィルをサポート
- ニュース収集は SSRF や XML 脆弱性対策（defusedxml）、応答サイズ制限、トラッキングパラメータ除去を実装
- 監査テーブルは冪等性・トレーサビリティを重視（UUID ベースのキー、created_at の保存）

ライセンス / 貢献
-----------------
- 本 README 内の記述はコード構成に基づく説明です。実際のライセンス表記はリポジトリルートの LICENSE ファイルを参照してください。
- バグ報告・プルリクエストはリポジトリの Issue / PR フローに従ってください。

以上。初期導入・運用上の具体的なヘルプ（具体的なエラーの対処や設定例など）が必要であれば、使用ケース（ETL 実行方法、OpenAI キーの扱い、デプロイ先など）を教えてください。追加でサンプルの .env.example や実行スクリプト例も作成できます。