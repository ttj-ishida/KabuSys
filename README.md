README — KabuSys
===============

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした小規模なフレームワークです。
本リポジトリには以下の主要機能が含まれます。

- 発注・実行エンジン（ExecutionEngine）とペーパートレード分離
- システム監視・リスク監視・Kill Switch（監視で条件を満たすと Execution を停止）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定、セクター制約）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- ニュース NLP（OpenAI）を用いたセンチメント評価・レジーム判定
- 各種 CLI ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

主な設計方針：
- 各モジュールはできるだけ副作用を減らし、純粋関数 / DB 操作を分離
- 本番データとペーパートレードデータは明確に分離
- ルックアヘッドバイアスを避ける設計（時刻参照の扱いなど）
- フェイルセーフ（API 失敗時は安全側の挙動で継続）

機能一覧
--------
- run_execution.py : 発注エンジンを起動（KABUSYS_ENV により実際のブローカー or Mock を切替）
  - Paper Trading 時は専用 SQLite（data/paper_trading.db）へ記録
- run_monitoring.py : SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整可能）
- validate_config.py : 環境変数および config/*.yaml の事前検証 CLI
- config_setup.py : .env の対話式ウィザード（初期作成・更新）
- tools/paper_verification_report.py : ペーパートレード履歴から運用検証レポートを生成
- portfolio/* : 候補選定、重み計算、ポジションサイズ、セクター制約、レジーム乗数などの純粋関数群
- research/* : ファクター計算（momentum, volatility, value）や特徴量解析ユーティリティ
- ai/* : ニュースセンチメント（OpenAI）と市場レジーム判定（OpenAI）機能
- monitoring/* : 監視 DB 周り、各種 Monitor（System / Trade / Risk）、KillSwitch、アラート統合用 Engine
- utils/* : ロギングセットアップ、プロセス優先度・CPU affinity ユーティリティ等

前提・依存
-----------
推奨環境
- Python 3.10+（typing と新しい構文を利用）
必須 Python パッケージ（実行に応じて必要）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- sqlite3（標準ライブラリ）
- PyYAML（config ファイル検証時にあるとよい。なくても動作するが警告が出ます）

（requirements.txt がある場合はそれを利用してください）
例:
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成し依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb psutil openai
   - （オプション）pip install pyyaml

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 生成後、必要項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

5. データディレクトリ
   - デフォルトでは data/ を使用します。必要に応じて .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等を設定してください。
   - 実行時に DB ファイルや logs/ が自動で作成されます（権限が必要）。

主な環境変数（重要）
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: 実際のブローカーを呼ばずペーパートレード用 DB を使用
  - live: 本番
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視・停止制御関連

使い方
------
起動スクリプト例

- 監視ループ起動
  - MONITOR_POLL_INTERVAL を指定可能（秒）
  - python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path を使って監視データを保持します（環境に依らず）

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用い data/paper_trading.db に記録して本番 DB と分離

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db でパスを指定可能。

停止と Kill Switch
- run_execution や monitoring はプロセス間のシグナルとしてファイルを監視します。
  - 停止フラグ: data/stop_requested.flag（スクリプトは存在を検出すると安全に終了）
  - Kill Switch: data/kill.flag（KillSwitch が評価して作成。ExecutionEngine 停止指令）
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に Kill Flag を自動クリアします（本番では 0 推奨）。

ログ
- ログは stdout に出力され、デフォルトで logs/<app_name>.log に日次ローテーションで保存されます。
- ログディレクトリは LOG_DIR 環境変数または setup_logging の引数で変更可能。
- デフォルトログ保持: 30 日。

データベースとマイグレーション
- monitoring DB（SQLite）スキーマは init_monitoring_db() で冪等に作成・一部マイグレーション実行されます。
- ペーパートレード用 DB は PAPER_TRADING_SQLITE_PATH に分離可能。

主要モジュールの簡単な説明
------------------------
- kabusys.config
  - .env 自動読み込み・環境変数ラッパー。Settings クラスを提供。
- kabusys.config_setup
  - .env を対話式に作成するウィザード。
- kabusys.validate_config
  - 環境変数・config/*.yaml の存在や妥当性をチェックする CLI。
- kabusys.utils.logging_setup
  - 統一的なログ設定（Stream + TimedRotatingFileHandler）。
- kabusys.utils.process_priority
  - Windows / POSIX を吸収したプロセス優先度と CPU affinity 設定ユーティリティ。
- kabusys.monitoring.*
  - MonitoringDB: SQLite テーブル定義・CRUD。
  - SystemMonitor, TradeMonitor, RiskMonitor: 各監視ロジック（SystemMonitor はデータ鮮度・プロセス稼働検出など）。
  - KillSwitch: リスクトリガーで kill.flag を作成。
  - MonitoringEngine: 各 Monitor を束ねてポーリング・アラート送出。
- kabusys.execution.*
  - ExecutionEngine と関連コンポーネント（BrokerFactory, OrderManager, RiskManager, Reconciler 等）
- kabusys.portfolio.*
  - 銘柄選定・重み計算・ポジションサイズ・セクター制約・レジーム乗数
- kabusys.research.*
  - DuckDB を使ったファクター計算、forward returns、IC 計算、統計サマリ
- kabusys.ai.*
  - news_nlp: raw_news を OpenAI に投げて銘柄別のセンチメントを ai_scores に書き込む
  - regime_detector: ma200 とマクロセンチメントを統合して market_regime を算出
- tools/
  - paper_verification_report: ペーパートレード DB に対する検証レポートを出力

ディレクトリ構成（概略）
-----------------------
（リポジトリの src/kabusys 以下を抜粋）
- kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装想定)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
  - data/（実行時に生成される想定）
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - execution.pid, stop_requested.flag, kill.flag

開発・運用の注意点
------------------
- 本番（KABUSYS_ENV=live）では Kill Flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0 を推奨します。
- OpenAI を使う AI 機能は API コスト・レート制限に注意してください。APIKey を必ず管理してください。
- Paper Trading モードでは本番 DB と完全に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- ログ・DB の保存先パスは .env で調整可能です。cron や systemd で運用する際はパスの権限に注意してください。
- DuckDB を用いた研究パイプラインはローカルのデータ品質に依存します。prices_daily / raw_financials 等のテーブルが整備されている必要があります。

おわりに
---------
この README はコードベースの主要コンポーネントと使い方の概要をまとめたものです。詳細な API 仕様や実装の補足は各モジュールの docstring（ソースコード内のコメント）を参照してください。質問や追加ドキュメントの要望があれば教えてください。