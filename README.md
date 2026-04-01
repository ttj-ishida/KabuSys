KabuSys — 日本株自動売買プラットフォーム（ミニマルドキュメント）
=================================

概要
----
KabuSys は日本株向けのデータプラットフォーム／研究・自動売買基盤のコンポーネント群です。本リポジトリには以下を目的としたモジュール群が含まれます。

- データ収集・ETL（J-Quants API 経由で株価・財務・カレンダーを取得し DuckDB に保存）
- データ品質チェック・カレンダー管理
- ニュースの NLP スコアリング（OpenAI を利用したセンチメント解析）
- 市場レジーム判定（ETF とマクロニュースを融合）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ用テーブル定義）

設計指針（抜粋）
- ルックアヘッドバイアスを避けるため、内部処理は target_date を明示して日付を計算します（datetime.today()/date.today() の直接参照を避ける等）。
- ETL/保存は冪等（idempotent）を意識し、ON CONFLICT/DELETE→INSERT 等で既存データを安全に更新します。
- ネットワーク系呼び出しはリトライ・バックオフ・レートリミット制御を備えます。
- 外部 API キー等は環境変数（.env）で管理します。パッケージ内に設定クラス（kabusys.config.Settings）を用意。

主な機能一覧
--------------
- data.jquants_client: J-Quants からのデータ取得・保存（株価、財務、カレンダー、上場銘柄情報）
- data.pipeline: 日次 ETL（run_daily_etl）と個別 ETL ジョブ（run_prices_etl 等）
- data.quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
- data.calendar_management: 市場カレンダーの判定・次/前営業日の取得
- data.news_collector: RSS からのニュース収集（SSRF 対策、トラッキング除去、前処理）
- data.audit: 監査ログ（signal_events/order_requests/executions テーブル）と初期化ユーティリティ
- ai.news_nlp: ニュースを銘柄ごとに集約して OpenAI に投げ、センチメント（ai_score）を ai_scores テーブルへ書き込む
- ai.regime_detector: ETF（1321）200日 MA とマクロニュースの LLM スコアを合成して market_regime を生成
- research.*: ファクター計算（momentum/volatility/value）、特徴量解析ユーティリティ
- config: 環境変数の自動読み込み（.env/.env.local）と Settings クラス

セットアップ手順
----------------

前提
- Python 3.10 以上（PEP 604 の型 | を使用しているため）
- DuckDB が使用されます（duckdb パッケージ）
- OpenAI API を利用する場合は openai パッケージ
- RSS パースに defusedxml

例: 仮想環境作成と依存インストール
- 仮想環境作成・有効化（例）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージ（最低限）
  - pip install duckdb openai defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

環境変数（.env）
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env/.env.local を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 必須の主要変数（最低限）:
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - KABU_API_PASSWORD=your_kabu_api_password
  - SLACK_BOT_TOKEN=xoxb-...
  - SLACK_CHANNEL_ID=CXXXXXXX
  - OPENAI_API_KEY=sk-...
- 任意・デフォルト値あり:
  - KABU_API_BASE_URL (default "http://localhost:18080/kabusapi")
  - DUCKDB_PATH (default "data/kabusys.duckdb")
  - SQLITE_PATH (default "data/monitoring.db")
  - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO

例 .env（テンプレート）
- .env.example を参考に作成してください。最低限の例:
  JQUANTS_REFRESH_TOKEN=REPLACE_ME
  OPENAI_API_KEY=REPLACE_ME
  KABU_API_PASSWORD=REPLACE_ME
  SLACK_BOT_TOKEN=REPLACE_ME
  SLACK_CHANNEL_ID=REPLACE_ME
  DUCKDB_PATH=data/kabusys.duckdb

使い方（主要 API の例）
----------------------

1) DuckDB 接続を作って ETL を回す（日次 ETL）
- Python スクリプト例:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

2) ニューススコアリング（ai.news_nlp.score_news）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

  - OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数に渡してください。

3) 市場レジーム判定（ai.regime_detector.score_regime）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

4) 監査ログ DB 初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を利用して order_requests 等の操作が可能

5) カレンダー / 営業日ユーティリティ
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))

注意点 / 運用ヒント
- OpenAI 呼び出しには課金が発生します。バッチサイズやモデルはモジュール内定数で調整可能です。
- ETL は冪等保存を前提としていますが、DuckDB のスキーマが未作成のまま実行するとエラーになります。最初に適切なスキーマを作成する手順（data.schema 等）を実行してください（本リポジトリに schema 初期化の関数がある場合それを利用）。
- 自動 .env 読み込みはプロジェクトルート（.git / pyproject.toml）を基準にします。CI などで環境変数を直接注入する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定するとファイル読み込みを抑制できます。
- DuckDB の executemany は空リストを渡せない箇所があるため、空リストチェックが内部で行われています。直接同様の処理を実装する場合は注意してください。

ディレクトリ構成（抜粋）
-----------------------

src/kabusys/
- __init__.py
- config.py                         — 環境変数・Settings
- ai/
  - __init__.py
  - news_nlp.py                      — ニュース NLP（score_news）
  - regime_detector.py               — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                — J-Quants API クライアント（fetch / save）
  - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
  - etl.py                           — ETLResult 再エクスポート
  - stats.py                         — 統計ユーティリティ（zscore_normalize）
  - quality.py                       — データ品質チェック
  - news_collector.py                — RSS 収集
  - calendar_management.py           — 市場カレンダー管理
  - audit.py                         — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py               — ファクター計算（momentum/volatility/value）
  - feature_exploration.py           — forward returns / IC / summary

（上記は主要ファイルのみ抜粋しています）

貢献・開発
----------
- 新しい機能や修正は PR でお願いします。
- 自動テスト・型チェック・静的解析（有る場合）を通すことを推奨します。
- 外部 API 呼び出し部分はモックしてユニットテストを書くことが可能です（例: kabusys.ai.news_nlp._call_openai_api を patch する等）。

ライセンス
---------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（ここでは記載していません）。

付録: よく使う環境変数一覧（まとめ）
- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (LLM 呼び出しが必要な機能を使う場合必須)
- KABU_API_PASSWORD (kabu API を使う場合必須)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (通知連携)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|...)

この README はコードベースの主要機能と利用方法を簡潔にまとめたものです。詳細は各モジュールの docstring を参照してください。必要があれば README にサンプルスクリプトや schema 初期化手順、requirements.txt/pyproject.toml の記載を追加できます。