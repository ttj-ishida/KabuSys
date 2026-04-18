# KabuSys

日本株自動売買システムのライブラリ / 起動スクリプト群です。  
このリポジトリには、シグナル生成・ポートフォリオ構築・発注エンジン・監視・Research ツール・AI ニュース解析などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成
- 重要な環境変数・ファイル
- トラブルシューティング／運用メモ

---

プロジェクト概要
- 日本株を対象とした自動売買システム（KabuSys）。  
- Strategy / Portfolio / Execution / Monitoring / Research / AI（ニュース NLP）をモジュール化して実装。  
- 永続化: DuckDB（分析用）と SQLite（監視・ペーパートレード用）を併用。  
- 本番（live）とペーパートレード（paper_trading）を分離して安全に運用できる設計。  
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析やレジーム判定機能を備える（APIキー必要）。

機能一覧
- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（本番 / paper_trading 切替）  
  - run_monitoring.py — SystemMonitor のポーリングループ起動（監視ログ記録）
- 環境管理・ユーティリティ
  - config.py — 環境変数の解決と Settings オブジェクト
  - config_setup.py — 対話式 .env ウィザード（.env の生成/更新）
  - validate_config.py — 起動前の設定検証 CLI
- 監視（Monitoring）
  - monitoring_db.py — SQLite ベースの監視 DB スキーマ / 永続化 API
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py — 各種監視ロジックとアラート連携（Kill Switch 等）
  - kill_switch.py — 条件を満たした際に data/kill.flag を書き込み Execution を停止
- Execution 関連（発注）
  - broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager（各種コンポーネント、ファクトリ）
  - run_execution.py は KABUSYS_ENV=paper_trading 時、MockBrokerClient を利用して data/paper_trading.db に記録
- Portfolio（銘柄選定・配分）
  - portfolio_builder, position_sizing, risk_adjustment — 候補選定、重み計算、株数決定、セクター制限、レジーム調整
- Research（ファクター計算・特徴量探索）
  - factor_research.py, feature_exploration.py — Momentum/Value/Volatility 等のファクター計算、IC 等の統計解析
- AI
  - ai/news_nlp.py — raw_news を OpenAI に投げて銘柄単位のセンチメントを ai_scores に保存
  - ai/regime_detector.py — ETF の MA200 とマクロニュースセンチメントを合成して市場レジーム判定
- ツール
  - tools/paper_verification_report.py — ペーパートレード DB を元に検証レポートを生成
- 共通ユーティリティ
  - utils/logging_setup.py — 統一ログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py — プラットフォーム差分を吸収したプロセス優先度 / CPU affinity 設定

セットアップ手順（概要）
1. Python（推奨: 3.10 以上）を用意する。
2. 必要パッケージをインストールする（例: pip）
   - 基本: duckdb, psutil
   - OpenAI を利用する場合: openai
   - config 検証で YAML を使う場合: PyYAML（任意）
   例:
     pip install duckdb psutil openai PyYAML
3. リポジトリのルートに移動し、データ/ログディレクトリを作成（通常は自動作成されるが権限確認）
     mkdir -p data logs
4. .env の作成（推奨: 対話式ウィザード）
     python -m kabusys.config_setup
   - ウィザードで J-Quants / kabuAPI / DB パス等を設定します。
5. 設定検証（起動前に推奨）
     python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いします。
6. 必要なら DuckDB / SQLite の初期化は各起動スクリプトが自動で行います（monitoring は init_monitoring_db を呼ぶ）。

使い方（主要なコマンド）
- 環境設定ウィザード:
    python -m kabusys.config_setup
- 設定検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict
- ExecutionEngine の起動（本番または paper_trading は KABUSYS_ENV で切替）
    python -m kabusys.run_execution
  - 起動時にプロセス優先度を "high" に設定します。
  - KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用します。
  - data/stop_requested.flag が存在すると起動せず終了、実行中に存在すると安全停止します。
- Monitoring の起動（ポーリング）
    python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを記録します。
- Paper Trading 検証レポート生成:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db オプションで上書き可。
- AI 周り（スコア計算・レジーム判定）はモジュール関数経由で呼ぶか、ユーザがラッパーを作成して呼び出します。
  - OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で渡します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照: 実装あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照: 実装あり)
  - execution/
    - execution_engine.py (参照)
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py (参照: get_last_price_date 等)
    - stats.py (zscore_normalize 等)
  - utils/
    - logging_setup.py
    - process_priority.py

（上記はこの README に含まれるソースからの抜粋。実コード全体は src/kabusys 以下をご参照ください）

重要な環境変数・デフォルト
- KABUSYS_ENV: execution 環境（development, paper_trading, live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須（validate_config により検出）
- DUCKDB_PATH: 分析 DB（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LOG_LEVEL: ログレベル（デフォルト INFO）
- LOG_DIR: ログ出力先（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の Fill 動作（instant, partial, never, reject。デフォルト "instant"）

重要なファイル／フラグ
- data/kill.flag: KillSwitch により書き込まれる。存在すると ExecutionEngine に停止命令を出す。
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に自動でクリアされる（production では 0 推奨）。
- data/stop_requested.flag: run_* スクリプトの外部停止フラグ。作成されると監視/実行ループを抜ける。
- data/*.db: SQLite / DuckDB のデフォルト配置（必要に応じて .env で変更）

ログ
- utils/logging_setup.setup_logging を通して stdout（StreamHandler）と日次ローテートファイル（logs/<app>.log）に出力します。ログディレクトリは自動作成を試みますが権限がなければコンソールのみで継続します。

運用メモ / トラブルシューティング
- .env 自動読み込み: .env / .env.local をプロジェクトルートから自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- PID / stop フラグ: run_execution/run_monitoring は data/* の flag/pid ファイルを参照して安全停止や二重起動防止を行います。手動運用時はこれらの存在を確認してください。
- monitoring と execution の DB 分離: Monitoring は本番の sqlite_path を使用してログを残しますが、ExecutionEngine は paper_trading 環境なら paper_sqlite_path を使用して本番 DB と分離します。
- OpenAI 呼び出し: API 呼び出し時の 429/ネットワーク/5xx は指数バックオフでリトライしますが、API キーやネットワークエラーは事前に確認してください。
- 権限: ログ・data ディレクトリに書き込み権限が必要です。ファイル作成に失敗すると一部機能（ログ記録など）が制限されます。
- PyYAML がない場合、validate_config は YAML 検証をスキップします（警告）。

付記
- 本 README はソース内の docstring / 実装コメントを元に作成しています。詳細な運用手順・設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）がプロジェクトに含まれている場合はそちらも参照してください。

必要なら、用途別の起動例（systemd ユニット、Dockerfile、ログローテーション設定など）や .env.example の自動生成テンプレートを README に追記します。どの情報を追加しますか？