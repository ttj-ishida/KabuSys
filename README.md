KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のプロトタイプ的ライブラリです。  
主に以下を提供します。

- J-Quants からのデータ ETL（株価日足、財務、JPX カレンダー）
- ニュースの収集と LLM による銘柄別センチメント計算（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメント合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）および統計ユーティリティ
- データ品質チェック、マーケットカレンダー管理
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化ユーティリティ

軽量な DuckDB を主要データストアとして使用し、バックテスト／研究用のデータ管理と実運用に近い監査・ETL の仕組みを備えます。

主な機能一覧
-------------
- data.jquants_client: J-Quants API クライアント（取得・保存・ページネーション・リトライ・レート制御）
- data.pipeline: 日次 ETL パイプライン（calendar / prices / financials の差分取得、品質チェック）
- data.news_collector: RSS からのニュース収集（SSRF対策・トラッキング除去・正規化）
- ai.news_nlp.score_news: OpenAI を用いた銘柄別ニュースセンチメント集計・ai_scores への書込み
- ai.regime_detector.score_regime: ETF（1321）MA とマクロニュース LLM を合成した市場レジーム判定
- research.factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
- data.quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
- data.audit: 監査ログ用テーブル定義・初期化ユーティリティ
- config: .env 自動読み込み（プロジェクトルート検出）と設定アクセスラッパー

セットアップ手順
----------------

1. リポジトリをクローン（もしくはプロジェクトソースを入手）
   - 例: git clone <repo-url>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 本リポジトリ内に requirements.txt がある想定で:
     - pip install -r requirements.txt
   - または最低限（推奨バージョンは利用環境に合わせて指定してください）:
     - pip install duckdb openai defusedxml

   ※標準ライブラリも多く使われていますが、OpenAI SDK / duckdb / defusedxml は必須です。

4. 環境変数設定 (.env)
   - プロジェクトルート（pyproject.toml もしくは .git があるディレクトリ）に `.env` を配置すると自動で読み込まれます。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env の例:
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-xxxxx
    KABU_API_PASSWORD=your_kabu_password
    KABU_API_BASE_URL=http://localhost:18080/kabusapi
    LINE_CHANNEL_ACCESS_TOKEN=
    LINE_USER_ID=
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    PID_FILE_PATH=data/execution.pid
    KILL_FLAG_PATH=data/kill.flag
    KILL_FLAG_CLEAR_ON_START=1
    CPU_THRESHOLD_PCT=90.0
    MEMORY_THRESHOLD_PCT=85.0
    DISK_THRESHOLD_PCT=90.0
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

5. データディレクトリの作成（必要に応じて）
   - デフォルトの DuckDB パスは data/kabusys.duckdb です。ディレクトリを事前に作成しておくと良いです。
   - mkdir -p data

使い方（基本例）
---------------

以下は主要ユースケースの最小例です。各関数は duckdb の接続オブジェクトを受け取ります。

- DuckDB 接続を作成して日次 ETL を実行する
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- OpenAI を使ってニューススコアを計算して ai_scores に書き込む
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    # OPENAI_API_KEY は環境変数 か api_key 引数で指定
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込んだ銘柄数: {n_written}")

- 市場レジーム判定（regime_score を market_regime テーブルへ書き込む）
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DuckDB を初期化する
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # これで signal_events / order_requests / executions テーブルが作成されます

- 研究用ファクター計算の例
    from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum

    conn = duckdb.connect("data/kabusys.duckdb")
    momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
    print(len(momentum), "銘柄のモメンタム計算結果を取得")

設定と環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須: ETL 実行時）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（実行管理用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: メイン DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視等に用いる SQLite パス
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視用設定
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 環境 (development / paper_trading / live)
- LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

主な注意点・設計方針
-------------------
- ルックアヘッドバイアス防止: 多くの処理は内部で date を明示的に渡し、datetime.today() の直接参照を避ける設計です。
- 冪等性: ETL の保存処理は ON CONFLICT で上書きするため、再実行が可能です。
- フェイルセーフ: LLM 呼び出しや API エラー時はシステムが継続できるようにフォールバック（例: macro_sentiment = 0）します。
- セキュリティ: news_collector は SSRF や XML Bomb を考慮して実装されています（defusedxml、ホスト/リダイレクト検査など）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                : パッケージのエントリ（version 等）
- config.py                  : 環境変数/.env 読み込みと Settings ラッパー
- ai/
  - __init__.py
  - news_nlp.py              : ニュースを LLM でスコアリング
  - regime_detector.py       : 市場レジーム判定ロジック
- data/
  - __init__.py
  - jquants_client.py        : J-Quants API クライアント（取得＋DuckDB 保存）
  - pipeline.py              : ETL パイプライン（run_daily_etl 等）
  - etl.py                   : ETLResult の再エクスポート
  - news_collector.py        : RSS 収集と前処理
  - calendar_management.py   : マーケットカレンダー管理・判定ユーティリティ
  - quality.py               : データ品質チェック
  - stats.py                 : Zスコア等の統計ユーティリティ
  - audit.py                 : 監査ログ（DDL/初期化）
- research/
  - __init__.py
  - factor_research.py       : モメンタム/バリュー/ボラティリティ等
  - feature_exploration.py   : 将来リターン・IC・統計サマリー等

ヘルプ / 開発メモ
-----------------
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OpenAI 呼び出し部はテスト容易性を考慮して内部関数を差し替え可能にしてあります（unittest.mock.patch を利用）。
- DuckDB の executemany に空リストを渡すと問題となるバージョンがあります（注意: 保存処理で空チェックを行っている箇所があります）。

貢献・ライセンス
----------------
リポジトリ内の CONTRIBUTING.md / LICENSE を参照してください（存在する場合）。

問い合わせ
--------
不明点や実装上の質問があれば、リポジトリの Issue を立ててください。