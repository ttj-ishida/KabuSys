KabuSys
=======

日本株向けのデータプラットフォーム / 自動売買支援ライブラリです。  
ETL（J-Quants）→ データ品質チェック → ファクター計算 → LLM を用いたニュース解析 → 監査ログ（発注トレース）など、実運用を意識した機能群を提供します。

主な特徴
--------
- J-Quants API からの差分取得（株価・財務・上場情報・カレンダー）と DuckDB への冪等保存
- データ品質チェック（欠損、スパイク、重複、将来日付・非営業日検出）
- ニュース収集（RSS）と LLM（OpenAI）による銘柄別センチメント評価（ai.score_news）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース LLM を合成、ai.score_regime）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Zスコア正規化）
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）と初期化ユーティリティ
- 設定は.env / 環境変数で管理。パッケージ起動時に自動で .env を読み込み（無効化可）

機能一覧（抜粋）
----------------
- kabusys.config: .env 自動読み込み、Settings オブジェクト（J-Quants / kabu API / Slack / DB パス等）
- kabusys.data.jquants_client:
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（自動リフレッシュ）
- kabusys.data.pipeline:
  - run_daily_etl: 市場カレンダー→株価→財務→品質チェックをまとめて実行
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別実行可）
- kabusys.data.quality: 各種品質チェック（結果は QualityIssue オブジェクト）
- kabusys.data.news_collector: RSS 取得・前処理・raw_news 保存（SSRF対策・サイズ制限等）
- kabusys.ai.news_nlp.score_news: 指定日のニュースを LLM でスコア化し ai_scores に保存
- kabusys.ai.regime_detector.score_regime: マクロニュース + ETF MA で市場レジーム判定（market_regime 保存）
- kabusys.research: calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- kabusys.data.audit: 監査ログ DDL と init_audit_schema / init_audit_db

動作環境（推奨）
----------------
- Python 3.10+
- 主な依存パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - その他（標準ライブラリで実装されている機能が多いですが、実運用では HTTP/SSL 等の環境整備が必要です）

セットアップ手順
----------------

1. リポジトリをクローン／配置
   - ソースが pip パッケージとして構成されている前提で、リポジトリルートに移る。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 例（pip）:
     - pip install duckdb openai defusedxml
     - またはプロジェクトの requirements.txt / pyproject.toml があればそちらを使用
   - 開発時はソースを編集できるように editable install:
     - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルートに .env を置くと、自動で読み込まれます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 最低限設定すべきキー（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - OPENAI_API_KEY=sk-...
   - DB パス等は Settings でデフォルト値が設定されています（duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db 等）。

例 .env
-------
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxx
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-xxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

使い方（代表的な呼び出し例）
--------------------------

1) DuckDB 接続を用意して日次 ETL を実行する
- 簡易例:
  - import duckdb
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(<path_to_db>))  # 例: "data/kabusys.duckdb"
  - res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(res.to_dict())

2) ニュースセンチメントのスコアリング（OpenAI API キーが必要）
- import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")  # api_key 省略時は env OPENAI_API_KEY を参照

3) 市場レジーム判定（MA200 + マクロニュース）
- from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)  # env OPENAI_API_KEY を使用

4) 監査ログ DB 初期化
- from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成してスキーマを初期化

5) 研究用ファクター計算
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026,3,20))

設定と注意点
-------------
- Look-ahead bias を防ぐ設計:
  - モジュールの多くは date 引数を外部から与えることを前提とし、内部で datetime.today() を盲目的に使わないようになっています。バックテスト時は必ず過去の状態のみを参照するように日付を固定してください。
- OpenAI 呼び出し:
  - gpt-4o-mini（response_format を JSON モードで使用）を前提とした実装。API 限度・エラーに対するリトライやフォールバックが組み込まれていますが、コストやレート制限には注意してください。
- J-Quants API:
  - レート制限（120 req/min）を守るため、内部でレートリミッタ／リトライが組み込まれています。認証はリフレッシュトークン経由で id_token を取得します。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査・プライベートIPブロック）や XML の安全パーサ（defusedxml）を使用していますが、運用時はネットワークポリシーやアクセス制御にも配慮してください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                      -- .env 自動読み込み / Settings
- ai/
  - __init__.py
  - news_nlp.py                  -- ニュースの LLM スコアリング
  - regime_detector.py           -- 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py            -- J-Quants API クライアント + 保存ロジック
  - pipeline.py                  -- ETL 実行（run_daily_etl 等）
  - etl.py                       -- ETL 用の型再エクスポート
  - quality.py                   -- データ品質チェック
  - news_collector.py            -- RSS 収集と前処理
  - calendar_management.py       -- 市場カレンダー管理（営業日判定等）
  - stats.py                     -- 統計ユーティリティ（zscore 正規化）
  - audit.py                     -- 監査ログ DDL と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py           -- モメンタム/バリュー/ボラティリティ
  - feature_exploration.py       -- forward returns / IC / ランク / 統計サマリ
- research/...                    -- その他研究用モジュール

補足
----
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に探索されます。テスト等で自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- コードは運用を想定してエラーハンドリングや冪等性（ON CONFLICT / DELETE→INSERT 等）に注意して実装されています。実運用前に小規模での動作確認、バックテスト向けのデータ整備（過去の stocks / prices の投入）を推奨します。
- 追加の CLI やデプロイ手順は本 README に含まれていません。用途に応じてスクリプトラッパーやスケジューラ（cron / Airflow 等）を用意してください。

ライセンスや貢献方法についてはリポジトリのトップレベルファイル（LICENSE / CONTRIBUTING）を参照してください。