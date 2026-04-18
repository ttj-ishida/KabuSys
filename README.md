README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。  
このリポジトリは、以下の主要機能を備えた Python パッケージ構成になっています。

- 発注実行エンジン（ExecutionEngine：本番 / ペーパートレード対応）
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築・ポジションサイジングの純関数群
- リサーチ用ファクター計算・特徴量解析（DuckDB 経由）
- ニュース NLP（OpenAI を利用したセンチメント評価）および市場レジーム判定
- 各種 CLI ユーティリティ（環境設定ウィザード・設定検証・レポート生成）

主要な設計方針は「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアスの回避」「外部 API 呼び出しは必要箇所のみ」「監視は冪等かつフェイルセーフ」にあります。

機能一覧
--------
- run_execution.py: ExecutionEngine を起動。KABUSYS_ENV により本番/ペーパートレードを切替。
  - paper_trading では MockBrokerClient を使用し data/paper_trading.db に記録。
- run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔指定可（デフォルト 60 秒）。
- monitoring/*: MonitoringDB（SQLite）、System/Trade/Risk モニタ、KillSwitch、Alert 管理等。
- portfolio/*: 候補選定、重み計算、セクター制約、ポジションサイズ計算等の純粋関数群。
- research/*: DuckDB を使ったファクター計算、将来リターン・IC 計算、統計サマリー等。
- ai/*: news_nlp（ニュースの LLM 評価→ai_scores へ書込）、regime_detector（市場レジーム判定）。
- tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成。
- config_setup.py: 対話式 .env 生成ウィザード。
- validate_config.py: .env と config/*.yaml の簡易検証 CLI。
- utils/*: ログ設定、プロセス優先度・CPU affinity ユーティリティ等。

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | 演算子や型注釈を使用）
- システムに sqlite3（標準）、DuckDB、psutil、openai などが必要（以下に推奨パッケージを示します）

推奨パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（config YAML を検証する場合）
- （必要に応じて）その他 DB ドライバや依存ライブラリ

インストール例（仮）
- 仮想環境作成・有効化後:
  - pip install duckdb psutil openai PyYAML

リポジトリ初期化
1. リポジトリルートで仮想環境を作り依存をインストール
2. data/ および logs/ ディレクトリを作成（多くの処理は自動作成しますが事前に作ると権限問題を回避できます）
   - mkdir -p data logs

環境変数（.env）設定
1. 対話式ウィザードで .env を作成:
   - python -m kabusys.config_setup
2. 作成後、設定検証を実行:
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

主な環境変数（重要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- OPENAI_API_KEY: OpenAI を使う機能に必要（news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- PAPER_FILL_MODE: ペーパートレードの注文執行モード（instant/partial/never/reject）

使い方（起動コマンド・ユーティリティ）
----------------

1. 環境設定作成（推奨）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード: python -m kabusys.validate_config --strict

3. ExecutionEngine 起動（本番または paper_trading に応じて挙動が変化）
   - python -m kabusys.run_execution
   - 備考:
     - KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に書き込みます。
     - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
     - エンジンは data/execution.pid を使用してプロセス管理を行います。
     - 停止シグナルは KillSwitch（data/kill.flag）または stop_requested.flag によって行います。

4. 監視ループ起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
   - 監視は常に（KABUSYS_ENV に関わらず）本番 sqlite_path を使用して記録します。
   - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行えます。

5. ペーパートレード検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - --from YYYY-MM-DD --to YYYY-MM-DD
   - DB 指定:
     - --db PATH（省略時は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

6. AI / リサーチ機能（プログラムから利用）
   - ニュース NLP（スコア付与）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key=...)
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key=...)
   - DuckDB 接続は duckdb.connect(path) で生成して渡します。

ログ・監視
--------
- ログはデフォルト logs/<app_name>.log に TimedRotatingFileHandler（日次ローテーション、30日分保持）として保存されます。アプリケーション開始時に kabusys.utils.logging_setup.setup_logging(app_name="execution") 等を呼び出します。
- 監視用データベース: data/monitoring.db（SQLite）
- ペーパートレード DB: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
- Kill Switch / 停止フラグ:
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止を促します（KillSwitch は書き込みを冪等に行います）。
  - run_execution/run_monitoring は data/stop_requested.flag の存在を検知してループを抜けます。
- PID ファイル:
  - data/execution.pid を利用して実行状態を管理します（エンジン起動時のためのファイルパス）。

ディレクトリ構成
----------------
以下は主要ファイル・ディレクトリの抜粋（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル初期化含む）
    - system_monitor.py
    - trade_monitor.py        — （trade の監視ロジック）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                     — 実行時生成することが想定されるディレクトリ（DB/フラグ等）
  - logs/                     — ログ出力先（デフォルト）

補足・運用上の注意
-----------------
- 本番（KABUSYS_ENV=live）では kill.flag 等の扱いに注意してください。validate_config は live 環境に対して追加の警告を出します。
- データ鮮度やプロセス死活検知は監視コンポーネントによって行われ、重大なアラート発生時には KillSwitch による停止や alert_manager での通知が行われます。通知先（LINE など）は環境変数で設定します。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）を要求します。API 呼び出しはリトライやフェイルセーフを含む実装になっていますが、料金・レートに注意してください。
- DuckDB / SQLite のファイルはデフォルトで data/ 以下を使います。バックアップや権限管理は運用ポリシーに従ってください。
- 開発者向け: 単体関数群（portfolio/*, research/*）は副作用がなくテストしやすい設計です。ユニットテストを書くことでアルゴリズムの妥当性を検証できます。

よく使うコマンドまとめ
--------------------
- .env の初期作成: python -m kabusys.config_setup
- 設定検証:         python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動:   python -m kabusys.run_monitoring (MONITOR_POLL_INTERVAL=30 等で上書き可)
- ペーパートレード検証: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

この README はコードベースの主要な使い方とアーキテクチャをまとめたものです。詳細な設計意図やアルゴリズムの説明（PortfolioConstruction.md、StrategyModel.md 等）が別資料にある想定のため、必要に応じてそれらのドキュメントやコード内の docstring を参照してください。