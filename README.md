KabuSys
=======

日本株向け自動売買システムのライブラリ群（軽量な実装サンプル）。  
このリポジトリはトレード実行エンジン、監視サブシステム、ポートフォリオ構築、ファクター計算、AIによるニュースセンチメント評価、および運用用ユーティリティ群を含みます。

主な特徴
--------
- ExecutionEngine（発注エンジン）と Monitoring（監視）を分離して起動可能
- Paper Trading モード（本番 DB と分離された SQLite を使用、MockBroker）をサポート
- 監視用 DB（SQLite）へのログ永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- Kill Switch（条件により data/kill.flag を書き込み、発注エンジンを停止）と stop フラグによる安全停止
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクターキャップ）
- Research 用ファクター計算（Momentum/Value/Volatility 等） — DuckDB を利用
- AI モジュール（OpenAI を用いたニュースセンチメント評価・レジーム判定）
- 設定ウィザード（.env 生成）と起動前検証 CLI
- ロギング設定ユーティリティ（コンソール + 日次ローテートファイル）

セットアップ手順
----------------

前提
- Python 3.10 以上（型ヒントに | 型を使用しているため）
- システムに SQLite（標準ライブラリ）利用可能

推奨手順（ローカル開発）
1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必要最低限:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証時に YAML をパースする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を使用してください）

3. 初期設定ファイル（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を基に）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合:
     - python -m kabusys.validate_config --strict

基本的な環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意／上書き可能:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading 時）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - LOG_DIR: ログ格納ディレクトリ（デフォルト logs/）
  - OPENAI_API_KEY: OpenAI を使う機能で必要
  - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔（秒）を一時的に上書き可能（デフォルト 60）

使い方
------

起動スクリプト
- ExecutionEngine 起動（本番 or paper_trading に応じて挙動が変わる）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB に記録します。

- Monitoring 起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可（例: export MONITOR_POLL_INTERVAL=30）

停止 / 制御
- グレースフル停止（run_execution / run_monitoring が検知）
  - data/stop_requested.flag を作成するとループを抜けて停止します（スクリプトはこのファイルの存在を監視します）。
- Kill Switch（自動停止）
  - KillSwitch が条件を満たすと data/kill.flag を作成します。ExecutionEngine は Settings.kill_flag_path（デフォルト data/kill.flag）を参照して動作します。
  - 注意: Settings.KILL_FLAG_CLEAR_ON_START により起動時に自動クリアするか設定できます（本番ではクリアしないことを推奨）。

ログ
- setup_logging を使い、コンソール（stdout）と日次ローテートのファイルログ（logs/<app_name>.log）を生成します。
- LOG_DIR/LOG_LEVEL 環境変数で調整可能。

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易的な稼働率、注文成功率、レイテンシ等のレポートを標準出力に出します。

ライブラリ API（概要）
- kabusys.config: Settings クラス — 環境変数 / .env を読み込むユーティリティ
- kabusys.config_setup: .env 対話ウィザード
- kabusys.validate_config: 起動前チェック CLI
- kabusys.utils.logging_setup.setup_logging: 統一ログ設定
- kabusys.utils.process_priority: プロセス優先度 / CPU affinity 設定
- kabusys.monitoring.*: MonitoringDB、SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine、KillSwitch、AlertManager（監視に関する実装）
- kabusys.execution.*: ExecutionEngine、OrderManager、RiskManager 等（発注ロジック）
- kabusys.portfolio.*: 候補選定、重み計算、ポジションサイズ計算、セクター制約
- kabusys.research.*: ファクター計算、特徴量解析（DuckDB 利用）
- kabusys.ai.*: news_nlp（ニュースセンチメント）、regime_detector（市場レジーム判定） — OpenAI を使用

ディレクトリ構成
----------------

（プロジェクトルートの src/kabusys 想定）
- src/kabusys/
  - __init__.py                 — パッケージ定義（__version__ 等）
  - config.py                   — Settings（環境変数 / .env 読み込み）
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py          — ロギング初期化ユーティリティ
    - process_priority.py       — 優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py          — SQLite 永続化層（テーブル作成、読み書きユーティリティ）
    - system_monitor.py         — システム・データ鮮度監視
    - trade_monitor.py          — 発注ログ監視（滞留注文等）
    - risk_monitor.py           — ドローダウン / ポジション上限監視
    - kill_switch.py            — Kill Switch 実装（flag ファイル書き込み）
    - monitoring_engine.py      — Monitors をまとめる実行ループ
    - alert_manager.py          — アラート送信（LINE 等）※コード参照（存在する場合）
  - execution/
    - execution_engine.py       — 発注セッションの実行本体
    - order_manager.py          — 発注ロジック管理
    - order_repository.py       — 注文履歴永続化（SQLite など）
    - broker_factory.py         — BrokerClient の生成（実ブローカ / モック切替）
    - reconciler.py             — ブローカーとの再整合処理
    - risk_manager.py           — 発注前リスクチェック
  - portfolio/
    - portfolio_builder.py      — 候補選定・スコアソート
    - position_sizing.py        — 発注株数計算
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py        — Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py    — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py               — ニュースの LLM スコアリング（OpenAI）
    - regime_detector.py        — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

運用上の注意
-------------
- 本番稼働時（KABUSYS_ENV=live）は設定値・API キー・Kill Switch の取り扱いに十分注意してください。
- .env は秘密情報を含むため決してリポジトリにコミットしないでください。
- OpenAI 等外部 API を使用する機能はレート制限・課金のリスクがあるため、必ず API キーと使用ポリシーを確認してください。
- run_execution/run_monitoring は簡易な stop フラグ・kill.flag による制御を行います。運用環境のプロセスマネージャ（systemd / supervisor / container orchestrator）と併用してください。

開発・テスト
-------------
- .env の自動読み込みは Settings の自動ロード機能で行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- AI 呼び出し部分は内部で _call_openai_api を使用しており、ユニットテストではモック（patch）で差し替え可能です。

その他
-----
- この README はコードベースから読み取れる主な機能と起動方法をまとめたものです。各モジュールの詳細な使用方法・パラメータは該当ソースの docstring / コメントを参照してください。

もし README に追加したいテンプレート（例: requirements.txt の内容、実運用での systemd サンプル、より詳細な .env.example）などがあれば教えてください。必要に応じて追記します。