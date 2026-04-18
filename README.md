README
=====

概要
----
KabuSys は日本株の自動売買システム向けユーティリティ群とコアロジック群を含む Python パッケージです。
主な目的は以下の通りです。

- 注文実行エンジン（ExecutionEngine）・発注管理・リスク管理の補助
- 監視（Monitoring）・アラート発行・Kill Switch
- ポートフォリオ構築（候補選定・配分・株数算出）
- 研究用ファクター計算・特徴量探索（DuckDB ベース）
- ニュース NLP を用いたセンチメント評価 / レジーム判定（OpenAI 利用オプション）
- ペーパートレード検証ツール（レポート生成）

主な機能
--------
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に分離保存
  - プロセス優先度設定・PID ファイル管理・停止フラグ監視をサポート
- 監視ループ起動スクリプト: run_monitoring.py
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
  - SystemMonitor / TradeMonitor / RiskMonitor を周期的に実行し DB に永続化
- 設定ウィザード: config_setup.py
  - 対話式で .env を生成・更新（.env は絶対に Git にコミットしないでください）
- 設定検証 CLI: validate_config.py
  - .env と config/*.yaml（存在する場合）を事前チェック。--strict オプションで警告も失敗扱い
- Paper Trading 検証レポート: tools/paper_verification_report.py
  - ペーパートレード用 SQLite DB を読み取り稼働率 / 約定・送信率 / レイテンシ等を集計して判定
- ポートフォリオ構築モジュール（純粋関数群）
  - 候補選定、等ウェイト／スコア加重、ポジションサイジング、セクター制限、レジーム乗数
- 研究モジュール（DuckDB 前提）
  - ファクター計算（Momentum / Volatility / Value）・将来リターン・IC 計算・統計サマリ
- AI モジュール（OpenAI 依存、任意）
  - ニュースセンチメント集計（news_nlp）・市場レジーム判定（regime_detector）
- ログ設定ユーティリティ
  - コンソール(stdout) と 日次ローテートファイル出力（logs/<app_name>.log）

前提・依存関係
--------------
主な依存（環境や機能により必要なものが変わります）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を使う場合）
- （SQLite 標準ライブラリを使用）

インストール（例）
------------------
1. 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージ依存をインストール:
   - pip install duckdb psutil openai pyyaml
     （AI 関連や YAML 検証を使わない場合は openai / pyyaml は不要）

初期セットアップ
---------------
1. .env の作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - 生成した .env はプロジェクトルートに保存される（デフォルト）

   自動 .env ロード:
   - モジュール import 時にプロジェクトルート (.git または pyproject.toml を起点) が見つかれば
     自動で .env（→ .env.local が存在すれば上書き）を読み込みます。
   - 自動ロードを無効化する場合:
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

2. 設定検証:
   - python -m kabusys.validate_config
   - 厳密モード（警告も FAIL）: python -m kabusys.validate_config --strict

3. DB/ディレクトリ
   - デフォルトでは以下を参照 / 作成:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading DB: data/paper_trading.db (paper_trading 環境)
     - ログディレクトリ: logs/
   - 起動スクリプトは必要に応じて監視用テーブル等を自動作成（init_monitoring_db）

主要コマンド / 使い方
--------------------

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading DB に書き込みます
    - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します
    - 実行中は data/execution.pid に PID を書きます
    - 停止は data/stop_requested.flag を作成することで行えます（Kill Switch とは別）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番の sqlite_path を使用（環境に依らず）
  - stop フラグ: プロジェクトルート/data/stop_requested.flag を置くと監視ループは終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

環境変数（主なもの）
-------------------
- KABUSYS_ENV
  - 値: development | paper_trading | live （デフォルト: development）
  - paper_trading の場合は本番 DB から分離された paper_trading DB を使用

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定モデル、instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（ログ保存ディレクトリ、デフォルト: logs/）
- MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト: 60）
- KILL_FLAG_PATH（Kill Switch 用 flag のパス、デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1。デフォルト: 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env ロードを無効化）

停止・Kill Switch・フラグ
------------------------
- stop_requested.flag（プロジェクトルート/data/stop_requested.flag）
  - run_execution / run_monitoring が検出すると安全に停止します（手動停止用）
- execution.pid（data/execution.pid）
  - run_execution が PID を書き込む
- kill.flag（data/kill.flag）
  - KillSwitch が条件を満たした場合に書き込まれ、ExecutionEngine に停止シグナルを送るために使用されます
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に自動クリアされます（本番では注意）

ロギング
--------
- ログ設定ユーティリティ (kabusys.utils.logging_setup.setup_logging) を全起動スクリプトが呼び出します
- 出力:
  - stdout（StreamHandler）
  - 日次ローテートファイル: logs/<app_name>.log（TimedRotatingFileHandler、デフォルト 30 日保持）
- ログレベルは LOG_LEVEL 環境変数 / setup_logging 引数で制御

注意点 / ヒント
---------------
- .env は絶対にリポジトリにコミットしないでください（秘密情報が含まれます）
- Paper trading は本番 DB と完全分離するよう設計されています。テスト時は KABUSYS_ENV=paper_trading を利用してください
- AI 関連（news_nlp / regime_detector）は OpenAI API を使います。API キーと料金に注意してください。API 呼び出しはリトライやフォールバック（失敗時は 0.0）を備えていますが、重要な自動売買決定に直接依存する場合は慎重に運用してください
- validate_config.py は起動前チェックに有用です。--strict オプションで警告もエラー扱いにできます
- DuckDB は分析用に使用されます。prices_daily / raw_financials / raw_news 等のテーブルが必要です

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                   # 環境変数管理・自動 .env ロード
    config_setup.py             # .env 対話ウィザード
    validate_config.py          # 設定検証 CLI
    run_execution.py            # ExecutionEngine 起動スクリプト（エントリポイント）
    run_monitoring.py           # Monitoring ポーリング起動スクリプト（エントリポイント）
    tools/
      paper_verification_report.py
    ai/
      news_nlp.py
      regime_detector.py
    monitoring/
      monitoring_db.py
      system_monitor.py
      trade_monitor.py          # （コードベースに存在）
      risk_monitor.py
      monitoring_engine.py
      kill_switch.py
      alert_manager.py          # （コードベースに存在）
    execution/
      execution_engine.py       # （コードベースに存在）
      order_manager.py
      order_repository.py
      reconciler.py
      broker_factory.py
      risk_manager.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    utils/
      logging_setup.py
      process_priority.py
    data/                       # 実行時に生成されることが多い（DB / flags / pid 等）
      monitoring.db
      paper_trading.db
      kabusys.duckdb
      stop_requested.flag
      execution.pid
      kill.flag

（注）上記は本リポジトリ内の主要ファイルを抜粋したものです。実際の配布パッケージではファイル配置が若干異なる場合があります。

ライセンス・貢献
----------------
プロジェクト固有のライセンスや貢献ガイドラインがある場合はリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください。

問い合わせ
----------
不明点やバグ報告、機能要望はリポジトリの Issue トラッカーへお願いします。

おわり。