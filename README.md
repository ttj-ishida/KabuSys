KabuSys — 日本株自動売買プラットフォーム（README）
=================================

概要
----
KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買基盤のコアライブラリです。本コードベースは以下の機能群を含みます。

- データ収集・ETL（J-Quants API 経由で株価・財務・市場カレンダーを取得し DuckDB に保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- ニュース NLP（OpenAI を使った銘柄ごとのニュースセンチメント算出）
- 市場レジーム判定（ETF・MA と マクロニュースセンチメントの合成）
- 監査ログ（シグナル→発注→約定をトレースする監査テーブル初期化）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Zスコア正規化 など）

主要設計方針は「ルックアヘッドバイアス防止」「冪等（idempotent）」「フェイルセーフ（API失敗時はスキップや中立値にフォールバック）」です。

主な機能一覧
--------------
- ETL / pipeline
  - 日次 ETL 実行（run_daily_etl）：市場カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック
  - 個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
- J-Quants クライアント（jquants_client）
  - fetch / save の一連の実装（レート制御、リトライ、トークン自動更新、ページネーション対応）
- データ品質チェック（data.quality）
  - 欠損 / スパイク / 重複 / 日付不整合の検出（QualityIssue を返す）
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、raw_news への冪等保存（SSRF 対策、サイズ制限、トラッキングパラメータ削除）
- ニュース NLP（ai.news_nlp）
  - 銘柄ごとのニュースを LLM（gpt-4o-mini）で評価し ai_scores に書き込み
- 市場レジーム判定（ai.regime_detector）
  - ETF（1321）200日MA乖離とマクロニュースセンチメントの重み付け合成で regime を算出
- 研究用モジュール（research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC、統計サマリ、Zスコア正規化（data.stats）
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等の DDL 初期化と専用 DB 初期化ユーティリティ

セットアップ手順
----------------

前提
- Python 3.10+（typing の Union 短縮表記などを使用）
- ネットワークアクセス（J-Quants API / OpenAI / RSS ソース）
- DuckDB をデータストアとして利用

依存パッケージ（例）
- duckdb
- openai
- defusedxml

インストール（pip 仮想環境例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（プロジェクト要件ファイルがある場合はそれを利用）
   - pip install duckdb openai defusedxml

環境変数
- 自動 .env 読み込み:
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動読み込みします。
  - テスト時など自動読み込みを無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（settings.jquants_refresh_token）
- KABU_API_PASSWORD: kabuステーション API パスワード（settings.kabu_api_password）
- SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン（settings.slack_bot_token）
- SLACK_CHANNEL_ID: Slack のチャンネル ID（settings.slack_channel_id）
- OPENAI_API_KEY: OpenAI API を利用する場合は環境変数か関数引数で指定（ai モジュール）

オプション（デフォルト値あり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用、デフォルト）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

基本的な使い方
--------------

DuckDB 接続の作成例
- Python REPL / スクリプト内で DuckDB に接続して関数を呼び出せます。

例: 日次 ETL を実行する
- from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

例: ニュース NLP（ai.news_nlp.score_news）
- from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数に設定するか、第二引数で渡す
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")

例: 市場レジーム算出（ai.regime_detector.score_regime）
- from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env または api_key 引数で指定

例: 監査ログ DB 初期化
- from kabusys.data.audit import init_audit_db
  from kabusys.config import settings
  conn = init_audit_db(settings.duckdb_path)  # または別パスを指定

設定（.env の例）
- .env.example を参照して .env を作成してください。主要キー例:
  - JQUANTS_REFRESH_TOKEN=...
  - OPENAI_API_KEY=...
  - KABU_API_PASSWORD=...
  - SLACK_BOT_TOKEN=...
  - SLACK_CHANNEL_ID=...
  - DUCKDB_PATH=data/kabusys.duckdb
  - KABUSYS_ENV=development
  - LOG_LEVEL=INFO

実装上のポイント（運用メモ）
- OpenAI 呼び出し:
  - API 呼び出しはリトライとフェイルセーフを備えています。キーは環境変数 OPENAI_API_KEY で与えるか、関数引数 api_key に渡してください。
- J-Quants API:
  - リフレッシュトークンを用いて id_token を取得します（自動更新処理あり）。JQUANTS_REFRESH_TOKEN を必ず設定してください。
- 自動 .env ロード:
  - パッケージ読み込み時にプロジェクトルートの .env を自動で読み込みます。.env.local があれば上書きされます。
- ルックアヘッドバイアス対策:
  - 多くの処理は date を明示的に受け取り、内部で datetime.today() / date.today() を不用意に参照しない実装です（バックテストでの使用を想定）。

ディレクトリ構成（主要ファイル）
--------------------------------
（プロジェクトルートの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（スコア算出）
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py         — マーケットカレンダー管理
    - etl.py                         — ETL インターフェース（ETLResult 再エクスポート）
    - pipeline.py                    — 日次 ETL パイプライン（run_daily_etl 等）
    - stats.py                       — 共通統計ユーティリティ（zscore_normalize）
    - quality.py                     — データ品質チェック
    - audit.py                       — 監査ログテーブル定義・初期化
    - jquants_client.py              — J-Quants API クライアント（fetch / save）
    - news_collector.py              — RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum/value/volatility）
    - feature_exploration.py         — 将来リターン / IC / 統計サマリ
  - research/__init__.py
  - (その他: strategy/, execution/, monitoring/ 等のモジュールが想定されます)

補足（テスト・開発）
-------------------
- 自動 .env 読み込みを無効化したいとき:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / J-Quants の外部 API をモックしてユニットテストが書きやすいように、内部の HTTP 呼び出し箇所は差し替え（patch）可能なよう設計されています。
- DuckDB のインメモリ DB を使う場合は conn = duckdb.connect(":memory:") としてテスト可能です。

ライセンス・貢献
----------------
- 本ドキュメントではライセンス情報は含めていません。実装リポジトリのトップレベル README / LICENSE を参照してください。

最後に
------
この README はコードベースの主要な使い方・設計の要点をまとめたものです。個別の関数やクラスの詳細な挙動は各モジュール（src/kabusys 以下）の docstring を参照してください。必要であれば、特定のユースケース（ETL の運用スケジュール、監査ログ運用方針、OpenAI レート制御設定など）に合わせた運用手順のテンプレートを作成しますのでお知らせください。