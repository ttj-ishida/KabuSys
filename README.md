# KabuSys — README

概要
- KabuSys は日本株の自動売買・リサーチ・監視を目的としたプロジェクトです。
- 発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI ベースのニュース分析などの機能を含みます。
- 設定は .env（または環境変数）で行い、DuckDB / SQLite をローカル DB として利用します。
- paper_trading（ペーパートレード）モードをサポートし、本番 DB と分離してテスト運用が可能です。

主な機能一覧
- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードの切り替え。paper_trading 時は MockBrokerClient を利用し data/paper_trading.db に記録
  - プロセス優先度設定・PID 管理・停止フラグ監視
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine（run_monitoring.py）
  - system_status / trade_logs / risk_logs / positions / dashboard を持つ監視用 SQLite（monitoring_db）
  - Kill Switch によるフラグファイル書き込みで ExecutionEngine を安全停止
  - MONITOR_POLL_INTERVAL によるループ間隔の調整（デフォルト 60 秒）
- ポートフォリオ構築
  - 候補選定、重み計算（等金額・スコア重み）、ポジションサイズ計算、セクター上限、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI 連携）
  - ニュースのセンチメントスコア化（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - 両者は OpenAI API キー（OPENAI_API_KEY）が必要
- ツール
  - .env 作成ウィザード（config_setup.py）
  - 起動前チェック（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- ユーティリティ
  - 統一ログ設定（utils.logging_setup.setup_logging）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン＆作業ディレクトリへ移動
   - （例）git clone ... && cd <repo>

2. Python 仮想環境の作成と有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール
   - duckdb, psutil, openai, PyYAML（validate_config の YAML チェック用）などをインストールしてください。
   - 例: pip install duckdb psutil openai PyYAML

   ※ requirements.txt はこのコードベースに含まれていないため、実行に必要なライブラリは用途に応じてインストールしてください。

4. 環境変数 / .env の作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - もしくは .env.example を参照して .env を作成してください（リポジトリに .env.example がある想定）。
   - 自動読み込み: プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env / .env.local を自動で読み込みます。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます: python -m kabusys.validate_config --strict

6. DB・ログディレクトリ
   - デフォルトで以下のファイルパスが使用されます（.env で上書き可）
     - DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH)
     - SQLite (監視): data/monitoring.db (SQLITE_PATH)
     - Paper trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
   - ログは logs/<app_name>.log（デフォルト）に日次ローテーションで出力されます。LOG_DIR で変更可能。

使い方（主なコマンド）
- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 説明: ExecutionEngine を起動します。KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB を使用します。
  - 停止方法: data/stop_requested.flag を作成すると起動中のエンジンに停止シグナルを送ります（監視プロセス等から Kill Switch により書き込まれる場合もあります）。
  - PID ファイル: data/execution.pid（デフォルト）

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 説明: SystemMonitor をポーリングし、監視 DB に記録・アラート判定を行う。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（環境にかかわらず production の monitoring DB を参照）

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env の初期作成・更新を対話式で行います。

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告を FAIL 扱いにできます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - --db で DB ファイルを明示的に指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（プログラムから直接呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）に問い合わせ、ai_scores テーブルへ書き込む
    - OPENAI_API_KEY 環境変数、または api_key 引数が必要
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 乖離とマクロニュースを組み合わせて市場レジームを判定・DB に書き込み

重要な環境変数（代表）
- 必須（起動前に設定）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB / ログ関連
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
  - LOG_LEVEL, LOG_DIR
- 実行制御
  - MONITOR_POLL_INTERVAL (監視ポーリング間隔、秒)
  - KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: 0/1)
  - PAPER_FILL_MODE (ペーパートレードでの約定挙動: instant | partial | never | reject)
- OpenAI
  - OPENAI_API_KEY（AI モジュールを使う場合必須）

停止 / Kill Switch / フラグファイル
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py などはこのファイルの存在を監視して安全にループを終了します（外部から停止したいときに利用）。
- data/kill.flag
  - KillSwitch が評価条件を満たした場合に書き込まれ、ExecutionEngine の停止トリガとして使用されます。
- PID ファイル
  - data/execution.pid（ExecutionEngine 起動時に書き込まれます）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py (パッケージ定義、バージョン)
  - config.py (環境変数/.env の自動ロードと Settings クラス)
  - config_setup.py (.env 対話式ウィザード)
  - validate_config.py (起動前チェック CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリングループ起動スクリプト)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート)
  - utils/
    - logging_setup.py (共通ログ設定)
    - process_priority.py (プロセス優先度 / CPU affinity)
  - monitoring/
    - monitoring_db.py (監視用 SQLite の初期化・永続化層)
    - monitoring_engine.py (複数 Monitor を束ねるエンジン)
    - system_monitor.py (システム状態・データ鮮度監視)
    - risk_monitor.py (ドローダウン・ポジション制限監視)
    - kill_switch.py (kill.flag 制御)
    - ... (TradeMonitor / AlertManager 等はコードベースに存在)
  - execution/ (発注系コンポーネントが集約される想定)
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, ...
  - portfolio/
    - portfolio_builder.py (候補選定・重み)
    - position_sizing.py (株数算出・制限)
    - risk_adjustment.py (セクターキャップ・レジーム乗数)
  - research/
    - factor_research.py (ファクター計算)
    - feature_exploration.py (将来リターン/IC/統計)
  - ai/
    - news_nlp.py (ニュースの LLM スコアリング)
    - regime_detector.py (レジーム判定)
  - data/ (実行時に生成・参照する想定のディレクトリ)
    - monitoring.db, paper_trading.db, kabusys.duckdb, kill.flag, stop_requested.flag, execution.pid
  - logs/
    - execution.log, monitoring.log, ... （ログはここに日次ローテーションで出力されます）

開発上のメモ / 注意点
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します（自動クリアは危険）。
- OpenAI を使用する機能は API コストがかかるため注意してください。API 呼び出しはリトライやバックオフ、レスポンス検証を実装していますが、利用前に設定と料金体系を確認してください。
- validate_config.py は PyYAML 非インストール時に YAML 内容チェックをスキップします。フルチェックのために PyYAML を入れておくとよいです。
- duckdb, psutil, openai など外部ライブラリは用途に応じてインストールしてください。

ライセンス・貢献
- この README にライセンス情報や貢献方法は含まれていません。実際のプロジェクトでは LICENSE ファイルや CONTRIBUTING を用意してください。

問い合わせ
- ソースコード内の docstring・コメントに設計意図・使い方が記載されています。各モジュールの docstring を参照して実装詳細を確認してください。

以上。必要なら「導入手順の詳しいコマンド例」や「主要 CLI の利用例（実行ログ例）」などを追記しますので教えてください。