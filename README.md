KabuSys
=======

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。  
主に以下を提供します。

- J-Quants API を使った株価 / 財務 / マーケットカレンダーの差分 ETL（DuckDB 保存、品質チェック付き）
- RSS ベースのニュース収集と銘柄紐付け（raw_news / news_symbols）
- OpenAI を使ったニュースセンチメント（銘柄別 ai_score）とマクロセンチメントを組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ）と特徴量解析ユーティリティ
- 発注〜約定までトレーサビリティを担保する監査ログ（監査テーブル初期化ユーティリティ）
- 環境変数 / .env ロード、運用向け監視設定などの共通設定

バージョン
----------
パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)

主な機能一覧
--------------
- 環境設定管理
  - 自動でプロジェクトルートの .env / .env.local を読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクトから設定値取得（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）
- Data (kabusys.data)
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（日足・財務・カレンダー等）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集: fetch_rss、前処理、SSRF 対策、raw_news への保存ロジック（news_collector）
  - 品質チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- AI (kabusys.ai)
  - ニュースセンチメント: score_news（gpt-4o-mini を利用、JSON Mode／バッチ）
  - 市場レジーム判定: score_regime（ETF 1321 の MA200 乖離 + マクロ LLM センチメントの合成）
- Research (kabusys.research)
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量解析: calc_forward_returns / calc_ic / factor_summary / rank

セットアップ手順
----------------

前提
- Python 3.10+（型ヒントで | を使っているため）
- DuckDB, OpenAI SDK 等のライブラリが必要（下記参照）

1. リポジトリをクローンし、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   実プロジェクトでは requirements.txt / pyproject.toml を用意し pip install -e . を推奨します。

3. 環境変数の設定
   - プロジェクトルートに .env を置くと自動読み込みされます（.env.local は上書き）。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主に必要なキー:
     - JQUANTS_REFRESH_TOKEN（J-Quants のリフレッシュトークン）
     - KABU_API_PASSWORD（kabuステーション API 用パスワード）
     - SLACK_BOT_TOKEN（監視通知用）
     - SLACK_CHANNEL_ID（監視通知用）
     - OPENAI_API_KEY（OpenAI 呼び出しに使用）
   - その他:
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL（DEBUG/INFO/…）

使い方（よく使う API 例）
------------------------

まず DuckDB 接続を作る例:
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL を回す（データ取得・保存・品質チェック）
- from kabusys.data.pipeline import run_daily_etl
- from kabusys.config import settings
- import duckdb, datetime
- conn = duckdb.connect(str(settings.duckdb_path))
- result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
- print(result.to_dict())

2) ニュースセンチメントを算出して ai_scores に書き込む
- from kabusys.ai.news_nlp import score_news
- score_news(conn, target_date=datetime.date(2026,3,20), api_key=os.environ.get("OPENAI_API_KEY"))

戻り値は書き込んだ銘柄数（int）。

3) 市場レジームスコアを算出して market_regime に保存
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=datetime.date(2026,3,20), api_key=os.environ.get("OPENAI_API_KEY"))

4) 監査ログ用 DB 初期化
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成

5) カレンダー関連ユーティリティ
- from kabusys.data.calendar_management import is_trading_day, next_trading_day
- is_trading_day(conn, datetime.date(2026,3,20))
- next_trading_day(conn, datetime.date(2026,3,19))

注意点 / 設計上の重要事項
------------------------
- Look-ahead バイアス対策:
  - AI / リサーチ用の関数群は内部で datetime.today() を参照せず、必ず target_date を引数で受け取ります。バックテスト時は適切な日付を指定してください。
- API リトライ / フェイルセーフ:
  - J-Quants クライアント・OpenAI 呼び出しはリトライ実装あり。API 失敗時はフェイルセーフ（例: macro_sentiment=0）で処理を継続する場合があります。ログで失敗は確認してください。
- .env 自動読み込み:
  - プロジェクトルートは .git または pyproject.toml を基準に探索します。CWD に依存しません。
  - OS 環境変数 > .env.local > .env の順に優先されます。
- DuckDB 互換性:
  - 一部処理で executemany の空リスト禁止などの DuckDB バージョン依存を考慮した実装があります。DuckDB の推奨バージョンで動作確認してください。

ディレクトリ構成（主要ファイル）
-------------------------------

- src/kabusys/
  - __init__.py                 パッケージ初期化（__version__）
  - config.py                   環境変数・設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py               ニュースセンチメント（score_news）
    - regime_detector.py        マクロ + MA200 による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py               ETL パイプライン（run_daily_etl 等）
    - jquants_client.py         J-Quants API クライアント（fetch/save）
    - calendar_management.py    JPX カレンダー管理（is_trading_day 等）
    - news_collector.py         RSS ニュース収集・前処理
    - quality.py                データ品質チェック（run_all_checks 等）
    - stats.py                  汎用統計ユーティリティ（zscore_normalize）
    - audit.py                  監査テーブル DDL と初期化ユーティリティ
    - etl.py                    ETLResult の公開エイリアス
  - research/
    - __init__.py
    - factor_research.py        ファクター計算（calc_momentum 等）
    - feature_exploration.py    将来リターン / IC / 統計サマリー等

依存ライブラリ（主なもの）
-------------------------
- duckdb
- openai (OpenAI Python SDK)
- defusedxml (RSS XML パースの安全化)
- （標準ライブラリ: urllib, json, datetime, logging 等）

サンプル .env キー（.env.example を参照のこと）
------------------------------------------------
- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

開発 / テストのヒント
---------------------
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、必要な環境変数はテスト側で注入してください。
- OpenAI 呼び出し関数は内部で分離されており、unittest.mock.patch により _call_openai_api を差し替えてテストできます。
- J-Quants の HTTP 呼び出しは内部で RateLimiter とリトライを挟んでいます。テストでは jquants_client._request などをモック推奨。

ライセンス / 貢献
-----------------
（該当プロジェクトのライセンス・貢献ルールをここに記載してください）

問い合わせ
----------
問題報告・機能提案は Issue を作成してください。開発者向けの詳細設計（DataPlatform.md / StrategyModel.md 等）がある場合はそれを参照してください。

以上。