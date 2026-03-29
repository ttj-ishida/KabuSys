KabuSys — 日本株自動売買 / データプラットフォーム
================================

バージョン: 0.1.0

概要
----
KabuSys は日本株向けのデータプラットフォーム兼自動売買（研究・シグナル生成・監査・発注）用ライブラリです。本リポジトリは以下の主要機能を提供します。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL（DuckDB 保存）
- RSS ベースのニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント・マクロセンチメント評価（ai スコア）
- マーケットレジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）
- 研究用ファクター計算（Momentum / Value / Volatility 等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）用のスキーマ定義と初期化
- 環境変数・設定管理（.env 自動読み込み、Settings API）

機能一覧
--------
- data.jquants_client: J-Quants からのデータ取得（株価 / 財務 / カレンダー）と DuckDB への冪等保存
- data.pipeline: 日次 ETL パイプライン（run_daily_etl）と個別 ETL ジョブ
- data.news_collector: RSS フィード取得・前処理・raw_news テーブル保存（SSRF・サイズ制限対策）
- data.quality: データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
- data.calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
- data.audit: 監査ログ用スキーマ作成・初期化（init_audit_schema / init_audit_db）
- ai.news_nlp: 銘柄ごとのニュースセンチメントを LLM で評価（score_news）
- ai.regime_detector: マクロ + MA200 を合成した市場レジーム判定（score_regime）
- research: ファクター計算（calc_momentum, calc_value, calc_volatility）と特徴量解析ユーティリティ
- config: .env / 環境変数の読み込みと Settings オブジェクト

前提条件 / 依存
----------------
- Python 3.10+
- 必要パッケージ（一例）:
  - duckdb
  - openai
  - defusedxml
- その他: ネットワークアクセス（J-Quants / RSS / OpenAI）

セットアップ手順
----------------

1. リポジトリをクローン・チェックアウト
   - git clone <repo_url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .    # パッケージを開発モードでインストールできる場合
   - pip install duckdb openai defusedxml

4. 環境変数設定 (.env)
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと、自動で読み込まれます。
   - .env.local がある場合は .env に上書きする形で優先読み込みされます。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用など）。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN       : Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID      : Slack 通知のチャンネル ID
   - 任意 / 追加:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — ロギングレベル（デフォルト INFO）
     - DUCKDB_PATH, SQLITE_PATH — デフォルト data/kabusys.duckdb / data/monitoring.db

5. データベース（監査用）初期化例
   - Python から監査 DB を初期化:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

使い方（代表例）
----------------

設定参照:
- 環境変数は Settings 経由で取得できます。
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  is_live = settings.is_live

DuckDB 接続を用意:
- import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

ETL（日次パイプライン）実行:
- from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

ニューススコア（OpenAI 必須: OPENAI_API_KEY 環境変数か引数で指定）:
- from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} symbols")

市場レジーム判定:
- from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))
  # market_regime テーブルに日次レジームを書き込みます

ファクター計算（研究用途）:
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))

監査スキーマ初期化:
- from kabusys.data.audit import init_audit_schema
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)

ニュース収集（RSS フェッチ）:
- from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")

重要な挙動と注意点
------------------
- .env 読み込み:
  - デフォルトでプロジェクトルートの .env（続けて .env.local）を自動読み込みします。
  - テストや特殊コンテキストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- OpenAI 呼び出し:
  - score_news / score_regime は OPENAI_API_KEY を環境変数または api_key 引数で受け取ります。
  - モックしやすい設計で、テストでは内部の _call_openai_api をパッチできます。
- Look-ahead バイアス対策:
  - 多くの関数は datetime.today()/date.today() に依存せず、target_date を明示的に与える設計です（バックテスト用）。
- 冪等性:
  - J-Quants→DuckDB 保存は ON CONFLICT DO UPDATE を使い、再取得で上書きできるようになっています。
- エラーハンドリング:
  - LLM / API エラー時はフェイルセーフ（多くの場合スコア0やスキップ）で続行するよう設計されています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                  # パッケージ初期化、__version__ (0.1.0)
- config.py                    # .env / 環境変数読み込みと Settings
- ai/
  - __init__.py
  - news_nlp.py                # ニュースセンチメント（score_news）
  - regime_detector.py         # マクロ + MA200 合成による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py          # J-Quants API クライアント（取得 + 保存）
  - pipeline.py                # ETL パイプライン（run_daily_etl など）
  - etl.py                     # ETLResult の再エクスポート
  - news_collector.py          # RSS 取得と前処理
  - quality.py                 # データ品質チェック
  - stats.py                   # 汎用統計関数（zscore_normalize）
  - calendar_management.py     # 市場カレンダー管理と営業日ユーティリティ
  - audit.py                   # 監査ログスキーマ定義 / 初期化
- research/
  - __init__.py
  - factor_research.py         # ファクター計算（Momentum/Value/Volatility）
  - feature_exploration.py     # 将来リターン / IC / 統計サマリー 等

開発・テストのヒント
--------------------
- OpenAI 呼び出しやネットワーク I/O はモック可能です（内部の _call_openai_api / _urlopen を patch する設計）。
- 自動 .env ロードを回避するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- duckdb を使うため、ローカルに DuckDB ファイル（デフォルト data/kabusys.duckdb）を用意してください。監査などは別 DB に分けても OK（init_audit_db）。

免責・備考
---------
本パッケージは研究・実験用途の設計を念頭に置いています。実際の資金での運用を行う際は、注文ロジック・接続先・レイテンシ・エラーハンドリング・法的責任等を十分検討してください。

問い合わせ
----------
- 実装や利用方法に関する質問はリポジトリの Issues をご利用ください。

以上。