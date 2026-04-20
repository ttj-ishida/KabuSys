KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株向けの自動売買・研究・監視ツール群の軽量実装です。  
モジュール化されており、ExecutionEngine（発注実行）／Monitoring（監視）／Research（因子計算）／Portfolio（銘柄選定・玉数決定）／AI（ニュース NLP）などを含みます。

主な特徴
--------
- ExecutionEngine（発注実行）と Monitoring（監視）を分離して運用可能
- Paper Trading 用に本番 DB と完全分離されたモードをサポート（MockBroker）
- 監視：CPU/メモリ/ディスク、Execution プロセス稼働、注文滞留、ドローダウン等の監視と kill-switch の発動
- 研究用：DuckDB を用いたファクター計算（モメンタム、バリュー、ボラティリティ等）
- ポートフォリオ構築：候補選定、等金額／スコア加重、リスクベース配分、セクターキャップ、単元丸め
- AI 統合（OpenAI）：ニュースのセンチメント算出、マクロセンチメントを用いた市場レジーム判定
- ログ出力はコンソール＋日次ローテーションで統一（kabusys.utils.logging_setup）

提供コマンド / エントリポイント
-------------------------------
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証 CLI
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し、data/paper_trading.db に記録
- Monitoring 起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒単位のポーリング間隔を上書き（デフォルト 60）
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

必須／主要環境変数
------------------
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- OPENAI_API_KEY （news_nlp / regime_detector を使う場合）
- KABUSYS_ENV: execution モード（development / paper_trading / live。デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL, LOG_DIR: ログ設定
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- PAPER_FILL_MODE: Paper Trading の約定動作（instant | partial | never | reject。デフォルト: instant）

.env の自動読み込み
------------------
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に .env を自動読み込みします。
- 読み込み順: OS 環境 > .env.local > .env
- 自動読み込みを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ログ設定
--------
- kabusys.utils.logging_setup.setup_logging(app_name=...) を呼ぶことで、stdout と日次ローテーション（logs/<app_name>.log）を設定します。
- デフォルトログディレクトリ: logs/
- ログレベルは LOG_LEVEL 環境変数または引数で指定可能

監視 / 停止フロー（Kill Switch）
------------------------------
- 監視は SQLite の監視テーブル（system_status / trade_logs / risk_logs / dashboard 等）へ記録します。
- KillSwitch は条件（ドローダウン超過・ポジション上限超過等）で data/kill.flag を生成し、ExecutionEngine に停止シグナルを送ります。
- 手動停止（外部から Execution を止めたい場合）は data/kill.flag を作成する、または monitoring 側に stop フラグ（data/stop_requested.flag）を置くことにより各プロセスが検知して終了します。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 にしていると自動で kill.flag を消去します（本番では 0 を推奨）。

Paper Trading の分離
--------------------
- KABUSYS_ENV=paper_trading の場合、Broker は MockBrokerClient を返し、DB は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。実際の発注は行われません。

AI（OpenAI）統合
----------------
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news / news_symbols からニュースを集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを計算し ai_scores テーブルへ書き込みます。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 比とマクロニュースセンチメントを合成して market_regime を算出・書き込みします。
- API 呼び出しには OPENAI_API_KEY が必要。失敗時はフォールバック（例: macro_sentiment=0）する設計になっています。

セットアップ手順（開発向け / 最小）
-------------------------------
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトをパッケージ化している場合は pip install -e .）

   依存関係は用途によって増えます（Monitoring: psutil、DuckDB を使った Research、OpenAI を使う場合は openai 等）。

3. .env を作成
   - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example がある場合は参照）

4. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正。--strict で警告も失敗扱いにできます。

5. DB 初期化は各スクリプト（run_execution / run_monitoring）が起動時に行います（monitoring テーブルの作成等は init_monitoring_db が担います）。

使い方（起動例）
----------------
- Execution（本番または Paper）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution  （デフォルトは .env の KABUSYS_ENV に従う）

- Monitoring（監視ループ）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を明示: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

ライブラリ的利用例
------------------
- 研究用ファクター計算（Python から）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - conn = duckdb.connect("data/kabusys.duckdb")
  - rows = calc_momentum(conn, date(2026, 4, 1))

- ニュース NLP をバッチで回す（Python スクリプト内）
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_news(conn, date(2026,4,1), api_key="sk-...")

注意点 / 補足
-------------
- .env は絶対に Git にコミットしないでください（config_setup でも警告）。
- Monitoring は MONITOR_POLL_INTERVAL 環境変数で間隔を調整できます。0 以下の値は無効でデフォルト（60 秒）にフォールバックします。
- run_monitoring は監視用 SQLite（settings.sqlite_path）を利用します。Monitoring DB と Paper Trading DB は用途による分離がされています（paper_trading の場合は別の sqlite を使用）。
- ローカル開発時は KABUSYS_ENV=development を使い、実際の発注は行わない設計になっています。

ディレクトリ構成（重要ファイル・モジュール）
-----------------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込み・検証機能
  - config_setup.py          — .env 作成ウィザード（CLI）
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 統合）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化層（テーブル作成・CRUD）
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - trade_monitor.py       — （注文）監視ロジック
    - kill_switch.py         — kill.flag の作成/評価
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — 外部通知（LINE 等）を扱う（実装参照）
  - execution/
    - execution_engine.py    — 発注ロジック本体（Engine）
    - order_manager.py
    - order_repository.py
    - broker_factory.py      — Broker クライアント生成（Mock/Real 切替）
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定、重み算出
    - position_sizing.py     — 株数算出、スケーリング、単元丸め
    - risk_adjustment.py     — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py     — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — IC / forward returns / 統計サマリー
  - data/                    — （実行時に作成される）DB / PID / flag 等を配置
  - utils/
    - logging_setup.py       — ログ共通設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

最後に
------
この README はコードベースから抽出した主要事項をまとめたものです。実運用前に python -m kabusys.validate_config で設定を確認し、必要な依存パッケージ（DuckDB / psutil / OpenAI SDK 等）をインストールしてください。README に書かれていない実装詳細は該当モジュールの docstring を参照してください。必要であれば README を追加で調整します。