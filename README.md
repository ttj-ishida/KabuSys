KabuSys — 日本株自動売買システム（概要 README）
=================================

概要
----
KabuSys は日本株のデータ収集（ETL）、データ品質チェック、特徴量計算（ファクター）、ニュース NLP（LLM によるセンチメント解析）および市場レジーム判定、監査ログ（発注〜約定のトレーサビリティ）などを含む「データ駆動型の自動売買プラットフォーム」のための Python ライブラリ群です。  
主に DuckDB をデータストアとして用い、J-Quants API から市場データを取得、OpenAI（gpt-4o-mini 等）でニュース解析を行い、研究・リサーチ・実行ロジックの基盤を提供します。

主な特徴
--------
- データ取得（J-Quants API）と DuckDB への冪等保存（ON CONFLICT）
- 日次 ETL パイプライン（市場カレンダー / 株価 / 財務データ）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）と前処理、LLM による銘柄別センチメントスコア生成
- マクロニュース + ETF（1321）200日移動平均乖離を用いた市場レジーム判定
- 研究用ユーティリティ（モメンタム、バリュー、ボラティリティ、将来リターン、IC、統計サマリ等）
- 監査ログスキーマ（signal_events / order_requests / executions）の初期化・運用支援
- 設定は環境変数 / .env / .env.local で管理（自動ロード機能あり）

セットアップ（開発環境）
--------------------
以下は最小限の手順例です。プロジェクトの pyproject.toml 等が存在する想定で説明します。

1. Python
   - Python 3.10+ を推奨（ソース内で型ヒントの | 記法を使用しています）。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate (Windows)

3. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements ファイルがあればそちらを使用してください）

4. 環境変数
   - 必須／推奨される環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須、ETL 用）
     - OPENAI_API_KEY         : OpenAI API キー（news_nlp, regime_detector）
     - KABU_API_PASSWORD      : kabuステーション API パスワード（発注系）
   - 任意／運用用:
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト data/monitoring.db)
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

5. .env 自動読み込み
   - パッケージは .git または pyproject.toml を基準にプロジェクトルートを探し、.env（優先度低）→ .env.local（優先度高）の順で自動ロードします。
   - 自動ロードを無効化する場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（簡単な例）
-----------------

基本的に DuckDB の接続オブジェクト（duckdb.connect(...) の返り値）を渡して各機能を実行します。以下は典型的な使用例です。

1) 日次 ETL を実行する
- 目的: カレンダー / 株価 / 財務 を差分取得し保存、品質チェックを実行
- 例:
  - import duckdb, datetime
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(Path("data/kabusys.duckdb")))
  - result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
  - print(result.to_dict())

  ※ J-Quants の認証トークン (idToken) は内部で settings.jquants_refresh_token を使って自動取得しますが、テスト等で id_token を明示的に渡すことも可能。

2) ニュースセンチメントを算出（AI）
- 目的: raw_news / news_symbols を集約して銘柄ごとの ai_score を ai_scores に書き込む
- 例:
  - from kabusys.ai.news_nlp import score_news
  - score_count = score_news(conn, target_date=datetime.date(2026, 3, 20), api_key=None)
  - print(f"scored {score_count} codes")

  api_key を None にすると環境変数 OPENAI_API_KEY を使用します。

3) 市場レジーム判定
- 目的: ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ書き込み
- 例:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=datetime.date(2026, 3, 20), api_key=None)

4) 監査ログ DB 初期化
- 目的: order_requests / signal_events / executions テーブルの作成
- 例:
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - # init_audit_db はスキーマ作成後の接続を返します

5) RSS フィードの取得（ニュースコレクタ）
- 例:
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  - for a in articles: print(a["title"], a["datetime"])

API と挙動についての注意
----------------------
- OpenAI 呼び出し:
  - gpt-4o-mini を想定し JSON Mode を用いてレスポンスを厳密な JSON として扱います。
  - 再試行・フォールバックロジック（429、タイムアウト、5xx 等）あり。失敗時はフェイルセーフ（多くの場合 0.0 やスキップ）して処理を継続します。
- J-Quants:
  - レート制限（120 req/min）を守る RateLimiter を実装しています。
  - 401 を受けた場合は自動でリフレッシュトークンから id token を再取得して再試行します（1 回）。
  - 取得データは fetched_at を UTC で記録（Look-ahead バイアス対策）。
- DuckDB 関連:
  - 一部の executemany 呼び出しは空リストを受け付けない制約（古い DuckDB）を考慮した実装があります。DuckDB のバージョン互換性に注意してください。

主要モジュールと機能一覧
---------------------
- kabusys.config
  - 環境変数の読み込み・検証（.env/.env.local 自動ロード）
  - settings オブジェクト経由で設定取得

- kabusys.data
  - jquants_client
    - J-Quants API クライアント（fetch/save の一連のユーティリティ）
    - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - pipeline
    - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
    - ETLResult（実行結果）
  - quality
    - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - news_collector
    - RSS 取得・前処理・記事 ID 正規化・SSRF 防止処理
  - calendar_management
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - audit
    - init_audit_schema / init_audit_db（監査ログ用テーブルの初期化）
  - stats
    - zscore_normalize（研究向け統計ユーティリティ）

- kabusys.ai
  - news_nlp.score_news
    - 銘柄ごとにニュースを集約し OpenAI へ送って ai_scores に保存
  - regime_detector.score_regime
    - ETF(1321) MA200 乖離とマクロニュース LLM を合成して market_regime に保存

- kabusys.research
  - factor_research
    - calc_momentum / calc_volatility / calc_value
  - feature_exploration
    - calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats の zscore_normalize と組み合わせてファクター研究に使用

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
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
  - quality.py
  - stats.py
  - news_collector.py
  - calendar_management.py
  - audit.py
  - pipeline.py (ETLResult を再エクスポートする etl.py)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/（他：utility 等）

（上記は主要実装ファイルのみ抜粋）

運用上の注意
------------
- 設定ミスによる API キー漏洩や誤発注を防ぐため、KABUSYS_ENV を production（live 等）に切り替える際は十分注意してください。
- 実際の発注・約定フローを組み込む場合は、order_requests の冪等キー（order_request_id）や監査ログの一貫性を確保し、重複発注や partial failure に備えてください。
- OpenAI / J-Quants のコスト・レート制限に注意して、バッチサイズや呼び出し間隔を設定してください。

貢献 / 拡張
-----------
- 新しい ETL 対象 API を追加する場合は data.jquants_client の設計に倣い fetch_* / save_* パターンで実装してください。
- ニュースソースを増やす、またはプロンプト調整でセンチメント精度を向上させることが可能です（news_nlp のプロンプトとバッチ処理ロジックを調整）。
- 研究・バックテスト用途では look-ahead バイアス防止の設計原則（target_date より前のデータのみを使用する）を維持してください。

補足（よく使う関数）
-------------------
- run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
- score_news(conn, target_date, api_key=None) -> 書き込み銘柄数
- score_regime(conn, target_date, api_key=None) -> 1（成功）
- jquants_client.get_id_token(refresh_token=None) -> id token
- data.audit.init_audit_db(path) -> DuckDB 接続（監査 DB 初期化）

ライセンス / 著作権
------------------
（ここにプロジェクトのライセンス情報を記載してください）

問い合わせ
---------
- 実運用上の質問やバグレポートはリポジトリの issue を利用してください。

以上。README に追加したい具体的なコマンド例や環境ファイルテンプレート（.env.example）等があれば提供します。