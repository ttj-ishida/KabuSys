# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株のデータパイプライン、AI によるニュースセンチメント評価、ファクター計算、監査ログ管理などを含む自動売買システムのコアライブラリ群です。本リポジトリはライブラリとして各コンポーネントを提供し、ETL / 研究 / AI / 監査 / カレンダー管理 等をモジュール化しています。

注意: 本 README はコードベースのソースから自動的に抜粋・要約しています。実運用では API キーや発注機能の取り扱いに十分注意してください（本コードは発注モジュールを含みますが、実運用前に充分なレビューを行ってください）。

目次
- プロジェクト概要
- 主な機能一覧
- 動作要件（依存）
- セットアップ手順
- 環境変数（設定）
- 使い方（クイックスタート / API 例）
- ディレクトリ構成
- 開発メモ・設計上の注意点

プロジェクト概要
----------------
KabuSys は次の主要機能を提供する Python パッケージです。
- J-Quants API と連携した ETL（株価・財務・市場カレンダー取得）と品質チェック
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄単位 / マクロ）
- 市場レジーム判定（ETF の MA とマクロセンチメント合成）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量探索ユーティリティ
- 監査ログ（signal / order_request / executions）用の DuckDB 初期化と管理
- マーケットカレンダー管理（営業日判定 / next/prev_trading_day 等）

主な機能一覧
-------------
- data.jquants_client: J-Quants API からの取得・DuckDB への保存（差分取得・ページネーション・リトライ・レートリミット対応）
- data.pipeline: 日次 ETL（run_daily_etl）と個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- data.quality: ETL 後の品質チェック（欠損・スパイク・重複・日付不整合）
- data.news_collector: RSS 収集、テキスト前処理、記事ID生成（冪等）・SSRF/サイズ制限対策
- data.calendar_management: market_calendar を用いた営業日判定ユーティリティ
- data.audit: 監査ログテーブル（signal_events, order_requests, executions）の初期化 / init_audit_db
- research.*: ファクター計算（calc_momentum / calc_volatility / calc_value）、特徴量解析（forward returns / IC / summary）
- ai.news_nlp / ai.regime_detector: OpenAI を用いたニュースセンチメントと市場レジーム判定
- config: .env 自動ロード、環境設定ラッパ（settings）で主要キーを取得

動作要件（依存）
----------------
主な依存ライブラリ（例）
- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （標準ライブラリのみで実装されている箇所も多いです）

実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。最低限上のパッケージをインストールしておくと各機能が使えます。

セットアップ手順
----------------
1. リポジトリをクローンして開発環境を作成
   - 例:
     - git clone <repo>
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージをインストール
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements ファイルがあればそれを利用してください）
   - pip install -e .

3. 環境変数の設定
   - ルートに .env を作成することで自動的に値が読み込まれます（パーソナル設定は .env.local を使用可）。
   - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用途）。
   - 詳細は「環境変数」セクション参照。

4. DuckDB 用ディレクトリが必要なら作成（デフォルト data ディレクトリ）
   - settings.duckdb_path の親ディレクトリを作成する（通常は data/）

環境変数（設定）
----------------
以下は code 内 Settings クラスで参照される主要変数です（必須は _require を通してチェックされます）:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注周りで使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API 呼び出しに使用（score_news / score_regime のデフォルト）

任意（デフォルト値あり）:
- KABUSYS_ENV: 開発環境 (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）。デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（1 等真値で無効）
- KABUSYS の DB パス:
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視用 sqlite データベースのパス（data/monitoring.db）

.env のパースは標準的な KEY=VALUE に加え、export KEY=VALUE、シングル／ダブルクォートやインラインコメント処理等に対応しています。

使い方（クイックスタート）
------------------------

1) DuckDB 接続を作り ETL を実行する（Python REPL / スクリプト）
- 日次 ETL の実行例:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(<path to duckdb file>))  # 例: settings.duckdb_path
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

  - run_daily_etl はカレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック を順に実行し ETLResult を返します。
  - 内部で J-Quants API を呼びます。API トークンは settings.jquants_refresh_token 経由で取得されます。

2) ニュースセンチメント評価（AI）
- 銘柄別ニューススコアを作成（score_news）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-xxxx")
  print(f"書き込み銘柄数: {n_written}")

  - OpenAI API キーは api_key 引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
  - score_news は raw_news / news_symbols テーブルを参照し ai_scores に書き込みます。
  - 設計上、LLM エラー時はスキップして継続するフェイルセーフ実装です。

3) 市場レジーム判定（AI + MA）
- ETF 1321 の MA とマクロ記事の LLM センチメントを合成して market_regime に書き込む

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を環境変数に設定しておく

4) 監査ログスキーマの初期化（発注/約定トレーサビリティ用）
- 監査 DB を初期化する例:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # :memory: も可

  - init_audit_db はテーブルとインデックスを冪等で作成します。すべての TIMESTAMP は UTC で保存されます。

5) 研究用ファクター計算
- 例: calc_momentum / calc_volatility / calc_value

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026,3,20))
  # records は各銘柄の辞書リスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）

ディレクトリ構成
----------------
以下は主要ファイル・モジュールの概要（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                     : 環境変数 / .env 自動ロードと Settings
  - ai/
    - __init__.py
    - news_nlp.py                  : ニュース NLP（score_news）
    - regime_detector.py           : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            : J-Quants API クライアント（取得・保存）
    - pipeline.py                  : ETL パイプライン（run_daily_etl 等）
    - etl.py                       : ETLResult の再エクスポート
    - news_collector.py            : RSS 収集 / 前処理
    - calendar_management.py       : 市場カレンダー管理・営業日判定
    - stats.py                     : 統計ユーティリティ（zscore_normalize）
    - quality.py                   : データ品質チェック
    - audit.py                     : 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py           : ファクター計算
    - feature_exploration.py       : 特徴量探索（forward returns / IC / summary）
    - ...（将来的な拡張）
  - research/*, ai/* は研究・解析用ユーティリティを含む

開発メモ・設計上の注意点
------------------------
- Look-ahead bias を防ぐため、多くの関数は内部で datetime.today() / date.today() を参照せず、target_date を明示的に受け取ります。バックテスト等で過去の時点のみを使用する際は target_date を必ず指定してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索して行います。テスト中の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止できます。
- OpenAI 呼び出しには retry（429, network, timeout, 5xx に対する指数バックオフ）が実装されています。テストでは _call_openai_api をモックして振る舞いを差し替え可能です。
- J-Quants クライアントは内部に ID トークンキャッシュと自動リフレッシュ（401 時）を持ち、レート制御（120 req/min）を行います。
- news_collector は SSRF 対策、受信サイズ上限、トラッキングパラメータ除去などセキュリティ・健全性に配慮した実装です。
- DuckDB への書込みは基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を利用しています。

ライセンス・安全性
------------------
- 実運用での自動発注（kabu API 等）の利用は十分な監査と安全対策・リスク管理を行った上で実施してください。
- API キー（J-Quants / OpenAI / kabu）や機密情報は絶対にソース管理にコミットしないでください。 .env を用いてローカルで管理してください。

お問い合わせ / 貢献
------------------
- バグ報告・機能提案は issue を立ててください。プルリクエストは歓迎します。

この README はコード中の docstring とモジュール構造を基に作成しました。より詳細な使い方は各モジュールの docstring と関数定義を参照してください。