README — KabuSys（日本株自動売買システム）
======================================

概要
----
KabuSys は日本株向けの自動売買システム用ライブラリ群および運用ユーティリティ群です。本リポジトリは以下の機能を持つモジュール群を含みます。

- 注文実行エンジン（ExecutionEngine 起動スクリプト）
- 監視用ポーリング（System / Trade / Risk）とアラート・Kill Switch
- ポートフォリオ構築（銘柄選定・重み付け・株数決定）
- 研究用ファクター計算・特徴量解析（DuckDB ベース）
- Paper Trading 検証レポート作成ツール
- ニュース NLP を使った銘柄スコアリング / レジーム判定（OpenAI 使用可）
- 環境設定ウィザード・設定検証 CLI

主な設計方針
- 本番 DB（monitoring 用 SQLite）と Paper Trading 用 DB は分離可能
- DuckDB を分析用データベースに使用
- OpenAI API を用いた NLP 処理は外部 API 依存であり、API キーが必要
- 自動起動時に .env を読み込む仕組み（プロジェクトルートの .git/pyproject.toml を基準）

機能一覧
--------
- config_setup: 対話式に .env を作成・更新
- validate_config: .env と config/*.yaml を検証（--strict オプションあり）
- run_execution: ExecutionEngine を起動（KABUSYS_ENV による paper_trading 切替）
- run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整可）
- monitoring:
  - SystemMonitor: CPU/メモリ/ディスク・プロセス死活・データ鮮度監視
  - TradeMonitor: 滞留注文（stale）や約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch: 条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager: LINE Messaging API による通知（オプション）
- portfolio: 銘柄選定、重み付け、ポジションサイズ計算、セクター上限適用、レジーム乗数
- research: DuckDB を用いたモメンタム／ボラティリティ／バリュー等のファクター計算と IC / 統計関数
- tools.paper_verification_report: Paper Trading の検証レポート生成
- ai.news_nlp / ai.regime_detector: OpenAI を使ったニュースセンチメント集計と市場レジーム判定

前提・依存
-----------
最低限必要な Python モジュール（例）:
- duckdb
- psutil
- openai  （AI 機能を使う場合）
- requests
- PyYAML（config/*.yaml のパース検証を行う場合に任意で必要）

インストール例:
- 仮想環境作成 → pip install duckdb psutil openai requests pyyaml

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

環境変数（主なもの）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD     : kabuステーションの API パスワード

運用上よく使う / 便利な設定:
- KABUSYS_ENV : 実行環境 (development | paper_trading | live). デフォルト: development
  - paper_trading の場合は MockBrokerClient を使用し、DB は data/paper_trading.db に出力される
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視 DB（SQLite）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE : paper_trading 時の約定モード（instant | partial | never | reject）
- OPENAI_API_KEY : OpenAI を使う場合に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : AlertManager（LINE 通知）の設定
- LOG_LEVEL : ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START : Execution 起動時に既存の kill.flag を自動クリアするか ("1" でクリア)

モジュール固有の動作に関する環境変数:
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト 60）。不正値は 60 秒にフォールバック。

重要ファイル・パス（デフォルト）
--------------------------------
- data/monitoring.db         : 監視用 SQLite（Settings.sqlite_path）
- data/paper_trading.db      : Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb        : DuckDB（Settings.duckdb_path）
- data/execution.pid         : ExecutionEngine の PID ファイル（Settings.pid_file_path）
- data/kill.flag             : Kill Switch フラグ（Settings.kill_flag_path）
- data/stop_requested.flag   : run_execution / run_monitoring が参照する停止フラグ（stop 用）

セットアップ手順
----------------
1. リポジトリをクローンし、ワークディレクトリへ移動
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests pyyaml
   （必要に応じてバージョンを固定してください）

4. 設定ファイル（.env）を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成
   - 注意: .env は絶対に Git にコミットしないでください

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

使い方（主要コマンド）
---------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env の初期作成 / 更新を対話式に行います

- 設定検証
  - python -m kabusys.validate_config [--strict]

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は Paper Trading 用 DB（data/paper_trading.db）を使用し、MockBroker を用います
  - 起動時に data/stop_requested.flag が存在すると起動しません
  - 実行中に data/stop_requested.flag を作成すると安全に停止を試みます

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用 sqlite_path を使用（環境に依らず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI (ニューススコア / レジーム判定)
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出す
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - CLI ラッパーは含まれていませんが、モジュールをインポートして利用できます

停止と Kill Switch
------------------
- Kill Switch: リスク条件（ドローダウンやポジション上限）を満たした場合、監視側が data/kill.flag を書き込みます。ExecutionEngine は起動時や実行中にこのフラグを検知して停止します。
- 手動で停止したい場合: data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検出して停止します。
- 実行を再開する前に kill.flag は必要に応じて手動で削除するか、Settings.kill_flag_clear_on_start=1 を設定すると起動時に自動クリアされます（本番では 0 を推奨）。

ディレクトリ構成（抜粋）
-----------------------
以下はソースツリー内の主要ファイル／パッケージ構成の抜粋です（src/kabusys を起点）:

- kabusys/
  - __init__.py
  - config.py                 # 環境変数読み込み / Settings
  - config_setup.py           # .env ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/                 # Execution 関連（エンジン / ブローカ等）
    - ... (OrderManager, BrokerFactory, ExecutionEngine, etc.)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/                      # (実行時に使用される) DB/フラグファイル置き場

補足・運用上の注意
-----------------
- Paper Trading と Live を明確に分離しています。KABUSYS_ENV を正しく設定してください（特に本番環境では注意）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を検出）を基準に行われます。テストや特殊用途で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process_priority（psutil）や CPU affinity の設定はプラットフォーム依存で失敗することがあります。失敗時はログに警告を出してスキップします。
- OpenAI / 外部 API を使用する機能はネットワーク障害や API 制限を考慮して再試行やフェイルセーフが組み込まれていますが、運用では API キー管理とコスト管理に注意してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存 DB に対して耐えるようにカラム追加等の簡易マイグレーションを含みます。

よくあるコマンドのまとめ
-----------------------
- .env を作る: python -m kabusys.config_setup
- 設定確認: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
（このテンプレートにライセンス情報・貢献ガイドを追記してください）

問い合わせ
----------
使用方法やバグ報告、改善提案はリポジトリの Issue にお願いします。

以上。README に含めたい追加情報（例: requirements.txt の内容、実運用時の systemd ユニット例、より詳しい .env の例など）があれば教えてください。