# KabuSys — 日本株自動売買システム

概要
----
KabuSys は日本株向けのデータプラットフォームおよび自動売買基盤のプロトタイプ実装です。  
主に以下を提供します。

- J-Quants API を使ったデータ ETL（株価・財務・JPX カレンダー）
- RSS ベースのニュース収集と LLM を用いたニュースセンチメント評価
- ETF とマクロニュースを組み合わせた「市場レジーム」判定
- 監査（監査ログ）テーブルによるトレーサビリティ（シグナル → 発注 → 約定）
- 研究用途のファクター計算・特徴量探索ユーティリティ
- DuckDB を中心としたローカル DB 保存、品質チェック機能

設計上のポイント
- ルックアヘッドバイアス対策（内部で date.today()/datetime.today() を直接参照しない設計）
- API 呼び出しに対するリトライ / レート制御 / フェイルセーフ
- DuckDB に対する冪等保存（ON CONFLICT DO UPDATE 等）
- セキュリティ考慮（ニュース収集の SSRF 対策、XML パースの安全化等）

主な機能一覧
----------------
- data/etl.py
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult による実行レポート
- data/jquants_client.py
  - J-Quants API 呼び出し（ページネーション・トークンリフレッシュ・レート制御）
  - save_daily_quotes/save_financial_statements/save_market_calendar
- data/news_collector.py
  - RSS 収集、記事正規化、SSRF 防御、raw_news への保存処理想定
- data/calendar_management.py
  - 営業日判定・next/prev_trading_day/get_trading_days
  - calendar_update_job（JPX カレンダー更新ジョブ）
- data/quality.py
  - 欠損・重複・スパイク・日付不整合のチェック
- data/audit.py
  - 監査テーブル（signal_events / order_requests / executions）の初期化・DB 作成ヘルパ
- ai/news_nlp.py
  - calc_news_window, score_news：ニュースを銘柄ごとにまとめて LLM でセンチメント評価し ai_scores に保存
- ai/regime_detector.py
  - ETF(1321) の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime を更新
- research/
  - factor_research.py: calc_momentum, calc_value, calc_volatility
  - feature_exploration.py: calc_forward_returns, calc_ic, factor_summary, rank
- config.py
  - .env 自動ロード（.env, .env.local）と Settings クラス（環境変数のラッパ）
- data/stats.py
  - zscore_normalize（クロスセクション標準化）

セットアップ手順
----------------

前提
- Python 3.10 以上（| 型アノテーション等を使用しているため）
- DuckDB を使用するためネイティブ依存がある環境でも動作します

1. リポジトリをクローン / checkout
   - 例: git clone <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - （requirements.txt が無い場合の最小例）
     - pip install duckdb openai defusedxml
   - 実際のプロジェクトでは setuptools/poetry の依存リストに従ってください。

4. 環境変数の設定
   - プロジェクトルートの .env / .env.local に必要な変数を設定できます。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必須環境変数（少なくとも ETL/AI を使う場合）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能を使う場合）
   - SLACK_BOT_TOKEN: Slack 通知に使う場合
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI を直接使う場合（score_news/score_regime に未指定時参照）

   オプション・デフォルト
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）

5. DuckDB スキーマの初期化（監査ログなど）
   - 監査テーブルを別 DB に初期化する例:

     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - または既存の接続にスキーマを追加:

     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)

使い方（主要なユースケース）
--------------------------

以下は代表的な操作例（Python スクリプトまたは REPL）です。OpenAI キーや J-Quants トークンは環境変数で与えることが多いです。

1) 日次 ETL の実行（株価・財務・カレンダー取得と品質チェック）
   - 例:

     import duckdb
     from datetime import date
     from kabusys.data.pipeline import run_daily_etl

     conn = duckdb.connect("data/kabusys.duckdb")
     result = run_daily_etl(conn, target_date=date(2026, 3, 20))
     print(result.to_dict())

   - run_daily_etl は内部で calendar_etl → prices_etl → financials_etl → 品質チェック を順に実行します。

2) ニュースセンチメントのスコアリング（ai/news_nlp）
   - 例:

     from kabusys.ai.news_nlp import score_news
     from datetime import date
     import duckdb

     conn = duckdb.connect("data/kabusys.duckdb")
     n = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が環境変数に必要
     print(f"scored {n} stocks")

3) 市場レジームの判定（ai/regime_detector）
   - 例:

     from kabusys.ai.regime_detector import score_regime
     from datetime import date
     import duckdb

     conn = duckdb.connect("data/kabusys.duckdb")
     score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が環境変数に必要

4) ファクター計算・研究ユーティリティ
   - 例:

     from kabusys.research.factor_research import calc_momentum, calc_value
     from kabusys.data.stats import zscore_normalize
     import duckdb
     from datetime import date

     conn = duckdb.connect("data/kabusys.duckdb")
     mom = calc_momentum(conn, date(2026,3,20))
     val = calc_value(conn, date(2026,3,20))
     mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

5) 監査 DB の初期化（発注トレーサビリティ）
   - 例:

     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # これで signal_events / order_requests / executions テーブルが作成される

追加の設定・注意点
- テスト時に .env 自動読み込みを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはネットワークや API レート制限の影響を受けます。score_news/score_regime は内部でリトライ・バックオフを実装しています。
- J-Quants クライアントは 120 req/min のレート制御を行います（モジュール内で RateLimiter を使用）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py                — パッケージ定義（__version__）
- config.py                  — 環境変数ロード & Settings
- ai/
  - __init__.py
  - news_nlp.py              — ニュース集約・LLM スコアリング（score_news）
  - regime_detector.py       — MA とマクロセンチメント合成による市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（fetch_* / save_*）
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）
  - etl.py                   — ETL 型エクスポート（ETLResult）
  - news_collector.py        — RSS フィード収集・前処理
  - calendar_management.py   — JPX カレンダー管理・営業日判定
  - quality.py               — データ品質チェック
  - stats.py                 — 統計ユーティリティ（zscore_normalize）
  - audit.py                 — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py       — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py   — 将来リターン / IC / 統計サマリー

運用ノウハウ（簡潔）
-------------------
- 本番（live）モードでは KABUSYS_ENV=live を設定し、発注周りの安全ポリシー・リスク管理を厳格に行ってください。
- paper_trading 環境と live 環境を明確に分離し、監査ログや発注の冪等性を担保してください（order_request_id を冪等キーとして利用）。
- ETL・ニュース収集・LLM 呼び出しはそれぞれ異なる頻度・実行タイミングでスケジュールすることを推奨します（例: ETL は日次深夜、ニュースは頻繁に、レジームは日次）。

ライセンス・貢献
----------------
（この README にライセンス情報は含めていません。必要に応じて LICENSE ファイルを追加してください。）

お問い合わせ
--------------
実装や API の使い方に関する質問・改善提案があれば README を置いたリポジトリの issue 等で共有してください。

---  
この README はコードベースの主要機能と使い方の概要を示しています。詳細は該当モジュール（特に docstring）を参照してください。