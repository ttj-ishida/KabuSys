KabuSys — 日本株自動売買 / データプラットフォーム
======================================

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買パイプラインのコアライブラリ群です。  
主に以下を提供します。

- J-Quants からのデータ ETL（株価、財務、JPX カレンダー）
- ニュース収集・NLP スコアリング（OpenAI を利用）
- 市場レジーム判定（ETF の MA とマクロニュースの合成）
- 監査ログ（signal → order → execution のトレーサビリティ）
- 研究用ファクター計算・特徴量解析ユーティリティ
- データ品質チェック・カレンダー管理などの運用ユーティリティ

機能一覧
--------
主なモジュールと機能（抜粋）:

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - settings: J-Quants, OpenAI, Slack, DB パス、監視閾値 等を取得

- kabusys.data
  - jquants_client: J-Quants API 呼び出し、レート制御、リトライ、DuckDB 保存関数
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL ジョブ（prices/financials/calendar）
  - news_collector: RSS 収集・前処理・raw_news への保存（SSRF 対策あり）
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - audit: 監査ログテーブルの初期化 / 接続ユーティリティ
  - stats: zscore 正規化など汎用統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュースを LLM でスコアリングし ai_scores に書き込み
  - regime_detector.score_regime: ETF の MA とマクロニュースを合成して market_regime に書き込み

- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー等

必要条件
--------
- Python 3.10+（型注釈や union 型表現などを利用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリのみで多くの部分は実装

（実際の requirements.txt / pyproject.toml に合わせてインストールしてください）

セットアップ手順
--------------
1. リポジトリのクローン（プロジェクトルートへ移動）
   - git clone ... && cd kabusys

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存インストール（プロジェクトに pyproject/requirements がある想定）
   - pip install -e .              # 開発インストール（setup/pyproject がある場合）
   - or
   - pip install duckdb openai defusedxml

4. データディレクトリ作成（デフォルト設定を使う場合）
   - mkdir -p data

環境変数（.env）
----------------
プロジェクトルート（.git か pyproject.toml があるディレクトリ）に .env/.env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主な必須環境変数（簡易 .env.example）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=your_openai_api_key
- KABU_API_PASSWORD=your_kabu_api_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567

任意 / デフォルト:
- KABUYS_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

使い方（代表例）
----------------

1) 設定の読み取り
- from kabusys.config import settings
- settings.duckdb_path / settings.jquants_refresh_token 等を参照できます。

2) DuckDB 接続と日次 ETL の実行
- import duckdb
- from kabusys.data.pipeline import run_daily_etl
- from kabusys.config import settings
- conn = duckdb.connect(str(settings.duckdb_path))
- result = run_daily_etl(conn, target_date=some_date)  # target_date を省略すると today
- result は ETLResult オブジェクト（取得数・保存数・quality issues 等を含む）

3) ニュースのスコアリング（LLM を使用）
- from kabusys.ai.news_nlp import score_news
- client には環境変数 OPENAI_API_KEY を使うか、api_key 引数で直接渡す
- count = score_news(conn, target_date=date(2026,3,20))
- 実行は記事が raw_news / news_symbols に存在することが前提

4) 市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026,3,20))  # OpenAI キーは env または api_key 引数で指定
- market_regime テーブルに書き込みされます

5) 監査ログ DB 初期化
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可
- これにより監査用のテーブル / インデックスが作成されます

6) 研究用ユーティリティ
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- 各関数に DuckDB 接続と target_date を渡して銘柄別の factor dict リストが返ります
- zscore_normalize は kabusys.data.stats にあります

開発・テストメモ
----------------
- OpenAI 呼び出しは retry/backoff を行いますが、テストでは各モジュール内の _call_openai_api を patch して差し替えてください（news_nlp._call_openai_api, regime_detector._call_openai_api）。
- .env 自動ロードはプロジェクトルートを __file__ の親階層から探索します。テスト環境等で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB への batch executemany は空リストを与えると DuckDB バージョンによりエラーになる箇所があるため、当ライブラリでは事前に空チェックを行っています。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                 — ニュースの LLM スコアリング
  - regime_detector.py          — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py           — J-Quants API クライアント + DuckDB 保存
  - pipeline.py                 — ETL パイプライン実装（run_daily_etl 等）
  - etl.py                      — ETL インターフェース（ETLResult を公開）
  - news_collector.py           — RSS 収集・前処理
  - quality.py                  — データ品質チェック
  - calendar_management.py      — 市場カレンダー管理 / 営業日関数
  - stats.py                    — zscore 正規化等
  - audit.py                    — 監査ログテーブル初期化
- research/
  - __init__.py
  - factor_research.py          — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py      — 将来リターン / IC / summary 等

補足
----
- セキュリティ: news_collector は SSRF 対策（スキーム検証、プライベート IP 拒否、リダイレクト検査、最大レスポンスサイズ）を備えています。
- LLM 関係の出力は JSON モードを想定して厳密な JSON を期待しますが、実運用ではパース失敗をフェイルセーフとして 0.0（中立）にフォールバックする設計です。
- J-Quants API 呼び出しはレート制限、401 の自動リフレッシュ、ページネーション、リトライ（バックオフ）に対応しています。

問題・貢献
----------
バグ報告やプルリクエストはリポジトリで受け付けてください。ドキュメントや型注釈の改善、テスト追加を歓迎します。

--- 
README は実装の要点をまとめたものです。運用時は各モジュールの docstring を参照してください。