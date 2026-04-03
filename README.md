KabuSys — 日本株自動売買プラットフォーム
======================================

概要
----
KabuSys は日本株のデータパイプライン、ニュース NLP、リサーチ（ファクター／特徴量探索）、監査ログ、及び市場レジーム判定などを含む自動売買／リサーチ向けライブラリ群です。  
主に J-Quants（株価・財務・カレンダー）や OpenAI（ニュースのセンチメント分析）を利用して、データ収集→品質チェック→特徴量計算→AI スコアリング→監査ログまでのワークフローを提供します。

主な特徴
---------
- データ ETL（J-Quants から株価・財務・マーケットカレンダーを差分取得／DuckDB に保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合など）
- ニュースの NLP スコアリング（OpenAI / gpt-4o-mini を用いた銘柄別センチメント）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースの LLM センチメント合成）
- 研究用ユーティリティ（モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン、IC、統計サマリ）
- 監査ログ（signal → order_request → execution のトレーサビリティを提供する監査スキーマ）
- ニュース収集モジュール（RSS 抽出、前処理、SSRF 防御、重複排除）

動作環境・依存
--------------
- Python 3.10 以上（型注釈で | 記法を使用しているため）
- 主な依存パッケージ（最低限）:
  - duckdb
  - openai (v1 SDK を想定)
  - defusedxml
- その他、標準ライブラリと urllib、json 等を使用

セットアップ手順
----------------
1. Python 環境を準備（推奨: virtualenv / venv）
   - python >= 3.10

2. 必要パッケージをインストール
   - 例（簡易）:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそちらを利用してください）

3. リポジトリをチェックアウトして editable インストール（開発用）
   - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env または .env.local を置くと自動的に読み込まれます（自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 重要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector 実行時に必要）
     - KABU_API_PASSWORD      : kabuステーション API パスワード（発注連携時）
     - KABU_API_BASE_URL      : kabu API のベースURL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH            : 監視用 SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV            : 環境 ('development' / 'paper_trading' / 'live')（デフォルト development）
     - LOG_LEVEL              : ログレベル（'DEBUG','INFO','WARNING','ERROR','CRITICAL'）

   - .env のサンプル（例）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

使い方（基本例）
----------------

- DuckDB 接続の作成（例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（J-Quants から差分取得して保存・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースの NLP スコアリング（ai_scores テーブルに書き込む）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定しておく必要があります。
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {written} scores")
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（監査ログ用）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

注意事項 / セキュリティ
---------------------
- API キーやトークンは絶対にリポジトリにコミットしないでください。.env/.env.local は .gitignore に追加することを推奨します。
- OpenAI 呼び出しは実行コストが発生します。開発時はテスト用のモックに差し替え可能です（モジュール内の _call_openai_api を patch する設計になっています）。
- J-Quants の API レート制限（120 req/min）を守る実装（RateLimiter、バックオフ、トークンリフレッシュ）になっています。

自動読み込みの挙動（.env）
-------------------------
- 起動時にプロジェクトルート（.git または pyproject.toml を含むディレクトリ）から .env を自動的に読み込みます。
- 読み込み順序: OS 環境変数 > .env.local > .env。つまり .env.local が .env を上書きします。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

ディレクトリ構成（抜粋）
-----------------------
- src/kabusys/
  - __init__.py              -- パッケージエントリ（__version__ 等）
  - config.py                -- 環境変数 / 設定管理（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュース NLP（銘柄別センチメント）
    - regime_detector.py     -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - quality.py             -- データ品質チェック
    - news_collector.py      -- RSS ニュース収集
    - calendar_management.py -- マーケットカレンダー管理（is_trading_day 等）
    - audit.py               -- 監査ログスキーマ初期化
    - etl.py                 -- ETLResult 公開
    - stats.py               -- 統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py     -- モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py -- 将来リターン・IC・統計サマリ等
  - ai/, data/, research/ 内の各モジュールはそれぞれの責務に分離されています。

主要関数一覧（代表）
-------------------
- ETL / データ:
  - kabusys.data.pipeline.run_daily_etl(...)
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.save_daily_quotes(...)

- 品質チェック:
  - kabusys.data.quality.run_all_checks(...)

- ニュース / AI:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- 研究:
  - kabusys.research.calc_momentum(...)
  - kabusys.research.calc_volatility(...)
  - kabusys.research.calc_value(...)
  - kabusys.data.stats.zscore_normalize(...)

貢献・拡張
----------
- 新しいデータソース追加（jquants_client の拡張）
- OpenAI モデルやプロンプトのチューニング
- 監査スキーマの拡張（追加カラムや状態遷移）
- テスト用のモックやシミュレーション環境の整備

ライセンス
----------
- 本リポジトリのライセンス情報はリポジトリの LICENSE を参照してください（ここでは記載されていません）。

問い合わせ
---------
- コードベースの実装方針や使用方法については各モジュールの docstring を参照してください。特に ETL / データ品質 / ニュース NLP / レジーム判定には設計上の考慮点（ルックアヘッドバイアス対策、フェイルセーフ等）が注記されています。

以上。必要であれば、README に含めるサンプル .env.example、requirements.txt、もしくは具体的な DB 初期化・スケジューリング（cron / Airflow 例）を追記します。どの情報を追加しますか？