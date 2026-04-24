KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。売買実行・監視・ポートフォリオ構築・リサーチ・AI（ニュース NLP）などのコンポーネントを含みます。本 README はプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

要約（Project overview）
---------------------
KabuSys は以下の責務を持つモジュール群から構成されています（主に src/kabusys 以下）:
- Execution: 発注エンジン（本番 / ペーパートレード切替対応）
- Monitoring: システム稼働状況・発注状況・リスク監視、Kill Switch（停止フラグ）
- Portfolio: 候補選定 / 重み計算 / ポジションサイズ算出 / セクター制限
- Research: DuckDB 上でのファクター計算・特徴量解析
- AI: ニュースの NLP スコアリング、レジーム判定（OpenAI を利用）
- Utils: ログ設定、プロセス優先度などユーティリティ
- Tools: ペーパートレード検証レポート生成などのスクリプト

主な設計方針:
- 設定は .env または環境変数で行う（自動ロード機能あり）
- Execution は paper_trading モード時に専用のペーパートレード DB を使用
- Monitoring は環境にかかわらず監視用 sqlite_path を使用
- DuckDB を分析用途に利用（prices_daily / raw_financials 等のテーブルを想定）
- AI 呼び出しは OpenAI（gpt-4o-mini）を想定。失敗時はフェイルセーフで継続

機能一覧
--------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading で MockBroker 使用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL により間隔指定可）
- 設定管理
  - config_setup.py: 対話式 .env ウィザードで初期設定
  - validate_config.py: .env と config/*.yaml を検証（--strict オプションあり）
- 監視・リスク管理
  - monitoring/*.py: system/trade/risk モニタ，kill switch，alert 管理，monitoring DB
  - monitoring_db: SQLite スキーマ初期化・永続化 API
- 発注処理
  - execution/*: BrokerFactory / ExecutionEngine / OrderManager / RiskManager / Reconciler 等（本コードでは起動フローを含む）
- ポートフォリオ構築
  - portfolio/*: 候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム補正
- リサーチ
  - research/*: momentum/value/volatility 等ファクター計算、forward returns、IC 計算、統計サマリ
- AI（ニュース NLP / レジーム判定）
  - ai/news_nlp.py: raw_news を LLM に投げて銘柄ごとにセンチメントスコアを ai_scores に書き込み
  - ai/regime_detector.py: ETF + マクロ NLP を合成して market_regime を算出・保存
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成

前提・依存関係（推奨）
-------------------
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - pyyaml（config YAML の検証に必要だが任意）
- 標準ライブラリ: sqlite3, threading, logging, pathlib など

インストール（例）
-----------------
1. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

設定（.env 作成）
----------------
1. 対話式ウィザードで .env を生成:
   - python -m kabusys.config_setup
   - ウィザードは既存 .env を読み、Enter で現在値を再利用できます。

2. 設定の検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。
   - 自動ロードを抑止したい場合: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主な環境変数（代表）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading モード時に使用）
- LOG_LEVEL: デフォルト INFO
- OPENAI_API_KEY: AI 関連処理で利用
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

重要ファイル・フラグ
-------------------
- data/kill.flag: Kill Switch が書き込む停止フラグ（ExecutionEngine はこれを見て停止可能）
- data/stop_requested.flag: run_execution / run_monitoring で停止を検知するためのフラグ
- data/execution.pid: Execution 用 PID ファイル（ExecutionEngine により作成／利用）
- logs/<app>.log: setup_logging により生成（例: logs/execution.log, logs/monitoring.log）

使い方（基本コマンド）
--------------------
- .env を作成・更新:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動:
  - 簡単: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading モードでは MockBrokerClient を用い、data/paper_trading.db に記録されます（本番 DB と分離）。
  - 本番: KABUSYS_ENV=live python -m kabusys.run_execution

- Monitoring を起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL で秒数を上書き（1 以上）。不正値は 60 秒にフォールバック。
    - Monitoring は環境にかかわらず Settings.sqlite_path を使用して監視 DB に書き込みます。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを明示的に指定可能（優先度: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

- AI 関連（ライブラリ的な呼び出し例）:
  - Python REPL やスクリプト内で呼び出し:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, date(2026,4,1), api_key="xxxx")
  - OPENAI_API_KEY を環境変数に設定しておくと api_key を省略可能

ログ・デバッグ
--------------
- setup_logging(app_name="execution" or "monitoring") により logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30 日保持）。
- コンソール出力は stdout に出力されます（cron 等との相性を考慮）。

プロセス優先度
------------
起動スクリプト（run_execution.py, run_monitoring.py）は開始時に set_process_priority("high") を呼び出してプロセス優先度を上げます（Windows/Linux に対応。権限不足時は警告でスキップ）。

停止制御（Kill Switch）
---------------------
- RiskMonitor 等が条件を満たすと KillSwitch が data/kill.flag を書き込みます。ExecutionEngine はこのフラグを検知して安全に停止する仕組みです。
- 手動で停止させたい場合は data/stop_requested.flag を作成すると run_* スクリプトはループを抜けて終了します。

ディレクトリ構成（抜粋）
---------------------
以下は src/kabusys の主要ファイル/ディレクトリの概要です（完全なツリーではありません）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - execution/
    - execution_engine.py, order_manager.py, broker_factory.py, ...
  - monitoring/
    - monitoring_db.py, system_monitor.py, trade_monitor.py, risk_monitor.py,
      kill_switch.py, monitoring_engine.py, alert_manager.py, ...
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py, ...
  - research/
    - factor_research.py, feature_exploration.py, ...
  - ai/
    - news_nlp.py, regime_detector.py
  - utils/
    - logging_setup.py, process_priority.py, ...

開発時の注意点 / ヒント
-----------------------
- .env は機密情報を含むため Git にコミットしないでください（config_setup でもその旨の注意を出力します）。
- validate_config.py は必須環境変数の未設定や config/*.yaml の未整合を起動前に検出できます。CI に組み込むと安全です。
- DuckDB のスキーマ（prices_daily, raw_financials, raw_news 等）はリサーチ/AI モジュールで利用されます。テストデータを用意してから実行してください。
- OpenAI API 呼び出しは外部依存かつコストが発生するため、テスト時はモック化することを推奨します（コード内でもテスト用差替えポイントを想定した実装になっています）。

ライセンス・貢献
----------------
（本 README にはライセンス情報が含まれていません。必要に応じて LICENSE ファイルを追加してください。）

補足（よくある質問）
-------------------
Q: ペーパートレードと本番の DB は混ざりますか？
A: いいえ。KABUSYS_ENV=paper_trading のときは paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 sqlite_path（data/monitoring.db など）とは分離されます。ただし Monitoring は常に sqlite_path を使用します。

Q: run_monitoring の間隔を変えたい
A: 環境変数 MONITOR_POLL_INTERVAL に秒数（1以上）を指定してください。不正値・0 や負は 60 秒にフォールバックします。

Q: 自動で .env をロードするのを止めたい
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップします（テスト等で便利）。

問い合わせ
--------
不明点や機能追加の提案がある場合はリポジトリの issue を作成してください。

以上。README の内容はコードのコメント／ドキュメントを元にまとめました。追加で「インストール手順を具体的な requirements.txt にまとめる」「実際の起動例（systemd / docker-compose）を追加する」などを希望される場合は教えてください。