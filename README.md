KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買 / 研究 / モニタリングを目的とした Python パッケージ群です。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine: 発注・リスク管理・注文整合などの実行系
- Monitoring: システム状態・注文・リスクの監視と Kill Switch
- Research / Portfolio: ファクター計算・ポートフォリオ構築・ポジションサイズ計算
- AI ツール: ニュースを LLM でスコアリングして市場レジーム判定 等
- ユーティリティ: 設定ウィザード・設定検証・ログ設定等

主な特徴
--------
- 実行環境切替:
  - KABUSYS_ENV により development / paper_trading / live を切替可能
  - paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
- 監視・アラート:
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - Kill Switch（data/kill.flag）により ExecutionEngine を停止可能
- 研究用モジュール:
  - DuckDB を用いたファクター計算（モメンタム、バリュー、ボラティリティ等）
  - ファクター評価 (IC) や将来リターン計算ツール
- AI 統合:
  - OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価と市場レジーム判定
  - 安全なリトライ・バリデーション処理を内包
- ロギング・運用性:
  - 統一された logging セットアップ（コンソール + 日次ローテートファイル）
  - プロセス優先度設定ユーティリティ（psutil を使用）

前提 / 必要環境
--------------
- Python 3.10+
- 推奨インストールパッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証を行う場合に必要）
- 任意: sqlite3 は標準ライブラリで提供
- 環境変数や .env を使用して API キー等を指定

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリに入る:
   - git clone <repo>
   - cd <repo>

2. 仮想環境を準備（例: venv）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール:
   - pip install duckdb psutil openai
   - （任意）pip install PyYAML

   ※ requirements.txt がある場合はそれを利用してください（本コードベースには含まれていません）。

4. ディレクトリ作成（初回起動用）:
   - mkdir -p data logs

5. 環境変数 (.env) を作成:
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - これにより .env を生成できます（.env は絶対に Git にコミットしないでください）
   - または .env を手動で作成し、最低限必要な変数を設定:
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_kabu_password
     - KABUSYS_ENV=development|paper_trading|live
     - OPENAI_API_KEY=your_openai_key (AI 機能を使う場合)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db (paper_trading 用)
     - LOG_LEVEL=INFO

6. 設定検証（起動前チェック）:
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合: python -m kabusys.validate_config --strict

使い方
------
基本的な起動例は以下のとおりです（プロセス管理ツール（systemd / supervisor / nohup 等）で運用してください）。

- Monitoring の起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは本番 DB に記録されます）

- ExecutionEngine の起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と完全分離）
  - 実行中に data/stop_requested.flag（または data/kill.flag）を作成すると安全に停止できます

- 設定ウィザード / 検証:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db /path/to/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI 機能（プログラム内からの呼び出し例）:
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # duckdb_conn は duckdb.connect() の接続オブジェクト
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

運用上のポイント
----------------
- Kill Switch:
  - KillSwitch は data/kill.flag を作成すると ExecutionEngine に停止信号を送ります（ExecutionEngine は起動時に kill.flag のクリアを制御できます）
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨

- DB:
  - デフォルト:
    - DUCKDB_PATH=data/kabusys.duckdb
    - SQLITE_PATH=data/monitoring.db
    - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - Monitoring は常に sqlite_path（本番）を使用します。paper_trading は run_execution が paper_sqlite_path を使用して分離します。

- ログ:
  - logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリを作成してください）
  - ログ設定は kabusys.utils.logging_setup.setup_logging を通して全スクリプトで統一されています

設定項目（主要）
----------------
- 必須（起動前に設定が必要）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 任意:
  - OPENAI_API_KEY（AI 機能を利用する場合）
  - KABUSYS_ENV (development|paper_trading|live)
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
  - KILL_FLAG_CLEAR_ON_START (0|1)

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 以下の主要ファイル・ディレクトリの概観です（完全なツリーではありません）。

- src/kabusys/
  - __init__.py
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env 作成ウィザード
  - validate_config.py       — 設定検証 CLI
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 永続化層
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py       (存在: 監視ロジック)
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       (通知管理)
  - execution/
    - execution_engine.py    — 実行エンジン本体
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - tools/
    - paper_verification_report.py

補足 / 開発者向けメモ
--------------------
- 型注釈やモジュール分割は運用性を意識して設計されています。テストの実行・モック化が容易なように外部 API 呼び出し部は抽象化されています。
- DuckDB 接続を渡して計算関数を呼ぶ設計（副作用を最小化）です。研究モジュールは prices_daily / raw_financials などのテーブルを参照します。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行われます。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で管理（例: 0.1.0）
- ライセンス情報は本リポジトリの LICENSE ファイルを参照してください（本 README では明示していません）。

問題や質問
----------
不明点や実行時のエラーが発生した場合は、ログ（logs/*.log）を確認してください。設定検証ツール（python -m kabusys.validate_config）で多くの設定ミスは事前に検出できます。