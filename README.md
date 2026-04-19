# KabuSys

日本株自動売買システムの参照実装（ライブラリ / 実行スクリプト群）

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買システムを構成するモジュール群をまとめたプロジェクトです。  
主な目的は以下です。

- 発注エンジン（ExecutionEngine）による注文管理（本番 / ペーパートレード両対応）
- システム監視（SystemMonitor / MonitoringEngine）とアラート／Kill Switch
- ポートフォリオ構築・ポジションサイズ算出（純粋関数群）
- リサーチ用ファクター計算（DuckDB ベース）
- ニュースの NLP（OpenAI）による銘柄スコアリング・レジーム判定
- 設定ウィザード・検証ツール・レポート生成ツール

機能一覧
--------
- 実行（run_execution）
  - 環境によるブローカークライアント切替（paper_trading では MockBrokerClient を利用）
  - 発注管理、リスク管理、照合（reconciler）などの組み合わせによるセッション実行
  - ペーパートレード時は data/paper_trading.db にログ（本番 DB と分離）
- 監視（run_monitoring, MonitoringEngine）
  - CPU/メモリ/ディスク・プロセス検知、データ鮮度チェック
  - トレード／リスク監視（滞留注文、異常約定、ドローダウンなど）
  - Kill Switch（条件に応じて data/kill.flag を出力して ExecutionEngine を停止）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額/スコア加重の重み計算、セクターキャップ適用、ポジションサイズ算定（単元丸め）
- リサーチ（kabusys.research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算（DuckDB を利用）
  - 将来リターン、IC（Information Coefficient）や統計サマリの計算
- AI（kabusys.ai）
  - news_nlp: raw_news を OpenAI（gpt-4o-mini 等）でセンチメント評価し ai_scores テーブルへ書込み
  - regime_detector: ETF の MA とマクロニュースを組み合わせて市場レジームを判定
- ユーティリティ
  - ロギングセットアップ（ログローテーション、コンソール出力統一）
  - プロセス優先度 / CPU affinity 設定
  - .env 対話式ウィザード（config_setup）と設定検証 CLI（validate_config）
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

前提・依存関係
--------------
主に以下のパッケージが必要です（環境によって追加が必要な場合があります）。

- Python 3.9+
- duckdb
- psutil
- openai  (AI機能を使う場合)
- PyYAML (config 検証で YAML をパースする場合)
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

セットアップ手順
--------------
1. リポジトリをクローンし、Python 仮想環境を作成・有効化する:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールする（requirements.txt が無い場合は手動で）:
   - pip install duckdb psutil openai pyyaml

3. 初期設定（.env）を作成する:
   - python -m kabusys.config_setup
     - 対話式ウィザードで .env を生成します（.env は必ず Git に入れないでください）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live
     - OPENAI_API_KEY: OpenAI を使う機能で必要
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（監視用 DB、デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時）
     - LOG_LEVEL: DEBUG/INFO/…
     - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動消去するか（開発用）

4. 設定検証（任意）:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

基本的な使い方
--------------
- 実行エンジンを起動する（本番/ペーパートレードは KABUSYS_ENV に依存）:
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用します
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします
    - 実行中に data/stop_requested.flag が書かれるとエンジンが順次停止します
    - 実行中は data/execution.pid（デフォルト）に PID を書きます

- 監視プロセスを起動する:
  - python -m kabusys.run_monitoring
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60）
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用します
    - 停止検知は repository 内の data/stop_requested.flag を参照

- Kill Switch / 停止フラグ
  - KillSwitch は条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止を促します
  - 実行時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリア（本番では 0 を推奨）

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定しておく必要があります
  - news_nlp.score_news や regime_detector.score_regime を呼び出して DuckDB 上のテーブルを更新します

- ペーパートレード検証レポート生成:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH

主な環境変数（まとめ）
--------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- データパス:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- ログ:
  - LOG_LEVEL (default: INFO)
  - LOG_DIR (default: logs/)
- AI:
  - OPENAI_API_KEY (AI 機能で必須)
- 監視:
  - MONITOR_POLL_INTERVAL (秒、default: 60)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)
- PAPER_FILL_MODE (paper_trading の MockBrokerClient の挙動):
  - instant | partial | never | reject（default: instant）

データ・ログファイル
-------------------
- デフォルトデータディレクトリ: data/
  - data/monitoring.db — 監視用 SQLite（monitoring は本番 sqlite_path を使用）
  - data/paper_trading.db — ペーパートレード用 SQLite（paper_trading 時）
  - data/kabusys.duckdb — DuckDB（分析・リサーチ用）
  - data/execution.pid — ExecutionEngine の PID（デフォルト）
  - data/kill.flag — Kill Switch 発動フラグ
  - data/stop_requested.flag — 手動停止要求（run_* スクリプトで利用）
- ログディレクトリ: logs/
  - <app_name>.log（TimedRotatingFileHandler で日次ローテーション、30日保持）

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / .env 自動ロード・Settings
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor 起動スクリプト
- utils/
  - logging_setup.py        — ロギング初期化ユーティリティ
  - process_priority.py     — 優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py        — SQLite 永続層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度の監視
  - trade_monitor.py        — （トレード関連の監視ロジック）※実装参照
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag 管理
  - monitoring_engine.py    — 各 monitor をまとめたポーリングエンジン
  - alert_manager.py        — アラート送信（LINE など）※実装参照
- execution/
  - execution_engine.py     — ExecutionEngine（注文処理の中心）※実装参照
  - broker_factory.py       — ブローカークライアント生成
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
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

（上記はコードベースの主要モジュールの一覧です。実際のファイルは src/kabusys 下を参照してください。）

よくある運用注意
----------------
- .env は必ずローカル専用にし、機密情報を Git 管理下に置かないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 とし、kill.flag の自動消去を無効にしてください。
- Monitoring は環境に関係なく本番 sqlite_path（SQLITE_PATH）を参照する設計になっています。運用時は DB の取り扱いに注意してください。
- OpenAI を利用する機能は API レート制限やエラーを考慮しており、失敗時はフェイルセーフでスコアを省略または中立に扱いますが、APIキー管理は厳重に行ってください。
- プロセス優先度の設定は psutil が必要で、環境によって権限不足で失敗することがあります（警告ログが出ますがプロセスは継続します）。

簡単な .env の例
----------------
（config_setup を使うことを推奨します。例として最低限必要な項目を示します。）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

ライセンス / バージョン
-----------------------
- パッケージの __version__ は src/kabusys/__init__.py に定義されています（現行: 0.1.0）。
- ライセンス情報はリポジトリのルートにある LICENSE ファイル（なければ運用ルールに従ってください）。

サポート / 開発者向けヒント
-------------------------
- 開発中は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動ロードを無効化できます（テスト時に有用）。
- DuckDB を使ったリサーチ機能はローカルの prices_daily / raw_financials / raw_news 等のテーブルを前提にしています。データ投入スクリプトは別途必要です。
- テスト時は OpenAI 呼び出し部分（_call_openai_api 等）をモック（unittest.mock.patch）してください。

この README はプロジェクトの概要と主要な使い方をまとめたものです。詳細は各モジュールの docstring（ソース内コメント）を参照してください。