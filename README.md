KabuSys
=======

日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注・約定トレーサビリティ）などを提供します。

主な特徴
-------
- データ取得（J-Quants API）と DuckDB への冪等保存（ON CONFLICT）
- 日次 ETL パイプライン（calendar / prices / financials）と品質チェック
- ニュース NLP（OpenAI / gpt-4o-mini を使用）による銘柄ごとのセンチメントスコア化
- マーケットレジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- ニュース収集（RSS）と SSRF / XML 安全対策
- 監査ログ用スキーマ（signal / order_request / executions）を DuckDB に初期化
- 環境変数/ .env を自動ロード（プロジェクトルート検出）、設定管理クラスを提供

機能一覧
-------
- データ取得 / 保存
  - jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- ETL
  - data.pipeline.run_daily_etl(target_date=None, ...)
  - 個別 ETL: run_prices_etl, run_financials_etl, run_calendar_etl
- 品質チェック
  - data.quality.run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency
- ニュース収集・前処理
  - data.news_collector.fetch_rss / preprocess_text / URL 正規化・SSRF 対策
- ニュース NLP（OpenAI）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 研究用
  - research.factor_research.calc_momentum / calc_volatility / calc_value
  - research.feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize
- 監査（監査ログスキーマ初期化）
  - data.audit.init_audit_db(db_path) / init_audit_schema(conn)
- 設定管理
  - config.settings（環境変数経由で設定を読み込む）

セットアップ手順
--------------
前提
- Python 3.10+（型アノテーションに Path | None などを使用しています）
- duckdb, openai, defusedxml などの依存パッケージ

例: 仮想環境作成 & インストール
1. 仮想環境作成・有効化
   $ python -m venv .venv
   $ source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（プロジェクトに requirements.txt があればそれを使用）
   $ pip install duckdb openai defusedxml

3. 開発中にローカルで使う場合（パッケージを editable インストール）
   $ pip install -e .

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）で .env / .env.local を自動読み込みします。
- 自動ロードを無効化したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN=xxxxx       # J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY=sk-...             # OpenAI API キー（news/regime 判定で使用）
- KABU_API_PASSWORD=...             # kabuステーション API 用パスワード（発注等で使用）
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag

簡易 .env.example
- .env.example を参考に .env をプロジェクトルートに作成してください。例:
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=your_openai_api_key
  KABU_API_PASSWORD=your_kabu_password
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

使い方（基本例）
---------------

1) DuckDB 接続を作る
- 設定からパスを取得して接続:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=None)  # target_date を指定することも可能
  print(result.to_dict())

3) ニュースのスコアリング（OpenAI が必要）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  # conn は DuckDB 接続、target_date はスコア付与対象日
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

4) マーケットレジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env または api_key 引数で指定

5) 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026,3,20))

6) 監査 DB 初期化
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます

7) 設定値の参照
  from kabusys.config import settings
  print(settings.is_live, settings.log_level, settings.duckdb_path)

注意点 / 実装ポリシー
-------------------
- Look-ahead bias（将来情報の漏洩）防止:
  - 各モジュール（news_nlp, regime_detector, pipeline 等）は date 引数を明示的に受け取り、内部で date.today() を安易に参照しない設計です。
  - ETL は取得日時（fetched_at）を UTC で記録します。
- 冪等性:
  - DB 保存処理は ON CONFLICT DO UPDATE / INSERT … ON CONFLICT などで冪等に実装。
- フェイルセーフ:
  - LLM / 外部 API 失敗時は例外で即停止させず部分的にフォールバックする（例: macro_sentiment=0.0、スコア取得失敗はスキップ）。
- セキュリティ:
  - news_collector: SSRF 対策、XML 脆弱性対策（defusedxml）、受信サイズ制限などを実装。
  - jquants_client: rate limiter、401 リフレッシュ処理、指数バックオフを実装。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                   # 環境変数 / Settings
- ai/
  - __init__.py
  - news_nlp.py               # ニュース NLP スコアリング
  - regime_detector.py        # 市場レジーム判定
- data/
  - __init__.py
  - pipeline.py               # ETL パイプライン & run_daily_etl 等
  - jquants_client.py         # J-Quants API クライアント & DuckDB 保存
  - news_collector.py         # RSS ニュース収集
  - quality.py                # データ品質チェック
  - calendar_management.py    # 市場カレンダー管理（is_trading_day 等）
  - stats.py                  # 統計ユーティリティ（zscore 正規化）
  - audit.py                  # 監査ログスキーマ初期化
  - etl.py                    # ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py        # momentum / value / volatility 等
  - feature_exploration.py    # forward_returns / IC / summary / rank

開発 / テストのヒント
--------------------
- OpenAI 呼び出し部分は内部で _call_openai_api を定義しており、unittest.mock.patch で差し替えてテスト可能です。
- ETL・保存処理は DuckDB の接続だけあればローカルで実行・検証できます（:memory: も使用可能）。
- 自動 .env ロードはプロジェクトルートを探索するため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと安全です。

ライセンス / 貢献
-----------------
（このリポジトリ固有のライセンス・貢献ルールがある場合はここに記載してください）

補足
----
- ここに示したコードや関数は内部設計に基づくもので、実際の運用では API キーの管理、RateLimit ポリシー、ログ設定、監視（pid/kill flag）などを適切に構成してください。
- 本 README はコードベースの概要と主要な使い方を簡潔にまとめたもので、詳細は各モジュールの docstring を参照してください。