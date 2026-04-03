KabuSys
=======

日本株向けのデータプラットフォーム＆自動売買補助ライブラリです。  
ETL（J-Quants）→ データ品質チェック → AI（OpenAI）によるニュース/NLP評価 → リサーチ/ファクター計算 → 監査ログのためのスキーマなど、研究・運用に必要なユーティリティ群を提供します。

主な特徴
--------
- J-Quants API 経由の差分ETL（株価・財務・市場カレンダー）と DuckDB への冪等保存
- ニュース収集（RSS）と前処理（SSRF/トラッキング除去等）
- OpenAI（gpt-4o-mini） を用いたニュースセンチメント評価（銘柄単位 / マクロ判定）
- 市場レジーム判定（ETF + マクロセンチメントの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- .env ファイル自動読み込み（プロジェクトルート検出により環境を自動セット）

含まれる主な機能一覧
-------------------
- data.jquants_client: J-Quants API クライアント（取得／保存／ページネーション／トークンリフレッシュ／レート制御）
- data.pipeline: 日次 ETL 実行（run_daily_etl 等）と ETL 結果オブジェクト（ETLResult）
- data.quality: 品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
- data.news_collector: RSS 取得・前処理（SSRF 対策、トラッキング除去、記事ID生成）
- data.calendar_management: JPX カレンダー管理・営業日判定・更新ジョブ
- data.audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- ai.news_nlp: 銘柄別ニュースセンチメント評価（score_news）
- ai.regime_detector: マクロ + ETF MA による市場レジーム判定（score_regime）
- research: ファクター計算（calc_momentum / calc_value / calc_volatility）と特徴量解析（calc_forward_returns / calc_ic / factor_summary / rank）
- data.stats: zscore_normalize（クロスセクション Z スコア正規化）
- config: 環境変数からの設定読み込み（自動 .env ロード、Settings オブジェクト）

前提・依存
-----------
- Python 3.10+
  - 型記法（X | None）などを使用しているため少なくとも 3.10 以上を推奨します。
- 主な外部ライブラリ（インストール例は下記）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - （logging / urllib などは標準ライブラリ）

セットアップ手順
----------------

1. リポジトリをクローンしてパッケージをインストール（開発モード）
   - 例:
     - git clone <repo>
     - cd <repo>
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install --upgrade pip
     - pip install -e ".[all]"  # extras が定義されている場合。なければ個別 pip install duckdb openai defusedxml 等

   必要パッケージ（最低例）:
   - pip install duckdb openai defusedxml

2. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと、自動で読み込まれます（config._find_project_root によりルートを検知）。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時などに有用）。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector で使用）
   - KABU_API_PASSWORD: kabuステーション等のパスワード（必要時）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: environment (development|paper_trading|live)
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   サンプル .env（簡略）
   - JQUANTS_REFRESH_TOKEN=xxxxx
   - OPENAI_API_KEY=sk-xxxx
   - DUCKDB_PATH=./data/kabusys.duckdb
   - KABUSYS_ENV=development
   - LOG_LEVEL=INFO

使い方（簡易例）
---------------

以下は基本的な利用例です。詳細は各モジュールの docstring を参照してください。

1) DuckDB 接続の作成
- Python REPL 例:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

2) 日次ETL の実行（J-Quants からデータ取得→保存→品質チェック）
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

3) ニュースセンチメント（銘柄別）のスコア化
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を使う場合 api_key を None にする

4) 市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- from datetime import date
- score_regime(conn, target_date=date(2026,3,20), api_key=None)  # OpenAI キーは OPENAI_API_KEY から取得される

5) 監査ログ DB 初期化（監査専用 DB を作る）
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db("data/audit.duckdb")  # ":memory:" も可

6) ファクター計算・リサーチ
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- records = calc_momentum(conn, target_date=date(2026,3,20))

7) ニュース RSS 取得（単体 fetch）
- from kabusys.data.news_collector import fetch_rss
- articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

便利な設定・挙動
----------------
- .env 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト用途）
- Settings オブジェクトは kabusys.config.settings 経由でアクセスできます（例: settings.duckdb_path）
- OpenAI 呼び出しは内部でリトライ・タイムアウト・JSON パース保護が実装されています。API 失敗時はフェイルセーフ（ゼロスコア等）で継続する実装方針です。

ディレクトリ構成（src/kabusys の主要ファイル）
---------------------------------------
- kabusys/
  - __init__.py (パッケージ定義、version)
  - config.py (環境設定の読み込み・Settings)
  - ai/
    - __init__.py
    - news_nlp.py (銘柄別ニューススコアリング: score_news)
    - regime_detector.py (市場レジーム判定: score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、保存関数)
    - pipeline.py (ETL パイプライン / ETLResult)
    - etl.py (ETL のインターフェース再エクスポート)
    - news_collector.py (RSS 収集・前処理)
    - calendar_management.py (JPX カレンダー管理 / is_trading_day 等)
    - quality.py (データ品質チェック)
    - stats.py (zscore_normalize 等統計ユーティリティ)
    - audit.py (監査ログスキーマ初期化)
  - research/
    - __init__.py
    - factor_research.py (モメンタム・バリュー・ボラティリティ等)
    - feature_exploration.py (forward returns, IC, factor summary, rank)
  - monitoring/ (実装ファイルはこのスニペットに含まれていませんが監視系を想定)
  - strategy/, execution/ (戦略／実行エンジン用の名前空間、個別実装はここに置かれます)

設計上の注意点
--------------
- ルックアヘッドバイアス対策:
  - 多くの関数は date を引数で受け取り、内部で datetime.today() を参照しない設計。ETL やスコアリングは「その日までにアプリが知りうるデータのみ」を使うことを強く意図しています。
- 冪等性:
  - DuckDB への保存は基本的に ON CONFLICT DO UPDATE / INSERT ... ON CONFLICT を利用して冪等に動作します。
- フェイルセーフ:
  - OpenAI 呼び出しや外部 API は、失敗時に例外を上位に投げずフォールバック動作（0.0 スコア等）で継続する箇所が多くあります。必要に応じてログを確認してください。

開発・テストヒント
-------------------
- 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- AI 呼び出しをユニットテストで差し替えるには、モジュール内の _call_openai_api 等の private 関数を unittest.mock.patch でモックできます（news_nlp._call_openai_api, regime_detector._call_openai_api など）。
- DuckDB を使った単体テストでは ":memory:" を指定するとインメモリ DB を使用できます（例: duckdb.connect(":memory:")）。

ライセンス・貢献
----------------
- この README には記載されていないライセンス情報がプロジェクトルートに存在するはずです。貢献や issue 提出はリポジトリの CONTRIBUTING / ISSUE テンプレートに従ってください。

補足
----
本 README はソースコードの docstring を元に主要な使い方 / 構成をまとめたものです。各機能の詳細なパラメータや挙動は該当モジュール（kabusys/data/*.py, kabusys/ai/*.py, kabusys/research/*.py）内の docstring を参照してください。必要であれば、使用例や運用手順のドキュメントを追記します。