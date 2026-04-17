README
======

本ドキュメントは、このリポジトリに含まれる KabuSys（日本株自動売買システム）の主要な使い方・セットアップ手順・構成を日本語でまとめたものです。

プロジェクト概要
--------------
KabuSys は日本株自動売買のためのモジュール群です。主な役割は以下のとおりです。

- 市場データ（DuckDB）を使ったファクター計算・リサーチ機能
- ポートフォリオ構築・ポジションサイズ計算（Portfolio construction）
- 注文発行・ExecutionEngine（本番 / ペーパートレードを分離）
- システム・注文・リスク監視（Monitoring）
- ニュースの NLP スコアリング（OpenAI を利用したセンチメント評価）
- 運用補助ツール（.env ウィザード、設定検証、Paper Trading レポート等）

特徴的な設計方針：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV=paper_trading）
- ルックアヘッドバイアスを防ぐ設計（日時取得の扱いに注意）
- フェイルセーフ（APIやDBエラー時に継続する挙動）
- シンプルなファイルベースの Kill Switch / Stop フラグによる制御

主な機能一覧
--------------
- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録
- Monitoring 起動（python -m kabusys.run_monitoring）
  - ポーリングで system / trade / risk をチェックしアラートや Kill Switch を評価
  - ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- ニュース NLP（kabusys.ai.score_news）：OpenAI を使った銘柄別センチメント付与
- 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- ポートフォリオ構築・位置サイズ計算（kabusys.portfolio）

必要条件（依存関係）
------------------
主な Python パッケージ（プロジェクトに requirements.txt が無い場合は個別インストール）:
- duckdb
- psutil
- openai
- requests
- PyYAML（config 検証で使用、必須ではない）

例:
pip install duckdb psutil openai requests PyYAML

（標準ライブラリとして sqlite3, pathlib, logging 等を使用）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests PyYAML

4. .env ファイル作成
   - 対話式で作成:
     - python -m kabusys.config_setup
   - もしくは手動でリポジトリルートに .env を作成

5. 設定の検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

6. data ディレクトリ等が必要に応じて自動作成されますが、権限に注意してください。

環境変数（主要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（デフォルトあり）:
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading: ブローカーは Mock、DB は data/paper_trading.db を使用
  - live: 本番モード（本番用 API を使う）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能（ニュース NLP、レジーム判定）で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）用（任意）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant/partial/never/reject、デフォルト instant）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml で検出）から .env と .env.local を自動読み込みします。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（主なコマンド）
--------------------
- 環境ウィザード（.env 作成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - Strict モード（警告を失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine（戦略実行）起動:
  - 標準起動:
    - python -m kabusys.run_execution
  - ペーパートレードで起動する例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止方法:
    - run_execution は起動時 / 実行中に data/stop_requested.flag を監視します。
      ファイルが存在するとエンジン停止・起動抑止が行われます。
    - KillSwitch は条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止指示を送ります。
    - Settings.kill_flag_clear_on_start が 1 の場合は起動時に kill.flag を自動クリアします（本番では 0 推奨）。

- Monitoring（監視ループ）起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite

- AI 機能（プログラムから呼び出す）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続
    - target_date: date オブジェクト
    - api_key: None の場合は OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI キーが必要で、API のリトライやエラー処理を内包しています。

運用上のファイル・フラグ
-----------------------
- data/stop_requested.flag
  - run_monitoring / run_execution が存在を検知してループ停止または起動抑止を行うためのフラグファイル
- data/kill.flag
  - KillSwitch が書き込むフラグ。ExecutionEngine に致命的な停止を指示するために使用
- data/execution.pid（デフォルト）
  - ExecutionEngine の PID ファイル。SystemMonitor はこの PID を参照してプロセス生存を確認
- DB デフォルト:
  - DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db

ディレクトリ構成（主なファイル）
------------------------------
以下は主要なモジュールとその役割（ソースは src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み/Settings クラス
  - config_setup.py
    - .env 対話ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py      : SQLite 監視 DB ラッパー
    - monitoring_engine.py  : 各 Monitor の統合実行ループ
    - system_monitor.py     : CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py      : 注文滞留・約定異常監視
    - risk_monitor.py       : ドローダウン・ポジション上限監視
    - kill_switch.py        : Kill Switch のフラグ書き込みロジック
    - alert_manager.py      : LINE への Push 通知
  - execution/
    - （Engine / OrderRepository 等：実行フロー全般）※今回の抜粋で全ファイルは省略
  - portfolio/
    - portfolio_builder.py  : 候補選定・重み計算
    - position_sizing.py    : 発注株数計算（単元丸め・リスク制御）
    - risk_adjustment.py    : セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    : Momentum/Volatility/Value 等の計算（DuckDB を使用）
    - feature_exploration.py: 将来リターン計算・IC・統計サマリ
  - ai/
    - news_nlp.py           : ニュースのセンチメント評価（OpenAI）
    - regime_detector.py    : 市場レジーム判定（MA + マクロセンチメント合成）
  - tools/
    - paper_verification_report.py : Paper Trading の検証レポート生成ツール
  - utils/
    - process_priority.py   : プロセス優先度・CPU affinity 設定ユーティリティ

開発・運用上の注意
------------------
- KABUSYS_ENV の値に応じて実行挙動が変わります。特に live モードは本番発注を行う可能性があるため取り扱いに注意してください。
- .env は決して Git にコミットしないでください（config_setup はその旨を警告しています）。
- OpenAI 呼び出しは料金・レート制限の対象です。API キーの取り扱いに注意してください。
- run_monitoring ではデフォルトで本番の sqlite_path（settings.sqlite_path）を参照します。必要に応じて設定を確認してください。
- process priority 設定は psutil の権限に依存します。権限不足で失敗した場合はログに警告されますが処理は継続します。

サンプル .env（参考）
--------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-xxxx...
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
PAPER_FILL_MODE=instant
KILL_FLAG_CLEAR_ON_START=0

サポート / 追加情報
-------------------
- config/*.yaml（system_config.yaml 等）が存在する想定の場所があります。validate_config で存在確認・フォーマット検証を行います（PyYAML が必要）。
- テストや CI 用に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env 読み込みを無効化できます。

以上が本プロジェクトの README 相当の概要です。必要であれば各モジュール（例: ExecutionEngine の使い方、OrderRepository の API など）について別途詳細ドキュメントを作成します。