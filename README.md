KabuSys — 日本株自動売買システム
=================================

このリポジトリは、日本株向けの自動売買システム KabuSys のコアライブラリ群です。
バックテスト／リサーチ、ポートフォリオ構築、発注実行、監視、AI を使ったニュース評価などの
機能を含みます。本 README はコードベース（src/kabusys）を対象にした利用ガイド兼導入手順です。

要約（Project 概要）
------------------
- Python ベースのモジュール群で構成された自動売買システムのコア。
- 主な機能: ファクター計算、特徴量探索、ポートフォリオ構築、ポジションサイズ計算、発注エンジン、監視エンジン、AI ベースのニュースセンチメント、設定ウィザード／検証ツール。
- 発注系は本番（live）・ペーパートレード（paper_trading）を区別。ペーパートレード時は専用 DB に記録して本番 DB と分離。

主な機能一覧
--------------
- config_setup: .env を対話式に作成・更新するウィザード（python -m kabusys.config_setup）。
- validate_config: .env / config/*.yaml の設定検証ツール（python -m kabusys.validate_config）。
- run_execution: ExecutionEngine 起動スクリプト。KABUSYS_ENV によって実 DB / モックを切り替え。
- run_monitoring: SystemMonitor のポーリングループ起動スクリプト。システムの稼働状況やデータ鮮度を記録。
- monitoring: risk_monitor / trade_monitor / system_monitor / kill_switch / monitoring_engine / monitoring_db — 監視・アラート・Kill Switch 機能。
- portfolio: 候補選定・重み計算・ポジションサイズ計算・セクター調整・レジーム乗数。
- research: ファクター計算（momentum/value/volatility）・特徴量探索（forward returns / IC / summary）。
- ai: news_nlp（OpenAI を用いた銘柄別ニュースセンチメント）、regime_detector（マクロセンチメント + 指標合成によるレジーム判定）。
- tools.paper_verification_report: ペーパートレードの検証レポート生成ツール。

前提（Requirements）
-------------------
- Python 3.10+
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai
- 任意（機能により必要）:
  - PyYAML（validate_config で config/*.yaml を検証する場合）
- 標準モジュール: sqlite3, logging 等

セットアップ手順
----------------
1. リポジトリをクローン / 配置
   - 本 README はパッケージルートにあることを想定します（src/ を PYTHONPATH に含めるか、パッケージとしてインストール）。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （オプション）pip install PyYAML

4. .env 初期作成（推奨）
   - 対話式ウィザード: python -m kabusys.config_setup
     - J-Quants のトークン / kabuステーション API パスワード 等の必須値を入力します。
   - もしくは .env を自分で作成してください（下の環境変数一覧参照）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります: python -m kabusys.validate_config --strict

6. （初回）データディレクトリ作成など
   - デフォルトでは data/ 以下に DB ファイルやフラグファイルが作られます。必要に応じて .env のパスを変更してください。

主要な環境変数（代表例）
------------------------
以下は主要な環境変数の抜粋。必須は太字で示します。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY（AI 機能を利用する場合）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading: MockBroker を使用し data/paper_trading.db に記録
  - live: 本番動作
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB; デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- LOG_DIR (logs ディレクトリを変更する場合)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒。デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (0/1) — ExecutionEngine 起動時に kill.flag を自動クリアするか

基本的な使い方
----------------

- 実行スクリプト（パッケージ経由で起動可能）
  - 監視ループ起動（SystemMonitor ポーリング）:
    - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を秒で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
    - 監視は常に settings.sqlite_path（監視用 DB）を使用する設計です。
  - 実行エンジン起動（ExecutionEngine）:
    - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録。live 時は本番 DB（SQLITE_PATH）を使用。
  - 設定ウィザード:
    - python -m kabusys.config_setup
  - 設定検証:
    - python -m kabusys.validate_config
  - ペーパートレード検証レポート:
    - python -m kabusys.tools.paper_verification_report
    - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- 停止方法 / Kill Switch
  - run_monitoring と run_execution は stop_requested.flag を検知するとループを終了します。
    - 停止フラグファイル: data/stop_requested.flag（プロジェクトルートの data/ 以下）
  - KillSwitch は監視ロジックで特定条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側で検知して安全停止させます。
  - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START を参照して kill.flag を自動消去する設定があります（本番では 0 推奨）。

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。
  - setup_logging でログディレクトリ（LOG_DIR）やログレベル（LOG_LEVEL）を制御可能。
- コンソール出力は stdout に書かれます（systemd / cron 等でリダイレクトしやすくするため）。

データベース
-----------
- DuckDB: 分析用データベース（デフォルト data/kabusys.duckdb）。research / ai の処理で使用。
- SQLite: 監視・発注ログ等（デフォルト data/monitoring.db）。ペーパートレード時は専用 DB（data/paper_trading.db）に分離。
- monitoring_db.init_monitoring_db は冪等にテーブルやマイグレーションを行います。初回起動時に自動でテーブル作成されます。

ツール例
--------
- レポート生成（ペーパートレード検証）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  - 簡単な合格基準（稼働率・成立率・送信率・P95 レイテンシ）をもとに PASS/FAIL を判定します。

ディレクトリ構成（重要ファイル抜粋）
-----------------------------------
（src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings 管理
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_monitoring.py      — SystemMonitor のポーリング起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py     — ログ設定ユーティリティ
    - process_priority.py  — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py     — SQLite の永続化（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/              — ExecutionEngine 周りの実装（BrokerFactory, OrderManager など）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

設計上の注意点 / 実運用時の注意
-----------------------------
- KABUSYS_ENV を必ず確認してください。live モードは実際に発注が行われます。
- 本番環境では KILL_FLAG_CLEAR_ON_START を 0 にすること（誤って Kill Switch をクリアしてしまわないようにするため）。
- OpenAI の呼び出しは外部 API なので、API キー管理・レート制限・コストに注意してください。news_nlp と regime_detector はリトライ・フォールバック戦略を実装していますが、運用時は監視が必要です。
- process_priority.set_process_priority で優先度変更を試みますが、権限不足やプラットフォーム差分で失敗する可能性があります（ログに警告が出ます）。
- DB マイグレーションやスキーマ変更は init_monitoring_db で一部対応していますが、重要な変更は慎重にテストしてください。

よくある操作コマンド（例）
-------------------------
- .env を作る:
  - python -m kabusys.config_setup
- 設定を検証:
  - python -m kabusys.validate_config
- 監視を開始:
  - export MONITOR_POLL_INTERVAL=60
  - python -m kabusys.run_monitoring
- エンジンを開始:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
-----
この README はコードベースの概要と実行に必要な情報をまとめたものです。詳細な実装やアルゴリズム（PortfolioConstruction.md や StrategyModel.md 等の設計ドキュメント参照箇所）はコード内の docstring や別の設計文書を参照してください。質問や補足があれば教えてください。