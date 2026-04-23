README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ基盤を目的とした Python パッケージです。  
市場ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、
LLM を用いたニュース NLP / レジーム判定など、トレーディング運用に必要な機能群を揃えています。

主な特徴
--------
- 発注エンジン（ExecutionEngine）と監視サービス（Monitoring）の分離起動
- Paper Trading モード（本番 DB と分離した SQLite を使用）をサポート
- DuckDB を用いた高速な価格・財務データ処理（研究モジュール）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（news_nlp）
- 市場レジーム判定（regime_detector）で資金配分の抑制を実施
- 監視 DB（SQLite）へのログ永続化・リスクモニタリング・Kill Switch
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、検証 CLI）
- Paper Trading 向け検証レポート生成ツール

必要条件（主な依存）
------------------
（プロジェクトの requirements ファイルが無い場合の代表的な依存）
- Python 3.9+
- duckdb
- psutil
- openai (LLM を利用する機能を使う場合)
- PyYAML (config/*.yaml の静的検証を行う場合)
- sqlite3（標準ライブラリ）

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロダクション運用に合わせてバージョン固定してください）

4. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env を作成 / 更新します。
   - .env には JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の機密値を含みます。絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。
   - 必須環境変数が未設定だとエラーになります。

基本的な使い方
---------------

環境変数の概念
- KABUSYS_ENV: 実行環境。'development' / 'paper_trading' / 'live' のいずれか。
  - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と完全分離）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の執行モード（instant/partial/never/reject、デフォルト: instant）
- LOG_LEVEL / LOG_DIR: ロギング設定
- OPENAI_API_KEY: OpenAI を利用する機能で必要

起動スクリプト
- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 動作:
    - Settings を読み取りプロセス優先度を high に設定
    - KABUSYS_ENV が paper_trading の場合は専用の paper_trading DB を使用
    - Engine はデーモンスレッドで run_session を実行し、data/stop_requested.flag があれば停止
    - 起動前に data/stop_requested.flag があれば起動を中止

- Monitoring（監視プロセス）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 監視は Settings.sqlite_path（本番 DB）を使用（KABUSYS_ENV に依存しない）
  - 監視ループは data/stop_requested.flag を検出すると終了する

ユーティリティ / CLI
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は env または data/paper_trading.db

主要モジュール（概要）
-------------------
- kabusys.config / Settings
  - 環境変数の読み込み・検証ロジック、.env 自動読み込み（プロジェクトルート検出）
- kabusys.execution
  - ExecutionEngine、OrderManager、RiskManager、Reconciler 等（発注関連）
  - BrokerClientFactory により本番/モックブローカーを切替
- kabusys.monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセスの生存確認、データ鮮度チェック
  - TradeMonitor: 注文の滞留・約定異常などの監視（該当ファイル参照）
  - RiskMonitor: ドローダウン・ポジション数制限の監視
  - KillSwitch: リスクトリガで data/kill.flag を書き、ExecutionEngine 停止指示
  - MonitoringDB: SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - MonitoringEngine: 各 Monitor を束ねるポーリングループ
- kabusys.portfolio
  - 銘柄選定（select_candidates）、重み算出（equal/score）、ポジションサイズ計算、セクター制約、レジーム乗数
- kabusys.research
  - factor_research: momentum / volatility / value の計算（DuckDB）
  - feature_exploration: forward returns / IC / 統計サマリー
- kabusys.ai
  - news_nlp.score_news: raw_news を OpenAI でスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM スコアを合成して market_regime に保存
- kabusys.tools
  - paper_verification_report: Paper Trading データの検証レポートを生成
- kabusys.utils
  - logging_setup.setup_logging: 一貫したログ設定（stdout + 日次ローテート）
  - process_priority.set_process_priority / set_cpu_affinity: プラットフォーム差を吸収した優先度設定

重要なファイル・パス（デフォルト）
--------------------------------
- .env                      — 環境変数ファイル（config_setup で作成）
- data/kabusys.duckdb       — DuckDB（DUCKDB_PATH）
- data/monitoring.db        — 監視用 SQLite（SQLITE_PATH）
- data/paper_trading.db     — Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/execution.pid        — ExecutionEngine PID（デフォルト）
- data/kill.flag            — Kill Switch フラグ（KillSwitch による書込み）
- data/stop_requested.flag  — run_* スクリプトの停止フラグ（外部から停止させる際に使用）
- logs/<app_name>.log       — 日次ローテートログ（LOG_DIR）

ディレクトリ構成
----------------
（主要な src/kabusys 以下を示します）
- src/kabusys/
  - __init__.py
  - config.py                — 環境設定ローダー / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
    - __init__.py
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py   (存在)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py   (存在)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

運用上の注意
-----------
- .env は機密情報を含むため、決してリポジトリへコミットしないでください。
- KABUSYS_ENV=live を使用する際は LINE 通知等の設定を確認し、Kill Switch の自動クリア設定（KILL_FLAG_CLEAR_ON_START）には注意してください。
- run_monitoring は監視 DB に本番 sqlite_path を使います。paper_trading とは独立して監視されます（意図的）。
- LLM（OpenAI）を利用する機能は API キー（OPENAI_API_KEY）が必要であり、API 呼び出しはコストとレイテンシを伴います。運用時はレート制限や失敗時のフォールバック動作を理解してください。
- ディスク・DB ファイルの親ディレクトリが存在しない場合、validate_config は警告を出しますが起動時に自動作成されることがあります。ログディレクトリ作成に失敗するとファイルログは無効化されます（コンソール出力のみ）。

開発者向けメモ
---------------
- DuckDB 接続を使う研究モジュールはテーブル名 prices_daily / raw_financials / raw_news 等を参照します。テスト用データの準備が必要です。
- monitoring/monitoring_db.py はスキーマの冪等初期化と簡単なマイグレーション処理を持っています。
- LLM 呼び出し部はテスト時に _call_openai_api をモックパッチする設計です（unittest.mock.patch が利用可能）。

問い合わせ
---------
- 不具合や質問はリポジトリの Issue へ立ててください。README に記載のない追加の実行方法や CI 設定がある場合はプロジェクト内ドキュメントを参照してください。

以上。