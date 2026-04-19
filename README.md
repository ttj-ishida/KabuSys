README
======

概要
----
KabuSys は日本株の自動売買・リサーチ基盤のサンプル実装です。本リポジトリは以下の機能群を持ち、モジュール化された監視・実行・リサーチ・AIスコアリングのコンポーネントを提供します。

- ExecutionEngine（発注エンジン：本番 / ペーパートレード切替）
- Monitoring（システム稼働・注文・リスク監視、Kill Switch）
- Portfolio 構築ユーティリティ（銘柄選定・配分・ポジションサイズ計算）
- Research（ファクター計算 / 特徴量解析）
- AI モジュール（ニュース NLP によるセンチメント / レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証、レポート生成）

主要な設計方針：
- データ永続化は DuckDB（分析）と SQLite（監視・ペーパー用）で分離
- 環境変数/.env による設定管理（config_setup.py でウィザード作成）
- 本番動作時の安全機構（Kill Switch、リスクモニタ、ログ、ポーリング監視）
- LLM（OpenAI）を用いる処理は API キーが必要で、失敗時はフェイルセーフで継続

機能一覧
--------
- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV により paper_trading モードでは MockBrokerClient を使用し paper_trading DB に書き込む。
  - プロセス優先度を高く設定、PID ファイルを生成、停止フラグ監視。
- run_monitoring.py
  - SystemMonitor を定期ポーリングして system_status / trade_logs 等を記録。MONITOR_POLL_INTERVAL で間隔を変更可能。
  - 監視は環境に関係なく本番の sqlite_path を使用（監視記録は共通）。
- monitoring パッケージ
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager / MonitoringEngine（監視ループ）
  - monitoring_db: SQLite スキーマの初期化と読み書きラッパー
- portfolio パッケージ
  - 銘柄選定、重み計算、セクター制約、ポジションサイズ算出など純粋関数群
- research パッケージ
  - ファクター計算（momentum, volatility, value）、特徴量解析（forward returns, IC, summary）
- ai パッケージ
  - news_nlp: OpenAI によるニュースセンチメントを ai_scores テーブルへ書き込み
  - regime_detector: ma200 とマクロニュースセンチメントを合成して market_regime を判定
- tools/paper_verification_report.py
  - ペーパートレード DB を解析して稼働率・注文成功率・レイテンシ等の検証レポートを出力
- config_setup.py / validate_config.py
  - .env を対話式に作成するウィザード、起動前の設定検証 CLI

要件
----
- Python 3.10+
- 必要な外部ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - pyyaml（config の YAML 検証を行う場合）
- 標準ライブラリ: sqlite3, logging, threading, datetime など

セットアップ手順
----------------
1. リポジトリをクローン / 取得
2. 仮想環境を作成・有効化（例）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール:
   - pip install duckdb psutil openai pyyaml
   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
4. .env の作成（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
     - ウィザードは .env を生成します（デフォルト: プロジェクトルート/.env）
5. 設定検証:
   - python -m kabusys.validate_config
   - 問題がある場合は .env を編集して再検証
6. データディレクトリ:
   - デフォルトで data/ や logs/ を使用します。必要に応じて環境変数でパスを変更してください。

主な環境変数（例）
------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- よく使う設定:
  - KABUSYS_ENV : development | paper_trading | live (default: development)
  - DUCKDB_PATH : data/kabusys.duckdb
  - SQLITE_PATH : data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH : data/paper_trading.db (paper_trading 用)
  - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR
  - OPENAI_API_KEY : OpenAI 呼び出しに必要
  - MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒） ※ run_monitoring 用（例: 30）
  - KILL_FLAG_CLEAR_ON_START : 本番での自動 kill.flag クリア（0 推奨）

簡単な .env サンプル（ウィザードで作成されます）
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO

使い方
------
全般
- パッケージとして実行可能なモジュールは "python -m kabusys.<module>" で起動できます（プロジェクトを PYTHONPATH に含めているか、パッケージインストール済みであることが前提です）。直接ファイルを実行しても動作します。

起動例（Monitoring）
- デフォルトポーリング（60秒）で監視を開始:
  - python -m kabusys.run_monitoring
- ポーリング間隔を変更:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが検知して終了します。

起動例（Execution）
- ExecutionEngine を起動:
  - python -m kabusys.run_execution
- paper_trading モードで起動するには .env で KABUSYS_ENV=paper_trading を設定
  - paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込みます。
- 停止:
  - monitoring / 実行スクリプトは data/stop_requested.flag を監視しています。ファイル作成で安全に停止できます。
  - KillSwitch が条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）を書き込み、ExecutionEngine に停止シグナルを送ります。

設定関連
- .env 作成（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

ツール
- Paper Trading レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db

AI / LLM 関連
- news_nlp.score_news と regime_detector.score_regime は OpenAI API を使用します。事前に OPENAI_API_KEY を環境変数で設定してください。
- 直接的な CLI は用意していませんが、Python から呼び出して使用できます。例:
  - >>> import duckdb, datetime
  - >>> from kabusys.ai.news_nlp import score_news
  - >>> conn = duckdb.connect("data/kabusys.duckdb")
  - >>> score_news(conn, datetime.date(2026,4,1))  # OPENAI_API_KEY 必須

ログ / DB / フラグ
- ログ: デフォルト logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日保持）
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。
- DB:
  - DuckDB: デフォルト data/kabusys.duckdb（分析用）
  - SQLite (監視): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
- 停止フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring のループ停止
  - data/kill.flag — KillSwitch が発動した場合に作成され、ExecutionEngine 停止のトリガー

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/.env の読み込みと Settings
- config_setup.py          — .env 作成ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

パッケージ（主なファイル）
- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（ma200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py       — SQLite スキーマ初期化と DB ラッパー
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
- execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

（注意）提示したファイル一覧は主要なものの抜粋です。詳細はリポジトリ内の src/kabusys 配下を参照してください。

運用上の注意点
--------------
- 本番環境 (KABUSYS_ENV=live) は危険を伴います。validate_config で各種ガード（LINE 通知設定、KillFlag 設定など）を確認してください。
- MONITOR の記録は常に Settings.sqlite_path（監視用 DB）へ行われます。監視用 DB は環境に依存せず共通で記録されます。
- paper_trading モードでは発注実行が実際のブローカーに送信されないよう MockBrokerClient を使い、専用の paper_trading DB に記録されるように設計されています（本番 DB と分離）。
- OpenAI API 呼び出しは失敗やレート制限を想定してリトライ／フェイルセーフ処理を入れていますが、API 使用時はコストとレートに注意してください。

開発者向けメモ
---------------
- ロギングは setup_logging を各スクリプト起動時に呼び出して統一してください。
- プロセス優先度や CPU affinity を設定するユーティリティが utils にあります。権限や OS によって設定がスキップされる場合があります。
- DuckDB を用いたリサーチ関数は副作用を持たない純粋関数で設計されています。テストしやすくしてあるため、単体テストの作成が容易です。

貢献・問い合わせ
-----------------
バグ報告や提案は Issue を作成してください。実装に関する設計上の質問はコード中の docstring とコメントを参照してください。

以上。README の内容はコードベースの抜粋に基づいて構成しています。追加で「使い方の例を具体的に載せたい」「requirements.txt を生成してほしい」などあれば教えてください。