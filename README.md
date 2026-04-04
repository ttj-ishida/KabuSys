KabuSys — 日本株自動売買／データ基盤ライブラリ
================================

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買支援ライブラリです。  
主に以下を提供します。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI を使ったニュースセンチメント分析（銘柄別 ai_score）およびマクロセンチメントとETF MA乖離を組合せた市場レジーム判定
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- リサーチ用ファクター計算（モメンタム／バリュー／ボラティリティ等）と統計ユーティリティ
- 取引監査ログ（signal → order_request → executions）のスキーマ定義と初期化ユーティリティ
- 環境変数（.env）を基にした設定管理

主な機能一覧
-------------
- ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・保存・品質チェック）
  - ETL 結果を表す ETLResult クラス
- J-Quants API クライアント:
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
  - トークン自動リフレッシュ、レートリミット、リトライ実装
- ニュース収集:
  - fetch_rss、記事正規化、記事ID生成（SHA-256）、raw_news への冪等保存想定
  - SSRF 対策／受信サイズ制限／XML パース堅牢化
- AI（OpenAI）:
  - score_news（銘柄ごとのニュースセンチメントを ai_scores へ保存）
  - score_regime（ETF 1321 の MA 乖離とマクロニュースセンチメントを合成して market_regime を更新）
  - 再試行・バックオフ・レスポンス検証を備えた実装
- データ品質:
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - QualityIssue 型で問題を集約
- リサーチ:
  - calc_momentum / calc_value / calc_volatility（prices_daily / raw_financials ベース）
  - calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- カレンダー:
  - market_calendar 管理関数（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - calendar_update_job（J-Quants から差分取得して保存）
- 監査ログ:
  - init_audit_schema / init_audit_db（監査用テーブル群を冪等に作成）

必須環境変数（代表）
--------------------
プロジェクトでは .env または環境変数から設定を読み込みます（自動で .env → .env.local を読みます）。
必須／重要なキー例:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須、ETL 用）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注等を行う場合）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）

自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

セットアップ手順
----------------
推奨: Python 3.10 以上（typing の | 記法 を利用）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （開発時）pip install -e .
   - ※requirements.txt があれば pip install -r requirements.txt を使用
4. 環境変数を準備
   - プロジェクトルートに .env を作成（下に例を記載）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD を使う場合は適宜設定

.example .env（最低限）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-xxxxx
- KABU_API_PASSWORD=your_kabu_password
- DUCKDB_PATH=./data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

使い方（サンプル）
------------------

- DuckDB 接続を作る（設定を利用）
  - from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニューススコアリング（OpenAI 必須）
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print("書込み銘柄数:", n_written)

  - api_key を直接渡すことも可能:
    score_news(conn, target_date=date(2026,3,20), api_key="sk-...")

- 市場レジーム判定
  - from datetime import date
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026,3,20))  # OpenAI キーは環境変数または引数で

- 監査 DB 初期化（監査専用 DB）
  - from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")
    # 必要に応じて conn_audit をアプリで保持

- RSS フェッチ（ニュース収集の一部）
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
    articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
    for a in articles:
        print(a["id"], a["datetime"], a["title"])

注意点 / 実運用上のヒント
------------------------
- OpenAI 呼び出しは API 料金が発生します。テスト時はモックして実行してください（モジュール内の _call_openai_api はテスト用に差し替え可能）。
- J-Quants API はレート制限とトークンの管理が必要です。設定ファイルにトークンを保管し、get_id_token 経由で取得します。
- DuckDB への保存は ON CONFLICT DO UPDATE を用いた冪等設計になっていますが、ETL の実行順やトランザクションには注意してください。
- look-ahead bias を避ける実装方針が多くの関数に組み込まれています（内部で date.today() を参照しない、DB のデータは target_date 未満／以前など）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                        - 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                     - ニュースセンチメント（ai_scores）
  - regime_detector.py              - 市場レジーム判定（ma200 + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py               - J-Quants API クライアント & DuckDB 保存
  - pipeline.py                     - ETL パイプライン（run_daily_etl など）
  - etl.py                          - ETL の公開型再エクスポート (ETLResult)
  - calendar_management.py          - 市場カレンダー管理
  - news_collector.py               - RSS → raw_news
  - quality.py                      - データ品質チェック
  - stats.py                        - 汎用統計ユーティリティ（zscore_normalize）
  - audit.py                        - 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py              - ファクター計算（momentum/value/volatility）
  - feature_exploration.py          - 将来リターン / IC / 統計要約

ライセンス・連絡
----------------
この README ではライセンス記載がありません。利用・配布に関してはリポジトリ側の LICENSE を参照してください。質問や改善提案はリポジトリの Issue または担当者へお知らせください。

付録: テスト用の環境変数の無効化
------------------------------
- テストで .env の自動ロードを無効にする:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

以上です。必要であれば README に含める具体的な .env.example、requirements.txt の候補、またはサンプルスクリプト（cron 用 wrapper など）を追記します。どの情報を追加しますか？