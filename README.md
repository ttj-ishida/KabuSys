KabuSys — 日本株自動売買システム
================================

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買システム / 研究ツール群です。  
主な目的は以下を含みます。

- 戦略のためのファクター計算（DuckDB を用いた時系列計算）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- 実行層（ExecutionEngine）とモニタリング層（MonitoringEngine）
- Paper Trading 用の分離された DB・モックブローカー
- ニュース系の NLP（OpenAI）を用いたスコアリング・レジーム判定
- 運用監視、Kill Switch、アラート送出の仕組み
- 運用検証用レポートツール（paper_verification_report）

主要機能
--------
- 環境ごとに挙動を切り替え（KABUSYS_ENV: development / paper_trading / live）
- モニタ監視（CPU / メモリ / ディスク / データ鮮度 / 実行プロセスの存在）とログ永続化（SQLite）
- リスク監視（ドローダウン、ポジション上限）と Kill Switch（data/kill.flag）
- ExecutionEngine は paper_trading 環境では MockBrokerClient を利用し、本番 DB と分離
- Portfolio コンポーネント（候補選定、等金額・スコア加重、リスクベースのポジションサイズ）
- Research コンポーネント（モメンタム、ボラティリティ、バリューなどのファクター計算）
- AI コンポーネント（ニュースセンチメント、レジーム判定） — OpenAI API 利用（キー必要）
- ツール: .env 対話式ウィザード、設定検証 CLI、Paper Trading 検証レポート生成

前提（依存パッケージ）
--------------------
※プロジェクトの requirements.txt が別途ある想定ですが、主に下記が必要です。

- Python 3.9+（型注釈に依存するため現行の安定版を推奨）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定検証中に YAML ファイル検証を行う場合に任意）
- sqlite3（標準ライブラリ）

セットアップ手順
----------------
1. ソースを取得（プロジェクトルートが存在する前提）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML
   （AI 機能を使わない場合は openai は不要）
4. 実行方法の注意
   - 本リポジトリはパッケージ構成（src/kabusys）になっているため、プロジェクトルートで実行する場合は PYTHONPATH に src を含めるか editable install を行ってください。
     例:
       - PYTHONPATH=src python -m kabusys.validate_config
       - または pip install -e src

環境変数（主要）
----------------
主に .env で管理します。.env の作成は対話式ウィザードを利用できます（下記参照）。

必須（最低限設定が必要なもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用上よく使う（デフォルトがあるもの）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — AI 機能（news_nlp / regime_detector）で必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）デフォルト INFO
- LOG_DIR — ログ保存先（デフォルト logs/）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、default 60）
- PAPER_FILL_MODE — paper_trading 時の執行挙動 ("instant" | "partial" | "never" | "reject")
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1)

よく使うファイルパス
- data/kill.flag — Kill Switch 信号（監視が書き込むと ExecutionEngine を停止する）
- data/stop_requested.flag — 明示的停止フラグ（run_monitoring/run_execution のループ停止）
- data/execution.pid — ExecutionEngine の PID（設定により生成）

使い方（主要 CLI / スクリプト）
-------------------------------

1) .env を対話式で作成・更新
- python -m kabusys.config_setup
  → プロンプトに従って .env を生成します。

2) 設定検証
- python -m kabusys.validate_config
  → 環境変数・config/*.yaml の存在や基本的妥当性をチェックします。
- strict モード:
  - python -m kabusys.validate_config --strict
    → 警告も失敗扱い（exit code != 0）

3) モニタリング起動
- PYTHONPATH=src python -m kabusys.run_monitoring
  挙動:
    - Settings を読み、Monitoring DB（sqlite）へ接続して SystemMonitor をポーリングします。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可。デフォルト 60 秒。
    - stop フラグ (data/stop_requested.flag) が存在するとループを終了します。

4) 実行エンジン起動（Execution）
- PYTHONPATH=src python -m kabusys.run_execution
  挙動:
    - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に書き込み（本番 DB と分離）。
    - プロセス優先度の設定、依存コンポーネント（リスク管理、オーダーマネージャ等）を組み立てて実行します。
    - data/stop_requested.flag があれば起動を中止または実行中に停止します。

5) Paper Trading 検証レポート
- PYTHONPATH=src python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
  レポート: 稼働率、注文成功率、送信率、P95 レイテンシ 等を出力し PASS/FAIL を判定します。

停止・Kill Switch
-----------------
- 単純な停止（監視ループ / 実行ループ）:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループを終了します。
- Kill Switch（自動停止判定）:
  - 監視側の KillSwitch は risk 条件（ドローダウン / ポジション数超過）を満たした場合に data/kill.flag を書き込みます。
  - ExecutionEngine は kill.flag を検出すると安全に停止される設計です。
- kill.flag の自動クリア:
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を削除します（本番では 0 を推奨）。

ログ
----
- ログは標準出力に出力され、さらに logs/<app_name>.log に日次ローテーションで保存されます（デフォルト 30 日保持）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に設定されます。

AI（OpenAI）機能
----------------
- ニュースセンチメント（kabusys.ai.news_nlp）、レジーム判定（kabusys.ai.regime_detector）は OpenAI API（gpt-4o-mini 想定）を利用します。
- OPENAI_API_KEY を環境変数で設定するか、関数呼び出し時に api_key を渡してください。
- API 呼び出しは 429 / ネットワーク断 / 5xx を対象に指数バックオフでリトライします。失敗した場合は安全側のデフォルトで継続する設計です。

開発向け注意点
--------------
- DuckDB に格納するテーブル構成は research / ai モジュールの前提に依存します。prices_daily / raw_financials / raw_news 等のテーブルが必要です。
- MonitoringDB（SQLite）は init_monitoring_db により必要テーブルを自動作成します（マイグレーションロジックあり）。
- 設定ファイル（config/*.yaml）が必要な場合は scripts 等で生成し、validate_config で検証できます（PyYAML があれば内容検証も行われます）。

ディレクトリ構成（抜粋）
------------------------
src/kabusys/
- __init__.py
- config.py               — 環境変数/設定読み込みロジック
- config_setup.py         — .env 対話式ウィザード
- validate_config.py      — 設定検証 CLI
- run_monitoring.py       — Monitoring のポーリング起動スクリプト
- run_execution.py        — ExecutionEngine 起動スクリプト
- utils/
  - logging_setup.py      — ログ設定ユーティリティ
  - process_priority.py   — プロセス優先度・CPU affinity
- monitoring/
  - monitoring_db.py      — SQLite の永続化層
  - system_monitor.py
  - trade_monitor.py      — （コードベースに存在）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py      — （アラート連携の実装想定）
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - risk_manager.py
  - reconciler.py
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
- monitoring/
  - その他の監視関連モジュール

付記（運用上の推奨）
------------------
- 本番（KABUSYS_ENV=live）を使用する前に必ず validate_config を実行し、LINE など通知設定が正しいことを確認してください。
- data ディレクトリおよび logs ディレクトリのアクセス権・ディスク容量を監視してください。
- kill.flag / stop_requested.flag は運用者が手動で作成・削除することができます。自動クリア設定は慎重に扱ってください（本番では無効推奨）。

ライセンス / コントリビューション
---------------------------------
（ここにプロジェクトのライセンスや貢献ガイドラインを記載してください。）

以上。初期セットアップや実行で詰まる点があれば、該当箇所のログや実行コマンド、環境変数の内容（秘匿情報を除く）を教えてください。