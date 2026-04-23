KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株自動売買のための基盤ライブラリ群です。  
データ収集・ファクター計算（Research）、ポートフォリオ構築（Portfolio）、発注・リスク制御（Execution）、およびシステム監視（Monitoring）をモジュール化して提供します。  
本リポジトリはライブラリ本体に加え、起動スクリプトや設定ウィザード、検証ツール、Paper Trading 用の検証レポート生成などのユーティリティを含みます。

主な機能
--------
- 環境設定ウィザード（.env の対話式生成）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の事前チェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / ペーパー分離）: run_execution.py
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring 起動スクリプト（SystemMonitor のポーリング）: run_monitoring.py
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可（デフォルト 60 秒）
  - 監視は本番の SQLite パス（SQLITE_PATH）を常に使用
- 監視永続化層（SQLite 用）: monitoring_db モジュール（テーブル作成／マイグレーション）
- RiskMonitor / SystemMonitor / TradeMonitor / KillSwitch / Alert 管理（監視・自動停止ロジック）
- Portfolio モジュール（候補選定、重み付け、ポジション算出、セクター上限適用）
- Research モジュール（ファクター計算、forward returns、IC 計算、統計サマリ）
- AI モジュール（ニュース NLP による銘柄センチメント／市場レジーム検出、OpenAI を利用）
- Paper Trading 検証レポート生成ツール: kabusys.tools.paper_verification_report

セットアップ手順（ローカル開発向け）
-------------------------------
1. Python 仮想環境を作成・有効化（Python 3.10+ 推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML をパースする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML
   （requirements.txt がある場合はそれを使用してください）

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）

4. 設定検証（起動前の確認）
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合:
     - python -m kabusys.validate_config --strict

5. DB とログディレクトリ
   - デフォルトでは以下のファイル/ディレクトリを使用します:
     - DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH で変更可)
     - SQLite (監視): data/monitoring.db (環境変数 SQLITE_PATH で変更可)
     - Paper Trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH で変更可)
     - ログ: logs/（LOG_DIR で変更可）
   - 起動時に必要なディレクトリは自動作成されますが、パーミッション等は確認してください。

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
  - paper_trading: 発注実行はモック、専用 DB を使用
- OPENAI_API_KEY: OpenAI を使う機能（ニュース NLP / レジーム判定）で必要
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: DB ファイルパス
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒） デフォルト 60
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に data/kill.flag を自動クリアするか（0/1）

使い方（実行例）
----------------
- 環境ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使います。
    - 実行中に data/stop_requested.flag が存在すると Engine の停止処理が実行されます。
    - Kill Switch（data/kill.flag）による停止は KillSwitch が設定された場合に ExecutionEngine を停止させます。

- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（例: MONITOR_POLL_INTERVAL=30）
  - run_monitoring は KABUSYS_ENV にかかわらず SQLITE_PATH（本番監視 DB）を使用します。
  - 実行中に data/stop_requested.flag が存在すると監視ループが終了します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH を上書き）

- Research / AI モジュールの利用（プログラムから）
  - duckdb 接続を渡してファクター計算等を呼び出す:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - calc_momentum(conn, target_date)
  - AI スコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")  # api_key が None の場合は OPENAI_API_KEY を参照
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key="...")

動作上の注意 / 実装のポイント
---------------------------
- run_execution:
  - KABUSYS_ENV=paper_trading の場合、発注は MockBrokerClient によってエミュレートされ、本番 DB と分離して data/paper_trading.db に記録されます。
  - 起動時/実行中に data/stop_requested.flag があると起動せず終了、または実行中に検知して停止します。
  - execution.pid（デフォルト data/execution.pid）をプロセス管理に使用します。

- run_monitoring:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を整数秒で指定可能。値が不正な場合はデフォルト 60 秒にフォールバックします。
  - 監視は常に Settings.sqlite_path（監視 DB）を使用します（KABUSYS_ENV に依らず）。

- Kill Switch:
  - KillSwitch（data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送ります。KillSwitch は主に監視側で条件に応じて作動します。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブル作成と必要カラムの追加（マイグレーション）を行います。

- ロギング:
  - 共通の setup_logging を用意。デフォルトは logs/<app_name>.log に日次ローテーションで出力（30日保持）。
  - ログディレクトリの作成が失敗した場合はコンソール出力のみで継続します。

依存関係（主要）
----------------
- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（設定ファイル検証を有効にする場合）

ディレクトリ構成（抜粋）
----------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env 読込
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 監視テーブルの初期化・永続化 API
    - system_monitor.py      — システム状態・データ鮮度チェック
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - trade_monitor.py       — （発注関連監視）※実装参照
    - kill_switch.py         — kill.flag の読書きロジック
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （通知管理）※実装参照
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig 等）
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
    - news_nlp.py             — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + ETF ma200）
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py
    - process_priority.py     — psutil を使った優先度・CPU affinity 設定

補足
----
- セキュリティ: .env は機密情報（API キー等）を含むため、絶対にリポジトリにコミットしないでください。
- 本番運用: KABUSYS_ENV=live の場合、LINE 通知設定や Kill Switch の扱いなどを慎重に確認してください（validate_config が注意喚起します）。
- テスト: AI モジュールの API 呼び出し部分はテスト時に差し替え可能な設計（_call_openai_api のパッチ等）になっています。

この README はコードベースの主要機能と運用手順を要約したものです。詳細な設計やアルゴリズム（PortfolioConstruction.md / StrategyModel.md 等）は別ドキュメントを参照してください。もし特定ファイルや機能について詳細なドキュメントが必要であれば、対象を指定してお知らせください。