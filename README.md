KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買基盤を想定した Python パッケージです。  
主に以下を提供します。

- J-Quants からのデータ ETL（株価日足、財務、JPX カレンダーなど）
- ニュースの収集・NLP（OpenAI を使ったセンチメント評価）と銘柄ごとの AI スコア格納
- 市場レジーム判定（ETF + マクロニュース → レジームスコア）
- データ品質チェック、マーケットカレンダー管理
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 研究用ユーティリティ（ファクター計算・特徴量探索・統計ユーティリティ）

本リポジトリはライブラリ／モジュール群で構成され、ETL バッチや監査 DB 初期化、AI スコアリングなどをプログラムから呼び出して利用します。

主な機能一覧
-------------
- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save / 認証・リトライ・レートリミット実装）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS → raw_news、URL 正規化、SSRF 対策、XML 安全パーサ）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - score_news: ニュースの銘柄別センチメントを OpenAI に送って ai_scores に書き込む
  - score_regime: ETF（1321）の MA 乖離 + マクロニュースセンチメントから市場レジームを判定して market_regime に書き込む
  - 各種 OpenAI 呼び出しはリトライとフェイルセーフ実装あり（失敗時は 0.0 等で継続）
- research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算・IC（情報係数）・統計サマリ（feature_exploration）
- config
  - 環境変数読み込み（.env / .env.local の自動ロード）と Settings オブジェクト

セットアップ手順
----------------

前提
- Python 3.10 以上（型注釈で X | Y 構文を使用）
- ネットワーク接続（J-Quants / OpenAI 利用時）

1. リポジトリをクローンしてインストール（開発モード推奨）
   - 例:
     - git clone <repo>
     - cd <repo>
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -e .  # setup がある場合

2. 依存パッケージ（代表例）
   - duckdb
   - openai
   - defusedxml
   - これらは setup.py / pyproject.toml に記載されている想定です。手動で入れる場合:
     - pip install duckdb openai defusedxml

3. 環境変数設定（.env）
   - プロジェクトルートに .env（または .env.local）を置くことで自動で読み込まれます（config モジュールが自動ロード）。
   - 主要なキー（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_api_password
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
     - SLACK_BOT_TOKEN=your_slack_bot_token
     - SLACK_CHANNEL_ID=your_slack_channel_id
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - 注意:
     - 自動読み込みを無効にする場合は環境で KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

使い方（例）
------------

基本的に Python から各関数を呼び出して使います。以下に代表的な利用例を示します。

1) DuckDB 接続を作って ETL を実行する
- 例:
  - from datetime import date
  - import duckdb
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect("data/kabusys.duckdb")
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

2) ニュースの AI スコア化（score_news）
- 例:
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う

3) 市場レジーム判定（score_regime）
- 例:
  - from datetime import date
  - import duckdb
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, target_date=date(2026,3,20), api_key=None)

4) 監査データベース初期化
- 例:
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")  # 必要なら ":memory:" でインメモリ

5) 市場カレンダーの判定ユーティリティ
- 例:
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
  - import duckdb, datetime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - is_trading_day(conn, datetime.date(2026,3,20))

使う時の注意点
- OpenAI / J-Quants を使用する関数は API キー（環境変数または引数）を必要とします。キー未設定時は ValueError を raise します。
- OpenAI 呼び出しはリトライとフェイルセーフ（失敗時は 0.0 で継続）を実装していますが、API レートやコストは利用者の責任です。
- ETL・DB 書き込みは冪等を考慮して実装されています（ON CONFLICT 等）。

テスト用フック
- OpenAI 呼び出しや URL オープン処理は内部関数を patch してモックできるように設計されています（例: unittest.mock.patch で kabusys.ai.news_nlp._call_openai_api や kabusys.data.news_collector._urlopen を差し替え）。

ディレクトリ構成（主要ファイル）
--------------------------------

以下はコードベースの主要モジュール一覧（src/kabusys 以下）です。実際のリポジトリではさらにファイルがある可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py             # ニュース NLP（score_news）
    - regime_detector.py      # マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（fetch / save / auth）
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  # マーケットカレンダー管理
    - news_collector.py       # RSS ニュース収集
    - quality.py              # データ品質チェック
    - stats.py                # 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                # 監査ログスキーマ初期化
    - etl.py                  # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      # ファクター計算（momentum / value / volatility）
    - feature_exploration.py  # 将来リターン / IC / rank / summary

設定（.env）の自動読み込み
-------------------------
- config.py はプロジェクトルート（.git または pyproject.toml を探索）から .env を自動的に読み込みます。
  - 読み込み優先順: OS 環境変数 > .env.local > .env
  - テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings クラス経由で設定値にアクセスできます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

運用上の注意
------------
- KABUSYS_ENV（development / paper_trading / live）で挙動判定が行われます。live 環境では発注実装と組み合わせる際に慎重に扱ってください（本コードベース内の発注実装は含まれていない／別モジュール想定）。
- ETL は外部 API（J-Quants）への依存があるため、レート制限・認証トークン管理に注意してください。jquants_client はリトライ・レート制限・401 リフレッシュを実装しています。
- RSS の取得・パースは SSRF 対策・DefusedXML・レスポンスサイズ制限等を盛り込んでいますが、運用時はニュースソース一覧や User-Agent ポリシーを確認してください。

開発・貢献
----------
- 開発時は仮想環境を使い、依存パッケージを明示的にインストールしてください。
- ユニットテストでは外部 API 呼び出しをモックして実行してください（例: openai クライアント、urllib の _urlopen、jquants_client._request など）。
- 自動環境読み込みはテストの副作用となるため、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用するか一時的に環境を隔離してください。

問い合わせ
----------
- 本 README に不足がある場合は、具体的にどの機能の使い方や API 定義が必要かを教えてください。コード内の関数／クラスに基づいて、より詳細な使用例や CLI ラッパーの案内を作成します。