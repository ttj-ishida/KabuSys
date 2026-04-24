README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究用ライブラリ群です。本リポジトリは以下を提供します。

- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視ポーリング（Monitoring）
- ペーパートレード用検証・レポート生成ツール
- ファクター計算・特徴量探索・ポートフォリオ構築の純粋関数群
- ニュース NLP / レジーム判定（OpenAI を用いたスコアリング）
- 設定ウィザード・設定検証 CLI
- SQLite / DuckDB を用いた永続化・分析インターフェース

特徴
----
- 実稼働（live）とペーパートレード（paper_trading）を環境変数で切り替え可能
- 監視コンポーネントは常に本番の monitoring DB（sqlite_path）へ記録
- ExecutionEngine は paper_trading 時に専用 DB に分離（PAPER_TRADING_SQLITE_PATH）
- ログは標準出力と日次ローテートファイル（logs/<app>.log）へ書き出し
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロセンチメントによる AI モジュール
- DuckDB を用いた高速な分析クエリ（ファクター計算・研究用モジュール）
- .env 対話式ウィザードと設定検証ツールを同梱

前提 / 必要パッケージ
-------------------
Python と pip が利用できること。主な外部依存（プロジェクトの用途によりすべて必要）:

- duckdb
- psutil
- openai
- PyYAML（config YAML の検証にのみ必要）
- その他（プロジェクト全体には他モジュールがある場合があります）

インストール（例）
- 仮想環境推奨:
  python -m venv .venv
  source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール:
  pip install duckdb psutil openai PyYAML

セットアップ手順
--------------
1. プロジェクトルートに移動（README があるディレクトリ）
2. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークン / kabuAPI パスワード 等を入力する
3. 設定検証
   - python -m kabusys.validate_config
   - 必須 env が揃っているか、ファイルパス等の基本チェックを行います
   - --strict を付けると警告も失敗扱いになります
4. 必要なディレクトリの作成
   - data/ logs/ （logging_setup が自動で作成しようとしますが、パーミッション等で失敗する場合があるため事前作成推奨）
5. DB 初期化
   - 実行スクリプト（run_monitoring / run_execution）が起動時に監視用テーブルを冪等で初期化します
   - DuckDB ファイル（デフォルト data/kabusys.duckdb）は外部処理で準備してください（analysis 用テーブル等）

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 時の専用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI モジュール利用時に必要）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。開発用）

自動 .env 読み込み
- プロジェクトルート（.git か pyproject.toml を探す）から .env と .env.local を自動読み込みします
- OS 環境変数が優先され、.env.local は .env を上書きします
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

使い方
------

1) 設定ウィザード（.env を作成 / 更新）
- python -m kabusys.config_setup

2) 設定の静的検証
- python -m kabusys.validate_config
- オプション: --strict

3) 監視（Monitoring）を起動
- python -m kabusys.run_monitoring
  - 役割: SystemMonitor 等を初期化しポーリングループで定期チェックを実行
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定可能（デフォルト 60）
  - 監視は Settings.sqlite_path（本番の monitoring DB）を常に使用する
  - 停止: プロジェクトの data/stop_requested.flag が存在するとループを抜けて終了

4) 実行エンジン（ExecutionEngine）を起動
- python -m kabusys.run_execution
  - 役割: Broker クライアントや OrderManager、RiskManager 等を組み立てて発注セッションを実行
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録する（本番 DB と分離）
  - 起動直後に data/stop_requested.flag がある場合は起動せず終了
  - 実行中は data/execution.pid に PID を書く（設定に応じたパス）

5) ペーパートレード検証レポート生成
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB パス: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 出力: 稼働率 / 注文成功率 / レイテンシ等を集計して PASS/FAIL 判定を出力

停止フラグ / Kill Switch
- data/stop_requested.flag
  - run_monitoring と run_execution の両方がチェックします。存在すると起動中ループを終了・停止します
- data/kill.flag
  - KillSwitch が条件を満たすと書き込むフラグ（ExecutionEngine 停止のための指示）
  - KillSwitch の判断は RiskMonitor / SystemMonitor / TradeMonitor の結果に基づきます
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアする（本番では 0 を推奨）

ログ
----
- logging_setup が統一的に設定します
  - コンソール（stdout）へ出力
  - 日次ローテーションで logs/<app_name>.log に出力（バックアップ 30 日）
- app_name は run_monitoring なら "monitoring"、run_execution なら "execution" など

監視 DB 初期化
---------------
- init_monitoring_db(conn) により SQLite に必須テーブル（system_status, trade_logs, positions, risk_logs, dashboard）を冪等で作成します
- マイグレーション処理（カラム追加）も一部自動で行います（例: trade_logs.latency_ms, dashboard.peak_value）

主要モジュール説明（抜粋）
------------------------
- kabusys.config
  - .env 自動読み込み、Settings クラスでアプリ設定を提供
- kabusys.config_setup
  - .env の対話式作成ウィザード
- kabusys.validate_config
  - 起動前チェック CLI（必須 env / config/*.yaml の検証 等）
- kabusys.utils.logging_setup
  - ルートロガーの初期化（コンソール + ファイルローテーション）
- kabusys.utils.process_priority
  - psutil を使ったプロセス優先度設定・CPU affinity ユーティリティ
- kabusys.monitoring.*
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch
  - MonitoringDB: SQLite を使った永続化層（読み書きロジック）
- kabusys.execution.*
  - BrokerFactory / ExecutionEngine / OrderManager / RiskManager 等（発注ロジック）
- kabusys.portfolio.*
  - 銘柄選定・重み計算・ポジションサイジング・セクター制限
- kabusys.research.*
  - ファクター計算（momentum / volatility / value）・特徴量探索（IC, forward returns 等）
- kabusys.ai.*
  - news_nlp: OpenAI を用いたニュースのセンチメント集計と ai_scores への保存
  - regime_detector: マクロ + ETF MA200 を合成して market_regime を算出

ディレクトリ構成（主要ファイル）
-----------------------------
リポジトリの主要なディレクトリ構成（src/kabusys 以下を中心にまとめています）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化・CRUD
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 発注ログ監視（ファイルに含まれる）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の作成 / 管理
    - monitoring_engine.py   — 各 Monitor の統合ループ
    - alert_manager.py       —（アラート送信処理）
  - execution/
    - execution_engine.py    — 実行エンジン本体
    - broker_factory.py      — ブローカークライアント生成
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
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/  (ランタイム生成 / DB 保存用ディレクトリ)
  - logs/  (ログ保存用ディレクトリ)

補足 / 運用上の注意
------------------
- 本番環境（KABUSYS_ENV=live）では kill.flag・stop フラグ等の設定を慎重に扱ってください。validate_config は本番時に注意喚起を出します。
- OpenAI を利用する機能は API キーと料金が必要です。API の失敗はフェイルセーフで 0 相当やスキップする設計ですが、運用ポリシーに合わせて監視を行ってください。
- run_execution と run_monitoring はプロセス優先度を高めに設定します（set_process_priority("high")）。権限不足で失敗する場合は警告ログが出ます。
- データベースファイル（特に本番の SQLite）はバックアップやパーミッションに注意してください。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = 0.1.0（src/kabusys/__init__.py）
- ライセンスや詳細はリポジトリのトップレベルの LICENSE / pyproject.toml を参照してください（存在する場合）。

問い合わせ
----------
コードやドキュメントに関する質問があれば、開発チームの運用ルールに従って issue を作成してください。

以上。