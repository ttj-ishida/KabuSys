# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼リサーチ／自動売買基盤のプロジェクトです。  
J-Quants や RSS、OpenAI（LLM）を組み合わせてデータ収集（ETL）、データ品質チェック、ニュースセンチメント解析、ファクター計算、監査ログ（トレーサビリティ）、市場レジーム判定などを提供します。

主な設計方針は「ルックアヘッドバイアス排除」「冪等性（idempotent）」「フェイルセーフ（APIエラー時は継続）」です。

--------------------------------------------------------------------------------
目次
- プロジェクト概要
- 機能一覧
- 必要条件 / 依存関係
- 環境変数（主要）
- セットアップ手順
- 使い方（利用例）
- ディレクトリ構成
- 開発・テスト・注意点
--------------------------------------------------------------------------------

プロジェクト概要
----------------
KabuSys は次の機能群を持つ Python パッケージです（パッケージ名：kabusys）。
- J-Quants からの株価・財務・カレンダーデータの差分 ETL（DuckDB 保存）
- RSS によるニュース収集 + ニュース前処理（raw_news 保存、news_symbols 連携）
- OpenAI を使ったニュースセンチメント解析（銘柄ごとの ai_score）と市場マクロセンチメントの判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）およびリサーチ用ユーティリティ（IC, forward returns 等）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマの初期化と管理
- 市場カレンダーの管理（営業日判定・前後営業日取得等）

機能一覧
--------
主な公開 API と役割（一部）
- 環境設定
  - kabusys.config.settings: 環境変数アクセス / 自動 .env 読み込み
- データ ETL / 保存
  - kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - kabusys.data.pipeline.run_daily_etl: 日次 ETL パイプライン（calendar → prices → financials → quality）
  - kabusys.data.pipeline.ETLResult: ETL 実行結果のデータクラス
- ニュース
  - kabusys.data.news_collector.fetch_rss: RSS 取得・前処理
  - kabusys.ai.news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込む
- 市場レジーム
  - kabusys.ai.regime_detector.score_regime: ETF 1321 の MA200 と LLM マクロセンチメントを合成して market_regime に書き込み
- リサーチ / ファクター
  - kabusys.research.calc_momentum / calc_value / calc_volatility
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.data.stats.zscore_normalize
- 品質チェック
  - kabusys.data.quality.run_all_checks（および個別チェック関数）
- 監査ログ
  - kabusys.data.audit.init_audit_db / init_audit_schema

必要条件 / 依存関係
------------------
- Python 3.10 以上（タイプヒントや |union 記法を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- その他、ネットワークアクセス（J-Quants API、RSS、OpenAI）や sqlite（監視用）等を使用する場合はそれぞれ環境が必要

環境変数（主要）
----------------
自動で .env/.env.local をプロジェクトルートから読み込む（CWD に依存しない探索）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須（使用する機能により必要）:
- JQUANTS_REFRESH_TOKEN：J-Quants リフレッシュトークン（jquants_client.get_id_token で使用）
- OPENAI_API_KEY：OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD：kabuステーション API パスワード（発注等を使う場合）
- SLACK_BOT_TOKEN：Slack 通知を使用する場合
- SLACK_CHANNEL_ID：Slack 通知チャンネルID

任意 / デフォルト:
- KABUSYS_ENV：development / paper_trading / live（デフォルト: development）
- LOG_LEVEL：DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：監視/モニタリング用 SQLite（デフォルト: data/monitoring.db）

簡易 .env.example（README 用サンプル）
- JQUANTS_REFRESH_TOKEN=xxxxxxxx...
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

セットアップ手順
----------------
1. リポジトリをクローン（src レイアウトを想定）
   - git clone <repo>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (または Windows の場合 .venv\Scripts\activate)
3. 依存パッケージをインストール（プロジェクトに requirements.txt がある前提）
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （プロジェクト配布の setup.cfg / pyproject.toml があれば pip install -e .）
4. 環境変数を用意
   - プロジェクトルートに .env を作成するか、OS 環境変数で設定
   - 例: see 上の .env.example
5. DuckDB 等のストレージパスがデフォルトなら data/ ディレクトリを作る（save 関数が親ディレクトリを自動作成する場合もある）
   - mkdir -p data

