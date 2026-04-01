KabuSys — 日本株データプラットフォーム & 自動売買基盤
==================================================

概要
----
KabuSys は日本株向けのデータ収集・ETL・品質チェック・ファクター研究・ニュースNLP・市場レジーム判定・監査ログを含むライブラリ群です。  
主な用途はデータ基盤の構築、研究環境（ファクター計算・IC評価）、および自動売買システムの監査・トレーサビリティ基盤の提供です。設計上、バックテストにおけるルックアヘッドバイアス防止・冪等性・堅牢な外部API呼び出し（リトライ/レート制御）を重視しています。

主な機能
--------
- データ収集 / ETL
  - J-Quants API から株価（日足）、財務データ、上場情報、JPXカレンダーを差分取得・保存（duckdb）
  - 差分更新・バックフィル・ページネーション対応
  - レートリミット制御とリトライ（401 の自動リフレッシュ含む）
- データ品質チェック
  - 欠損、スパイク（急騰/急落）、重複、日付不整合チェックを実施
  - QualityIssue 型で問題を収集（Fail-Fast ではなく全件収集）
- ニュース収集
  - RSS フィード取得、前処理、SSRF対策、トラッキングパラメータ除去、raw_news + news_symbols への冪等保存
- ニュースNLP（OpenAI）
  - gpt-4o-mini を用いた銘柄別センチメントスコアリング（news_nlp.score_news）
  - マクロニュースの LLM 判定を組み合わせた市場レジーム判定（ai.regime_detector.score_regime）
  - API 経由の呼び出しは JSON Mode と堅牢なリトライ設計
- リサーチ / ファクター計算
  - Momentum / Value / Volatility / Liquidity 等のファクター計算
  - 将来リターン計算、IC（Spearman rank）計算、統計サマリー、Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events, order_requests, executions テーブルなどを含む監査スキーマの初期化（冪等）
  - order_request_id を冪等キーとして二重発注防止、タイムスタンプは UTC 固定
- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）および Settings オブジェクト経由で環境変数アクセス

セットアップ
----------
前提:
- Python 3.9+（ソースは型ヒントに | を使っているため 3.10 推奨）
- system に応じた pip / virtualenv を利用

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（最小）
   - pip install duckdb openai defusedxml

   実運用では他に urllib / defusedxml 等が必要です。プロジェクトに requirements.txt がある場合はそちらを利用してください。

3. ソースをインストール（開発モード）
   - pip install -e .

4. 環境変数を用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env または .env.local を配置すると自動で読み込まれます（起動時）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client が使用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が使用）
- SLACK_BOT_TOKEN: Slack 通知用（必要に応じて）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必要時）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用DB）パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視設定）

基本的な使い方（例）
------------------

設定取得:
- from kabusys.config import settings
- settings.jquants_refresh_token, settings.duckdb_path, settings.env などでアクセス

DuckDB 接続:
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))

ETL（日次）実行:
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=some_date)  # target_date を省略すると today を用いる
- result は ETLResult オブジェクト（取得数・保存数・品質問題・エラー情報 を保持）

ニューススコアリング（OpenAI）:
- from kabusys.ai.news_nlp import score_news
- n = score_news(conn, target_date=some_date, api_key="sk-...")  # api_key を省略すると環境変数 OPENAI_API_KEY を使用

市場レジーム判定:
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=some_date, api_key=None)

監査スキーマ初期化:
- from kabusys.data.audit import init_audit_db, init_audit_schema
- audit_conn = init_audit_db(settings.duckdb_path)  # 監査用 DB を作成・初期化
- もしくは既存 conn に対して init_audit_schema(conn)

J-Quants からのデータ取得（直接呼び出し）:
- from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
- records = fetch_daily_quotes(date_from=..., date_to=...)

注意事項 / 設計上のポイント
-------------------------
- ルックアヘッドバイアス防止:
  - 多くの処理（news window 計算、regime/score/news）は内部で datetime.today() や date.today() を使わない設計（target_date を明示的に渡すことを想定）
- 冪等性:
  - ETL / 保存関数は ON CONFLICT DO UPDATE など冪等保存を行う
  - audit の order_request_id は冪等キーとして二重発注防止を支援
- 外部API呼び出し:
  - J-Quants クライアントはレートリミット（120 req/min）を守る RateLimiter とリトライ・トークン自動更新を実装
  - OpenAI 呼び出しは JSON Mode を利用し、429/接続障害/5xx などをリトライ（バックオフ）
- セキュリティ:
  - news_collector は SSRF 対策（ホスト検査・リダイレクト検査）、最大レスポンスサイズ制限、XML パースに defusedxml を使用

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/設定管理（Settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースの LLM ベースセンチメント（score_news）
    - regime_detector.py          — マクロ + MA200 を合成した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（fetch_*/save_*）
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - etl.py                      — ETLResult の再エクスポート
    - calendar_management.py      — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py           — RSS 取得・前処理・保存
    - stats.py                    — zscore_normalize 等の統計ユーティリティ
    - quality.py                  — データ品質チェック（check_missing_data 等）
    - audit.py                    — 監査スキーマ定義と初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py          — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py      — calc_forward_returns / calc_ic / factor_summary / rank
  - research/... (その他ユーティリティ)

貢献 / 開発
-----------
- バグ修正・機能追加は Pull Request を受け付けます。コードはユニットテストと静的解析（型チェック）を推奨します。
- テストを実行する際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動的な .env ロードを無効化できます。

よくある操作例（要約）
---------------------
- ETL を手動で実行してデータを duckdb に貯める
  - settings を整え、conn を作成後 run_daily_etl(conn)
- 新聞記事の NLP スコアを算出
  - score_news(conn, target_date)
- 市場レジーム（bull/neutral/bear）を判定して保存
  - score_regime(conn, target_date)

参考: よく使う API 関数
- kabusys.config.settings
- kabusys.data.pipeline.run_daily_etl
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
- kabusys.ai.news_nlp.score_news
- kabusys.ai.regime_detector.score_regime
- kabusys.data.audit.init_audit_db / init_audit_schema

ライセンス
---------
- 本ドキュメントではライセンス情報を含んでいません。実際のプロジェクトでは LICENSE ファイルをご確認ください。

補足
----
この README はコードベースから抽出した主な機能と使い方の要約です。個々の関数やモジュールにより細かな引数や動作が異なりますので、実装ファイル内の docstring を参照して詳しい挙動を確認してください。