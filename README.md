# KabuSys — 日本株自動売買システム（README）

この README はコードベース（src/kabusys/*.py）をもとに作成した簡易ドキュメントです。起動スクリプト・設定周り・主要モジュールの概要、セットアップと使い方、ディレクトリ構成を日本語でまとめています。

注意: 実行には外部ライブラリ（duckdb, psutil, openai 等）が必要です。AI 機能を使わない場合は openai は不要です。

---

目次
- プロジェクト概要
- 機能一覧
- 必要な環境変数（要点）
- セットアップ手順
- 使い方（コマンド例）
- フラグ / ファイルによる制御
- ディレクトリ構成（主要ファイル）
- 開発時の補足

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムのコアライブラリ群です。
- 監視 (monitoring)、注文実行 (execution)、ポートフォリオ構築、ファクター計算（research）、AI を用いたニュース解析（ai）など、複数コンポーネントを含みます。
- 設定は .env / .env.local または環境変数で管理し、Settings クラス（kabusys.config）から参照します。

---

主な機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて本番 or ペーパートレード）
  - run_monitoring.py: SystemMonitor をポーリングで実行
- 設定管理・補助
  - config_setup.py: 対話式で .env を作成・更新するウィザード
  - validate_config.py: .env / config/*.yaml の検証 CLI（--strict オプションあり）
- モジュール群
  - monitoring
    - MonitoringDB: SQLite ベースの監視用永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager（監視関連）
  - execution
    - ExecutionEngine、OrderManager、RiskManager、Reconciler、BrokerClientFactory 等（発注・リスク管理）
    - paper_trading 環境では MockBrokerClient を使用し本番 DB と分離
  - portfolio
    - 銘柄選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
    - ポジションサイズ決定（calc_position_sizes）
    - セクター上限・レジーム調整（apply_sector_cap, calc_regime_multiplier）
  - research
    - ファクター計算（calc_momentum, calc_volatility, calc_value）
    - 将来リターン、IC 計算、ファクター統計（calc_forward_returns, calc_ic, factor_summary, rank）
  - ai
    - news_nlp.score_news: OpenAI を用いたニュースのセンチメント計算と ai_scores への書き込み
    - regime_detector.score_regime: ETF マクロ指標 + LLM で市場レジーム判定
  - tools
    - paper_verification_report: ペーパートレード DB を解析して検証レポートを生成

---

必要な環境変数（要点）
- 必須（validate_config でもチェック）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
    - paper_trading: Execution は MockBrokerClient を使い data/paper_trading.db に記録
    - live: 実口座での発注を行う
- DB / ログ関連（デフォルト）
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_LEVEL (default: INFO)
  - LOG_DIR (default: logs/)
- AI（使用時）
  - OPENAI_API_KEY — OpenAI API キー（ai.news_nlp, ai.regime_detector で使用）
- 監視関連
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — ペーパートレードの約定動作（instant | partial | never | reject、デフォルト: instant）
- 自動 .env ロード
  - デフォルトでプロジェクトルートの .env と .env.local を自動ロードする
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化

---

セットアップ手順（ローカル）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai
   - PyYAML は validate_config の YAML 検証に使われる（必須ではない）
3. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - あるいは .env を手動で作成（.env.example を参照）
4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする: python -m kabusys.validate_config --strict
5. 必要なディレクトリ（data, logs）は起動時に自動作成されることが多いですが、手動で作ることも可能:
   - mkdir -p data logs

---

使い方（実行例）
- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV で制御）
  - python -m kabusys.run_execution
  - ペーパートレード DB は環境変数 PAPER_TRADING_SQLITE_PATH で上書き可
- Monitoring を起動（ポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止はプロジェクトルート data/stop_requested.flag を作成して行う（監視側はこのファイルを検知してループを終了）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定

主要オプションの例:
- MONITOR_POLL_INTERVAL — 監視ループ間隔（秒）
- KABUSYS_ENV=paper_trading — 発注を仮想化して data/paper_trading.db に記録
- OPENAI_API_KEY=... — AI モジュールを使う場合に必要

---

フラグ / ファイルによる制御
- data/stop_requested.flag
  - run_monitoring と run_execution の両方で監視されており、存在するとループを終了・エンジン停止のトリガになります。
- data/kill.flag
  - KillSwitch（監視）によって書き込まれ、ExecutionEngine 側で停止要求として参照されます。
  - Settings.kill_flag_clear_on_start が 1 の場合は起動時に自動クリアされる設定になり得る（本番注意）。
- data/execution.pid
  - ExecutionEngine の PID ファイル（デフォルト）。設定でパスを変更可能。

---

主要モジュール・API（ざっくり）
- kabusys.config.Settings
  - 各種環境変数のラッパー（型変換・検証あり）
- kabusys.utils.logging_setup.setup_logging(app_name, log_dir, level)
  - StreamHandler (stdout) と TimedRotatingFileHandler（日次）を設定
- kabusys.utils.process_priority.set_process_priority(level)
  - psutil 経由でプロセス優先度を設定（"high"/"normal"/"low"）
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.ai
  - score_news（ニュース NLP を実行して ai_scores に保存）
  - regime_detector.score_regime（市場レジーム判定）
- kabusys.monitoring.monitoring_db.MonitoringDB
  - DB の初期化 init_monitoring_db(conn) と読み書きメソッド群（log_system_status, log_trade_event, upsert_dashboard 等）
- kabusys.monitoring.MonitoringEngine
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねて周期実行する

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 設定（.env 自動ロード / Settings）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前検証 CLI
  - run_execution.py — Execution 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照)
  - execution/ (発注実行関連)
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

---

開発時の補足 / 注意点
- .env は絶対に Git にコミットしないでください（config_setup も README に書かれているとおり注意喚起あり）。
- Settings は自動でプロジェクトルートの .env / .env.local を読み込みます（テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定）。
- validate_config は PyYAML がインストールされている場合に config/*.yaml のパース検証も行います（未インストール時は警告でスキップ）。
- DuckDB の接続は多くの研究モジュールで使用します。DuckDB ファイルパスは DUCKDB_PATH で指定。
- AI 周り (news_nlp, regime_detector) は OpenAI API 呼び出しを行います。API 失敗時はフェイルセーフとしてスコア = 0 等で続行する設計ですが、API キーが必要です。
- run_execution は KABUSYS_ENV=paper_trading の時に paper_trading DB を使用し本番 DB と分離します（安全対策）。
- run_monitoring と run_execution ともに起動時にプロセス優先度を "high" に設定しようとします（psutil と権限に依存）。

---

問い合わせ / 変更
- このドキュメントはソースコードの現状（src/kabusys 以下）から自動的に要点を抜粋して作成しています。実運用前に config/*.yaml（もしあれば）や各モジュールの詳細実装、依存パッケージのバージョンを必ず確認してください。

以上。必要があれば README に具体的な例（.env.sample のテンプレート、requirements.txt 例、systemd サービス定義など）を追加します。どの情報を優先して追記しますか？