使い方（例）
------------
以下は基本的な利用例（Python スクリプト / REPL から）。

共通: 設定取得
- from kabusys.config import settings
- settings.jquants_refresh_token, settings.duckdb_path などでアクセス可能

DuckDB に接続する
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=date(2026,3,20))
- print(result.to_dict())

2) ニュースセンチメントをスコアリング（ai_scores テーブルに保存）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- count = score_news(conn, target_date=date(2026,3,20))
- print("scored:", count)

3) 市場レジーム判定（market_regime テーブルに保存）
- from kabusys.ai.regime_detector import score_regime
- from datetime import date
- score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キーは環境変数か引数で指定可能

4) 監査ログ用 DuckDB を初期化する
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

5) ファクター計算・リサーチ
- from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns
- from datetime import date
- m = calc_momentum(conn, date(2026,3,20))
- v = calc_value(conn, date(2026,3,20))
- vol = calc_volatility(conn, date(2026,3,20))
- fwd = calc_forward_returns(conn, date(2026,3,20), horizons=[1,5,21])

6) データ品質チェック
- from kabusys.data.quality import run_all_checks
- issues = run_all_checks(conn, target_date=date(2026,3,20))
- for i in issues: print(i)

補足:
- OpenAI を使用する関数は api_key 引数を受け取るか環境変数 OPENAI_API_KEY を参照します。
- J-Quants 呼び出しは内部でトークン自動リフレッシュとレート制御を行います（settings.jquants_refresh_token が必要）。

ディレクトリ構成（主要ファイル）
------------------------------
src/
  kabusys/
    __init__.py
    config.py                    # 環境変数 / .env 自動読み込み
    ai/
      __init__.py
      news_nlp.py                # ニュースセンチメント解析・score_news
      regime_detector.py         # 市場レジーム判定
    data/
      __init__.py
      jquants_client.py          # J-Quants API クライアント + 保存関数
      pipeline.py                # ETL パイプライン（run_daily_etl など）
      etl.py                     # ETLResult 再エクスポート
      news_collector.py          # RSS 収集・前処理
      calendar_management.py     # market_calendar 管理・営業日判定
      stats.py                   # 統計ユーティリティ（zscore_normalize）
      quality.py                 # データ品質チェック
      audit.py                   # 監査ログスキーマ初期化
    research/
      __init__.py
      factor_research.py         # calc_momentum / calc_value / calc_volatility
      feature_exploration.py     # calc_forward_returns / calc_ic / factor_summary / rank
    research/                    # （上記）
    ...                          # （その他モジュールは README に記載したとおりの責務を持つ）

開発・テスト・注意点
-------------------
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行われます。テスト環境や一時的に無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany はバージョン差異で空リストを受け付けない場合があるため、モジュール内で空チェックを行っています。
- OpenAI 呼び出しはリトライ（429, network errors, timeout, 5xx の一部）を実装していますが、API レートや料金に注意してください。テスト時は内部の _call_openai_api をモックできます。
- J-Quants API はレート制限（120 req/min）を守るために内部で RateLimiter を使用しています。大量取得は API 制限に留意してください。
- セキュリティ: news_collector は SSRF 対策、XML に対する defusedxml 使用、レスポンスサイズ上限（10MB）などを実装していますが、稼働環境ではさらに運用面の注意が必要です。
- データベースや API のエラー発生時、モジュールは可能な限り例外を捕捉して継続する設計ですが、ETL 結果の ETLResult.errors や quality_issues を必ず確認してください。
- Python バージョンは 3.10 以上を推奨します（型表記に | を使用）。

ライセンス / 貢献
-----------------
- 本 README にはライセンス情報が含まれていません。実際のリポジトリに LICENSE ファイルを置いてください。
- バグ修正や機能追加は Pull Request を歓迎します。コーディング規約（フォーマット、型注釈、テスト）を整備しておくとよいです。

以上が KabuSys の概要・セットアップ・使い方の簡易ドキュメントです。必要であれば、具体的なサンプルスクリプト（ETL 定期実行、ニュース収集 cron、監視通知連携など）や .env.example の完全版を追記します。どの部分を詳しく知りたいか教えてください。