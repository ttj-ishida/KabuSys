# KabuSys

日本株向け自動売買システムのコアライブラリ群および起動スクリプト群です。  
このリポジトリは、発注エンジン、監視エンジン、ポートフォリオ構築・サイズ決定ロジック、リサーチ（ファクター計算）および AI 補助モジュール（ニュースセンチメント／レジーム判定）を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 動作要件
- セットアップ手順
- 環境変数（主要）
- 使い方（起動・停止・ツール）
- ディレクトリ構成

---

プロジェクト概要
- 自動売買 ExecutionEngine（実発注 / ペーパートレード分離）
- システム監視（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ファクター計算および特徴量探索（DuckDB を用いた分析）
- ニュースの LLM によるセンチメント評価・日次レジーム判定（OpenAI API）
- 各種 CLI ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート）

主な機能
- Execution
  - 実際のブローカークライアントまたはペーパートレード用の MockBrokerClient を切替可能（KABUSYS_ENV=paper_trading）
  - ペーパートレード時は data/paper_trading.db に記録し本番 DB と分離
  - 起動時にプロセス優先度を high に設定
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス生存確認、データ鮮度チェック
  - TradeMonitor / RiskMonitor: 滞留注文／約定異常／ドローダウン／ポジション上限監視
  - KillSwitch: しきい値超過時に data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送信
  - MonitoringEngine: 各モニタを束ねてポーリング。run_monitoring スクリプトで起動
- Portfolio
  - 候補選定（スコア順）、等比率／スコア重み付け、セクター上限適用、レジーム乗数
  - 株数決定ロジック（リスクベース、等分配、スコア配分）、単元株丸め、アグリゲートキャップ処理
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメント評価 → ai_scores に書込
  - regime_detector: ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成して market_regime を判定・書込
- ユーティリティ
  - .env ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）
  - ロギング設定ユーティリティ、プロセス優先度設定ユーティリティ

動作要件（概略）
- Python 3.9+
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config YAML 検証を行う場合）
- システム上でのネットワークアクセス（kabuステーション / OpenAI を使う場合）
- SQLite / DuckDB ファイルはローカルファイル（デフォルト: data/monitoring.db, data/kabusys.duckdb）

セットアップ手順
1. クローン / 配布ファイルの配置
   - ソースルートに `src/` があり、パッケージ名は `kabusys` です。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

3. 依存関係インストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は必要なパッケージを個別にインストール）
     - pip install duckdb psutil openai pyyaml

4. 環境変数設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
     - KABU_API_PASSWORD（kabuステーション API 用）
   - 主要な環境変数のデフォルト:
     - KABUSYS_ENV=development | paper_trading | live（default: development）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY（AI 機能を使う場合に必要）
   - 自動ロード:
     - プロジェクトルートに .env / .env.local がある場合、起動時に自動で読み込まれます（OS 環境変数は上書きされません）。
     - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DB 初期化
   - monitoring 用 SQLite は起動スクリプトが自動で init_monitoring_db を実行してテーブルを作成します。

環境変数（主要）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 主要（省略可 / デフォルトあり）
  - KABUSYS_ENV: development | paper_trading | live（default: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default: 60）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1、production では 0 推奨）

使い方（起動 / 停止 / CLI）
- .env の作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - 起動時に data/execution.pid を使用（pid ファイル）
    - 停止は外部に設置された停止フラグで制御（下記参照）
    - プロセス優先度を high に設定

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更（秒、デフォルト 60）
    - 監視は常に本番 sqlite_path を使用（環境に依らず）
    - 停止は data/stop_requested.flag の存在検出でループを抜けます

- 停止・Kill Switch
  - ExecutionEngine 停止リクエスト:
    - KillSwitch はしきい値を満たすと data/kill.flag を書き込みます（ExecutionEngine が起動時に kill_flag_clear_on_start を考慮して自動クリアする設定あり）
  - 手動で監視 / 実行ループを停止する:
    - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して終了します
  - kill.flag:
    - KillSwitch が書き込むファイル。ExecutionEngine はこれを検出して停止します

- ログ
  - デフォルトは stdout（コンソール）と logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日分保持）
  - ログレベルは LOG_LEVEL 環境変数または setup_logging 呼び出しで設定

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能
  - OpenAI を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要
  - news_nlp.score_news(), regime_detector.score_regime() は DuckDB 接続と target_date を受け取るプログラム API

開発者向け情報
- コードは src/kabusys 以下に配置
- 主要モジュール:
  - kabusys.config / config_setup / validate_config
  - kabusys.run_execution, kabusys.run_monitoring
  - kabusys.monitoring.*（monitoring_db, system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, alert_manager）
  - kabusys.execution.*（broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager） — 実装ファイルを参照
  - kabusys.portfolio.*（portfolio_builder, position_sizing, risk_adjustment）
  - kabusys.research.*（factor_research, feature_exploration）
  - kabusys.ai.*（news_nlp, regime_detector）
  - kabusys.utils.*（logging_setup, process_priority）

ディレクトリ構成（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (実装参照)
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py
    - data/ (実行時に使用するファイル置き場)
      - monitoring.db (default)
      - kabusys.duckdb (default)
      - paper_trading.db (paper_trading 用)
      - kill.flag, stop_requested.flag, execution.pid など

注意事項 / 運用上のヒント
- .env は絶対に Git にコミットしないでください（config_setup.py も README で注意喚起しています）。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します。自動クリアは危険です。
- OpenAI を利用する場合のエラーハンドリングはフェイルセーフ化されていますが、API 利用はコストが発生します。キー管理に注意してください。
- run_monitoring は環境にかかわらず（development でも）本番 sqlite_path を参照して monitoring データを記録します（設計上の意図に注意）。
- データ鮮度チェックやレジーム判定などはルックアヘッドバイアスを避ける実装方針に従っています（date/time の扱いに注意）。

ライセンス / 貢献
- この README にはライセンス情報やコントリビューションガイドは含まれていません。運用チームの方針に従って LICENSE ファイルや CONTRIBUTING を追加してください。

---

質問や追加があれば、使用したい機能（例: ペーパートレードでの詳細ログ取得、AI モジュールのロギング強化、モニタリング通知先の追加など）を教えてください。必要に応じて README の具体的な実行例や systemd/cron 用の起動スクリプト例も作成できます。