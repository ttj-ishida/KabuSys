README
=====

概要
---
KabuSys は日本株の自動売買・リサーチ基盤を想定した Python パッケージです。  
主な機能は以下のとおりです。

- 注文実行エンジン（ExecutionEngine）とそれを監視する Monitoring システム
- ポートフォリオ構築（銘柄選定・重み計算・株数決定）
- リサーチ用ファクター計算 / 特徴量探索
- ニュースの NLP スコアリング（OpenAI を利用）
- Paper Trading 用の検証レポート生成ツール
- 設定ウィザード（.env 生成）と起動前検証 CLI

本 README はリポジトリの src/kabusys 以下のコードベースに基づく使用手順と構成説明です。

主な機能一覧
--------------
- execution
  - 実際の発注処理を行う ExecutionEngine（kabuステーション API または MockBroker を利用）
  - OrderManager / OrderRepository / RiskManager / Reconciler 等のコンポーネント
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使い data/paper_trading.db に記録
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine による定期監視
  - KillSwitch（閾値超過時に data/kill.flag を書き込み Execution を停止させる仕組み）
  - monitoring_db：監視用 SQLite スキーマと永続化 API
- portfolio
  - 銘柄選定（select_candidates）、配分重み（equal/score）、ポジションサイズ計算（risk_based 等）
  - セクター上限・レジーム乗数などのリスク調整関数
- research
  - ファクター計算（momentum/value/volatility）と特徴量解析（forward returns / IC / summary）
  - DuckDB を用いた高速分析を想定
- ai
  - news_nlp: raw_news を OpenAI に送り銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: ETF の MA 乖離 + マクロニュースの LLM センチメントで市場レジーム判定
- tools
  - paper_verification_report: Paper Trading の検証レポートを標準出力に出すスクリプト
- utils
  - logging_setup: 統一的なログ設定（コンソール + 日次ローテーションファイル）
  - process_priority: psutil を使ったプロセス優先度設定 / CPU affinity

前提（Prerequisites）
--------------------
- Python 3.10 以上（ソースは型アノテーションで | を使用）
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - openai （AI 機能を利用する場合）
  - PyYAML（validate_config の YAML 検証を行う場合、任意）
- SQLite は標準ライブラリで利用可能

インストール（ローカル開発環境）
--------------------------------
1. リポジトリのルートで Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - validate_config の YAML 検証を有効にする場合: pip install pyyaml

   ※ requirements.txt がある場合:
   - pip install -r requirements.txt

3. 開発時にパッケージをインストール（オプション）
   - pip install -e src

.env と設定
------------
- 設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます。
- 必須環境変数（最低限設定が必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 主要な環境変数（一部）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
  - OPENAI_API_KEY: OpenAI を利用する機能で必要
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）

.env を対話的に作る / 更新する
------------------------------
プロジェクトルートから次を実行（src が PYTHONPATH に入るか、pip install -e した状態で）
- PYTHONPATH=src python -m kabusys.config_setup
（Windows の PowerShell 等では適宜環境変数の設定方法を変更）

設定の検証
----------
起動前に設定をチェックできます：
- PYTHONPATH=src python -m kabusys.validate_config
- 警告も FAIL 扱いにする場合:
  - PYTHONPATH=src python -m kabusys.validate_config --strict

使い方（起動スクリプト）
-----------------------
注意: パッケージを直接 import できるようにするため、プロジェクトルートから PYTHONPATH=src を指定するか pip install -e src を行ってください。

1) Monitoring を起動（常駐ポーリング）
- PYTHONPATH=src python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を変更可能（デフォルト 60 秒）。
  - 終了方法: Ctrl+C またはプロジェクトルート/data/stop_requested.flag を作成するとループが終了します。

2) Execution（発注エンジン）を起動
- PYTHONPATH=src python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
  - 実行中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag の作成で行います。

3) Paper Trading 検証レポート生成
- PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルトの DB パスは data/paper_trading.db。別パスを使う場合は --db または環境変数 PAPER_TRADING_SQLITE_PATH を指定。

4) AI 機能（ニュース NLP / レジーム判定）
- OPENAI_API_KEY を設定することで kabusys.ai.news_nlp.score_news, kabusys.ai.regime_detector.score_regime を利用可能
- これらは DuckDB 接続を受け取りデータベース内の raw_news / news_symbols テーブルを参照します。

停止・Kill Switch
------------------
- run_monitoring.py / run_execution.py はプロジェクトルートの data/stop_requested.flag をチェックして終了します。
- Monitoring の KillSwitch はしきい値（ドローダウンやポジション過多）を検出した場合 data/kill.flag を書き込み、Execution 側に停止合図を与える仕組みです。
- Execution 起動時の挙動は Settings.kill_flag_clear_on_start による自動クリア設定に注意（本番では無効化推奨）。

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日分保持）。
- setup_logging() により app_name を指定して統一的に設定されます。
- コンソール出力は stdout に出力されるため、cron 等でのリダイレクトに適しています。

主なコマンドまとめ
------------------
- 設定ウィザード: PYTHONPATH=src python -m kabusys.config_setup
- 設定検証:      PYTHONPATH=src python -m kabusys.validate_config [--strict]
- 実行エンジン起動: PYTHONPATH=src python -m kabusys.run_execution
- 監視起動:      PYTHONPATH=src python -m kabusys.run_monitoring
- Paper 検証レポート: PYTHONPATH=src python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要なファイル/ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py

開発上の注意点・ヒント
---------------------
- パッケージをモジュールとして実行する際は PYTHONPATH=src を忘れないか、pip install -e src しておくこと。
- run_monitoring/run_execution はプロセス優先度を上げようとします（psutil による操作）。権限により警告となる場合がありますが、致命的ではありません。
- validate_config は PyYAML がないと YAML の中身検証をスキップします（インストール推奨）。
- OpenAI API を使う機能は API レート制限やネットワークエラーに対してリトライロジックを備えていますが、API キーと利用上限には注意してください。
- データベースファイルはデフォルトで data/ 以下に作られます。複数環境（paper_trading と live）で DB を分ける設計になっています。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

問い合わせ
--------
- コードの理解・拡張やセットアップで問題があれば、該当モジュール（例: monitoring/system_monitor.py, execution/execution_engine.py）を参照してください。README に足りない情報や追記したい点があれば教えてください。