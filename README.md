KabuSys — 日本株向けデータプラットフォーム & 自動売買補助ライブラリ
=============================================================================

概要
----
KabuSys は日本株のデータ取得（J-Quants 経由）、ETL、品質チェック、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを統合した内部ライブラリです。DuckDB をローカル DB として使用し、ETL パイプラインや分析ワークフロー、実行系の監査ログ初期化などを提供します。

主な機能
---------
- J-Quants API クライアント（差分取得・ページネーション・トークン自動更新・レート制御）
- ETL パイプライン（株価 / 財務 / カレンダーの差分取得・保存・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- ニュース収集（RSS → raw_news、SSRF 対策、正規化）
- ニュース NLP（OpenAI を使った銘柄別センチメント取得、ai_scores へ書込み）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）と特徴量探索ユーティリティ
- 監査ログテーブルの初期化（signal_events / order_requests / executions、冪等・UTC タイムスタンプ）
- 設定管理（.env / 環境変数自動読み込み、設定ラッパー）

要件
----
- Python 3.10+
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
  - （その他：標準ライブラリ以外を使う箇所は requirements に合わせてインストールしてください）

セットアップ手順
----------------
1. Python (3.10+) を用意する
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください:
     - pip install -r requirements.txt
     - または pip install -e .（インストール可能なパッケージとしてセットアップされている場合）
4. 環境変数 / .env ファイルを用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_PASSWORD: kabu API パスワード（必要に応じ）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を使う場合
     - DUCKDB_PATH (省略時: data/kabusys.duckdb)
     - SQLITE_PATH (省略時: data/monitoring.db)
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
   - .env.example を参考にしてください（リポジトリにある想定）。

使い方（簡単なコード例）
-----------------------

1) 設定参照
- 環境変数をラップした Settings を利用できます。

  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path

2) DuckDB 接続例

  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

3) 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）

  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

4) ニュースセンチメント（銘柄別）を取得して ai_scores に書き込む

  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を利用
  print(f"written {written} codes")

5) 市場レジーム判定を実行（1321 MA + マクロニュース LLM）

  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

6) 監査ログ DB を初期化する（発注・約定用）

  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit を使って order_requests / executions を管理

設定の自動読み込みについて
------------------------
- kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基準に .env と .env.local を自動で読み込みます。
  - 読み込み優先度: OS環境変数 > .env.local > .env
  - テストなどで自動読み込みを無効にする場合:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 必須環境変数が未設定の場合、Settings のプロパティ呼び出しで ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD が必須となる箇所あり）。

注意点・設計ポリシー（要約）
-------------------------
- Look-ahead bias を避けるため、各関数は内部で datetime.today()/date.today() を参照しない設計（呼び出し側で target_date を与える）。
- DuckDB に対する書き込みは基本的に冪等（ON CONFLICT や DELETE→INSERT の置換戦略）を採用。
- OpenAI API 呼び出しは JSON Mode を利用し、レスポンスのバリデーション／リトライ（指数バックオフ）を実装。
- RSS の収集は SSRF 対策、トラッキングパラメータ除去、サイズ制限、XML の安全パーシング（defusedxml）を行う。
- J-Quants クライアントはレート制御（120 req/min）、トークン自動リフレッシュ、リトライ（408/429/5xx）を実装。

ディレクトリ構成（主要ファイル・モジュール）
--------------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                  — ニュースセンチメント（銘柄別）
  - regime_detector.py           — 市場レジーム判定（1321 MA + マクロセンチメント）
- data/
  - __init__.py
  - calendar_management.py       — 市場カレンダー管理（営業日判定等）
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - etl.py                       — ETL 結果の公開（ETLResult）
  - jquants_client.py            — J-Quants API クライアント（fetch/save）
  - news_collector.py            — RSS ニュース収集
  - quality.py                   — データ品質チェック
  - stats.py                     — 統計ユーティリティ（zscore_normalize）
  - audit.py                     — 監査ログテーブル初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py           — Momentum/Volatility/Value 等の計算
  - feature_exploration.py       — 将来リターン / IC / 統計サマリー 等
- ai/...、research/...（上記以外の補助モジュール）

よくある利用フローの例
---------------------
1. ETL（夜間バッチ）
   - run_daily_etl() をスケジューラ（cron / Airflow 等）から実行し、prices/raw_financials/market_calendar を更新。品質チェック結果は ETLResult に含まれる。

2. ニュースハンドリング・AI スコアリング
   - news_collector.fetch_rss() で raw_news を収集 → news_symbols に紐付け
   - score_news() を実行して銘柄別 ai_score を ai_scores テーブルへ保存

3. 市場レジーム判定
   - score_regime() を実行して market_regime テーブルに書き込み（バックテストやリスク管理に利用）

4. 監査ログの初期化
   - init_audit_db() で監査用 DB を作成し、発注フローのトレーサビリティを確保

サポート / 開発者向けメモ
------------------------
- テストや CI で環境変数の自動読み込みが邪魔な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI や J-Quants の呼び出しは外部 API へ依存するため、ユニットテストでは該当関数（_call_openai_api や jquants_client._request など）をモックすることを推奨します。
- DuckDB の executemany に空リストを渡すと問題になる古いバージョン対策がコード内にあるため、DuckDB バージョンに注意してください（推奨は最新安定版）。

ライセンス／貢献
----------------
- （リポジトリに LICENSE があればここに記載してください）
- バグ報告や機能改善はプルリクエスト / Issue を作成してください。

以上。必要であれば README にサンプル .env.example、requirements.txt の候補、より具体的な CLI / スケジューリング手順などを追記します。どの情報を追加しましょうか？