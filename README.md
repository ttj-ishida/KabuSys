KabuSys — 日本株自動売買 / データ基盤ライブラリ
=====================================

概要
----
KabuSys は日本株向けの自動売買、データプラットフォーム、リサーチツール群を含む Python パッケージです。  
主に以下を提供します。

- J-Quants API からのデータ ETL（株価・財務・マーケットカレンダー）
- ニュース収集（RSS）と NLP による銘柄別センチメント評価（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム / バリュー / ボラティリティ 等）
- データ品質チェック、マーケットカレンダー管理
- 監査ログ（signal → order → execution のトレーサビリティ）初期化ユーティリティ

主な機能
--------
- data（ETL / calendar / jquants client / news collector / quality / audit）
  - 日次 ETL（run_daily_etl）で差分取得・保存・品質チェック
  - market_calendar の更新・営業日判定ユーティリティ
  - J-Quants API クライアント（トークン自動リフレッシュ・レート制御・再試行）
  - RSS 収集（SSRF / GZip / XML Bomb 対策）と raw_news 保存ロジック
  - 監査ログテーブル初期化（init_audit_schema / init_audit_db）
- ai（news_nlp / regime_detector）
  - ニュースを LLM（gpt-4o-mini）でバッチセンチメント評価して ai_scores に保存（score_news）
  - ETF（1321）の MA とマクロニュースの LLM 評価を組み合わせた市場レジーム判定（score_regime）
- research（factor_research / feature_exploration）
  - モメンタム・バリュー・ボラティリティ等ファクター計算
  - 将来リターン計算・IC（スピアマン）・ファクター統計サマリ
- utils（data.stats の zscore 正規化 等）
- 設定管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数取得ユーティリティ（settings オブジェクト）

セットアップ
------------
1. リポジトリを取得
   - git clone した後、プロジェクトルート（pyproject.toml または .git がある場所）で作業します。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須: duckdb, openai, defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject がある場合はそちらを使用してください）
   - 開発インストール例:
     - pip install -e .

4. 環境変数 / .env
   - プロジェクトルートの .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 最低限設定が必要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...   （必須: J-Quants リフレッシュトークン）
     - OPENAI_API_KEY=...          （AI 評価に使用。score_* に直接渡すことも可能）
     - KABU_API_PASSWORD=...      （kabuステーション API のパスワード）
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb   （デフォルト）
     - SQLITE_PATH=data/monitoring.db    （デフォルト）
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...

使い方（基本例）
----------------

共通: DuckDB 接続を作成する例
- Python REPL やスクリプト内で:
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

ETL（日次パイプライン）を実行する
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date)  # target_date は datetime.date オブジェクト。省略で今日。
- result は ETLResult オブジェクト（取得件数や品質問題を含む）

ニュースセンチメントのスコア付け（AI）
- from kabusys.ai.news_nlp import score_news
- # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
- written = score_news(conn, target_date, api_key=None)
- returns: 書き込んだ銘柄数（int）

市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date, api_key=None)  # OpenAI API キーは環境変数か引数で指定

監査ログ DB を初期化する
- from kabusys.data.audit import init_audit_db, init_audit_schema
- conn_audit = init_audit_db("data/audit.duckdb")  # ":memory:" も可
- または既存接続に対して init_audit_schema(conn, transactional=True)

ファクター計算 / リサーチユーティリティ
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- momentum = calc_momentum(conn, target_date)  # list[dict]
- from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
- fwd = calc_forward_returns(conn, target_date, horizons=[1,5,21])

マーケットカレンダー / 営業日判定
- from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
- is_trading_day(conn, date(2026,3,20))
- next_trading_day(conn, some_date)
- get_trading_days(conn, start, end)

データ品質チェック
- from kabusys.data.quality import run_all_checks
- issues = run_all_checks(conn, target_date=some_date)
- QualityIssue オブジェクトのリストが返る。severity により対処を判断。

設定周り（settings）
- from kabusys.config import settings
- settings.jquants_refresh_token などのプロパティで必要な値を取得できます。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

注意点 / 実運用に関する考慮
--------------------------
- OpenAI 呼び出し: API エラー時はフェイルセーフで 0.0 を返す等の設計があり、全体処理を停止しない実装です。ただし API キーやレート制限には注意してください。
- J-Quants クライアント: レート制限（120 req/min）やトークン自動リフレッシュ、再試行ロジックを内包しています。get_id_token の結果はキャッシュされます。
- ルックアヘッドバイアス対策: 多くの関数は date.today() を直接参照せず、target_date を引数で与える設計です。バックテスト時は過去日時を明示して使用してください。
- DuckDB バージョン依存: 一部実装は DuckDB の挙動を前提にしています（executemany 空リスト不可など）。運用時は互換性に留意してください。
- セキュリティ: RSS 取得では SSRF 対策、XML のデフューズ処理、レスポンスサイズ制限などの安全対策が組み込まれています。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主なモジュールと役割です（省略せず全体を把握しやすい構成）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP / score_news（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py                   — ETL パイプライン（run_daily_etl, run_prices_etl...）
    - etl.py                        — ETLResult 型の再エクスポート
    - calendar_management.py        — 市場カレンダー管理 / 営業日判定 / calendar_update_job
    - news_collector.py             — RSS 収集・前処理・保存ロジック
    - quality.py                    — データ品質チェック
    - stats.py                      — zscore_normalize 等統計ユーティリティ
    - audit.py                      — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py            — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py        — 将来リターン / IC / サマリー等
  - monitoring/ (存在する場合: 監視関連コード等)
  - strategy/, execution/, monitoring (パッケージメンバーとして公開される可能性)

補足
----
- README の用途に応じて、pyproject.toml / requirements.txt / CI ワークフローを追加してください。  
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動ロードを無効化すると制御しやすくなります。

ライセンスやコントリビューションガイドはこのプロジェクト特性に合わせて別途追加してください。

以上。必要であれば、具体的な実行スクリプト例（systemd / cron / GitHub Actions 用のジョブ定義）や .env.example を作成する README の拡張を作成します。どの部分を詳しく出力しますか？