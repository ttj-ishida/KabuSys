README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームの骨組みを提供する Python パッケージです。本プロジェクトは以下の役割を持ちます。

- 発注実行エンジン（ExecutionEngine）
- システム・取引・リスク監視（Monitoring）
- ポートフォリオ構築（銘柄選定・重み付け・株数決定）
- ファクター計算・研究ユーティリティ（DuckDB を使った時系列解析）
- ニュースの LLM によるセンチメントスコアリング & 市場レジーム判定（OpenAI API 経由）
- .env の対話式作成ウィザード・設定検証ツール・運用向けユーティリティ（レポート等）

特徴
----
- 実稼働を想定したログ／DB 管理（DuckDB / SQLite）
- paper_trading モードではモックブローカーを使い本番 DB と分離
- モジュールはライブラリとしても呼び出せる（portfolio 関数群、research モジュールなど）
- OpenAI を使ったニュース集約とスコアリング（フェイルセーフなリトライ/バリデーション実装）
- 監視からの Kill Switch（条件を満たすと data/kill.flag を生成して ExecutionEngine に停止要求）

セットアップ
-----------
前提
- Python 3.10 以上（typing の新構文を使用）
- 推奨パッケージ（必要に応じてインストール）:
  - duckdb
  - psutil
  - openai
  - pyyaml（config 検証で YAML のパースを行う場合に必要）

例: 仮想環境作成・依存インストール
- Unix 系（例）
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai pyyaml

ディレクトリ作成（手動）
  mkdir -p data logs

環境変数設定
- 対話式ウィザードで .env を作ることを推奨:
  python -m kabusys.config_setup
  （.env は絶対に Git 等にコミットしないでください）

主要な環境変数（抜粋・デフォルト）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合に必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading の場合は MockBroker を使い data/paper_trading.db に記録
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db (Monitoring 用)
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

設定検証
- .env や config/*.yaml の不備をチェック:
  python -m kabusys.validate_config [--strict]

使い方
------

起動スクリプト
- ExecutionEngine を起動
  python -m kabusys.run_execution

  動作概要:
  - KABUSYS_ENV によって paper_trading モードなら MockBroker を使用し専用の SQLite に記録
  - プロセス優先度を "high" に設定し、内部で execution.pid を管理
  - 起動前に data/stop_requested.flag が既にある場合は起動を行わず終了
  - 実行中に data/stop_requested.flag を作成するとスレッドを停止する

- Monitoring を起動（監視ループ）
  python -m kabusys.run_monitoring

  重要設定:
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60）
  - 監視は Settings に従って本番 sqlite_path を使用（環境にかかわらず）
  - data/stop_requested.flag を置くとループを終了する
  - 各種モニタ（System/Trade/Risk）を実行し、条件に応じて data/kill.flag を書く（KillSwitch）

停止・Kill
- 停止用フラグ:
  - data/stop_requested.flag : 起動スクリプト（run_execution/run_monitoring 等）の外部停止用
  - data/kill.flag : モニタからの「実行停止要求」（Kill Switch）。ExecutionEngine はこれを検知して停止する
- kill.flag の自動クリアは設定 KILL_FLAG_CLEAR_ON_START による（本番では無効推奨）

運用ツール
- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

プログラムからの利用（一例）
- ポートフォリオ計算:
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
- 研究用ファクター計算（DuckDB 接続を渡す）:
    from kabusys.research import calc_momentum, calc_volatility, calc_value
- ニュース NLP（DuckDB 接続と target_date を渡す）:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="...")

ログ
- ログは console(stdout) とファイル (logs/<app_name>.log) に出力されるよう設定されます。
- ログファイルの日次ローテーション（30日保持）を行います。ログディレクトリは自動作成されますが権限等で失敗する可能性あり。

ディレクトリ構成（主要ファイル）
--------------------------------
以下はプロジェクト内の主要モジュール / パッケージ（src/kabusys 以下）です。実際のファイルはリポジトリに合わせてください。

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (実装参照)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装参照)
    - monitoring_engine.py
  - execution/
    - execution_engine.py (実装参照)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (ランタイムで作成されることが多い)
    - *.db, kill.flag, stop_requested.flag, execution.pid 等

補足・運用上の注意
-----------------
- 本番モード（KABUSYS_ENV=live）では設定ミスが重大なリスクを生むため、validate_config での検証を必ず行ってください。
- .env は機密情報（API トークン等）を含むため、絶対にバージョン管理にコミットしないでください。
- OpenAI API を使う機能は API キーが必要です。API のコール回数や遅延、エラーに備えた制御（リトライ・バックオフ）が実装されていますが、コスト管理は運用側で行ってください。
- Paper Trading を使うときは KABUSYS_ENV=paper_trading を設定すると、本番 DB と分離して data/paper_trading.db に記録されます。

問い合わせ / 追加情報
--------------------
- 各モジュールの詳細な使い方・パラメータはソースコードの docstring を参照してください。
- 新しい設定や機能を追加する場合は config_setup.py と validate_config.py の更新を忘れないでください。

以上。