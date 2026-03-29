KabuSys — 日本株自動売買プラットフォーム（README）
======================================

概要
----
KabuSys は日本株向けのデータパイプライン、リサーチ（ファクター計算）、ニュース NLP（LLM を用いたセンチメント評価）、市場レジーム判定、監査ログ機能などを備えた自動売買／リサーチ基盤用ライブラリ群です。  
主に以下を目的としています。

- J-Quants API からのデータ ETL（株価・財務・市場カレンダー）
- ニュース収集と LLM によるセンチメント評価（銘柄別スコア）
- 市場レジーム判定（テクニカル指標 + マクロニュースの統合）
- ファクター計算、特徴量探索（研究用途）
- 監査ログ用 DuckDB スキーマ（シグナル→発注→約定のトレース）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

主な機能一覧
--------------
- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（日次株価、財務、カレンダー、上場情報）
  - ニュース収集: RSS 取得、正規化、raw_news への保存ロジック
  - カレンダー管理: 営業日判定、next/prev_trading_day、calendar_update_job
  - 品質チェック: 欠損、重複、スパイク、日付不整合（run_all_checks）
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 汎用統計: zscore_normalize
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI に問い合わせて ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースの LLM 評価を合成して market_regime に保存
- research
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 特徴量解析: calc_forward_returns, calc_ic, factor_summary, rank

前提 / 必要環境
----------------
- Python 3.10+
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / 各 RSS ソース）を行うため適切な API キーおよび接続環境

インストール
------------
ローカルで開発／利用する場合の一例:
1. 仮想環境を作成・有効化（任意）
2. パッケージをインストール
   - pip install -e .   （ソース配布がセットアップ済みの場合）
3. 依存パッケージを個別にインストール:
   - pip install duckdb openai defusedxml

環境変数（.env）の設定
-----------------------
config.Settings が環境変数を参照します。プロジェクトルートに .env/.env.local を置くと自動読み込みされます（CWD ではなくパッケージファイル位置から .git または pyproject.toml を探索してプロジェクトルートを特定します）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: データ用 DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（いずれか）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector で利用）

基本セットアップ手順
--------------------
1. .env を作成（.env.example を参考に必要なキーを設定）
2. データディレクトリを準備（例: mkdir -p data）
3. 監査用 DB を初期化（任意）
   - Python 例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
4. DuckDB に接続してスキーマを整備（別途 schema 初期化関数があれば呼ぶ）
   - import duckdb
     from kabusys.config import settings
     conn = duckdb.connect(str(settings.duckdb_path))
     # 必要なテーブルを作成するユーティリティがあればここで実行

使い方（代表的な呼び出し例）
---------------------------

- 日次 ETL を実行する
  - 目的: 株価・財務・カレンダーを差分取得して保存、品質チェックまで実行
  - 例:
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

- ニュースセンチメントを算出して ai_scores に保存
  - 例:
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect(str(settings.duckdb_path))
    count = score_news(conn, target_date=date(2026,3,20))
    print(f"scored {count} codes")

  - 注意: OPENAI_API_KEY が環境変数に設定されているか、api_key 引数を渡してください。

- 市場レジーム判定を実行
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))

- 監査 DB の初期化（独立 DB を作る）
  - 例:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn を使って監査テーブルにアクセス・INSERT など

- J-Quants API の直接利用（低レベル）
  - 例:
    from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
    token = get_id_token()
    data = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,20))

運用・開発上の注意点
-------------------
- Look-ahead バイアス回避:
  - 多くの関数（score_news, score_regime, ETL, research）は内部で datetime.today() を参照せず、引数で与えられた target_date を基準に処理します。バックテスト等で意図しない未来情報の利用を防ぎます。
- 自動 .env ロード:
  - パッケージインポート時にプロジェクトルートの .env/.env.local を自動読み込みします。テストや明示的な設定読み込みを行いたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- エラーハンドリング:
  - OpenAI / J-Quants など外部 API 呼び出しはリトライとフォールバックを組み込んでありますが、APIキー未設定などの設定ミスは ValueError を投げます。
- DuckDB executemany の制約に注意:
  - DuckDB のバージョン差異により executemany に空リストを渡せない箇所が考慮されています（該当箇所はコード内に条件ガードあり）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py         — パッケージ初期化、バージョン定義
- config.py           — 環境変数 / 設定管理（.env 自動読み込み、Settings）
- ai/
  - __init__.py
  - news_nlp.py       — ニュースセンチメント（score_news）
  - regime_detector.py— 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save 系）
  - pipeline.py       — ETL パイプライン（run_daily_etl 等）
  - etl.py            — ETLResult の公開
  - news_collector.py — RSS 収集・前処理
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - quality.py        — データ品質チェック（欠損／スパイク／重複／日付）
  - stats.py          — zscore_normalize 等汎用統計
  - audit.py          — 監査ログスキーマ初期化、init_audit_db
- research/
  - __init__.py
  - factor_research.py   — momentum / value / volatility ファクター計算
  - feature_exploration.py — 将来リターン / IC / summary / rank

その他の補足
------------
- OpenAI 呼び出しは openai.OpenAI クライアントを利用しています。API レスポンスのパースやリトライポリシーはモジュール単位で実装されています（テスト時は内部呼び出し関数をモックして差し替え可能）。
- news_collector は SSRF 対策、gzip サイズ上限、防御的 XML 解析（defusedxml）等のセキュリティ考慮を行っています。
- J-Quants クライアントはレートリミット（120 req/min）を守るための固定間隔レートリミッタと、401 の場合のトークン自動リフレッシュ、リトライ（指数バックオフ）を備えています。

ライセンス / コントリビューション
----------------------------------
（この README にライセンス文は含めていません。実際のプロジェクトでは LICENSE ファイルを追加してください。）

お問い合わせ
------------
利用上の質問や改善提案があれば、リポジトリの issue を通じてお願いします。README に記載した設定（特に API キー）や DB パスの取り扱いに注意して利用してください。