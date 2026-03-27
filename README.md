KabuSys
=======

プロジェクト概要
--------------
KabuSys は日本株向けのデータプラットフォーム兼自動売買（研究）ライブラリです。  
J-Quants からのデータ取得（株価・財務・市場カレンダー）、RSS ニュース収集、OpenAI を使ったニュースセンチメント評価、ファクター計算／特徴量探索、監査ログ（トレーサビリティ）などを包括的に提供します。  
設計上、バックテストでのルックアヘッドバイアス回避、DuckDB を用いた効率的クエリ、ETL の冪等性・品質チェック、外部 API のリトライ／フェイルセーフを重視しています。

主な機能
--------
- データ取得・ETL
  - J-Quants API から株価（日足）、財務、上場情報、JPXカレンダーを差分取得・保存（ページネーション対応・再取得バックフィル付き）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合の検出
- ニュース収集・NLP
  - RSS からの記事収集（SSRF対策、サイズ制限、URL正規化）
  - OpenAI（gpt-4o-mini）を用いた銘柄別／マクロセンチメント評価（JSON Mode）
  - スコアを ai_scores / market_regime に保存
- 市場レジーム判定
  - ETF (1321) の MA200 乖離とマクロセンチメントを合成して日次で 'bull'/'neutral'/'bear' を判定
- 研究用ユーティリティ
  - モメンタム／バリュー／ボラティリティ等のファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal → order_request → execution までの監査テーブル定義と初期化ユーティリティ
- 設定管理
  - .env / .env.local / OS 環境変数からの自動読み込み（パッケージ配布後も動作するようプロジェクトルートを探索）

依存関係（主なもの）
-------------------
- Python 3.10+
- duckdb
- openai
- defusedxml

（上記はサンプル。実際には pyproject.toml / requirements.txt を参照してください）

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone ... （プロジェクトルートが .git/ または pyproject.toml を含むことを前提）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS/Linux
   - .venv\Scripts\activate     # Windows

3. 依存関係インストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - あるいはプロジェクトに requirements/pyproject があればそれを使用

4. 環境変数の用意（.env ファイル）
   - プロジェクトルートに .env または .env.local を作成してください。
   - 自動ロードの挙動:
     - デフォルトで OS 環境変数 > .env.local > .env の順で読み込みます。
     - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY:       OpenAI の API キー（score_news / score_regime 等で使用）
- KABU_API_PASSWORD:    kabuステーション API パスワード（必須）
- KABU_API_BASE_URL:    kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN:      Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID:     Slack 送信先チャンネル ID（必須）
- DUCKDB_PATH:          DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH:          SQLite（monitoring 用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV:          環境（development / paper_trading / live。デフォルト development）
- LOG_LEVEL:            ログレベル（DEBUG/INFO/...）

例（.env）
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

基本的な使い方
-------------

- DuckDB 接続の用意
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（株価・財務・カレンダー）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=some_date)  # target_date を省略すると today を使用
  - result は ETLResult オブジェクト（取得数、保存数、品質問題などを含む）

- ニュースセンチメント算出（OpenAI 必須）
  - from kabusys.ai.news_nlp import score_news
  - n_written = score_news(conn, target_date, api_key="sk-...")  # api_key を省略すると OPENAI_API_KEY を参照

- 市場レジーム算出（OpenAI 必須）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key="sk-...")

- 監査ログ DB 初期化（監査専用 DuckDB を使う例）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - init_audit_schema を呼ばずに済むユーティリティが用意されています（init_audit_db は transactional=True で初期化）

- ファクター計算 / 研究系
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - factors = calc_momentum(conn, target_date)
  - from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
  - fwd = calc_forward_returns(conn, target_date)
  - ic = calc_ic(factors, fwd, "mom_1m", "fwd_1d")

設計上の注意点（重要）
- ルックアヘッドバイアス防止:
  - 各モジュール（news_nlp, regime_detector, ETL など）は内部で date を明示的に受け取り、datetime.today()/date.today() をむやみに参照しないよう設計されています。バックテスト用途での利用時は target_date に注意してください。
- 冪等性:
  - ETL / save_* 系は ON CONFLICT を用い、同一データの再投入に耐えるようになっています。
- フェイルセーフ:
  - 外部 API（OpenAI・J-Quants）呼び出し失敗時は大半で例外を投げずにフォールバック（ゼロスコア等）やログ出力で継続します。ただし API キー未設定など必須パラメータは ValueError を送出します。
- テスト容易性:
  - OpenAI 呼び出し部分は内部で _call_openai_api を定義しており、ユニットテスト時にモック差し替えしやすくしています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                        # 環境変数 / .env 自動読み込み設定
- ai/
  - __init__.py
  - news_nlp.py                     # ニュース NLP（銘柄別スコア）
  - regime_detector.py              # マクロ + MA200 による市場レジーム判定
- data/
  - __init__.py
  - pipeline.py                     # ETL パイプライン（run_daily_etl 等）
  - etl.py                          # ETL インターフェース（ETLResult 再エクスポート）
  - jquants_client.py               # J-Quants API クライアント + DuckDB 保存
  - news_collector.py               # RSS 取得・前処理・raw_news 保存
  - calendar_management.py          # 市場カレンダー管理（営業日判定等）
  - quality.py                      # データ品質チェック
  - audit.py                        # 監査ログ（監査テーブル DDL / 初期化）
  - stats.py                        # 統計ユーティリティ（zscore_normalize）
- research/
  - __init__.py
  - factor_research.py              # モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py          # 将来リターン, IC, 統計サマリー, rank 等

追加情報
---------
- .env のパースはシェルの export KEY=val やクォート、コメント等に対応しています。config._find_project_root は __file__ を基準に .git や pyproject.toml を探索するため、CWD に依存しません。
- news_collector は SSRF / XML Bomb / 大容量レスポンスを考慮して堅牢化されています。
- jquants_client はレートリミッター、リトライ（指数バックオフ）、401 時のトークン自動更新を備えています。

問い合わせ / 貢献
-----------------
バグ報告や機能改善の提案は issue を立ててください。Pull Request は歓迎します。コード内の docstring を参照すると各関数の詳細挙動（引数・返り値・例外）が確認できます。

以上。README に記載してほしい追加の例やセクションがあれば教えてください。