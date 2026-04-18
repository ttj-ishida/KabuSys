KabuSys — 日本株自動売買システム
================================

このドキュメントはリポジトリ内のコードベース（src/kabusys/**）をもとに作成した README です。
実行スクリプト、設定周り、主要コンポーネント、ディレクトリ構成、セットアップ／利用手順を日本語でまとめています。

概要
----
KabuSys は日本株の自動売買／リサーチ基盤を想定した Python パッケージです。  
主な機能は以下のカテゴリに分かれます。

- 実行（Execution）: 注文生成・発注・リスク管理を行う ExecutionEngine（run_execution.py）
- 監視（Monitoring）: システム稼働状況・注文ログ・リスク指標を定期収集するモジュール（run_monitoring.py / MonitoringEngine）
- ポートフォリオ構築: 銘柄選定、重みづけ、ポジションサイズ算出（kabusys.portfolio）
- リサーチ: ファクター計算／特徴量解析（kabusys.research）
- AI ユーティリティ: ニュース NLP による銘柄センチメント / 市場レジーム判定（kabusys.ai）
- ユーティリティ: ロギング設定、プロセス優先度設定、.env ウィザード、設定検証など

主な特徴
--------
- Execution と Monitoring を別プロセスで実行する設計（PID / フラグファイルで連携）
- Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker + 専用 SQLite（data/paper_trading.db）を使用し本番 DB と分離
- DuckDB を用いた分析用データ格納（デフォルト: data/kabusys.duckdb）
- OpenAI（gpt-4o-mini 相当）を利用したニュースセンチメント判定と市場レジーム判定機能（API キー必要）
- 監視ログ用の SQLite（data/monitoring.db）を使った履歴・アラート管理
- .env 対話式ウィザードと起動前の設定検証ツールを提供

セットアップ手順（ローカル開発用）
--------------------------------
前提:
- Python 3.10+ を推奨（PEP 604 の union 型等を使用）
- 仮想環境（venv / pyenv など）を推奨

1. ソース取得
   - リポジトリをクローンし、プロジェクトルートで作業します。パッケージは src 配下に配置されています。

2. 依存ライブラリのインストール
   - requirements.txt が無い場合は最低限以下をインストールしてください（機能に応じて追加で必要）。
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル検証に利用、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env の作成（対話式）
   - 対話式ウィザードで初期 .env を作成できます:
     - python -m kabusys.config_setup
   - ウィザードでは J-Quants / kabuステーション の認証情報などを設定します。

4. 設定の検証
   - .env 作成後に設定チェックを実行:
     - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. DB / ディレクトリ
   - デフォルトのパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要に応じて上記を .env で上書きしてください。起動時に監視 DB のテーブルは自動作成されます。

主要な環境変数（抜粋）
--------------------
必須（少なくとも設定ウィザードで入力すること）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意 / 設定可能な変数
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能利用時に必要）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）、デフォルト 60）

使い方（実行例）
----------------

1. 監視プロセスの起動
   - 監視ループを開始する:
     - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - run_monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使って監視テーブルを初期化します。

2. 実行エンジンの起動（注文発注）
   - ExecutionEngine を起動:
     - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録されるため本番 DB と分離されます。

3. 強制停止 / Kill スイッチ
   - 外部からの停止要求（監視・実行プロセス共通）:
     - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検出して終了します。
   - Kill Switch は内部で data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る仕組みです（しきい値に応じて監視モジュールが書き込みます）。
   - KILL_FLAG_CLEAR_ON_START を 1 に設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

4. Paper Trading 検証レポート
   - ペーパートレード用の検証レポートを生成:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

内部 API / 呼び出し可能関数（概要）
--------------------------------
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡しニュースセンチメントを ai_scores テーブルへ書き込む。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込む。
- kabusys.research.calc_momentum / calc_volatility / calc_value
  - DuckDB を使ってファクター計算を実行。
- kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier
  - ポートフォリオ構築に関する純粋関数群（DB 参照なし）。

ロギング & プロセス優先度
------------------------
- 全スクリプトは共通のロギング設定ユーティリティ（kabusys.utils.logging_setup.setup_logging）を使います。ログファイルは logs/<app_name>.log に日次ローテートで保存されます（デフォルト 30日保持）。
- 起動時に set_process_priority("high") を呼び出してプロセス優先度を上げます（プラットフォーム依存で失敗しても警告のみ）。

監視 / DB（簡単な説明）
---------------------
- 監視用 SQLite（monitoring.db）に以下のテーブルを保持します（自動作成／マイグレーションあり）:
  - system_status: CPU/Memory/Disk/プロセス稼働などの時系列
  - trade_logs: 注文イベントログ（Created/ Sent / Filled 等）
  - positions: 保有ポジション（code を主キー）
  - risk_logs: リスクに関するログ（ドローダウンなど）
  - dashboard: 集計（id=1 の単一レコード）
- MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor を束ね、アラート判定・KillSwitch 評価を行います。

ディレクトリ構成（src/kabusys の主要ファイル一覧）
----------------------------------------------
（重要なファイル・モジュールの概要）

- __init__.py
- config.py
  - 環境変数のロード（.env/.env.local 自動読み込み）と Settings クラス
- config_setup.py
  - .env の対話式ウィザード
- validate_config.py
  - 起動前設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV による動作分岐）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- monitoring/
  - monitoring_db.py: 監視 DB アクセス層
  - monitoring_engine.py: 各モニタの束ね
  - system_monitor.py: システム/データ鮮度監視
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の書き込みロジック
  - trade_monitor.py, alert_manager.py 等（監視ロジック群）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - （注文発注ロジック・Broker インタフェース）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py: ニュースを LLM でスコアリングして ai_scores 更新
  - regime_detector.py: MA とマクロニュースを組み合わせたレジーム判定
- utils/
  - logging_setup.py: 共通ログ設定
  - process_priority.py: プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py: Paper Trading 検証レポート生成

運用に関する注意点
------------------
- 本番（KABUSYS_ENV=live）では kill.flag 自動クリア（KILL_FLAG_CLEAR_ON_START=1）を避けてください。誤って自動クリアすると Kill Switch が無効化される可能性があります。
- 設定ファイル（.env）はセキュリティ上 Git 管理しないでください（config_setup のヘッダにもその旨を記載）。
- OpenAI API を利用する機能は API キーと料金に注意してください。API 呼び出しはバックオフやフォールバック（失敗時は中立値）を実装していますが、呼び出し量に留意してください。
- Paper Trading モードでは必ず専用 DB（PAPER_TRADING_SQLITE_PATH）を使用することで本番 DB と記録を分離しています。切り替え忘れに注意してください。

よくある操作フロー（例）
-----------------------
1. 初回セットアップ
   - pip install ...
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. 監視開始
   - python -m kabusys.run_monitoring

3. 実行（当日のセッション）
   - python -m kabusys.run_execution

4. ペーパートレード検証
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 追記
----------------
この README はコードベースに含まれる docstring と実装を元に作成しました。実際のデプロイ時には OS 固有の挙動（プロセス優先度設定やファイルパーミッション）、Broker 実装、ネットワーク設定、監視・アラートの配信先（LINE 等）の動作確認を行ってください。

必要であれば、README に起動時の具体的な systemd unit 例や Dockerfile / docker-compose のサンプル、さらに詳細なアーキテクチャ図を追加できます。どの情報が必要か教えてください。