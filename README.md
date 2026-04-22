KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした小規模なフレームワークです。  
主な機能は以下のとおりです（詳細は次節を参照）。

主な特徴
--------
- 戦略リサーチ（DuckDB を使ったファクター計算、将来リターン、IC 計算など）
- ポートフォリオ構築（候補選定、重み計算、セクター制限、リスクベースのポジションサイジング）
- 実行エンジン（本番 / ペーパー分離、ブローカーファクトリによる抽象化）
- 監視機能（システム健全性・データ鮮度・トレード状態・リスク監視、アラート／Kill Switch）
- AI 統合（OpenAI を使ったニュースセンチメントおよび市場レジーム判定）
- 運用ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート）
- ログはコンソール + 日次ローテート（logs/ ディレクトリ）で統一管理

前提条件
--------
- Python 3.10 以上（型ヒントの Union 表記などのため）
- SQLite（標準ライブラリ）
- 以下の主要ライブラリ（最低限）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合に推奨）
- ネットワーク接続（OpenAI を使う機能を利用する場合）

推奨インストール例
------------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（requirements.txt がない場合）
   - pip install duckdb psutil openai PyYAML

設定（.env）
-----------
プロジェクトルートに .env を置くことで環境変数を簡単に管理できます。自動生成ツールと検証ツールを用意しています。

- 対話式ウィザードで作成:
  - python -m kabusys.config_setup
- 起動前に検証:
  - python -m kabusys.validate_config
  - 必須環境変数が不足しているとエラーになります。--strict を付けると警告も失敗扱いになります。

主要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- よく使う / 推奨:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb（分析用 DB）
  - SQLITE_PATH: data/monitoring.db（監視ログ用 DB）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパー用監視 DB）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR
  - OPENAI_API_KEY: OpenAI を使う場合に設定
  - PAPER_FILL_MODE: ペーパー売買時の成り行き・部分約定挙動（instant|partial|never|reject）
- モニタリング設定:
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、既定 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

注意:
- .env は決して Git にコミットしないでください（機密情報が含まれます）。

セットアップ手順（簡易）
------------------------
1. 必要パッケージをインストール（上記参照）。
2. .env を作成（python -m kabusys.config_setup を推奨）。
3. 設定検証（python -m kabusys.validate_config）。
4. data/ および logs/ ディレクトリが自動作成されますが、権限等に注意してください。

使い方（実行例）
----------------

- 実行エンジン（ExecutionEngine）
  - 本番／ペーパー共通起動スクリプト:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）へ記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
    - 実行中は内部で data/execution.pid（デフォルト）を書きます。
    - プロセス優先度を high に設定します（可能な場合）。
    - 停止は KeyboardInterrupt、または kill.flag による Kill Switch、あるいは data/stop_requested.flag ファイル作成で検知します。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL によりポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
    - 監視は本番 sqlite_path を使用（環境にかかわらず同じ監視 DB を使います）。
    - data/stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI 関連（プログラムから呼ぶ API）
  - ニュース NLP スコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

運用・停止
----------
- Graceful 停止（外部から）:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring スクリプトが起動中に検知して停止します。
- Kill Switch:
  - 監視コンポーネント（KillSwitch）が条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）を作成して ExecutionEngine に停止を促します（ExecutionEngine 側で対応する処理が入っています）。
- ログ:
  - logs/<app_name>.log に日次ローテーションで保存されます。コンソール出力は stdout。

主要モジュールと役割
--------------------
- kabusys.config: 環境変数と .env 自動ロード・Settings 抽象化
- kabusys.config_setup: .env を対話式で生成するウィザード
- kabusys.validate_config: 起動前チェック（必須環境変数、ファイルパス、YAML 構文など）
- kabusys.run_execution: ExecutionEngine を起動する CLI スクリプト
- kabusys.run_monitoring: SystemMonitor のポーリングループ起動スクリプト
- kabusys.execution.*: 発注・リスク管理・リコンシリエーションなどの実行ロジック（ファクトリ／エンジン等）
- kabusys.monitoring.*: system/trade/risk の各種監視、MonitoringDB（SQLite）への永続化、KillSwitch、MonitoringEngine
- kabusys.portfolio.*: 候補選定、重み付け、リスク適用、ポジションサイジング（純粋関数群）
- kabusys.research.*: DuckDB を用いたファクター計算・特徴量解析（研究用途）
- kabusys.ai.*: OpenAI を用いたニュースセンチメント、レジーム判定
- kabusys.utils.*: ログ設定、プロセス優先度、ユーティリティ

データ／ファイルレイアウト（主要）
---------------------------------
プロジェクトルート（抜粋）
- src/kabusys/
  - ai/
    - news_nlp.py
    - regime_detector.py
  - config.py
  - config_setup.py
  - validate_config.py
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - run_execution.py
  - run_monitoring.py
- config/  （各種 YAML テンプレート: system_config.yaml 等）
- data/    （デフォルトの DB / フラグ / pid ファイルを置く場所）
  - monitoring.db (SQLite)
  - paper_trading.db (ペーパー用 SQLite)
  - kabusys.duckdb (DuckDB)
  - execution.pid
  - kill.flag
  - stop_requested.flag
- logs/
  - execution.log
  - monitoring.log
  - ...（日次ローテート）

実装上の注意点
--------------
- Settings は環境変数を直接参照します。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動 .env 読み込みを無効化できます。
- 実行コンポーネントはプロセス優先度を "high" に変更しようとしますが、権限不足などで失敗する可能性があります（警告で継続します）。
- DuckDB / SQLite への書き込みはモジュール単位で行われ、監視用 DB と発注 DB（ペーパー）は用途に応じて分離されています。
- OpenAI API を使う機能は API キー必須。API の失敗時はバックオフしフォールバック（ゼロスコア等）で続行する設計です。

開発者向けメモ
--------------
- 研究・解析機能は DuckDB 接続を受け取る純粋関数として実装されています（外部副作用なし）。
- ユニットテスト時は OpenAI 呼び出し箇所（_kall_openai_api 等）をモックして挙動を検証してください。
- monitoring_db.init_monitoring_db は冪等で、既存 DB に対してカラム追加の簡易マイグレーションも実施します。

ライセンス / バージョン
-----------------------
- パッケージバージョン: kabusys.__version__ = 0.1.0
- ライセンス情報はリポジトリの LICENSE を参照してください（存在する場合）。

お問い合わせ
-----------
不明点や改善提案があれば Issue を立てるか、リポジトリの管理者に連絡してください。

（README 終わり）