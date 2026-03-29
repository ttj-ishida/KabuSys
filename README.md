# KabuSys — 日本株自動売買基盤 (README)

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買基盤のコアライブラリです。  
主に以下を提供します。

- J-Quants からのデータ取得 / ETL パイプライン（株価、財務、マーケットカレンダー）
- ニュース収集と LLM によるニュースセンチメント（銘柄別 ai_score）
- 市場レジーム判定（MA と マクロニュースの混合スコア）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック、マーケットカレンダー管理
- 監査ログ（信号→発注→約定のトレーサビリティ）スキーマ初期化ユーティリティ

主な機能一覧
-------------
- ETL
  - run_daily_etl: 市場カレンダー・株価日足・財務データの差分取得と品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別ジョブ
  - jquants_client: J-Quants API 呼び出し（自動リフレッシュ、レート制御、リトライ、保存）
- ニュース処理 / AI
  - news_collector.fetch_rss: RSS からニュース取得・前処理
  - ai.news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に保存
  - ai.regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースを合成して market_regime を書込
- 研究（Research）
  - calc_momentum / calc_value / calc_volatility：ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank：特徴量探索・統計
- データ管理
  - data.calendar_management: 営業日判定・next/prev_trading_day 等
  - data.pipeline: ETLResult 等の ETL インターフェース
  - data.quality: 欠損・スパイク・重複・日付不整合チェック
  - data.audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - data.jquants_client: J-Quants API クライアント（fetch / save 系）

セットアップ手順
----------------

前提
- Python 3.10+（typing の union と型注釈が利用されているため）
- DuckDB が必要（pip で duckdb をインストール）

1. リポジトリをクローン / パッケージをインストール
   - 開発中: ソースを編集しながら使う場合
     - pip install -e . もしくは pip install -r requirements.txt
   - 依存パッケージ（例）
     - duckdb
     - openai
     - defusedxml
     - これらはプロジェクトの requirements に合わせてインストールしてください。

2. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテスト等で使用）。
   - 必須の環境変数（settings から参照）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知に使用（必須）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネルID（必須）
   - 任意（デフォルトあり）
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — sqlite（monitoring 用）パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV — 環境 (development / paper_trading / live)。デフォルト development
     - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト INFO
   - OpenAI（LLM）用
     - OPENAI_API_KEY を環境変数で渡すか、AI 関数の api_key 引数で明示的に渡します。

3. データベース初期化（監査ログなど）
   - 監査ログ専用 DB を初期化する例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - 既存の DuckDB 接続にスキーマだけ追加する場合:
     - from kabusys.data.audit import init_audit_schema
     - init_audit_schema(conn, transactional=True)

使い方（簡単な例）
-----------------

共通: DuckDB 接続を取得して各関数に渡す
- 例: settings の duckdb_path を使う
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL の実行
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=some_date, id_token=None)
- ETLResult に取得/保存件数や品質チェック結果が含まれます

2) ニュースセンチメントの計算（LLM 必須）
- from kabusys.ai.news_nlp import score_news
- written = score_news(conn, target_date=some_date, api_key="sk-...")  # api_key を渡すか OPENAI_API_KEY を設定
- ai_scores テーブルに書き込まれ、戻り値は書き込んだ銘柄数

3) 市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=some_date, api_key="sk-...")  # market_regime テーブルに書込

4) 監査ログ（スキーマ初期化）
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db("data/audit.duckdb")  # テーブル群が作成されます

5) 研究用ユーティリティ
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- momentum = calc_momentum(conn, target_date=some_date)

6) ニュース RSS 取得（ニュースコレクタを単体利用）
- from kabusys.data.news_collector import fetch_rss
- articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
- 返り値は NewsArticle 型（id, datetime, source, title, content, url）

重要な設計・運用上の注意
-----------------------
- Look-ahead バイアス対策:
  - モジュール内の多くの関数は datetime.today() や date.today() を直接参照しません。target_date を明示して処理する設計です。バッチやバックテストでは target_date を必ず明示してください。
- 環境変数の自動ロード:
  - .env / .env.local はプロジェクトルートを起点に自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- OpenAI 呼び出し:
  - API の失敗時は多くの箇所でフェイルセーフ（0.0 にフォールバック、あるいは空スコア）する設計です。LLM を使う機能は api_key を引数で注入でき、ユニットテストでは内部呼び出しをモックできます。
- J-Quants API:
  - 内部でレートリミッタ・リトライを実装しています。401 の場合は自動的に refresh token で再取得を試みます。
- DuckDB の executemany:
  - DuckDB のバージョン差に配慮した実装（空パラメータでの executemany を回避）になっています。

ディレクトリ構成（主なファイル）
------------------------------

- src/kabusys/
  - __init__.py  （パッケージ定義、バージョン）
  - config.py    （環境変数・設定管理：settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py         （ニュースセンチメント -> ai_scores）
    - regime_detector.py  （市場レジーム判定 -> market_regime）
  - data/
    - __init__.py
    - calendar_management.py  （市場カレンダー / 営業日判定）
    - pipeline.py             （ETL パイプライン / run_daily_etl 等）
    - etl.py                  （ETLResult 再エクスポート）
    - stats.py                （統計ユーティリティ zscore_normalize）
    - quality.py              （データ品質チェック）
    - audit.py                （監査ログスキーマ初期化）
    - jquants_client.py       （J-Quants API クライアント / fetch/save）
    - news_collector.py       （RSS 取得・前処理）
  - research/
    - __init__.py
    - factor_research.py      （モメンタム・バリュー・ボラティリティ）
    - feature_exploration.py  （forward returns, IC, summary, rank）
  - research/*.py             （研究用ユーティリティ）

ライセンス・貢献
----------------
- この README はコードベースに基づく概要説明です。実運用で使用する際は各種 API キーの管理、ログ出力、監視・リトライ設定、テストを十分に行ってください。
- パッチや改善提案は Pull Request を歓迎します。README の更新も随時反映してください。

補足（トラブルシューティング）
-----------------------------
- .env が読み込まれない／テストで環境を固定したい
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数で設定して自動ロードを無効化してください。
- OpenAI の JSON レスポンスのパースで失敗する場合
  - モデルの挙動や応答が仕様と異なるとパースに失敗します。score_news / score_regime は失敗時にフォールバックする設計ですが、ログに WARN/ERROR が出るため内容を確認してください。
- DuckDB で executemany が空リストだと例外になる
  - パラメータが空のケースはコード側でチェックして呼び出しを省くよう実装されていますが、独自コードで呼ぶ際は注意してください。

以上。必要であれば使用例やセットアップの自動化（docker-compose、systemd タイマー、cron での ETL 実行例など）の追加ドキュメントも作成できます。どの項目を詳しく書いてほしいか教えてください。