KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームのコアライブラリ群です。
主要機能（発注エンジン・監視・リスク管理・ポートフォリオ構築・ファクター計算・NLProcによるニュース評価など）をモジュール化して提供します。実行スクリプトは python -m で起動でき、環境ごと（development / paper_trading / live）に挙動を切り替えられます。

主な特徴
--------
- ExecutionEngine（発注実行エンジン）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、本番DBと分離された paper_trading DB に記録。
  - プロセス優先度を上げて実行（set_process_priority）。
  - 停止はフラグファイルで制御（data/stop_requested.flag / data/kill.flag）。
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる監視エンジン。
  - SQLite を用いた監視ログ（data/monitoring.db、デフォルト）を持つ。
  - KillSwitch による自動停止判定とアラート連携。
- Portfolio モジュール
  - 候補選定、等配分・スコア加重配分、ポジションサイジング、セクター上限・レジーム乗数などの純粋関数を提供。
- Research（ファクター計算・特徴量探索）
  - DuckDB 接続を受け取り、モメンタム・バリュー・ボラティリティ等のファクターを計算。
  - 将来リターン計算、IC（Information Coefficient）や統計サマリーを算出。
- AI モジュール
  - ニュース NLP（OpenAI）で銘柄別センチメントを算出し ai_scores に保存。
  - 市場レジーム判定（ETF ma200 + マクロニュースによる LLM スコア合成）。
  - OpenAI 呼び出しはリトライ/バリデーション付きで安全化。
- ツール
  - 環境設定ウィザード（.env の対話式作成）や設定検証 CLI、Paper Trading 検証レポート生成など。

セットアップ手順
----------------
※必要パッケージはプロジェクトに同梱されている requirements.txt があればそれを使ってください。なければ少なくとも以下が必要です:
- Python 3.10+
- duckdb
- psutil
- openai
- (PyYAML は config ファイル検証時に使用)

1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（例）:
   - pip install duckdb psutil openai

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参考にしてください）。
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB, デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（DEBUG/INFO/...）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合は --strict を付ける

使い方
------
- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - 動作切り替え:
    - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にログを保存します。
  - 実行中停止:
    - data/stop_requested.flag が存在すると起動ループ中に停止します。
    - KillSwitch による data/kill.flag が書かれると ExecutionEngine 側で停止処理を行います（KillSwitch は監視側から書き込まれる想定）。

- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60）を設定できます（正の整数のみ。無効値はデフォルトにフォールバック）。
  - 監視は MonitoringDB（Settings.sqlite_path / data/monitoring.db）へログを残します。
  - run_monitoring は実行時にプロセス優先度を high に設定します。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）。

- プログラム的 API:
  - ポートフォリオ:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - リサーチ:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  - AI:
    - from kabusys.ai import score_news  # ニューススコア算出（DuckDB 接続, target_date, api_key(optional)）
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - 設定読み取り:
    - from kabusys.config import settings  # settings.jquants_refresh_token 等にアクセス

運用時の注意点 / フラグ・ファイル
---------------------------------
- 停止系フラグ:
  - data/stop_requested.flag: run_monitoring/run_execution の外部停止用。存在するとループを終了します。
  - data/kill.flag: KillSwitch が書き込む停止トリガ（ExecutionEngine 側はこれを検知して安全停止）。
  - data/execution.pid: ExecutionEngine が PID を書く想定（run_execution 内定義）。
- ログ:
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日分保持）。
  - setup_logging(app_name="execution") のようにアプリ名を指定して利用する。
- DB:
  - 監視用 DB: settings.sqlite_path（デフォルト data/monitoring.db）
  - DuckDB: settings.duckdb_path（デフォルト data/kabusys.duckdb）
  - Paper Trading 用 SQLite は settings.paper_sqlite_path（デフォルト data/paper_trading.db）
  - init_monitoring_db() がテーブル作成・簡易マイグレーションを行います（冪等）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールの一覧（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                 # 環境変数 /.env 自動読み込み・ Settings クラス
  - config_setup.py           # .env 対話式ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  # Paper Trading 検証レポート
  - execution/                # 発注関連（Engine, OrderManager, BrokerFactory 等）
    - ... (実装ファイル群)
  - monitoring/
    - monitoring_db.py
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
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                     # データアクセス / pipeline（DuckDB 用）
    - ...
  - utils/
    - logging_setup.py
    - process_priority.py

例: よく使うコマンドまとめ
-----------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足 / 実装上のポイント
----------------------
- Settings クラスは .env 自動読み込みを行い、環境変数をラップして提供します（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込み無効化可能）。
- Logging は共通ユーティリティで統一され、コンソール（stdout）出力と日次ローテーションファイル出力を提供します。
- OpenAI 呼び出し（AI 機能）はリトライ・JSON バリデーションを実装しており、APIエラー時は安全にフォールバック（例: macro_sentiment=0.0）します。
- Paper Trading と本番 DB は分離される設計（settings.is_paper により paper_sqlite_path を利用）。

ライセンス・セキュリティ
-----------------------
- .env ファイルには機密情報（API トークン等）が含まれるため、絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。

問題が発生したら
----------------
- 設定検証（python -m kabusys.validate_config）をまず実行し、エラーや警告を確認してください。
- ログ（logs/）を確認して詳細なエラー原因を調査してください。
- AI 系の機能で OpenAI を使う場合は OPENAI_API_KEY が正しく設定されていることを確認してください。

以上が README の要点です。必要であれば各モジュール（ExecutionEngine の使い方、OrderRepository API、monitoring のアラート連携方法など）について別途詳細ドキュメントを作成します。どの部分を深掘りしますか？