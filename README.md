# KabuSys

日本株向け自動売買・データ分析フレームワークの一部コードベースです。本READMEはリポジトリ内の主要スクリプト / モジュール群をもとに、日本語で使い方・セットアップ方法・ディレクトリ構成をまとめたものです。

注意: このREADMEは該当コードの説明用ドキュメントです。実際の運用前に必須環境変数や設定（APIキー、パスワード、DBパス等）を必ず適切に設定したうえで、`validate_config` による検証を行ってください。

概要
- KabuSys は監視（Monitoring）、発注実行（Execution）、ポートフォリオ構築、リサーチ（ファクター計算／特徴量解析）、AI を用いたニュースセンチメント評価等の機能を含むモジュール群です。
- SQLite（監視/ペーパー用）と DuckDB（分析用）を併用し、ログ・ダッシュボード・取引ログなどを永続化します。
- 本番（live）・ペーパートレード（paper_trading）・開発（development）の環境切り替えをサポートします。
- OpenAI を利用したニュースNLP / レジーム検出機能（APIキー必須）を備えます。

主な機能一覧
- 実行／監視
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV に応じて本番/ペーパートレードを分離。
  - run_monitoring.py: SystemMonitor を定期ポーリングしてシステム状態を記録。
  - kill_switch: データ駆動で ExecutionEngine を停止するフラグを書き込む仕組み（data/kill.flag）。
- 監視関連
  - monitoring_db: SQLite に監視用テーブル群（system_status, trade_logs, positions, risk_logs, dashboard）を初期化・操作。
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, alert_manager 等（各種監視ロジック）。
- 発注関連（Execution）
  - BrokerClientFactory / ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager（発注、リスク管理の基盤）。
  - Paper trading：KABUSYS_ENV=paper_trading 時は MockBrokerClient を用い、ペーパーデータは data/paper_trading.db に記録。
- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder: 候補選定、等重・スコア加重の重み計算。
  - portfolio.position_sizing: 発注株数計算（リスクベース、等分配など）、単元（lot）丸め、aggregate cap 処理。
  - portfolio.risk_adjustment: セクター上限適用、レジーム乗数計算。
- リサーチ（DuckDB を利用）
  - research.factor_research: モメンタム／ボラティリティ／バリュー等のファクター計算（prices_daily, raw_financials を参照）。
  - research.feature_exploration: 将来リターン、IC（スピアマン ρ）、統計サマリ等。
- AI（OpenAI）
  - ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini 等）でセンチメントスコアを算出し ai_scores に書き込む（バッチ処理、リトライ、バリデーション実装）。
  - ai.regime_detector: ETF（1321） MA200乖離 + マクロニュースセンチメントを合成して日次レジーム判定を行い market_regime テーブルへ保存。
