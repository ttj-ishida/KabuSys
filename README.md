README.md

プロジェクト概要
--------------
KabuSys は日本株向けの自動売買・研究基盤です。シグナル生成、ポートフォリオ構築、注文発行（本番 / ペーパートレード）、監視（システム／注文／リスク）、およびニュース NLP / レジーム判定などの補助機能を備えています。データ解析には DuckDB、監視／履歴には SQLite を使用します。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 本番 (live) / ペーパートレード (paper_trading) を切替可能。ペーパートレードは専用 SQLite に記録され、本番 DB と分離されます。
  - リスク管理(RiskManager)、注文管理(OrderManager)、再整合(Reconciler) 等のコンポーネントを組み合わせて動作。
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリングしてシステム健全性を記録。
  - KillSwitch によるフラグファイルで ExecutionEngine を停止可能。
  - MonitoringDB（SQLite）への永続化・履歴保持。
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み計算（等金額・スコア加重）、位置サイズ計算（risk_based 等）、セクター上限適用、レジーム乗数。
- Research（研究用モジュール）
  - ファクター計算（モメンタム、バリュー、ボラティリティなど）、将来リターン、IC/統計サマリ。
  - DuckDB を利用した高速集計。
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を使ったニュースのセンチメント評価と市場レジーム判定。
  - バッチ処理、JSON レスポンス検証、リトライ/バックオフ対応。
- ユーティリティ
  - .env 対話式ウィザード（config_setup）、設定検証 CLI（validate_config）、ログ設定ユーティリティ、プロセス優先度設定等。
- ツール
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを出力。

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - プロジェクトルートは .git / pyproject.toml を基準に自動判定します。

2. Python 仮想環境（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須（代表例）:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config/*.yaml のパース検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを使用してください。

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成（.env.example を参照）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いします。

6. ディレクトリ／ファイル
   - デフォルトの DB / ログ / PID / フラグ は以下を参照（必要に応じて .env で上書き）。
     - DuckDB: data/kabusys.duckdb (環境変数: DUCKDB_PATH)
     - SQLite (monitoring): data/monitoring.db (SQLITE_PATH)
     - Paper trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
     - ログ: logs/ (LOG_DIR)
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

使い方（主要スクリプト）
-----------------------
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用して data/paper_trading.db に記録します。
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
  - 停止方法: data/stop_requested.flag を作成すると実行スレッドが検知して停止します（または KillSwitch が data/kill.flag を書き込み ExecutionEngine 停止をトリガー）。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（監視ログは本番 DB に保存）。

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告を FAIL 扱いにします。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

主要な環境変数（抜粋）
---------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 推奨
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL (デフォルト: INFO)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使う場合）
  - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
  - KILL_FLAG_CLEAR_ON_START: 0|1（1 にすると起動時に kill.flag を自動クリア）
  - MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒）

データ分離について
------------------
- ペーパートレードモード (KABUSYS_ENV=paper_trading) は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番の monitoring DB と分離します。
- 監視（Monitoring）は設計上、本番 sqlite_path を参照する仕様です。環境にかかわらず同じ sqlite_path を使用します。

停止と Kill Switch
------------------
- run_execution / ExecutionEngine の停止:
  - 外部から data/stop_requested.flag を作成すると run_execution 側が検知して Engine を停止します（※実行スレッド内で定期的にフラグを確認）。
- KillSwitch:
  - RiskMonitor 等が条件を満たすと data/kill.flag を書き込み、ExecutionEngine 停止を促します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag を消去します（本番では 0 推奨）。

ログ
----
- デフォルトは logs/<app_name>.log（毎日ローテート、30 日分保持）。
- setup_logging(app_name="execution" | "monitoring" 等) で統一的に設定されます。
- 標準出力は stdout に出力されます（cron 等の出力統合を想定）。

開発 / 研究向け
----------------
- research モジュールは DuckDB の prices_daily / raw_financials 等テーブルからファクターを計算します。データ投入は別途データパイプラインを利用してください。
- AI モジュール（news_nlp, regime_detector）は OpenAI を呼び出します。API キーとレート制限に注意してください。失敗時はフォールバック（スコア 0.0 等）して継続する実装です。

ディレクトリ構成
----------------
（プロジェクトルート）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - execution/                — 発注エンジン関連（Engine, OrderManager, BrokerFactory, RiskManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル作成 / CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に使用する DB / PID / フラグ 等を格納する想定)
- config/                     — YAML 設定ファイル群（system_config.yaml など。テンプレート生成スクリプトあり）
- logs/                       — ログ出力先（既定）
- pyproject.toml / setup.cfg 等（プロジェクト管理ファイル）

注意事項 / ベストプラクティス
-----------------------------
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- 本番環境では KABUSYS_ENV=live を使う前に validate_config を実行してすべての設定を確認してください（LINE 通知設定等のチェックがあります）。
- OpenAI を利用する機能は API コストとレート制限に注意して運用してください。API 呼び出しはバックオフ・リトライを実装していますが、費用は発生します。
- ログディレクトリ、data ディレクトリは適切なパーミッションで配置してください。
- psutil によるプロセス優先度／CPU affinity 操作は OS に依存し、権限不足などで失敗することがあります（警告が出力されますが処理は継続します）。

ライセンス / 貢献
-----------------
（ここにライセンス情報やコントリビュート手順を記載してください）

以上。README の不足点や、特定機能（ExecutionEngine の詳細な起動オプションや Broker 実装、DB スキーマの説明など）について追記希望があれば教えてください。