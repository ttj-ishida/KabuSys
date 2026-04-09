README
=====

プロジェクト概要
--------------
KabuSys は日本株向けのデータプラットフォーム兼リサーチ／自動売買支援ライブラリです。  
J-Quants からのデータ取得（株価・財務・市場カレンダー）、ニュース収集と NLP による銘柄スコアリング、ファクター計算・特徴量解析、監査ログ（注文シグナル〜約定のトレーサビリティ）、ETL パイプラインなどを提供します。モジュールは DuckDB をデータ層に利用し、OpenAI（gpt-4o-mini）をニュース／マクロセンチメントの評価に利用する設計になっています。

主な特徴
--------
- J-Quants API クライアント（差分取得、ページネーション、自動トークンリフレッシュ、レート制御）
- ETL パイプライン（prices / financials / market_calendar の差分取得・保存・品質チェック）
- ニュース収集（RSS）およびニュース NLP（OpenAI）による銘柄別スコアリング
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- 研究用ユーティリティ：ファクター計算（モメンタム／バリュー／ボラティリティ等）、将来リターン計算、IC 計算、Zスコア正規化等
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログスキーマ（signal / order_request / executions）と初期化ユーティリティ
- フォールバックやフェイルセーフ設計（API失敗時の挙動など）

必要条件（推奨）
----------------
- Python 3.10 以上（型アノテーションの union などを利用）
- 依存パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトに合わせて requirements.txt / pyproject.toml に記載してください）

セットアップ手順
----------------
1. リポジトリをクローン / ソースを配置する。
2. 仮想環境を作成して有効化（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate (macOS / Linux)
   - .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール（最低限の例）:
   - pip install duckdb openai defusedxml
   - あるいはプロジェクトに requirements.txt があれば pip install -r requirements.txt
4. 環境変数を用意する:
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local を上書きに使用可能）。
   - 自動ロードを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト等）。
5. データベース用ディレクトリを用意（必要に応じて）:
   - デフォルトでは data/ に DB ファイルを作成します（settings.duckdb_path 等）。

重要な環境変数
----------------
（主なもののみ抜粋）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース / レジーム判定で使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（注文などで使用）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_FILL_MODE: paper_trading 時のモック埋め方（instant/partial/never/reject）
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

.env の自動読み込みについて
---------------------------
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を基に .env/.env.local を自動ロードします。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

基本的な使い方（例）
------------------

- Settings の取得（環境変数参照）
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path などを参照

- DuckDB 接続
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- ETL（日次パイプライン）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=some_date, id_token=None)
  - result は ETLResult（取得/保存件数・品質問題・エラー一覧）を返します

- 個別 ETL ジョブ
  - run_prices_etl(conn, target_date)
  - run_financials_etl(conn, target_date)
  - run_calendar_etl(conn, target_date)

- ニュース NLP（銘柄ごとの ai_scores 生成）
  - from kabusys.ai.news_nlp import score_news
  - n = score_news(conn, target_date, api_key=None)
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)

- 研究用ユーティリティ
  - from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank
  - 各関数は DuckDB 接続と target_date を受け取り、結果を list[dict] の形で返す

- 監査ログスキーマ初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

コード例（簡潔）
----------------
- ETL 実行（当日）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    import duckdb
    from kabusys.config import settings
    conn = duckdb.connect(str(settings.duckdb_path))
    res = run_daily_etl(conn, target_date=date.today())

- ニューススコア作成
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    n = score_news(conn, target_date=date(2026, 3, 20))

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20))

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                         - 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                      - ニュース NLP（銘柄別スコア）
  - regime_detector.py               - 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py                - J-Quants API クライアント（fetch / save）
  - pipeline.py                      - ETL パイプライン（run_daily_etl など）
  - etl.py                           - ETL 便宜 API (ETLResult の公開)
  - news_collector.py                - RSS ニュース収集
  - calendar_management.py           - 市場カレンダー管理（is_trading_day 等）
  - quality.py                       - データ品質チェック
  - stats.py                         - 汎用統計ユーティリティ（zscore 等）
  - audit.py                         - 監査ログスキーマ定義 / 初期化
- research/
  - __init__.py
  - factor_research.py               - ファクター計算（momentum/value/volatility）
  - feature_exploration.py           - 将来リターン / IC / 統計サマリー等
- research/*（他補助モジュールなど）
- その他モジュール（execution, monitoring, strategy 等があることを暗示）

開発メモ
--------
- ルックアヘッドバイアス回避のため、各処理は target_date を明示し、date.today() や datetime.now() に直接依存しない設計です（テスト・バックテストを意識）。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスのパースやリトライを組み込んでいます。テスト時は内部の _call_openai_api をモックしてください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を探索して行います。CI／テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にすると良いです。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コードは空チェックを行っています。

貢献 / ライセンス
-----------------
- CONTRIBUTING や LICENSE ファイルをプロジェクトルートに置いてください。

以上。README の内容はリポジトリの構成やコードコメントを元にまとめています。必要があればサンプル .env.example や requirements.txt、セットアップ用の pyproject.toml/setup.cfg のテンプレート作成も支援できます。