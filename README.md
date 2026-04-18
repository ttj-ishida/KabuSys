KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ベースのシステムです。  
主な機能は取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、LLM を使ったニュース NLP / レジーム検出、ペーパートレード検証などを含みます。  
パッケージは src/kabusys 以下に実装されており、設定は .env（環境変数）や config/*.yaml で行います。

特徴（機能一覧）
----------------
- ExecutionEngine
  - 本番 / ペーパートレード（環境切替）をサポート
  - ブローカークライアント抽象化（BrokerClientFactory）
  - リスク管理・オーダー管理・調整（Reconciler, RiskManager, OrderManager）
  - PID ファイル管理、停止フラグ監視（data/stop_requested.flag）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - Kill Switch による ExecutionEngine 停止（data/kill.flag）
  - ポーリング間隔を環境変数で調整可能（MONITOR_POLL_INTERVAL）
- Portfolio（銘柄選定、重み付け、ポジションサイズ計算）
  - 等分配・スコア加重・リスクベースのサイズ計算
  - セクター上限制御、レジーム乗数適用
- Research（ファクター計算 / 特徴量探索）
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - 将来リターン・IC（Information Coefficient）等の解析ユーティリティ
- AI（ニュース NLP / レジーム検出）
  - OpenAI（gpt-4o-mini 等）を利用してニュースのセンチメントを算出し ai_scores に格納
  - 市場レジーム判定（MA200 とマクロニュースの LLM センチメントを合成）
- ツール
  - ペーパートレード検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- 設定支援
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

セットアップ手順
----------------
前提
- Python 3.9+（プロジェクトの Python バージョンは環境に合わせてください）
- システムによっては psutil のインストールにビルドツールが必要です

1. リポジトリをクローン（またはソースを取得）
   - 例: git clone <repo> && cd <repo>

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存ライブラリをインストール
   - 必要なパッケージ（コードベースから参照される主なもの）:
     - duckdb, psutil, openai, PyYAML（任意：config YAML 検証用）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）

4. 実行方法の準備
   - パッケージが src/kabusys にあるため、実行時に PYTHONPATH に src を含めるか、パッケージ化してインストールします。
   - 簡単な実行例（プロジェクトルートで）:
     - PYTHONPATH=src python -m kabusys.config_setup
     - PYTHONPATH=src python -m kabusys.validate_config

.env（環境変数）の準備
-----------------------
- 対話式で .env を作る:
  - PYTHONPATH=src python -m kabusys.config_setup
- 主要な必須環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
- 主要な任意 / デフォルト設定:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH: 分析用 DB（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 用）
  - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使う場合）
  - LOG_LEVEL, LOG_DIR など
- 自動読み込みはプロジェクトルートの .env / .env.local を参照します。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

設定検証
-------
- 設定検証ツールを実行:
  - PYTHONPATH=src python -m kabusys.validate_config
  - --strict オプションで警告を失敗扱いにできます。

使い方（起動・停止・ツール）
----------------------------
1. ExecutionEngine を起動（本番またはペーパートレードは KABUSYS_ENV に依存）
   - PYTHONPATH=src python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）
     - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了
     - 実行中は data/execution.pid に PID を書き込み、停止フラグ（data/stop_requested.flag）を検知すると安全停止
     - Kill Switch（data/kill.flag）が書かれると ExecutionEngine 側で停止を検出できます

2. Monitoring を起動
   - PYTHONPATH=src python -m kabusys.run_monitoring
   - 挙動:
     - 環境にかかわらず監視は本番 sqlite_path（SQLITE_PATH）を使用して監視ログを保存します
     - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
     - data/stop_requested.flag を検知するとループを終了

3. Kill Switch（監視側で書き込む停止フラグ）
   - KillSwitch はリスク条件（ドローダウン、ポジション数超過等）を評価し、必要に応じて data/kill.flag を作成します
   - ExecutionEngine は起動時またはポーリング中に kill.flag の存在をチェックして停止できます

4. ログ
   - logging_setup によりコンソール出力（stdout） + 日次ローテートファイル（logs/<app_name>.log）
   - デフォルトログディレクトリ: logs/
   - ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御

5. ペーパートレード検証レポート
   - PYTHONPATH=src python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可）
   - 出力: 稼働率、注文成功率、レイテンシ等の指標と PASS/FAIL 判定

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- OPENAI_API_KEY（AI 機能）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト 60）
- PAPER_FILL_MODE（paper_trading 時の fill 挙動: instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか 1/0）

ディレクトリ構成（主なファイル）
------------------------------
（パスはプロジェクトルート、ソースは src/kabusys 内）

- src/
  - kabusys/
    - __init__.py  (パッケージ定義、__version__)
    - config.py    (Settings クラス、.env 自動ロード)
    - config_setup.py  (対話式 .env 作成ウィザード)
    - validate_config.py (設定検証 CLI)
    - run_execution.py   (ExecutionEngine 起動スクリプト)
    - run_monitoring.py  (Monitoring 起動スクリプト)
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py (※ここでは省略されているが概念上存在)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (※アラート送信ロジック)
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
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - data/ (実行時に生成されることが多い)
      - monitoring.db (デフォルト SQLITE_PATH)
      - paper_trading.db (ペーパートレード用)
      - kabusys.duckdb (デフォルト DUCKDB_PATH)
      - execution.pid, stop_requested.flag, kill.flag など

開発メモ / 実運用上の注意
------------------------
- KABUSYS_ENV を誤って live に設定したまま開発・テストすると実発注が行われるため注意してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup もそう案内します）。
- OpenAI API 呼び出しを使う機能は API キーと呼び出し料金が発生します。ネットワークやレート制限に対するリトライ・フォールバック実装あり。
- Monitoring は監視 DB（SQLite）へ永続化します。監視 DB は監視・分析に重要なのでバックアップを検討してください。
- run_execution/run_monitoring は stop flag（data/stop_requested.flag）で安全停止します。運用スクリプトや systemd / supervisor からの制御を想定しています。

よく使うコマンド例
------------------
- .env を作成:
  - PYTHONPATH=src python -m kabusys.config_setup
- 設定検証:
  - PYTHONPATH=src python -m kabusys.validate_config
- Execution 起動:
  - PYTHONPATH=src python -m kabusys.run_execution
- Monitoring 起動:
  - PYTHONPATH=src python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
（ここにはプロジェクトのライセンスと貢献方法を追記してください）

補足
----
この README はコードベースの主要モジュールと実行フローに基づき作成しています。細かい実装や追加の CLI、外部設定（config/*.yaml）については該当するソースファイルと config ディレクトリを参照してください。必要なら README に追記・調整します。