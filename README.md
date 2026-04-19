KabuSys — 日本株自動売買システム（README 日本語版）
=================================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。本リポジトリは以下の主要機能を持ちます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行うランタイム
- 監視（Monitoring）: システム稼働状況・注文状態・リスクを定期チェックしアラート／Kill Switch を管理
- ポートフォリオ構築ユーティリティ: 候補選定、重み計算、ポジションサイズ決定、セクター制約等
- 研究用モジュール（Research）: ファクター計算、将来リターン・IC 計算、特徴量サマリ
- AI 統合（news_nlp / regime_detector）: OpenAI を利用したニュースセンチメント・レジーム判定
- ユーティリティ: ログ設定、プロセス優先度、設定ウィザード・検証、Paper Trading レポート生成 等

機能一覧
--------
主な機能と責務（抜粋）:

- config_setup.py: .env ファイルを対話式に生成・更新するウィザード
- validate_config.py: 環境変数や config/*.yaml を起動前に検証する CLI
- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV が paper_trading のときはペーパートレード用 DB / MockBroker を使用）
- run_monitoring.py: SystemMonitor をポーリング実行（MONITOR_POLL_INTERVAL で間隔を変更可能）
- monitoring/*: MonitoringDB（SQLite）への永続化、RiskMonitor、SystemMonitor、TradeMonitor、KillSwitch、MonitoringEngine、AlertManager（概要）
- portfolio/*: 候補選定、重み計算、ポジションサイズ、セクター制約、レジーム乗数など、純粋関数群
- research/*: DuckDB を使ったファクター計算・将来リターン・IC・統計サマリ
- ai/news_nlp.py, ai/regime_detector.py: OpenAI API を使ったニュースセンチメントや市場レジーム判定
- tools/paper_verification_report.py: ペーパートレード用 DB から検証レポートを生成

前提条件
--------
- Python 3.9+
- 必要なライブラリ（主なもの）:
  - duckdb
  - psutil
  - openai (AI 機能を利用する場合)
  - PyYAML（validate_config の YAML 検証を行う場合）
- SQLite（標準ライブラリで利用）
- （任意）kabuステーション API 環境

セットアップ手順
----------------

1. リポジトリをクローン / 展開
   - 例: git clone ...

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - 必要なパッケージを直接インストール:
     - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合は）pip install -r requirements.txt

4. データ・ログディレクトリの作成（自動作成されるが、手動で用意しておくと権限問題を回避できます）
   - mkdir -p data logs

5. 環境変数設定（対話式推奨）
   - python -m kabusys.config_setup
     - .env を生成 / 更新します。重要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。

6. 設定検証（任意）
   - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading: Execution は MockBroker を使用しデータは data/paper_trading.db に保存
  - live: 本番動作（実際に発注）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — AI 機能を使う場合に必要
- LOG_LEVEL — デフォルト: INFO
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（デフォルト: 0: クリアしない）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject、デフォルト instant）

使い方（コマンド例）
------------------

- 設定ウィザード（.env の作成/編集）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine の起動
  - python -m kabusys.run_execution
  - 実行は data/stop_requested.flag の存在を監視しており、フラグが作成されると停止処理を行います。
  - PID ファイル: data/execution.pid（デフォルト）。起動時にこのファイルを更新します。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
  - run_monitoring は monitoring 用 DB（Settings.sqlite_path）を使用します（環境に依らず本番の sqlite_path を使用する実装上の仕様に注意）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数、または data/paper_trading.db

- AI 機能（プログラムからの呼び出し）
  - news_nlp.score_news(duckdb_conn, target_date, api_key=None)
    - api_key を None にすると環境変数 OPENAI_API_KEY を参照します
  - ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

停止方法
--------
- 実行中プロセス（monitoring / execution）はプロジェクトルート下の data/stop_requested.flag をチェックして停止します。手動で停止するにはこのファイルを作成してください。
- KillSwitch（監視サブシステム）: 条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナル（kill.flag の存在）を与えます。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動で削除されます（本番では 0 推奨）。

ロギング
-------
- ログはデフォルト logs/ ディレクトリにアプリ名ごとに保存されます（例: logs/execution.log, logs/monitoring.log）。
- setup_logging() により Stream stdout と TimedRotatingFileHandler（日次ローテーション・30日保持）が設定されます。
- LOG_DIR / LOG_LEVEL 環境変数で出力先やレベルを上書き可能。

開発者向けメモ
--------------
- 設定ファイルの自動ロード:
  - プロジェクトルート（.git もしくは pyproject.toml のある親）から .env を自動的に読み込みます（.env.local は上書き）。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB は研究モジュール（research/*）や AI モジュールが参照します。必要なテーブル（prices_daily, raw_financials, raw_news など）は事前にロードしておく必要があります。
- MonitoringDB は SQLite を使用し、init_monitoring_db() により初期テーブルとマイグレーションを行います。

ディレクトリ構成
----------------
（src/kabusys 以下の主要ファイル・ディレクトリの抜粋）

- kabusys/
  - __init__.py (パッケージ定義・バージョン)
  - config.py (設定管理: .env 読み込み・Settings クラス)
  - config_setup.py (.env ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (Monitoring ポーリング起動スクリプト)
  - tools/
    - __init__.py
    - paper_verification_report.py (ペーパートレード検証レポート)
  - utils/
    - __init__.py
    - logging_setup.py (統一ログ設定)
    - process_priority.py (プロセス優先度・CPU affinity)
  - monitoring/
    - monitoring_db.py (SQLite 永続化層)
    - monitoring_engine.py (各 Monitor を束ねる)
    - system_monitor.py (システム状態・データ鮮度監視)
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - kill_switch.py (kill.flag 管理)
    - trade_monitor.py (注文滞留・約定異常検出: 実装あり)
    - alert_manager.py (アラート送信: 実装あり)
  - portfolio/
    - portfolio_builder.py (候補選定・重み計算)
    - position_sizing.py (株数決定・資金配分/丸め)
    - risk_adjustment.py (セクターキャップ・レジーム乗数)
    - __init__.py
  - research/
    - factor_research.py (Momentum / Value / Volatility 等)
    - feature_exploration.py (将来リターン / IC / 統計)
    - __init__.py
  - ai/
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
    - __init__.py
  - execution/ (発注・注文管理・ブローカ抽象など)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/ (実行時に生成される想定)
    - monitoring.db (SQLite, デフォルト)
    - paper_trading.db (ペーパートレード用)

補足（安全上の注意）
-------------------
- .env は決してバージョン管理にコミットしないでください（README のウィザード・ヘッダにも注意書きあり）。
- KABUSYS_ENV=live の場合は設定を慎重に確認し、LINE 等のアラート設定を必ず整えてください。
- KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険です（kill.flag が誤って自動でクリアされると安全装置が無効化される可能性があります）。

トラブルシューティング
----------------------
- ログファイルが生成されない場合は logs/ ディレクトリの権限を確認してください。setup_logging は作成に失敗するとコンソール出力のみで継続します。
- DuckDB / SQLite のパス関連は validate_config で警告が出ます。必要なディレクトリが存在するか確認してください。
- OpenAI 呼び出しが失敗しても（API 鍵未設定等）モジュールはフォールバック（多くは無効化して継続）する実装になっていますが、AI 機能は結果が重要な場合 API キーを必ず設定してください。

最後に
------
この README はコードベースに基づく利用手順・概観をまとめたものです。詳細な設計方針・アルゴリズム（PortfolioConstruction.md や StrategyModel.md 参照の旨がコード中に記述されています）はリポジトリ内の該当ドキュメントを参照してください。ご不明点があれば実行時のログや validate_config の出力を確認してください。