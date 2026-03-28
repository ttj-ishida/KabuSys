KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株のデータ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを一貫して提供する Python パッケージです。  
バックテスト／研究用のデータ処理と、本番運用の監査・発注インフラを分離して設計されています。

主な特徴
--------
- J-Quants API 経由での差分 ETL（株価日足 / 財務 / 市場カレンダー）と DuckDB への冪等保存
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）＋ニュース文章の前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（銘柄別 ai_score）とマクロセンチメントからの市場レジーム判定
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）と統計ユーティリティ（Zスコア、IC、前方リターン等）
- 監査ログ（signal_events / order_requests / executions）の初期化・管理（DuckDB）
- 環境変数管理（.env / .env.local の自動読み込み、無効化可能）

必要条件
--------
- Python 3.10+
- 主要ライブラリ（最低限）:
  - duckdb
  - openai
  - defusedxml

インストール例
-------------
仮想環境を作成してライブラリをインストールしてください（requirements.txt がある場合はそれを使ってください）。

例:
1) 仮想環境の作成
   python -m venv .venv
   source .venv/bin/activate

2) 必要パッケージのインストール
   pip install duckdb openai defusedxml

3) 開発インストール（プロジェクトルートに pyproject.toml 等がある想定）
   pip install -e .

環境変数 / .env
----------------
設定は環境変数かプロジェクトルートの .env / .env.local から読み込まれます（src/kabusys/config.py）。自動読み込みはルートに .git または pyproject.toml がある場合に行われます。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須：ETL）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注系）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（monitoring 用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 開発環境 (development / paper_trading / live)（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）（デフォルト INFO）

自動 .env 読み込みを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードをスキップします（テスト等で便利）。

セットアップ手順（実践）
---------------------
1. リポジトリをクローンしてプロジェクトルートに移動
2. Python 仮想環境を作成してアクティベート
3. 必要パッケージをインストール（上記参照）
4. プロジェクトルートに .env を作成（.env.example を参照）
   .env の例:
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

基本的な使い方（コード例）
-------------------------

- DuckDB 接続を作成して日次 ETL を実行する（J-Quants トークンは settings から取得）:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect(str(settings.duckdb_path))  # settings は自動読み込みされる
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを生成して ai_scores に書き込む:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数に設定しているか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"書き込み銘柄数: {written}")

- 市場レジーム判定（ma200 とマクロセンチメント合成）:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

  ※ OPENAI_API_KEY が未設定の場合は api_key を明示してください。AI 呼び出しに失敗した場合はフェイルセーフ値（macro_sentiment=0）で処理を継続します。

- 監査ログ（audit）テーブルの初期化:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # :memory: も可
  # 以後 conn を使って監査ログを書き込めます

注意点 / 動作方針
-----------------
- ルックアヘッドバイアス防止:
  - 多くの関数は date.today() / datetime.today() を内部で参照しません。必ず target_date を渡して使用します（ETL や scoring など）。
- 冪等性:
  - J-Quants から取得したデータは ON CONFLICT DO UPDATE 等で冪等に保存します。
  - audit の order_request_id / broker_execution_id などは冪等キーとして二重発注を抑止する用途に設計されています。
- フェイルセーフ:
  - AI API のエラー／タイムアウトはリトライとフォールバック処理（0相当）を経て例外を上位へ伝播しないケースが多く、長期バッチを安定的に回せるようにしています。
- API 呼び出しのリトライやレートリミットは内部で実装されています（J-Quants は固定間隔スロットル、OpenAI 呼び出しは指数バックオフ等）。

ディレクトリ構成（主なファイル）
-------------------------------
src/kabusys/
- __init__.py            — パッケージ定義（version 等）
- config.py              — 環境変数 / 設定管理（.env 自動ロード）
- ai/
  - __init__.py          — AI 関連の公開 API（score_news 等）
  - news_nlp.py          — ニュース NLP（銘柄別スコア生成）
  - regime_detector.py   — 市場レジーム判定（ma200 + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py    — J-Quants API クライアント + DuckDB 保存ロジック
  - pipeline.py          — ETL パイプライン（run_daily_etl 等）
  - etl.py               — ETL の公開型（ETLResult）
  - calendar_management.py — マーケットカレンダー管理 / 営業日判定
  - news_collector.py    — RSS ニュース収集（SSRF 対策等）
  - quality.py           — データ品質チェック
  - stats.py             — 共通統計ユーティリティ（zscore_normalize）
  - audit.py             — 監査ログ（テーブル初期化 / init_audit_db）
- research/
  - __init__.py
  - factor_research.py   — モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration.py — IC, forward returns, factor summary, rank
- research/...           — 研究用コード群（factor 計算・解析）

付録：よくある操作
------------------
- .env の自動読み込みを止めたい（テスト）:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 開発環境と本番環境切替:
  export KABUSYS_ENV=paper_trading  # または live / development

- OpenAI を明示的に使う（テストなど）:
  score_news(conn, target_date, api_key="sk-...")

ライセンス / コントリビューション
---------------------------------
（この README にライセンス情報は含まれていません。実際のリポジトリの LICENSE ファイルをご確認ください。）  

その他
-----
本 README はコードベースの主要機能と使い方のガイドです。各モジュールの詳細（引数や戻り値の仕様、例外仕様）はソース内の docstring を参照してください。必要であれば、CLI スクリプトや運用手順（cron/airflow ジョブ、監視・アラート設定）を別ドキュメントとして追加することを推奨します。