KabuSys
=======

日本株向けの自動売買 / データ基盤ライブラリです。データの ETL、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注／約定トレース）などの主要機能を提供します。

本リポジトリはライブラリ形式での利用を想定しており、DuckDB をデータストアに用いて各種処理を行います。

主な特徴
--------
- データ取得・ETL（J-Quants API を利用）と品質チェック
- RSS ニュース収集と LLM を使った銘柄センチメント（ai_score）生成
- マーケットレジーム判定（ETF 1321 の MA とマクロニュースの組合せ）
- ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- DuckDB を前提とした冪等保存（ON CONFLICT）や堅牢なエラーハンドリング
- OpenAI（gpt-4o-mini など）とのインテグレーション（JSON Mode 利用）

必須機能一覧（モジュール）
-------------------------
- kabusys.config
  - .env / 環境変数からの設定読み込み、自動ロード機能（.env / .env.local）
  - settings オブジェクトで各種設定へアクセス
- kabusys.data
  - jquants_client: J-Quants からの取得 / DuckDB への保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline: 日次 ETL の実装（run_daily_etl 等）
  - news_collector: RSS フィード収集・前処理と raw_news 保存
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - calendar_management: 営業日判定とカレンダー更新ジョブ
  - audit: 監査ログ（テーブル定義・初期化ヘルパー）
  - stats: 汎用統計ユーティリティ（zscore 正規化）
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM に投げ銘柄別スコアを ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースで market_regime を判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: forward returns / IC / summary / rank 等

前提・依存
----------
- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード、OpenAI API）
- J-Quants / OpenAI の API キー（環境変数で指定）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （パッケージ化されていれば）pip install -e .

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を用意して下さい。

4. 環境変数 / .env を用意
   - プロジェクトルートの .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須例（.env に設定する代表例）:

     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C...
     OPENAI_API_KEY=sk-...
     # データベースパス（省略時は data/kabusys.duckdb）
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

   - settings オブジェクトからは上記を取得できます（kabusys.config.settings）。

5. DuckDB の準備
   - ETL や保存先となる DuckDB ファイルパス（settings.duckdb_path）を用意してください。
   - 監査ログ用 DB は下記 API で初期化できます（必要に応じて）:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

   注意: raw_prices / raw_financials / raw_news などのスキーマ初期化はプロジェクト内の別スクリプト（schema 初期化機能）を用いるか、手動でテーブルを作成してください。audit モジュールには監査用スキーマ初期化が含まれています。

基本的な使い方（コード例）
------------------------

- DuckDB に接続して日次 ETL を実行する

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースを LLM に渡してスコアを生成（score_news）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None なら環境変数 OPENAI_API_KEY を利用
  print("書き込んだ銘柄数:", n_written)

- 市場レジーム判定（score_regime）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB の初期化

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って audit テーブルにアクセス可

設計上の注意点 / 運用メモ
-----------------------
- Look-ahead バイアス対策
  - 多くのモジュールは date/datetime を外部引数で受け取り、内部で date.today() を直接参照しない設計です（ETL/分析・バックテストでの時間の取り扱いに注意）。
- 冪等性
  - J-Quants の保存関数は ON CONFLICT DO UPDATE を使い冪等保存を行います。
- レート制限
  - jquants_client は内部で固定間隔スロットリング（120 req/min）と再試行ロジックを実装しています。
- OpenAI 呼び出し
  - news_nlp / regime_detector は gpt-4o-mini（JSON Mode）を想定した処理で、429 / タイムアウト / 5xx に対するリトライを行います。API キーは OPENAI_API_KEY で指定してください。
- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に .env / .env.local を自動読み込みします。テスト時に自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
----------------
（主要ファイルと説明）

- src/kabusys/
  - __init__.py                        -- パッケージ定義・バージョン
  - config.py                          -- .env / 環境変数管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py                      -- ニュース NLP（score_news）
    - regime_detector.py               -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                -- J-Quants API クライアント、保存処理
    - pipeline.py                      -- ETL パイプライン（run_daily_etl 等）
    - etl.py                           -- ETLResult の公開
    - news_collector.py                -- RSS ニュース収集
    - quality.py                       -- データ品質チェック
    - calendar_management.py           -- JPX カレンダー管理
    - stats.py                         -- 統計ユーティリティ（zscore_normalize）
    - audit.py                         -- 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py               -- ファクター計算 (momentum/value/volatility)
    - feature_exploration.py           -- forward returns / IC / summary / rank

運用上のチェックリスト（簡易）
-----------------------------
- 環境変数（J-Quants / OpenAI / Slack 等）が正しく設定されているか
- DuckDB のパスとテーブルスキーマが用意されているか
- ネットワークアクセス（J-Quants、RSS ソース、OpenAI）が許可されているか
- 定期ジョブ（ETL / calendar update / news collection）を Cron 等で運用する場合はレート制限と API キー管理に注意

貢献・拡張
----------
- 新しいニュースソースの追加、スキーマ変更、バックテスト用のデータ取り出し関数追加などが想定されます。
- テスト：OpenAI / HTTP 呼び出し部分はモック可能な設計（内部 _call_openai_api, _urlopen の差替え）になっています。ユニットテストを書く際はこれらの差替えを活用してください。

免責
----
- 本プロジェクトは学術／研究目的で提供される実装例です。実際の運用での発注やマネタイズ用途に使用する場合は、法規制や証券会社 API の仕様、リスク管理を必ず確認・実装してください。

以上。必要であれば README にサンプル .env.example ファイル、テーブルスキーマ初期化手順、または実行用 CLI スクリプト例を追加できます。どの情報を追記しますか？