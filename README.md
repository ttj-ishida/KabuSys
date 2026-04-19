# KabuSys

日本株向け自動売買システムのパッケージ（ライブラリ＋起動スクリプト群）。

このリポジトリは戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（実運用／ペーパートレード）、およびシステム監視機能を含みます。設計方針として、外部 API 呼び出しや DB は明確に分離され、テストしやすい純粋関数群・I/O 層で構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成
- 環境変数（主なもの）
- 運用メモ（停止・Kill Switch・ログ）

---

プロジェクト概要
- 日本株自動売買システムのコアライブラリと起動スクリプト群を提供します。
- 主な構成要素:
  - strategy / research: ファクター計算・特徴量解析
  - portfolio: 銘柄選定・重み計算・ポジションサイズ決定
  - execution: ExecutionEngine（ブローカークライアント・注文管理・リスク管理）
  - monitoring: システム稼働監視、トレード監視、Kill Switch、アラート
  - ai: ニュース NLP（OpenAI）によるセンチメント評価 / レジーム判定
  - tools: レポート生成等のユーティリティスクリプト

機能一覧
- 環境設定ウィザード（.env の対話式生成）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の事前チェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）: run_execution.py
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、ペーパートレード専用 DB に記録
- SystemMonitor / MonitoringEngine（定期ポーリングによる監視）: run_monitoring.py
  - MONITOR_POLL_INTERVAL によりポーリング間隔上書き可能（デフォルト 60 秒）
- MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard テーブルを管理
- Kill Switch（フラグファイルを書いて ExecutionEngine を停止）
- Paper Trading 検証レポート生成スクリプト: tools.paper_verification_report
- AI モジュール:
  - news_nlp.score_news: raw_news を集約して OpenAI に送信し ai_scores に保存
  - regime_detector.score_regime: ma200 + マクロセンチメントの合成で market_regime を判定
- portfolio モジュール: 候補選定、等配分 / スコア加重、リスク調整（セクター集中制限、レジーム乗数）、株数計算（単元丸め・アグリゲートキャップ）

セットアップ手順（ローカル）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 環境（推奨: 3.10 以上）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須パッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - (sqlite3 は標準ライブラリ)
     - PyYAML（config YAML の検証を利用する場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt がない場合はプロジェクトに合わせてインストールしてください）

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（参照: .env.example が存在する場合はそれを利用）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

6. データディレクトリ / ログディレクトリの準備
   - デフォルトの DB / PID / フラグ / ログは project-root/data, logs 配下
   - 例: mkdir -p data logs

使い方（起動 / 各種スクリプト）
- 環境変数の指定例（.env または export）:
  - JQUANTS_REFRESH_TOKEN=...
  - KABU_API_PASSWORD=...
  - KABUSYS_ENV=development|paper_trading|live
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - LOG_LEVEL=INFO
  - OPENAI_API_KEY=...

- 起動スクリプト
  - 実行エンジン（ExecutionEngine）を起動:
    - python -m kabusys.run_execution
    - 実行中に停止させたい場合: data/stop_requested.flag を作成するとループが検知して終了
    - 実運用（live）では実際のブローカークライアントが使われ、paper_trading では MockBrokerClient と別 DB（PAPER_TRADING_SQLITE_PATH）を使います

  - 監視プロセス起動:
    - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（例: export MONITOR_POLL_INTERVAL=30）
    - 監視は常に本番用 sqlite_path を使用（環境にかかわらず）

- 設定検証 / ウィザード
  - 設定ウィザード:
    - python -m kabusys.config_setup
  - 設定検証:
    - python -m kabusys.validate_config
    - python -m kabusys.validate_config --strict

- レポート
  - Paper Trading 検証レポート:
    - python -m kabusys.tools.paper_verification_report
    - 引数:
      - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
    - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定可能

- AI スコアリング / レジーム判定（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で渡します

主要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード:
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading: MockBrokerClient を使用しデータを data/paper_trading.db に記録
- DB / ファイル:
  - DUCKDB_PATH: data/kabusys.duckdb（分析用）
  - SQLITE_PATH: data/monitoring.db（監視ログ等）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用）
  - PID_FILE_PATH / KILL_FLAG_PATH（Settings にアクセス）
- ログ:
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - LOG_DIR: デフォルト logs/
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）

ディレクトリ構成（要点）
- src/kabusys/
  - __init__.py
  - config.py                — .env 自動ロード / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定（stdout + 日次ローテート）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・読み書き
    - system_monitor.py
    - trade_monitor.py       (存在: ロジックは本体参照)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       (通知ロジック)
  - execution/
    - execution_engine.py
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（上記はリポジトリ内の主要ファイルを抜粋したものです）

運用メモ（停止・Kill Switch・ログ）
- 停止フラグ:
  - run_execution と run_monitoring ではプロジェクト内 data/stop_requested.flag を監視し、存在すると安全にループを終了します。
  - ExecutionEngine 側には Kill Switch（data/kill.flag）を用いた停止機構があります。Kill Switch はリスクしきい値（ドローダウン・ポジション上限など）で自動的に kill.flag を書き、ExecutionEngine はこれを検知して停止します。
  - kill.flag は Settings.kill_flag_clear_on_start=1 の場合に起動時自動クリアするオプションがあります（本番では 0 推奨）。
- PID ファイル:
  - data/execution.pid を ExecutionEngine が利用してプロセス管理を行います。
- ログ:
  - ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力され、コンソール（stdout）にも出ます。
  - 共通セットアップ: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)

注意事項 / 推奨
- KABUSYS_ENV=live の場合は設定（特に API トークン・LINE 通知設定・Kill Switch 設定）を慎重に確認してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも明記）。
- OpenAI API を利用する機能は API キーと API 利用料が必要です。テスト時はモックを使用してください（コード中で _call_openai_api を差し替えてテスト可能）。

サンプル .env（最小）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

最後に
- 詳細な設計（PortfolioConstruction.md, StrategyModel.md 等）はリポジトリ内ドキュメントを参照してください（本 README はコードベースから抽出した利用手引きです）。質問や追加のドキュメント化が必要であれば、どの箇所を深掘りしたいか教えてください。