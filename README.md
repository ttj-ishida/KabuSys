# KabuSys

日本株自動売買システムのコードベース（ドキュメント版）。この README はリポジトリ内の主要スクリプト・モジュールを元に、導入・実行方法とディレクトリ構成を日本語でまとめています。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提 / 必要ライブラリ
- セットアップ手順
- 使い方（起動スクリプト・ツール）
- 環境変数（主要項目）
- ファイル / フラグの説明
- ディレクトリ構成（主要ファイルの説明）

---

プロジェクト概要
- KabuSys は日本株向けの自動売買フレームワークです。戦略の研究（ファクター計算・特徴量解析）、ポートフォリオ構築、ポジションサイジング、発注エンジン（ExecutionEngine）および監視（Monitoring）を含む一連のコンポーネントが実装されています。
- DuckDB を用いた分析用データベース（価格・財務データ等）と、SQLite を用いた運用向けログ／監視 DB を組み合わせた設計です。
- Paper Trading モード（実発注なし）と Live モード（実際の発注）を切り替え可能。LLM（OpenAI）を使ったニュースセンチメントや市場レジーム判定の機能も含みます。

主な機能一覧
- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading と Live の隔離（paper_trading 用 SQLite を使用）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - 注文管理、リスク管理、照合（OrderManager, RiskManager, Reconciler）
- 監視系
  - SystemMonitor（CPU/MEM/DISK、データ鮮度、実行プロセス監視）
  - TradeMonitor（注文滞留・約定異常検出）
  - RiskMonitor（ドローダウン、ポジション上限検知）
  - MonitoringEngine（上記を束ねてポーリング）
  - KillSwitch（条件により ExecutionEngine に停止信号を送る）
- 研究系 / ツール
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算、統計サマリー
  - Portfolio construction（候補選定、重み、ポジション計算）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- AI（OpenAI）
  - ニュースの NLP スコアリング（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
- ユーティリティ
  - 設定管理（.env 自動ロード、Settings クラス）
  - .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ロギングセットアップ（utils.logging_setup）
  - プロセス優先度設定（utils.process_priority）

前提 / 必要ライブラリ
- Python 3.9+（typing 機能を想定）
- 必須ライブラリ（実行環境に応じて）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意（機能強化）
  - PyYAML（config/*.yaml の構文チェック用。未インストールでも動作はする）
- その他、標準ライブラリ（sqlite3, logging, threading, datetime など）

セットアップ手順（サンプル）
1. リポジトリをクローンし、src 以下を Python パッケージとして使えるようにする。
2. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール:
   - pip install duckdb psutil openai
   - （開発時）pip install pyyaml
4. .env の初期作成:
   - python -m kabusys.config_setup
     - ウィザードに従って J-Quants / kabuAPI パスワード等を入力してください。
   - もしくは .env を手動作成（.env.example を参照）。
5. 設定検証:
   - python -m kabusys.validate_config
   - 本番環境では --strict オプションを検討。
6. データディレクトリの確認:
   - デフォルトでは data/ 以下に DB 等を置きます（DUCKDB_PATH / SQLITE_PATH）。
   - ログは logs/ 以下へ保存（LOG_DIR で変更可能）。

使い方（主要スクリプト）
- 実行（ExecutionEngine）
  - 開発 / Paper / Live の切り替えは KABUSYS_ENV 環境変数（.env）で制御。
  - Paper Trading の場合、MockBrokerClient を使用し専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動:
    - python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag ファイルを作成すると安全に停止シグナルを受け取り終了します（run_execution はこのファイルを監視）。
    - KillSwitch（監視側）から data/kill.flag が書かれると ExecutionEngine に停止シグナルを送る設計になっています。
  - 実行中の PID ファイル:
    - data/execution.pid（設定により別パス可）

- 監視（Monitoring）
  - 起動:
    - python -m kabusys.run_monitoring
  - ポーリング間隔:
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を指定（デフォルト 60 秒）。
  - 停止:
    - data/stop_requested.flag を作成するとループを終了します。

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --db PATH --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB パスは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。

- AI / 研究機能（プログラム的に）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # 書き込み件数を返す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (default: development)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (monitoring DB, default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject (paper trading の約定動作)
- OPENAI_API_KEY (AI 機能を使う場合)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (アラート通知用、任意)
- LOG_LEVEL (DEBUG/INFO/...)
- LOG_DIR (ログディレクトリ、デフォルト logs/)
- KILL_FLAG_CLEAR_ON_START (0/1) — ExecutionEngine 起動時に既存の kill.flag を自動クリアする（本番では 0 推奨）
- MONITOR_POLL_INTERVAL (監視のポーリング間隔秒)

自動 .env のロード
- プロジェクトルート（.git または pyproject.toml を探す）を基に .env/.env.local を自動読み込みします。
- OS 環境変数が優先され、.env.local は .env を上書きできます。
- 自動ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

プロセス / フラグファイルの説明
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py が監視する停止用フラグ。存在するとループが終了します。
- data/kill.flag
  - monitoring 側の KillSwitch が作成するファイル。ExecutionEngine はこのファイルの存在を検知して安全停止します。
  - KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリアする設定があります（本番は推奨しない）。
- data/execution.pid
  - 実行エンジンの PID 保存ファイル（設定可能）。

ログ
- utils.logging_setup.setup_logging を各起動スクリプトで使用しています。
- デフォルトは logs/<app_name>.log（日次ローテーション、30日保管）と stdout に出力。
- ログレベルは LOG_LEVEL 環境変数または引数で指定可能。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py: パッケージ定義、バージョン
  - config.py: .env 自動読み込み、Settings クラス（環境変数アクセスの一元化）
  - config_setup.py: .env 対話式ウィザード
  - validate_config.py: 起動前設定検証 CLI
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py: ロギング初期化ユーティリティ
    - process_priority.py: プロセス優先度 / CPU affinity の設定ユーティリティ
  - monitoring/
    - monitoring_db.py: SQLite に対する永続化層（テーブル初期化・読み書き）
    - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py (監視関連)
  - execution/ (注文・エンジン関連: BrokerFactory, Engine, OrderManager, RiskManager, Reconciler 等)
  - portfolio/ (portfolio_builder.py, position_sizing.py, risk_adjustment.py)
  - research/ (factor_research.py, feature_exploration.py)
  - ai/
    - news_nlp.py: ニュースを LLM でスコアリングし ai_scores へ書込み
    - regime_detector.py: マクロ+MA によるレジーム判定と書込み
  - tools/
    - paper_verification_report.py: Paper Trading の検証レポート出力ツール

補足・運用上の注意
- 本番運用時（KABUSYS_ENV=live）は設定に十分注意してください。validate_config は本番チェックを助けます。
- KillSwitch や stop_requested.flag の挙動は冪等性・安全性を考慮して設計されていますが、ファイルの誤操作に注意してください。
- OpenAI API を利用する機能は API の利用状況に依存し、レート制限やエラー処理（リトライ・フォールバック）が組み込まれています。API キーは適切に管理してください。
- データベースファイル（DuckDB/SQLite）は運用データを格納するため、バックアップ・権限設定を適切に行ってください。
- ローカルでの開発と本番で DB を混同しないよう、paper_trading 用 DB を使って検証することを推奨します。

---

この README はコードベースの主要点をまとめたものです。実運用やカスタマイズを行う場合は、各モジュール（monitoring/*, execution/*, ai/*, research/*）のドキュメントやソースコード内の docstring を参照してください。必要があれば、各スクリプトや設定ファイルの具体的な使い方例（systemd ユニット / docker-compose / cron での起動例）も追記できます。