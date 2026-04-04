KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株向けのデータパイプライン、ファクター研究、ニュースNLP、マーケットレジーム判定、監査ログなどを備えた自動売買／リサーチ基盤の Python パッケージです。  
設計上の特徴は以下です。

- DuckDB を中心としたローカルデータプラットフォーム（raw_prices, raw_financials, raw_news, market_calendar, ai_scores, market_regime, audit テーブル等）
- J-Quants API との差分 ETL（レートリミット制御・トークン自動リフレッシュ・再試行）
- RSS ニュース収集（SSRF 対策、トラッキング除去、記事ID の SHA-256）
- OpenAI を用いたニュースセンチメント解析（gpt-4o-mini を想定）
- レジーム判定（ETF 1321 の MA200 とマクロニュースのセンチメントを合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェックと監査ログ（監査テーブルの初期化ユーティリティあり）
- ルックアヘッドバイアスを避ける設計（内部で date.today() や datetime.now() を不用意に参照しない等）

主な機能一覧
-------------
- 環境設定管理（kabusys.config.Settings）
  - .env 自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得、バックフィル、品質チェック（kabusys.data.quality）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - fetch / save の idempotent な処理、レートリミット・リトライ・401 リフレッシュ
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news / news_symbols への保存（冪等）
- カレンダー／営業日管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- ニュース NLP（kabusys.ai.news_nlp）
  - calc_news_window / score_news（銘柄ごとの ai_score を ai_scores テーブルへ書込み）
- レジーム判定（kabusys.ai.regime_detector）
  - score_regime（ETF 1321 の MA200 乖離 + マクロセンチメントを合成）
- 研究モジュール（kabusys.research）
  - calc_momentum / calc_value / calc_volatility 等
  - calc_forward_returns, calc_ic, factor_summary, rank
- 監査ログ（kabusys.data.audit）
  - init_audit_schema / init_audit_db（監査テーブルの冪等初期化）

セットアップ手順
----------------
前提:
- Python 3.9+（コードの注釈により型ヒントが多用されています）
- DuckDB, OpenAI SDK, defusedxml 等を利用します

1. リポジトリをクローン／プロジェクトルートへ移動:
   - git clone ... && cd your-repo

2. 仮想環境を作成・有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージと依存ライブラリをインストール:
   - pip install -e .
   - 必要な主要依存例（requirements.txt がない場合は手動で）:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject に依存があればそちらを参照してください）

4. 環境変数（.env）の準備:
   - プロジェクトルートに .env を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須/よく使う環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...        ← J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY=...               ← OpenAI API キー（score_news/score_regime で使用）
     - KABU_API_PASSWORD=...            ← kabu ステーション API パスワード（必要時）
     - KABU_API_BASE_URL=...            ← kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH=data/kabusys.duckdb   ← DuckDB ファイルパス（デフォルト）
     - SQLITE_PATH=data/monitoring.db   ← 監視用 SQLite（オプション）
     - LOG_LEVEL=INFO
     - KABUSYS_ENV=development|paper_trading|live

   - .env の書式はシェルライク（export KEY=val, 引用符, コメント等に対応）で読み込まれます。

使い方（簡単な例）
-----------------

共通の前提: DuckDB 接続を用意して作業します。

1) DuckDB 接続例:
   from datetime import date
   import duckdb
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）:
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())

3) ニュースのセンチメントを計算して ai_scores に書き込む:
   from kabusys.ai.news_nlp import score_news
   count = score_news(conn, target_date=date(2026, 3, 20))
   print(f"scored {count} codes")

   - OPENAI_API_KEY は環境変数か api_key 引数で指定できます。
   - window は calc_news_window により前日 15:00 JST ～ 当日 08:30 JST を対象に集計します。

4) 市場レジームを判定して market_regime テーブルへ書き込む:
   from kabusys.ai.regime_detector import score_regime
   score_regime(conn, target_date=date(2026, 3, 20))

5) ファクター計算（研究用途）:
   from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
   mom = calc_momentum(conn, date(2026, 3, 20))
   vol = calc_volatility(conn, date(2026, 3, 20))
   val = calc_value(conn, date(2026, 3, 20))
   normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

6) 監査ログ用 DB 初期化:
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")

注意点 / 設計ポリシー
-------------------
- ルックアヘッドバイアス回避:
  - score_news / score_regime / ETL 等は target_date を明示的に受け取り、内部で datetime.today() を不用意に参照しない設計です。
- 冪等性:
  - 保存処理は ON CONFLICT DO UPDATE などで上書きされるため複数回実行しても安全です。
- リトライ・フェイルセーフ:
  - OpenAI/J-Quants 呼び出しは再試行ロジックを持ち、API 失敗時にゼロやスキップで継続する箇所があります（例: マクロセンチメントが得られない場合は 0.0 にフォールバック）。
- セキュリティ:
  - news_collector は SSRF 対策、XML パースに defusedxml、レスポンスサイズ制限などを実装しています。
- ロギング:
  - logger を適宜使用。LOG_LEVEL 環境変数で制御できます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                         ← 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                      ← ニュース NLP（score_news）
  - regime_detector.py               ← レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                ← J-Quants API クライアント + 保存関数
  - pipeline.py                      ← ETL パイプライン（run_daily_etl 等）
  - etl.py                           ← ETL の再エクスポート
  - news_collector.py                ← RSS 収集と前処理
  - calendar_management.py           ← 市場カレンダー管理
  - stats.py                         ← zscore_normalize 等
  - quality.py                       ← データ品質チェック
  - audit.py                         ← 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py               ← calc_momentum / calc_value / calc_volatility
  - feature_exploration.py           ← calc_forward_returns / calc_ic / factor_summary / rank
- ai/、research/ は研究・AI 関連の主要ロジックを格納

よくある質問（簡易）
-------------------
Q: .env が自動で読み込まれない / テストで無効にしたい  
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

Q: OpenAI のレスポンスが不正な場合はどうなる？  
A: news_nlp/regime_detector は JSON パース失敗や API エラー時に警告ログを出して該当処理をスキップまたはスコア 0.0 にフォールバックします。致命的な例外は上位に伝播されます。

Q: 監査テーブルの初期化は破壊的ですか？  
A: init_audit_schema / init_audit_db は冪等にテーブルを作成します（CREATE TABLE IF NOT EXISTS）。既存データは削除しません。

ライセンス
---------
リポジトリに明記されていないため、使用・配布前にライセンス方針を確認してください。

問い合わせ / 開発
-----------------
- 開発中の変更は pyproject.toml / setup.py を確認のうえ仮想環境で pip install -e . を行ってください。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして環境依存を切り離すことを推奨します。

以上がこのコードベースの概要と使い方の簡易ドキュメントです。README に追記したい具体的なコマンドや .env.example のテンプレを作成する場合は、必要な項目（持っている API キー・DB パスなど）を教えてください。