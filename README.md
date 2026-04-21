KabuSys — 日本株向け自動売買プラットフォーム
=====================================

概要
----
KabuSys は日本株の自動売買システム向けライブラリ／ランタイム群です。  
本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine（発注エンジン）：ブローカークライアント経由で発注を行う（本番 / ペーパートレード両対応）。
- Monitoring（監視）：システム稼働状況・注文状況・リスクを定期監視し、Kill Switch を発動可能。
- Research / AI：DuckDB 上の価格・財務データからファクター計算／IC解析、LLM を用いたニュースセンチメント評価・レジーム検出。
- Portfolio：銘柄選定、配分重み計算、ポジションサイズ算出、セクター制約などの純粋関数群。
- ユーティリティ：設定ロード、ログ設定、プロセス優先度設定、設定ウィザードや設定検証 CLI、運用レポート生成ツール等。

主な特徴
--------
- 環境切替（development / paper_trading / live）に対応。ペーパートレードは本番 DB と完全分離。
- DuckDB（分析）とSQLite（監視・履歴）を併用したデータ設計。
- OpenAI を用いたニュース NLP（ニュース→セントメント → ai_scores 保存）とレジーム判定（ma200 + マクロセンチメント）。
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor）による自動アラート & Kill Switch。
- 設定ウィザード（対話式 .env 作成）と設定検証 CLI（起動前チェック）。
- ログはコンソール出力＋日次ローテーションファイル（logs/<app>.log）に保存。

セットアップ手順
----------------
以下は一般的なセットアップ手順の例です（プロジェクト内に requirements.txt がある場合はそれに従ってください）。

1. Python 環境を用意
   - 推奨: Python 3.10+
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - pip install duckdb psutil openai pyyaml

3. プロジェクトルートに移動し .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参照）:
     - 必須環境変数:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     - 推奨 / 任意:
       - KABUSYS_ENV (development | paper_trading | live)
       - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - SQLITE_PATH (デフォルト: data/monitoring.db)
       - PAPER_TRADING_SQLITE_PATH (ペーパートレード時の DB, デフォルト: data/paper_trading.db)
       - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)
       - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番アラート用）
       - OPENAI_API_KEY（AI モジュールを使用する場合）
   - 注意: .env は Git にコミットしないでください。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

5. データディレクトリ／ログディレクトリの作成
   - デフォルトでは data/ と logs/ を使用します。実行時に自動作成されますが、権限等の確認を推奨します。

使い方（実行例）
----------------

- 監視ループを起動（SystemMonitor をポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - run_monitoring は常に「本番用の monitoring sqlite_path」を使用（KABUSYS_ENV に依らず）

- ExecutionEngine を起動（当日のセッションを実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
  - 実行中に停止させるには monitoring の Kill Switch（data/kill.flag）や stop フラグ（data/stop_requested.flag）を利用できます

- 設定ウィザード（.env を作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit(1)

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

運用関連（フラグ / ログ）
-----------------------
- 停止フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution のループを止めるために使用
  - data/kill.flag: Monitoring の KillSwitch が書き込むフラグ。ExecutionEngine に対する停止シグナルとして機能
- PID ファイル:
  - data/execution.pid: ExecutionEngine が PID を記録（設定によりパス変更可能）
- ログ:
  - logs/<app_name>.log（例: logs/monitoring.log, logs/execution.log）に日次ローテーションで保存されます
  - setup_logging() で統一的に設定されます

環境変数（主なもの）
-------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード:
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading: 発注はモック、専用 sqlite（PAPER_TRADING_SQLITE_PATH）を使用
    - live: 実際の発注を行う
- DB 関連:
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- ログ:
  - LOG_LEVEL (INFO 等)
  - LOG_DIR
- AI:
  - OPENAI_API_KEY
- 監視/運用:
  - MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数、デフォルト 60)
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等は Settings 経由で取得可能

主なモジュール説明
------------------
- kabusys.config
  - .env 自動ロード（プロジェクトルート検出）・Settings クラス（環境変数ラッパ）
- kabusys.config_setup
  - 対話式 .env 作成ウィザード
- kabusys.validate_config
  - 起動前チェック（必須 env, DB パス, config/*.yaml の存在等）
- kabusys.run_execution
  - ExecutionEngine の起動スクリプト（プロセス優先度設定・DB 接続・スレッドで run_session 実行）
- kabusys.run_monitoring
  - SystemMonitor のポーリングスクリプト（MONITOR_POLL_INTERVAL を参照）
- kabusys.monitoring
  - monitoring_db: SQLite テーブル初期化・読み書き用 wrapper
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / alert_manager
- kabusys.execution
  - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler、BrokerClientFactory（実装は省略）
- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment（純粋関数群）
- kabusys.research
  - factor_research（mom/value/volatility）、feature_exploration（forward returns, IC）
- kabusys.ai
  - news_nlp: LLM を使ってニュースをスコアリングし ai_scores に保存
  - regime_detector: ma200 + マクロセンチメントで市場レジーム判定
- kabusys.utils
  - logging_setup: 共通ログ設定
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

ディレクトリ構成（抜粋）
-----------------------
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (※プロジェクト内に実装あり)
    - execution/
      - execution_engine.py
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
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/ (DB 関連や監視ロジック)
- data/           (runtime: sqlite DB, pid, flag ファイル 等)
- logs/           (ログファイル出力先)

運用上の注意
-----------
- 本番モード（KABUSYS_ENV=live）の場合、設定ミスは実取引につながるため validate_config を必ず実行・確認してください。
- .env は秘匿情報を含むため絶対にリポジトリにコミットしないでください。
- OpenAI やブローカークライアント等の外部 API キーは適切に管理してください（環境変数で設定）。
- monitoring / execution の停止には data/stop_requested.flag または監視側からの data/kill.flag を利用します。どちらも data/ にフラグファイルを作成することで作用します。

トラブルシューティング
----------------------
- ログが作成されない:
  - 権限や指定した LOG_DIR の存在を確認してください。setup_logging はディレクトリ作成に失敗するとファイル出力をスキップします。
- DuckDB / SQLite への接続エラー:
  - DUCKDB_PATH / SQLITE_PATH が正しく設定されているか、親ディレクトリの存在および書き込み権限を確認してください。
- OpenAI 呼び出しのエラー:
  - OPENAI_API_KEY が設定されているか、ネットワーク・レート制限を確認してください。news_nlp と regime_detector はリトライロジックを持ちますが、API キー未設定では例外になります。

ライセンス / 貢献
----------------
- 本ドキュメントではライセンス表記を行っていません。実プロジェクトでは LICENSE をプロジェクトルートに配置してください。
- 貢献は PR ベースで受け付ける想定です。ドキュメント、テスト、型アノテーションの追加を歓迎します。

以上が本コードベースの概要と基本的な使い方になります。必要であれば、各コンポーネント（ExecutionEngine、監視ロジック、AI モジュール等）の詳細動作説明や運用手順書（起動順序、監視ダッシュボード、アラートハンドリング例）を追加で作成します。どの部分を詳しく補足しますか？