KabuSys — 日本株自動売買プラットフォーム（README）
====================================

概要
----
KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買（戦略→発注→監査）を支援する Python モジュール群です。  
主に以下を目的とします。

- J-Quants 等の外部 API からのデータ ETL（株価、財務、マーケットカレンダー）
- ニュースの収集と LLM を用いたセンチメント評価（銘柄別 / マクロ）
- ファクター計算・特徴量探索（リサーチ用ユーティリティ）
- 監査（signal → order → execution）のための監査テーブル初期化・管理
- 市場レジーム判定や監視・品質チェックなどの運用ユーティリティ

設計上のポイント
- ルックアヘッドバイアスを避ける（date/time を直接参照しない処理設計）
- DuckDB を主要な永続層として利用（ETL は冪等で安全）
- 外部 API 呼び出しはレート制御・リトライ・フォールバック実装
- LLM 呼び出しは JSON Mode を想定し、レスポンス検証を厳密に行う

主な機能一覧
----------------
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（get_id_token）、fetch_*、save_*（DuckDB へ冪等保存）
- 市場カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合チェック、run_all_checks
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理・SSRF対策・記事ID生成
- ニュース NLP（kabusys.ai.news_nlp）
  - calc_news_window, score_news（銘柄別センチメントを ai_scores に保存）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime（ETF 1321 の MA とマクロニュースの LLM スコア合成）
- 研究用ユーティリティ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- 監査ログ初期化（kabusys.data.audit）
  - init_audit_schema / init_audit_db

セットアップ手順
----------------
1. リポジトリをチェックアウト
   - 例: git clone <repo>

2. Python 仮想環境を作成（推奨 Python 3.10+）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - requirements.txt が無い場合は最低限以下をインストールしてください：
     - duckdb, openai, defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （実運用では HTTP リクエスト用の標準ライブラリのみを使用していますが、OpenAI SDK 等が必要です）

4. 環境変数 / .env 設定
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に .env/.env.local を置くと自動で読み込まれます（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...
   - 任意:
     - KABUSYS_ENV=development|paper_trading|live  (default: development)
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

例 .env (簡易)
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C12345678
- KABUSYS_ENV=development

使い方（主要な呼び出し例）
-------------------------
以下は Python からの直接利用例です。プロセス化（バッチ/cron）して使う想定です。

- DuckDB 接続
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL の実行（カレンダー・株価・財務・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニューススコアの実行（前日15:00〜当日08:30 JST のウィンドウ）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026,3,20))  # ai_scores に書き込む

- 市場レジームの判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))  # market_regime に書き込む

- 監査 DB の初期化（監査専用 DB を作る場合）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- 市場カレンダーの判定ユーティリティ
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_trading_day(conn, date(2026,3,20))
  next_trading_day(conn, date(2026,3,19))

- J-Quants から直接データを取得して保存
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  recs = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
  save_daily_quotes(conn, recs)

運用上の注意
- OpenAI や J-Quants の API キーは外部に流出しないよう管理してください。ログや .env の取り扱いに注意を払ってください。
- レート制限・コストに注意。jquants_client は API レート制御を行いますが、大量呼び出し時は運用設計が必要です。
- ETL と LLM 呼び出しはリトライとフォールバックを備えていますが、運用上の監視とアラートを設定してください。
- テスト時に環境変数の自動読み込みを無効化したい場合、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                      -- 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                  -- ニュースセンチメント（ai_scores）
  - regime_detector.py           -- 市場レジーム判定（market_regime）
- data/
  - __init__.py
  - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
  - etl.py                       -- ETL インターフェース再エクスポート（ETLResult）
  - jquants_client.py            -- J-Quants API クライアント（fetch/save）
  - news_collector.py            -- RSS ニュース収集
  - calendar_management.py       -- 市場カレンダー管理
  - quality.py                   -- データ品質チェック
  - stats.py                     -- 汎用統計ユーティリティ（zscore_normalize）
  - audit.py                     -- 監査ログ（schema / init）
- research/
  - __init__.py
  - factor_research.py           -- momentum/value/volatility
  - feature_exploration.py       -- forward returns / IC / summary / rank
- research/（上記に含まれる）
- その他: strategy/, execution/, monitoring/（パッケージ公開名は __all__ に含まれます）

API キー・環境変数一覧（抜粋）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (LLM 呼び出しに必須) — OpenAI API キー
- KABU_API_PASSWORD (必須) — kabu ステーション等の API パスワード
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — 通知用 Slack 設定
- DUCKDB_PATH / SQLITE_PATH — データベースファイルのパス
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル

開発・テスト
-------------
- モジュール内部は外部呼び出し（HTTP / OpenAI）をモック化できるよう設計されています（例えば _call_openai_api を patch するなど）。
- 自動 .env 読み込みはプロジェクトルートを .git / pyproject.toml で検出して行います。テストで副作用を避ける場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。

ライセンス / 貢献
-----------------
（本 README では記載していません。リポジトリの LICENSE を参照してください）

問い合わせ
----------
実運用や導入に関する質問があれば、リポジトリの issue を作成してください。README に未記載のユーティリティや想定フローについてはコード内ドキュメント（docstring）を参照してください。

以上。