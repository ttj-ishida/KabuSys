KabuSys
======

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集 / NLP（OpenAI）、ファクター計算、監査ログなどを含む一連のコンポーネントを提供します。

概要
----
KabuSys は以下を目的とした Python ライブラリです。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL（DuckDB 保存）
- RSS ベースのニュース収集と OpenAI を用いた銘柄別センチメント算出（ai_scores）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメント合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ）と研究用ユーティリティ
- 監査ログ（signal / order_request / executions）用スキーマ初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

主な機能一覧
-------------
- データ取得・保存
  - J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- ニュース処理・NLP
  - RSS 取得・前処理（news_collector.fetch_rss / preprocess_text）
  - OpenAI を用いた銘柄別ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
- 研究・因子算出
  - calc_momentum, calc_value, calc_volatility（kabusys.research）
  - forward returns / IC / 統計サマリー（feature_exploration）
  - zscore 正規化ユーティリティ（data.stats.zscore_normalize）
- 運用ユーティリティ
  - market_calendar 管理・営業日判定（data.calendar_management）
  - 監査ログスキーマ初期化・DB生成（data.audit.init_audit_schema / init_audit_db）
  - データ品質チェック（data.quality.run_all_checks）
- 設定管理
  - 環境変数 / .env 自動読み込み（kabusys.config.settings）
  - 自動読み込みはプロジェクトルート（.git / pyproject.toml）から .env / .env.local を読み込み

インストール（開発環境）
-----------------------
1. リポジトリをクローン:
   git clone <repo-url>
2. 仮想環境作成（任意）:
   python -m venv .venv
   source .venv/bin/activate
3. 依存パッケージをインストール:
   pip install -e ".[dev]"  # setup.py/pyproject がある場合
   または最低限:
   pip install duckdb openai defusedxml

環境変数 / .env
----------------
kabusys はプロジェクトルート（.git または pyproject.toml）から自動的に .env を読み込みます（優先順: OS 環境 > .env.local > .env）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン（ETL に必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（実行/発注周りに使用）
- OPENAI_API_KEY : OpenAI 呼び出しに使用（news_nlp / regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知用（オプション）
- DUCKDB_PATH (デフォルト data/kabusys.duckdb) : メイン DuckDB ファイルパス
- SQLITE_PATH (デフォルト data/monitoring.db) : 監視系 SQLite パス（任意）
- PID_FILE_PATH / KILL_FLAG_PATH など監視設定
- KABUSYS_ENV (development | paper_trading | live) : 実行環境
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

セットアップ手順（初期 DB 作成例）
-------------------------------
1. .env を用意（.env.example を参考に必要な値を設定）。
2. データディレクトリを作成:
   mkdir -p data
3. DuckDB 接続と監査ログ DB 初期化例:
   python -c "import duckdb; from kabusys.data.audit import init_audit_db; init_audit_db('data/kabusys_audit.duckdb')"
   もしくは既存の DuckDB に監査スキーマを追加:
   python -c "import duckdb; from kabusys.data.audit import init_audit_schema; conn=duckdb.connect('data/kabusys.duckdb'); init_audit_schema(conn, transactional=True)"
4. ETL 実行（例）:
   python -c "import duckdb, datetime; from kabusys.data.pipeline import run_daily_etl; conn=duckdb.connect('data/kabusys.duckdb'); run_daily_etl(conn, target_date=datetime.date(2026,3,20))"

基本的な使い方（API 例）
-----------------------

- 日次 ETL 実行
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニューススコアリング（銘柄別 ai_scores へ書き込み）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  print(f"wrote {n_written} scores")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))  # api_key を渡すことも可能

- ファクター計算（研究用途）
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は [{ "date":..., "code":..., "mom_1m":..., ... }, ...]

注意点 / 運用メモ
-----------------
- OpenAI 呼び出しはモデル gpt-4o-mini を想定し、JSON Mode を利用して厳密な JSON 応答を期待します。OPENAI_API_KEY を設定してください。テスト時は _call_openai_api をパッチしてモックできます。
- J-Quants API はレート制限（120 req/min）を守る実装になっています。JQUANTS_REFRESH_TOKEN を .env に設定してください。
- ETL は差分更新・バックフィル（デフォルト 3 日）を行います。run_daily_etl でカレンダー取得→株価→財務→品質チェックの順に処理します。
- news_collector は RSS の SSRF 対策、受信サイズ制限、トラッキングパラメータ除去、記事 ID を SHA-256（先頭32文字）で生成するなど安全性・冪等性に配慮しています。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード内で空チェックが入っています。
- 自動 .env ロードはプロジェクトルートを .git / pyproject.toml から検索します。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                -- 環境変数 / .env 管理（自動ロード）
- ai/
  - __init__.py
  - news_nlp.py            -- ニュース NLP / スコアリング（score_news）
  - regime_detector.py     -- 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      -- J-Quants API クライアント / 保存関数
  - pipeline.py            -- ETL パイプライン（run_daily_etl など）
  - calendar_management.py -- マーケットカレンダー管理（is_trading_day 等）
  - news_collector.py      -- RSS 収集 / 前処理
  - quality.py             -- データ品質チェック
  - stats.py               -- zscore_normalize 等
  - audit.py               -- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - etl.py                 -- ETL 結果型の再エクスポート
- research/
  - __init__.py
  - factor_research.py     -- calc_momentum / calc_value / calc_volatility
  - feature_exploration.py -- forward returns / IC / factor_summary / rank
- execution/                -- （発注/実行ロジック/モニタ）※コードベースに含まれる場合あり
- monitoring/               -- （監視 / プロセス管理）※コードベースに含まれる場合あり

貢献 / テスト
--------------
- ユニットテストでは外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモックしてください。
- news_nlp と regime_detector は内部で別々の _call_openai_api を持っており、個別にパッチ可能です。
- 自動 .env ロードによる副作用を避けるには KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を設定してください。

ライセンス / その他
-------------------
（ここにライセンス情報を追記してください）

問い合わせ
----------
不明点や改善提案があれば Issue を立ててください。README の不足やセットアップで詰まる点を報告いただければ追記します。