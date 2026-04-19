README
======

概要
----
KabuSys は日本株向けの自動売買および研究ツール群です。本リポジトリは以下を含みます:
- 発注・実行エンジン起動スクリプト（run_execution）
- システム監視 / Kill Switch / アラート処理（run_monitoring, monitoring パッケージ）
- ポートフォリオ構築、ポジションサイジング等の純粋関数群（portfolio パッケージ）
- ファクター計算・特徴量探索（research パッケージ）
- LLM を用いたニュースセンチメントや市場レジーム判定（ai パッケージ）
- 環境設定ウィザード・設定検証ツール（config_setup / validate_config）
- 運用支援ツール（tools/*.py）

主要な設計方針:
- 本番 DB とペーパートレード用 DB を分離（paper_trading モード）
- ルックアヘッドバイアス対策のため日付参照を直接使わない実装
- フェイルセーフ（API 失敗時は安全側にフォールバック）
- ロギング・プロセス優先度設定・Kill Switch 等の運用機能を組み込み

機能一覧
--------
- 環境設定ウィザード: python -m kabusys.config_setup にて .env を対話的に作成
- 設定検証: python -m kabusys.validate_config で .env と config/*.yaml の整合性確認
- ExecutionEngine 起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring 起動: python -m kabusys.run_monitoring
  - システム・注文・リスクを定期チェックし、必要なら kill.flag を書き込む
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
- Kill Switch: 監視コンポーネントでドローダウンやポジション上限を検出すると data/kill.flag を作成
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- LLM ベースのニュースセンチメント（OpenAI）および市場レジーム判定
- ポートフォリオ構築ユーティリティ（候補選定・重み計算・ポジションサイズ計算・セクターキャップ等）
- DuckDB を利用した研究・ファクター計算モジュール

セットアップ手順
----------------
前提:
- Python 3.10+
- システムパッケージ: libsqlite3 等が必要な場合あり

1. リポジトリをクローン／配置
   - ソースは src/kabusys に入っています。

2. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 主要依存例:
     - duckdb
     - psutil
     - openai
     - pyyaml (設定検証で使用)
   - 例: pip install duckdb psutil openai pyyaml

3. .env を作成
   - 対話式ウィザードで作成: python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 推奨設定:
     - KABUSYS_ENV=development | paper_trading | live
     - LOG_LEVEL=INFO（または DEBUG 等）
   - 自動ロード:
     - リポジトリルートに .env / .env.local があれば自動で読み込みます（環境変数優先）。
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit 1）になります。

5. データディレクトリ（任意）
   - デフォルトの DB / フラグファイルパス:
     - DuckDB: data/kabusys.duckdb (DUCKDB_PATH)
     - SQLite (monitoring): data/monitoring.db (SQLITE_PATH)
     - Paper trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
     - ログ: logs/<app_name>.log
     - PID / stop フラグ: data/execution.pid / data/stop_requested.flag
     - Kill フラグ: data/kill.flag

使い方
------
環境変数の例（.env）:
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_token
- KABU_API_PASSWORD=your_password
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

主要コマンド:
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading DB に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動を中止
    - 正常起動後は data/execution.pid に PID を書き、内部スレッドで engine.run_session() を実行
    - 停止要求: data/stop_requested.flag を作る（外部で作成）とエンジンを停止します
- Monitoring 起動:
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings.sqlite_path を使って監視用 SQLite に接続（環境にかかわらず本番 sqlite_path を参照）
    - MONITOR_POLL_INTERVAL（秒）でポーリング（デフォルト 60）
    - Stop リクエストは data/stop_requested.flag を作成
    - 監視で Kill 条件が満たされた場合、KillSwitch が Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込みます
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH または --db で DB を指定

監視・停止関連
- 停止（外部）:
  - run_execution / run_monitoring は project_root/data/stop_requested.flag を監視してループを終了します。停止したい場合はそのファイルを作成してください。
- Kill Switch（自動停止）:
  - 監視モジュールがドローダウンやポジション上限等を検出すると Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START が 1 に設定されていると起動時に自動で kill.flag をクリアしますが、本番では 0 を推奨します。
- ログ:
  - logs/<app_name>.log に日次ローテーションで出力（デフォルト 30 日保持）。標準出力にも同じ内容を出力します。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
- LOG_LEVEL — デフォルト INFO
- OPENAI_API_KEY — ai モジュールで必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading のモック執行挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

ディレクトリ構成（主なファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数/.env の自動読み込みと Settings クラス
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定検査 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（PID / stop フラグ管理）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
- utils/
  - logging_setup.py: ログ設定ユーティリティ（stdout + 日次ローテートファイル）
  - process_priority.py: プロセス優先度・CPU affinity 設定
- monitoring/
  - monitoring_db.py: SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: システム・データ鮮度監視
  - trade_monitor.py: （発注ログ等の監視）※実装あり
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 書き込みロジック
  - alert_manager.py: （アラート送信管理）※実装あり
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - Execution ロジック・ブローカ抽象化（paper_trading 用の MockBroker をサポート）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定・重み算出・ポジションサイズ計算・セクター制限等
- research/
  - factor_research.py, feature_exploration.py
  - DuckDB を使ったファクター計算・IC 等の研究ユーティリティ
- ai/
  - news_nlp.py: ニュースセンチメントの LLM スコアリング
  - regime_detector.py: マクロ + ma200 を使った市場レジーム判定
- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成ツール

運用メモ / 注意点
----------------
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離されます。安全に動作確認できます。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup でも注意喚起あり）。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します。自動クリアは危険です。
- OpenAI API や外部 API 呼び出しは冪等性・リトライを考慮して実装されていますが、API キーの管理とコストに注意してください。
- ロギングディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

サポート / 開発
----------------
- 新しい設定項目を追加した場合は config_setup.py と validate_config.py を合わせて更新してください。
- DB スキーマ変更は monitoring_db.init_monitoring_db にマイグレーションロジックを追加してください。
- テストでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードが無効になります。

以上。運用時の操作や設定に不明点があれば該当モジュールの docstring を参照してください（モジュール内に詳細な説明があります）。