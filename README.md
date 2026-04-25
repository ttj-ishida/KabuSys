README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。
主な目的は以下です。

- 日次のファクタ計算・リサーチ（DuckDB を用いた時系列処理）
- ポートフォリオ構築（候補選定・重み算出・株数決定）
- ExecutionEngine（発注エンジン）およびモニタリング周りのユーティリティ
- Paper Trading 検証レポートやニュース NLP / レジーム判定の補助ツール

本リポジトリはライブラリモジュール群と、対話式設定ウィザード・検証ツール・起動スクリプトを含みます。

主な機能
--------
- 環境設定ウィザード（.env の対話作成）: kabusys.config_setup
- 起動前設定検証 CLI（.env / config/*.yaml のチェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）: run_execution.py
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を用い、paper_trading 用 DB に記録
- Monitoring（System / Trade / Risk の監視）起動スクリプト: run_monitoring.py
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- 監視ログ永続化（SQLite）: monitoring.monitoring_db（テーブル初期化・読み書き）
- リスク監視 / Kill Switch（kill.flag によるエンジン停止）: monitoring.risk_monitor / monitoring.kill_switch
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・株数算出）:
  - portfolio.portfolio_builder
  - portfolio.position_sizing
  - portfolio.risk_adjustment
- リサーチ（ファクター計算 / 将来リターン / IC 等）: research.factor_research, research.feature_exploration
- ニュース NLP（OpenAI を利用したニュースセンチメント）およびレジーム判定（AI 統合）:
  - ai.news_nlp.score_news
  - ai.regime_detector.score_regime
- Paper Trading 検証レポート生成スクリプト: tools.paper_verification_report

セットアップ手順
----------------
1. リポジトリをクローンし、Python 仮想環境を作成・有効化する
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールする（最低限の推奨）
   - duckdb, psutil, openai, （任意で PyYAML）
   - 例:
     - pip install duckdb psutil openai
     - （YAML 検証を使う場合）pip install PyYAML

   注: requirements.txt は本コードスニペットに含まれていません。実環境ではプロジェクトの配布物に合わせて依存管理してください。

3. .env を作成する
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（ルートに配置）
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な任意変数（デフォルト値あり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト data/paper_trading.db）
     - LOG_LEVEL — デフォルト INFO
     - KILL_FLAG_CLEAR_ON_START — 0（本番では 0 推奨）

4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

使い方
------
主要なエントリポイント（モジュールとして実行）:

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- ExecutionEngine の起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV で制御:
    - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - live / development: settings.sqlite_path を使用
  - 停止制御:
    - data/stop_requested.flag を作成するとループが検知して停止（この flag の検出で起動を中断することもある）
    - Kill Switch（監視側が data/kill.flag を書くと ExecutionEngine 側で停止を検知する仕組み）

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60）
  - 監視は常に本番用 sqlite_path を参照（環境に関わらず）

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先して使用）
  - 出力: 標準出力にレポートを印字（稼働率、注文成功率、レイテンシ等）

- AI / リサーチ関数の利用（ライブラリ API の例）
  - ニュース NLP:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="XXXX")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="XXXX")
  - ファクター計算:
    - from kabusys.research import calc_momentum, calc_value, calc_volatility
    - calc_momentum(duckdb_conn, date(2026, 4, 1))

環境変数 / 設定の主な項目
-------------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用関連（よく使うもの）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング秒数（run_monitoring 用、デフォルト 60）
  - OPENAI_API_KEY: OpenAI API を使う機能で使用

ファイル・フラグの挙動
--------------------
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py が監視している停止フラグ。存在するとループが終了します（起動前に存在する場合は起動せず終了することがあります）。
- data/kill.flag
  - Kill Switch が書き込むファイル。ExecutionEngine に「全停止」を指示するために使用される（存在検知で停止処理へ）。
- data/execution.pid
  - run_execution が PID を書き込むファイル（デフォルト。Settings.pid_file_path で変更可）。

ログ
---
- ログはデフォルトで logs/ ディレクトリに日次ローテートで出力されます（TimedRotatingFileHandler、30日分保持）。
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")

ディレクトリ構成（主要ファイル）
------------------------------
以下は package の主要モジュール構成（src/kabusys 以下）です。実際のリポジトリにはさらにファイルやサブパッケージが含まれる可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings クラス
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI 統合）
    - regime_detector.py     — レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py      — SQLite テーブル初期化 + MonitoringDB ラッパ
    - system_monitor.py
    - trade_monitor.py      (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py      (参照あり)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - execution/
    - execution_engine.py   (参照あり)
    - order_manager.py      (参照あり)
    - order_repository.py   (参照あり)
    - reconciler.py         (参照あり)
    - broker_factory.py     (参照あり)
    - risk_manager.py       (参照あり)
  - data/                   — 実行時に作成されることが想定されるディレクトリ
    - monitoring.db (SQLITE_PATH のデフォルト)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト)
    - stop_requested.flag
    - kill.flag
    - execution.pid
  - logs/                   — ログ出力先（デフォルト）

注意事項 / 運用上のヒント
------------------------
- .env は機密情報を含むため、決して Git 等にコミットしないでください（config_setup にもその旨の注意が入っています）。
- 本番（KABUSYS_ENV=live）では特に KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。
- OpenAI を使用する機能は API コストとレイテンシに注意して運用してください。API キーは OPENAI_API_KEY で渡します。
- DuckDB/SQLite のパスはデフォルトで data/ 以下に置かれます。運用環境では永続ストレージのある場所に変更してください。
- run_execution / run_monitoring は stop_requested.flag（および kill.flag）を使ったファイルベースの停止機構を持ちます。自動化スクリプトや運用手順書に停止フローを明記してください。

ライセンス / コントリビューション
--------------------------------
（このスニペットにはライセンスファイルは含まれていません。実プロジェクトでは LICENSE を配置してください。）

お問い合わせ
------------
実運用や改修・拡張を行う際は、Settings クラス（config.py）を起点に環境変数の管理を確認してください。スクリプト実行前に python -m kabusys.validate_config で問題がないことを確認するのを推奨します。