- ユーティリティ
  - utils.logging_setup: 統一的なログ設定（コンソール stdout + 日次ローテートファイル）。
  - utils.process_priority: プロセス優先度・CPU affinity 設定（Windows/Linux 対応）。
  - config: .env 自動読み込み・Settings 抽象化。
  - config_setup: .env の対話式ウィザード生成。
  - validate_config: .env と config/*.yaml の存在・整合性チェック。
- ツール
  - tools.paper_verification_report: ペーパートレード DB（data/paper_trading.db）をもとに各種指標（稼働率、約定率、レイテンシ等）を集計してレポート出力。

セットアップ手順（概略）
1. Python 環境
   - Python 3.9+ を想定（duckdb, psutil, openai 等のサポートを確認してください）。
2. 必要パッケージのインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（config/*.yaml の内容検証を行う場合に必要）
   - 例: pip install duckdb psutil openai PyYAML
   - 実際のプロジェクトでは requirements.txt を用意している場合はそちらを使用してください。
3. 初期設定（.env）
   - 対話式ウィザードで .env 作成:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限設定が必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 主な環境変数（デフォルト値あり）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL, LOG_DIR
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START（停止フラグ関連）
     - PAPER_FILL_MODE（paper trading の約定挙動）
4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いにできます。
5. データディレクトリ
   - data/ ディレクトリ（デフォルトの DB / PID / flag を格納）を作成します。多くのコードは必要に応じて自動作成しますが、権限など確認してください。
6. ログ
   - デフォルトログディレクトリ: logs/
   - ログ設定は kabusys.utils.logging_setup.setup_logging を通して行われます。

使い方（主要な起動・実行コマンド）
- 環境変数の設定（一時的に上書きする例）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 説明: data/stop_requested.flag が存在するとループを終了します。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60秒）。監視は常に本番 sqlite_path を使用します。
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 説明: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、専用の paper_sqlite_path（デフォルト data/paper_trading.db）へ記録。本体実行は別スレッドで行われ、data/stop_requested.flag を検出すると停止します。
- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 例: python -m kabusys.validate_config --strict
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は env または data/paper_trading.db
- AI 関連（プログラムから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

運用上の注意 / フラグ・ファイル
- Kill Switch / Stop フラグ
  - data/kill.flag: Kill Switch が発動したことを示すファイル（ExecutionEngine 停止シグナル）。
  - data/stop_requested.flag: run_monitoring / run_execution が外部停止を検出するためのファイル。
  - 起動時の挙動: Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動削除します（本番では 0 を推奨）。
- PID ファイル
  - data/execution.pid（デフォルト）を ExecutionEngine が使用します。
- Paper trading 分離
  - 本番 DB（monitoring.db 等）とペーパー用 DB は明示的に分離されます（PAPER_TRADING_SQLITE_PATH を使用）。

ディレクトリ構成（主なファイル・モジュール）
- src/
  - kabusys/
    - __init__.py
    - config.py              — 環境変数読み込み / Settings
    - config_setup.py        — .env 対話式ウィザード
    - validate_config.py     — 起動前の設定検証 CLI
    - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py       — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — ペーパートレード検証レポート生成
    - ai/
      - __init__.py
      - news_nlp.py           — ニュースを OpenAI でスコア付けする処理
      - regime_detector.py    — レジーム判定（MA200 + マクロセンチメント）
    - monitoring/
      - monitoring_db.py     — SQLite テーブル初期化・永続化 API
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - trade_monitor.py (参照されるが本一覧には省略あり）
      - alert_manager.py (参照されるが本一覧には省略あり）
    - execution/
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/ (上記)
    - monitoring_db、tools など（上記参照）
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - data/ (実行時に作成される想定)
      - monitoring.db（デフォルト SQLite）
      - paper_trading.db（ペーパー用）
      - kabusys.duckdb（分析用）
      - execution.pid, kill.flag, stop_requested.flag

設定の検証と安全策
- 本番 (KABUSYS_ENV=live) での起動前に必ず validate_config を実行してください。LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の設定等、本番固有の警告が出力されます。
- OpenAI 経由の自動決定ロジックを利用する場合、API リクエストのエラーや JSON バリデーション、スコアのクリッピング等の保護ロジックが組み込まれていますが、運用では API キーのレート制限や課金に注意してください。
- process_priority はプラットフォーム依存の権限制約（Linux の nice 値や Windows の優先度）で失敗する場合があるため、失敗時は警告ログが出力されます。

開発者向けの補足
- DuckDB を用いたリサーチ系関数は DuckDB 接続を受け取り SQL で処理します。テスト用に軽量な DuckDB ファイルを用意すると良いです。
- 一部モジュールは外部ライブラリ（openai, psutil, duckdb, PyYAML 等）に依存します。CI / dev 環境にこれらを追加してください。
- ログは kabusys.utils.logging_setup.setup_logging を起動時に呼ぶことで統一されます。ログディレクトリ作成に失敗した場合はコンソールのみの出力になります。

よく使うコマンドまとめ
- .env の作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視開始
  - python -m kabusys.run_monitoring
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動
  - python -m kabusys.run_execution
  - ペーパートレードで起動する例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
- このリポジトリは自動売買システムの核となるロジック群を含みます。実資金での運用は重大なリスクを伴います。十分な検証・バックテスト・モニタリング体制を整えたうえで運用してください。
- 追加のドキュメント（設計仕様 / PortfolioConstruction.md / StrategyModel.md 等）がある場合はそちらも参照してください（コード内コメントや docstring に実装方針が多く記載されています）。

必要があれば、README に含める具体的な .env のサンプル、より詳しいデプロイ手順（systemd / supervisor 用のサービス設定例）、CI/CD 用のチェックリストなども作成します。どの情報を追加しますか？