KabuSys — 日本株自動売買／データ基盤ライブラリ
================================

概要
----
KabuSys は日本株向けのデータプラットフォームと研究／自動売買に必要なユーティリティ群を集めた Python パッケージです。本コードベースは次を含みます。

- J-Quants API からの株価・財務・カレンダー取得（差分 ETL・保存・品質チェック）
- ニュース収集（RSS）と NLP（OpenAI）による銘柄/マクロのセンチメント算出
- 市場レジーム判定（MA200 と マクロセンチメントの合成）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- DuckDB を用いたローカル DB レイヤ

主な機能
--------
- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（認証・ページネーション・リトライ・レートリミット対応）
  - カレンダー管理（営業日判定 / next/prev_trading_day / calendar_update_job）
  - ニュース収集（RSS の安全取得・前処理・冪等保存）
  - 品質チェック（欠損・重複・スパイク・日付不整合検出）
  - 監査ログテーブルの初期化・ユーティリティ
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news: 複数銘柄のニュースをまとめて LLM に投げるバッチ処理）
  - レジーム判定（score_regime: ETF 1321 の MA200 乖離 + マクロセンチメントの合成）
  - OpenAI 呼び出しはリトライ・タイムアウト等を考慮
- research/
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算・IC・統計サマリー等の探索ユーティリティ

セットアップ手順
----------------

1. Python 環境
   - Python 3.9+ を推奨（typing 機能を利用）
   - 仮想環境を作成してアクティブ化することを推奨

2. 依存パッケージをインストール
   - 必要な最低依存（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらからインストールしてください）

3. 環境変数設定（.env）
   - プロジェクトルート（.git または pyproject.toml を基準）に .env を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。
   - 最低限設定が必要なキー（例）:

     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=your_slack_bot_token
     - SLACK_CHANNEL_ID=your_slack_channel_id
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development      # development | paper_trading | live
     - LOG_LEVEL=INFO               # DEBUG | INFO | WARNING | ERROR | CRITICAL

   - .env の読み込みは kabusys.config モジュールが行います。自動ロードが働き、OS 環境変数を優先します。

使い方（代表例）
----------------

以下は基本的な利用例（Python スクリプト内での呼び出し）です。各関数は DuckDB 接続（duckdb.connect）を直接受け取ります。

1. DuckDB 接続を作る（デフォルトファイルは settings.duckdb_path）
   - 例:
     from kabusys.config import settings
     import duckdb
     conn = duckdb.connect(str(settings.duckdb_path))

2. 日次 ETL を実行する
   - run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェック を順に実行します。
     from kabusys.data.pipeline import run_daily_etl
     from datetime import date
     result = run_daily_etl(conn, target_date=date(2026, 3, 20))
     print(result.to_dict())

3. ニュースセンチメントを算出して ai_scores に保存する
   - ai.score_news は raw_news / news_symbols / ai_scores テーブルを参照します。
     from kabusys.ai.news_nlp import score_news
     from datetime import date
     n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用

4. 市場レジーム判定を実行する
   - ETF 1321（Nikkei 連動 ETF）の MA200 乖離とマクロセンチメントを合成して market_regime に書き込みます。
     from kabusys.ai.regime_detector import score_regime
     from datetime import date
     score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

5. 監査ログ DB の初期化
   - 監査ログ専用の DuckDB を初期化するユーティリティがあります。
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")
     # または既存 conn に対しスキーマを初期化:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)

6. カレンダー更新ジョブ
   - calendar_update_job は J-Quants からカレンダーデータを差分取得して market_calendar に保存します。
     from kabusys.data.calendar_management import calendar_update_job
     calendar_update_job(conn)

注意点 / 設計上のポリシー
-----------------------
- ルックアヘッドバイアス防止
  - 多くの関数は内部で datetime.today() / date.today() を直接参照しない（引数で基準日を与える）。バックテスト等での誤使用を防ぐ設計です。
- 冪等性
  - ETL の保存関数は ON CONFLICT DO UPDATE の形で保存し、同一主キーの再投入を安全に扱います。
- フェイルセーフ
  - AI 呼び出しや外部 API 呼び出しで失敗した場合、重大な例外を全体に投げずフォールバック（0.0 等）で継続する箇所があります。ログを確認してください。
- セキュリティ
  - RSS 取得処理には SSRF 対策（リダイレクト検査 / プライベートアドレス拒否）・XML パースは defusedxml を利用。
  - API トークン等は .env や環境変数で安全に管理してください。

サンプル .env.example
---------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

ディレクトリ構成（抜粋）
-----------------------
- src/kabusys/
  - __init__.py                # パッケージ初期化（__version__ 等）
  - config.py                  # 環境変数読み込み・設定ラッパ
  - ai/
    - __init__.py
    - news_nlp.py              # ニュース NLP / score_news
    - regime_detector.py       # 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント + 保存関数
    - pipeline.py              # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   # 市場カレンダー管理
    - news_collector.py        # RSS 収集・前処理
    - quality.py               # データ品質チェック
    - stats.py                 # zscore_normalize 等
    - audit.py                 # 監査ログスキーマ定義・初期化
    - etl.py                   # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py       # calc_momentum, calc_value, calc_volatility
    - feature_exploration.py   # calc_forward_returns, calc_ic, factor_summary, rank

開発・テスト
-------------
- 自動 .env ロードを無効化したいときは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテスト時に便利）。
- OpenAI 呼び出しや HTTP 呼び出しはモックしやすいように関数を分離しており、ユニットテスト向けに差し替え可能です（モジュール内の _call_openai_api 等を patch）。

ライセンス・貢献
----------------
- 本 README にはライセンス情報は含まれていません。実際のプロジェクトでは LICENSE ファイルを置いてください。
- 貢献時はコードのスタイル、一貫したロギング、エラー処理方針に従ってください。

お問い合わせ
------------
- 実装や利用上の質問があれば、リポジトリの Issue に記載してください。README に含めるべき補足があれば PR も歓迎します。

----- 

必要であれば、以下を追加で作成できます:
- インストール用 requirements.txt / pyproject.toml のテンプレート
- CLI 用の簡易コマンド例（etl run / ai score_news / ai score_regime 等）
- .env.example ファイルの完全テンプレート

どれを用意しましょうか？