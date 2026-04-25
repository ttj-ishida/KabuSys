KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買・リサーチ・監視ユーティリティ群を含む
Python パッケージです。設計は本番運用を想定しており、発注（Execution）、
監視（Monitoring）、リサーチ（Research）、AI（ニュース NLP / レジーム判定）等の
コンポーネントで構成されています。

概要
----
KabuSys は以下のような機能を備えた自動売買システムのコアライブラリです。

- ExecutionEngine：発注ロジック、注文管理、リスク管理、Reconciler 等
- Monitoring：システム稼働状況、注文ログ、リスク検出 → Kill Switch 発動可能
- Portfolio モジュール：銘柄選定、重み計算、ポジションサイズ計算、セクター制約
- Research：DuckDB を使ったファクター計算・特徴量探索
- AI：ニュースの LLM によるセンチメントスコアリング / 市場レジーム判定
- ユーティリティ：ログ設定、プロセス優先度設定、.env ウィザード、設定検証 等

主な特徴
---------
- モジュール化された監視・発注スタック（MonitoringEngine / ExecutionEngine）
- Paper Trading（完全に本番 DB と分離）をサポート
- DuckDB を用いたオフライン解析・ファクター計算
- OpenAI を利用したニュースセンチメント / レジーム判定（任意）
- .env ウィザードと設定検証ツールを備え、運用前に設定不備を検出可能
- 日次ローテーションログ、プロセス優先度・CPU affinity の簡易設定

セットアップ手順
----------------

1. リポジトリをクローンし、仮想環境を作成して有効化します（例: venv）:
   - git clone <repo>
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（最低限）:
   - pip install duckdb psutil openai
   - 任意: PyYAML（config YAML 検証を有効化したい場合）

   ※ sqlite3 は標準ライブラリです。

3. .env を作成する（推奨）:
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 生成後、内容を確認し必要な環境変数（特に JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY (AI を使う場合)）を設定してください。

4. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ等を作成（通常は自動作成されますが明示的に作る場合）:
   - mkdir -p data logs

環境変数（主なもの）
-------------------
以下は主要な環境変数とデフォルト値（存在する場合）です。config_setup.py で入力が促されます。

- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用トークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI API を使う場合に必要
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB のデフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB デフォルト: data/paper_trading.db
- KABUSYS_ENV — execution の動作モード: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

自動 .env 読み込み
- 起動時にプロジェクトルート（.git または pyproject.toml のある場所）から .env を自動読み込みします。
- 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（主要スクリプト）
-----------------------

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- ExecutionEngine を起動（本番/ペーパートレード切替）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading モードでは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - KABUSYS_ENV=live python -m kabusys.run_execution
    - 本番では実際に発注します。十分に設定を確認してください。

  実行の挙動:
  - 起動時にプロセス優先度を "high" に設定し、監視用 SQLite / DuckDB に接続します。
  - data/stop_requested.flag が既に存在する場合は起動を中止します。
  - エンジンは別スレッドで run_session を実行し、stop フラグで停止できます。
  - PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）に書き込まれます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
  - 監視は本番 sqlite_path（SQLITE_PATH）を使用します（環境に関わらず本番用パスを使用する実装上の注意）。

- Paper Trading の検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

停止・Kill Switch / フラグファイル
---------------------------------
- Execution の停止指示はフラグファイル（data/stop_requested.flag, data/kill.flag など）で行われます。
  - run_execution / run_monitoring はプロジェクト内の data/stop_requested.flag を監視し、存在すると優雅に終了します。
  - KillSwitch（監視側コンポーネント）は条件を満たした際に data/kill.flag を書き込み、ExecutionEngine に停止を促します。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

ログ
---
- ログは以下の構成で出力されます（kabusys.utils.logging_setup が設定）:
  - コンソール（stdout）
  - 日次ローテートファイル: logs/<app_name>.log （30日保持）
- LOG_DIR 環境変数でログディレクトリを上書きできます。

主要モジュール説明
------------------
- kabusys.config
  - 環境変数/ .env の読み込みと Settings クラス（設定値のラッパ）。
  - 自動 .env ロード、必須値チェック機能を持つ。

- kabusys.execution
  - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler 等（発注ロジック）

- kabusys.monitoring
  - MonitoringEngine（複数モニタ統合）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringDB（SQLite 操作ラッパ）

- kabusys.portfolio
  - 銘柄選定（select_candidates）、重み計算（calc_equal_weights / calc_score_weights）、ポジション決定（calc_position_sizes）、セクター制約（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）

- kabusys.research
  - DuckDB を使ったファクター計算（momentum/volatility/value）、将来リターン・IC 計算など

- kabusys.ai
  - news_nlp: ニュースを LLM でセンチメント評価して ai_scores テーブルへ保存
  - regime_detector: ETF MA200 とマクロセンチメントを合成して market_regime を判定

- kabusys.utils
  - logging_setup: ログ設定ユーティリティ
  - process_priority: プロセス優先度・CPU affinity の設定ユーティリティ

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                 — 環境設定 / Settings
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring 起動スクリプト

subpackages:
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - risk_monitor.py
  - trade_monitor.py
  - alert_manager.py
  - kill_switch.py
- execution/
  - (ExecutionEngine, order_manager, broker_factory, risk_manager, reconciler, ...)
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
- tools/
  - paper_verification_report.py

運用上の注意
------------
- 本番（KABUSYS_ENV=live）での起動前に必ず python -m kabusys.validate_config で設定をチェックしてください。
- .env は絶対に機密情報を含めたまま VCS にコミットしないでください。
- OpenAI を使う機能（ニュース NLP / レジーム判定）は API キーが必須です。API コールは課金対象になります。
- Paper Trading は本番 DB と分離するよう実装されていますが、本番モードを誤って設定しないよう注意してください。

開発者向けメモ
---------------
- 自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
- logging_setup は既存ハンドラをクリアして再設定するため、ユニットテストで複数回呼ぶ場合の副作用に注意してください。
- DuckDB 接続は research / ai / regime_detector 等で使用します。テーブルスキーマはプロジェクトの data 構成に依存します。

この README はコードベースの主要部分を簡潔にまとめたものです。詳細な API 仕様や実運用手順は該当モジュール（コード内 docstring）と運用ドキュメントを参照してください。質問や追加したい項目があれば教えてください。