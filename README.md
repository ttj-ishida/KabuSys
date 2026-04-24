README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買/研究プラットフォームのコアライブラリです。  
システムは主に以下の責務を持ちます:

- 市場データ・ファクターの計算（research）
- ポートフォリオ構築とポジションサイジング（portfolio）
- 発注・リスク管理を担う ExecutionEngine（execution）
- システム稼働監視・アラート・キルスイッチ（monitoring）
- ニュースの NLP スコアリングと市場レジーム判定（ai）
- 運用補助ツール（設定ウィザード、設定検証、Paper Trading レポート等）

特徴
----
- モジュール化された純粋関数群（ファクター計算・ポートフォリオ構成）
- DuckDB / SQLite を使ったローカルデータ管理（分析用と監視/発注用を分離）
- Paper Trading モードをサポート（本番 DB と完全分離）
- OpenAI を用いたニュースセンチメント評価・レジーム検出（フェイルセーフ設計）
- 監視ループ/ExecutionEngine による永続運用（停止フラグ、Kill Switch、ログローテーション）

必須 / 推奨依存パッケージ
------------------------
以下は主にソースから参照されているライブラリです（環境に合わせてインストールしてください）:

- Python 3.9+
- duckdb
- psutil
- openai
- (オプション) PyYAML — config/*.yaml の検証に使用

セットアップ手順
--------------
1. リポジトリをクローンし、仮想環境を作成して有効化します（省略可）。
2. 必要パッケージをインストールします。例:
   - pip install duckdb psutil openai PyYAML
3. .env を作成します:
   - 対話式ウィザードで作成: python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成
   - 自動で .env を読み込みます（PROJECT ルートが .git または pyproject.toml により検出可能な場合）。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

重要な環境変数
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / デフォルトあり:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading: 発注はモック（paper_trading.db を使用）
  - live: 本番動作（kabu API を使用）
- DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db） — Monitoring は環境にかかわらず本番 sqlite_path を参照します
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のフィルモード（instant / partial / never / reject）デフォルト: instant
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログファイルディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI を使う機能（ai/news_nlp, ai/regime_detector）で必要
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（1 = 自動クリア、0 = しない）

設定検証
--------
作成した .env や config/*.yaml を起動前にチェックできます:

- 設定検証 CLI:
  - python -m kabusys.validate_config
  - 警告をエラーとして扱う場合: python -m kabusys.validate_config --strict

使い方（起動方法）
-----------------

1. ExecutionEngine を起動（取引エンジン）
   - 本番/ペーパーは KABUSYS_ENV によって切り替わります（paper_trading は専用 DB を使用）。
   - コマンド:
     - python -m kabusys.run_execution
   - 動作概要:
     - プロセス優先度を "high" に設定
     - SQLite / DuckDB に接続（paper_trading なら paper_trading.db）
     - BrokerClientFactory でブローカクライアント作成（paper_trading は Mock）
     - ExecutionEngine.run_session() をスレッドで実行
     - data/stop_requested.flag が存在すると停止する

2. Monitoring を起動（監視ループ）
   - Monitoring は KABUSYS_ENV の値に関係なく本番 sqlite_path を使用します（監視・アラートの一貫性のため）。
   - コマンド:
     - python -m kabusys.run_monitoring
   - 環境変数:
     - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
   - 動作概要:
     - プロセス優先度を "high" に設定
     - SystemMonitor, TradeMonitor, RiskMonitor 等をポーリング
     - data/stop_requested.flag を検知するとループ終了

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
   - 出力: 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などのサマリと PASS/FAIL 判定

4. 設定ウィザード（.env の初期生成）
   - python -m kabusys.config_setup

運用 / 停止
-----------
- 停止フラグ: data/stop_requested.flag を作成すると run_execution/run_monitoring はそれを検知して終了します。
- Kill Switch: リスク条件により data/kill.flag（デフォルトパスは Settings.kill_flag_path, デフォルト data/kill.flag）を書き込むと ExecutionEngine に停止シグナルを送ります。起動時に自動クリアするかは KILL_FLAG_CLEAR_ON_START で制御可能。
- PID ファイル: Execution は data/execution.pid を使用して状態管理します（Settings.pid_file_path）。

ログ
---
- ログは標準出力（stdout）とファイル（logs/<app_name>.log）に出力します（TimedRotatingFileHandler で日次ローテーション、30世代保持）。
- ログディレクトリ: 環境変数 LOG_DIR で変更可能。作成に失敗した場合はコンソールのみで継続します。

データベース
-----------
- DuckDB: 分析・研究データ（prices_daily, raw_financials, raw_news, ai_scores, 等）
  - Path: DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLite:
  - 監視/発注履歴用: SQLITE_PATH（デフォルト data/monitoring.db）
  - Paper Trading 用（分離）: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）

セキュリティ注意事項
--------------------
- .env ファイルには API トークン等の機密情報が含まれます。絶対にリポジトリにコミットしないでください（config_setup.py にもその旨のコメントあり）。
- 本番環境（KABUSYS_ENV=live）での設定は慎重に検証してください。LINE 通知等が未設定だと重要アラートを見逃します。

主要なモジュール一覧（抜粋）
---------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数・設定管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ポーリング起動スクリプト

パッケージ：
- ai/
  - news_nlp.py             — ニュースセンチメント（OpenAI）処理
  - regime_detector.py      — 市場レジーム判定（ma200 + macro sentiment）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/
  - monitoring_db.py        — SQLite テーブル初期化・IO 層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py        — （アラート送信ロジック）
- execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- utils/
  - logging_setup.py        — ログ設定ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity
- tools/
  - paper_verification_report.py

ディレクトリ構成（例）
--------------------
プロジェクトルート（src 配下をパッケージとして扱う想定）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
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
    - tools/
      - paper_verification_report.py
- .env (推奨・機密扱い)
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/
  - monitoring.db (SQLite)
  - paper_trading.db (Paper Trading 用 SQLite)
  - kabusys.duckdb (DuckDB)
  - stop_requested.flag, kill.flag, execution.pid など
- logs/
  - execution.log
  - monitoring.log
  - ...（日次ローテート）

開発者向けメモ
--------------
- .env 自動ロードはプロジェクトルートの検出に .git または pyproject.toml を使用します。テストなどで自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ai/news_nlp と ai/regime_detector は OpenAI 呼び出しの失敗に対してフェイルセーフ設計（スコアは 0.0 にフォールバックする等）です。ただし API キーは必須です。
- monitoring モジュールは監視情報の永続化（monitoring_db）を担い、RiskMonitor からのアラートで KillSwitch を発動できます。

よくある運用コマンド例
--------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問い合わせ / 貢献
-----------------
バグ修正・機能追加は PR を歓迎します。README の不足点や誤記があれば issue を作成してください。

以上。必要であれば README にサンプル .env テンプレートや具体的な CLI サンプル（ExecutionEngine のログ解釈等）を追加します。どの情報を優先で追記しますか？