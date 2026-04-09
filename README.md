KabuSys
=======

概要
----
KabuSys は日本株のデータプラットフォームと自動売買基盤を想定した Python パッケージです。  
主に以下を提供します：

- J-Quants からのデータ取得（株価・財務・マーケットカレンダー）と DuckDB への ETL
- ニュース収集・前処理・銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュース NLP（銘柄別センチメント）およびマクロセンチメントを用いた市場レジーム判定
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化ユーティリティ

主な機能一覧
-------------
- data.jquants_client: J-Quants API クライアント（取得・保存・ページネーション・リトライ・レートリミット）
- data.pipeline: 日次 ETL パイプライン（calendar / prices / financials の差分取得と品質チェック）
- data.news_collector: RSS からのニュース収集（SSRF 対策・正規化・冪等保存）
- data.quality: データ品質チェック群（missing / spike / duplicates / date consistency）
- data.calendar_management: JPX カレンダー管理と営業日ロジック（next_trading_day 等）
- data.audit: 監査ログテーブル定義と初期化（DuckDB）
- ai.news_nlp: ニュースを銘柄ごとに集約して LLM でセンチメントを算出（ai_scores に保存）
- ai.regime_detector: ETF（1321）200日移動平均乖離 + マクロニュースセンチメントを合成して市場レジームを判定
- research: ファクター計算・特徴量探索ユーティリティ（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic など）
- config: 環境変数・設定管理（.env 自動読み込みのロジック・settings オブジェクト）

前提・依存関係
--------------
- Python 3.10+
- 必須ライブラリ（代表）
  - duckdb
  - openai
  - defusedxml
- その他：標準ライブラリ（urllib, json, datetime, logging, sqlite3 など）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて他の開発依存を追加）

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに .env（および必要なら .env.local）を作成してください。
   - config モジュールは自動でプロジェクトルートの .env を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主要な環境変数例（.env）
------------------------
必須：
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- （OpenAI を使う場合）OPENAI_API_KEY=your_openai_api_key

認証・API:
- KABU_API_PASSWORD=...            # kabuステーション API パスワード
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # デフォルト

通知:
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...

DB / ファイルパス:
- DUCKDB_PATH=data/kabusys.duckdb           # デフォルト
- SQLITE_PATH=data/monitoring.db            # 監視/モニタリング用（デフォルト）
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

Paper Trading 設定:
- KABUSYS_ENV=development|paper_trading|live
- PAPER_FILL_MODE=instant|partial|never|reject

監視設定:
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0 or 1
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0

LOG:
- LOG_LEVEL=INFO|DEBUG|WARNING|ERROR|CRITICAL

使い方（基本例）
----------------

1) DuckDB 接続を作り日次 ETL を実行する
- 例:
  - from datetime import date
  - import duckdb
  - from kabusys.config import settings
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

2) ニュースセンチメントを算出して ai_scores に保存する
- 例:
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - written = score_news(conn, target_date=date(2026, 3, 20), api_key="あなたのOPENAI_API_KEY")
  - print(f"書き込んだ銘柄数: {written}")

3) 市場レジーム（bull/neutral/bear）を判定して market_regime に保存する
- 例:
  - from datetime import date
  - import duckdb
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="あなたのOPENAI_API_KEY")

4) 監査ログ用 DB / スキーマを初期化する
- 例:
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")
  - # conn は監査テーブルが初期化された DuckDB 接続

5) 研究用ユーティリティの利用
- 例: calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic などは
  kabusys.research 以下からインポートして DuckDB 接続と target_date を与えて実行します。

自動 .env ロードについて
------------------------
- config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env と .env.local を自動で読み込みます。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な公開 API（抜粋）
-------------------
- kabusys.config.settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.paper_fill_mode など

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, ...)

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.data.audit
  - init_audit_db(path) -> DuckDB connection
  - init_audit_schema(conn, transactional=False)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=None)
  - calc_ic(factor_records, forward_records, factor_col, return_col)

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                    # 環境変数・.env 自動ロード・settings
- ai/
  - __init__.py
  - news_nlp.py                # ニュース NLP（銘柄別センチメント）
  - regime_detector.py        # 市場レジーム判定（1321 MA + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py         # J-Quants API クライアント（fetch / save）
  - pipeline.py               # ETL パイプライン（run_daily_etl など）
  - calendar_management.py    # JPX カレンダー管理 / 営業日ロジック
  - news_collector.py         # RSS 収集・前処理・保存
  - quality.py                # データ品質チェック
  - audit.py                  # 監査ログスキーマ初期化
  - etl.py                    # ETLResult 再エクスポート
  - stats.py                  # 統計ユーティリティ（zscore_normalize）
- research/
  - __init__.py
  - factor_research.py        # ファクター計算（momentum, value, volatility）
  - feature_exploration.py    # forward returns, IC, summary, rank

補足・設計ノート
----------------
- Look-ahead bias を避けるため、多くのモジュールで datetime.today()/date.today() を直接参照せず、target_date を明示的に渡す設計になっています。
- J-Quants クライアントはレート制限（120 req/min）やリトライ・トークン自動リフレッシュを実装しています。
- OpenAI 呼び出しは JSON モードを使用して厳密な JSON を期待し、失敗時はフェイルセーフ（スコア = 0.0 など）で継続するよう配慮しています。
- DuckDB 用の保存関数は冪等（ON CONFLICT DO UPDATE）を意識しており、ETL を安全に再実行できます。

お問い合わせ / 開発
------------------
- 開発時は logging を DEBUG に設定して動作ログ・警告を確認してください（環境変数 LOG_LEVEL=DEBUG）。
- テスト時には config の自動 .env 読み込みを無効化したり、OpenAI 呼び出し・ネットワークリクエストをモックしてください。

以上が KabuSys の概要・導入・使い方のサマリです。必要であれば、特定モジュールの使い方（関数引数詳細や例）を追記しますので、どの機能のドキュメントを深掘りしたいか教えてください。