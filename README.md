KabuSys
=======

日本株向けの自動売買・研究プラットフォームの一部（ライブラリ + 起動スクリプト群）。  
このリポジトリは取引実行エンジン、監視系、ファクター計算、ニュースNLP（OpenAI 利用）などの主要コンポーネントを含みます。

概要
----
KabuSys は以下の関心を分離したモジュールで構成されています。

- ExecutionEngine（発注・リスク管理・注文管理）
- Monitoring（システム稼働監視、トレード監視、Kill Switch）
- Research（ファクター計算・特徴量解析）
- AI（ニュース NLP によるセンチメント評価・レジーム検出）
- Portfolio（銘柄選定・重み付け・ポジションサイズ計算）
- ユーティリティ（ログ設定・プロセス優先度設定・設定管理）

主な特徴
---------
- 起動スクリプト（run_execution, run_monitoring）で実運用とペーパートレードを分離
- SQLite（監視/注文履歴）と DuckDB（分析/リサーチ）を併用
- OpenAI API を用いたニュースセンチメント評価（AI モジュール）
- 監視モジュールは Kill Switch を発行し、重大なリスクがある場合は ExecutionEngine を停止
- 設定ウィザード（.env 生成）・設定検証 CLI を提供
- ファクター計算やポートフォリオ構築は純粋関数として実装されテスト容易

前提（Prerequisites）
--------------------
- Python 3.10 以上（| 型注釈などを使用）
- インストール推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config 検証時に YAML パースを行う場合）
- 任意: 仮想環境 (venv / virtualenv)

セットアップ手順
----------------

1. リポジトリをクローンして移動
   - git clone ... && cd <project>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （config.yaml のパース検証を使うなら）pip install pyyaml

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. 環境変数の初期設定（.env）
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（主要な環境変数は下記参照）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題があればエラー / 警告が出ます。--strict を付けると警告も失敗扱いになります。

主要な環境変数
----------------
（config_setup で扱う/Settings で参照されるものの主要一覧）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
- MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒、デフォルト 60）

起動方法（使い方）
-----------------

- 監視ループ起動（SystemMonitor 単体ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - run_monitoring は stop_requested.flag（data/stop_requested.flag）存在で終了

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB に記録
  - 起動中に data/stop_requested.flag を作成すると安全に停止させられます

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として扱い exit code 1

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB を指定可能

監視 / 停止フラグ、PID
-----------------------
- Kill Switch 用フラグ: data/kill.flag（KillSwitch が書き込む）
- 起動停止監視用フラグ: data/stop_requested.flag（run_* スクリプトが参照）
- 実行エンジンの PID ファイル: data/execution.pid（Settings.pid_file_path で参照）

主要なモジュール説明
--------------------

- kabusys.config
  - 環境変数 /.env 自動読込・Settings クラスを提供

- kabusys.config_setup
  - .env を対話式に作成・更新するウィザード

- kabusys.validate_config
  - .env と config/*.yaml の基本的な事前検証を行う CLI

- run_execution.py
  - ExecutionEngine の起動スクリプト。paper_trading モードは DB を分離

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL により間隔を変更可能

- kabusys.monitoring
  - monitoring_db.py: SQLite のスキーマ初期化と永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/MEM/DISK/プロセス存在チェック、データ鮮度チェック
  - trade_monitor.py: （トレード関連監視ロジック）
  - risk_monitor.py: ドローダウン、ポジション数上限の監視
  - kill_switch.py: 条件により data/kill.flag を書き込む
  - monitoring_engine.py: 各 Monitor の連携とアラート発行

- kabusys.execution
  - Broker クライアントファクトリ、ExecutionEngine、OrderManager、RiskManager、Reconciler 等（発注フロー）

- kabusys.portfolio
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 発注株数算出・丸めロジック
  - risk_adjustment.py: セクター上限・レジーム乗数

- kabusys.research
  - factor_research.py: モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB 利用）
  - feature_exploration.py: 将来リターン、IC、統計サマリ等

- kabusys.ai
  - news_nlp.py: raw_news を OpenAI に送信して ai_scores に書き込む（バッチ・リトライ・バリデーション実装）
  - regime_detector.py: ETF MA とマクロニュースの LLM 評価を合成して市場レジームを判定し保存

- kabusys.utils
  - logging_setup.py: ルートロガーの初期設定（コンソール + 日次ローテーションファイル）
  - process_priority.py: プラットフォーム横断のプロセス優先度 / CPU affinity 設定ユーティリティ

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
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
  - alert_manager.py (存在すれば)
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - risk_manager.py
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
- monitoring/
  - monitoring_db.py (DB 層)
- tools/
  - paper_verification_report.py

運用上の注意
-------------
- KABUSYS_ENV=live の場合は本番運用になります。設定（API トークン・Kill Switch など）は慎重に行ってください。
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダーにも警告あり）。
- OpenAI 利用機能は API キーが必要で、コストが発生します。使用頻度とバッチサイズを運用方針に合わせて調整してください。
- run_execution/run_monitoring は stop_requested.flag や kill.flag で安全に操作できます。デプロイ先のファイルパーミッションに注意してください。

サポート・拡張
--------------
- DuckDB のスキーマ（prices_daily, raw_news, raw_financials など）を準備しておくと research/ai 機能を有効にできます。
- config/*.yaml（system_config.yaml 等）は各種設定ファイル。ない場合は generate_config スクリプト等で生成できます（リポジトリ内のスクリプトがある場合）。

附記
----
この README はソースコードの docstring と設定ロジックに基づいて作成されています。詳細な挙動や追加コマンドラインオプションは各モジュールの docstring / ヘルプ（python -m モジュール）を参照してください。