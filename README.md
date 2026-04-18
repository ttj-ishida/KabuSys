KabuSys
=======

日本株向けの自動売買 / 研究プラットフォームの一部実装です。  
リポジトリは以下の主要機能を含み、実運用・ペーパートレード・研究用途のコンポーネントを分離して提供します。

- 実行エンジン（ExecutionEngine）
- 監視（Monitoring）
- ポートフォリオ構築／ポジションサイズ計算
- ファクター計算・リサーチユーティリティ（DuckDB ベース）
- AI ベースのニュースセンチメント / レジーム判定（OpenAI）
- ペーパートレード検証レポート生成ツール

以下はこのコードベースの概要、セットアップ手順、使い方、ディレクトリ構成の説明です。

プロジェクト概要
----------------
KabuSys は日本株の自動売買に必要な以下の機能群をモジュール化しています：

- Execution（発注・注文管理・リスク管理・再整合化）
  - 本番では kabuステーション API を利用。ペーパートレード時は MockBrokerClient を使用し、実際の発注は行わず data/paper_trading.db に記録します。
- Monitoring（システム／トレード／リスク監視）
  - system_status / trade_logs / risk_logs / positions / dashboard などを SQLite に永続化し、Kill Switch（data/kill.flag）で ExecutionEngine を安全に停止できます。
- Portfolio（銘柄選定、重み付け、ポジションサイズ決定、セクター制限）
  - 純粋関数群として設計され、DB 参照なしでメモリ内計算を行います。
- Research（ファクター計算、将来リターン、IC 計算、統計）
  - DuckDB 経由で prices_daily / raw_financials 等の表を参照して計算します。
- AI（news_nlp, regime_detector）
  - OpenAI API（gpt-4o-mini を想定）を用いてニュースのセンチメントや市場レジームを判定します（API キー必須）。
- ユーティリティ
  - .env 生成ウィザード、設定検証ツール、ログ設定、プロセス優先度設定 等。

主な機能一覧
-------------
- .env 対話式作成: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config [--strict]
- 実行エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用。
- 監視ポーリング起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。
- ペーパートレード検証レポート生成: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- DuckDB を使ったファクター計算・研究ユーティリティ（calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic など）
- ニュース NLP スコアリング（kabusys.ai.news_nlp.score_news）
- 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 監視 DB 初期化（init_monitoring_db） — system_status, trade_logs, positions, risk_logs, dashboard テーブルを作成・マイグレーション対応

セットアップ手順
----------------
1. Python 環境（推奨: Python 3.9+）を用意します。

2. 依存パッケージをインストールします（例）:
   - duckdb
   - psutil
   - openai（AI 機能を使う場合）
   - PyYAML（設定ファイル検証を行いたい場合）
   具体的には requirements.txt がある場合はそれを使用してください。リポジトリに無い場合は pip で個別に入れてください。

   例:
   pip install duckdb psutil openai pyyaml

3. .env を用意します（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
   - 対話が難しい場合は .env.example を参考にして .env を作成してください。

   重要な環境変数（必須）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   主要な任意 / 設定可能項目:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（監視用、デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト data/paper_trading.db）
   - PAPER_FILL_MODE（instant | partial | never | reject、デフォルト instant）
   - LOG_LEVEL（DEBUG|INFO|WARNING|ERROR）
   - LOG_DIR（ログ保存ディレクトリ、デフォルト logs/）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用）
   - KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア。実運用では 0 推奨）
   - OPENAI_API_KEY（AI 機能を使う場合に必要）

4. 設定検証を行います:
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けて警告もエラー扱いにできます。

5. データディレクトリ準備:
   - デフォルトでは data/ 配下に DB や PID / flag ファイルを作成します。実行ユーザーが書き込み可能であることを確認してください。

使い方（運用例）
----------------
- 監視ループの起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL を設定するとポーリング間隔を秒単位で変更できます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（SQLITE_PATH）の DB を使用します（monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する仕様です）。

- 実行エンジンの起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db にトレードログを記録します（本番 DB と分離）。
  - エンジンは data/stop_requested.flag が存在すると起動を行わない、あるいは実行中に検知すると停止処理を行います。
  - 実行開始時にプロセス優先度を "high" に設定します（set_process_priority）。

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを指定できます（指定がない場合は環境変数 PAPER_TRADING_SQLITE_PATH、無ければ data/paper_trading.db を参照）。
  - レポートは稼働率、注文成功率、送信率、レイテンシ（P95）等を出力し、PASS/FAIL 判定を行います。

- AI 機能（ニューススコア・レジーム判定）:
  - OPENAI_API_KEY を設定してください（例: export OPENAI_API_KEY=sk-...）。
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出すと DuckDB 内の raw_news / prices_daily 等のデータを参照してスコアを計算し、ai_scores / market_regime テーブルへ保存します。
  - 使用モデル: gpt-4o-mini（コード内で指定）。API 呼び出しの失敗には指数バックオフで対処し、最終的にはフォールバック値で継続します。

運用上のフラグ・ファイル
----------------------
- 停止フラグ（run_monitoring / run_execution が監視）:
  - data/stop_requested.flag
  - このファイルが存在すると run_execution は起動せず、run_monitoring は監視ループで検出して終了します。

- Kill Switch（ExecutionEngine に停止シグナルを出す）:
  - data/kill.flag（KILL_FLAG_PATH で変更可）
  - KillSwitch が条件に該当した場合に書き込まれ、ExecutionEngine による停止トリガーになります。

- PID ファイル:
  - data/execution.pid（デフォルト。Settings.pid_file_path で変更可）

ログ
----
- ログはデフォルトで logs/ ディレクトリに日次ローテートで出力されます（kabusys.utils.logging_setup.setup_logging）。
- 各スクリプトは app_name を指定してログファイルを分離します（例: logs/execution.log, logs/monitoring.log）。
- LOG_DIR 環境変数でログディレクトリを変更できます。

注意点 / 実装上の挙動
--------------------
- Monitoring の DB 初期化:
  - init_monitoring_db(conn) により必要なテーブルとインデックスを作成します（冪等）。既存 DB のマイグレーション（カラム追加）にも対応しています（例: dashboard.peak_value, trade_logs.latency_ms）。
- run_monitoring は MONITOR_POLL_INTERVAL に 0 以下を渡すと警告してデフォルトにフォールバックします。
- run_execution は KABUSYS_ENV が paper_trading のとき専用の paper_sqlite_path を使用して本番 DB と分離します。
- AI モジュールは外部 API 呼び出しを行うため、API キーの管理とコストに注意してください。
- 設定自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml がある場所）を起点に .env/.env.local を自動ロードします。テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

コマンドまとめ
--------------
- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 監視起動
  - python -m kabusys.run_monitoring
- 実行エンジン起動
  - python -m kabusys.run_execution
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前設定検証 CLI
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュース NLP スコアリング
  - regime_detector.py     — レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py       — （省略されているが存在想定の監視ロジック）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py       — （アラート送信ロジック想定）
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

補足: 必要な追加ドキュメント
--------------------------
- config/*.yaml（system_config.yaml 等）は config ディレクトリにあり、validate_config.py で存在・パースチェックを行います。生成スクリプト（scripts/generate_config.py）でテンプレートを作る想定です（リポジトリ内にない場合は自前で用意してください）。
- 実運用前には KABUSYS_ENV=live に切り替える前に必ず validate_config を実行し、LINE などの通知設定を確認してください。

ライセンス / バージョン
-----------------------
パッケージバージョンは kabusys.__version__ = "0.1.0"（src/kabusys/__init__.py）に定義されています。ライセンス情報はリポジトリのルートにある LICENSE 等をご確認ください（本抜粋コードには含まれていません）。

以上が README の要約です。必要であれば、各モジュールの API 使用例（関数引数・戻り値の詳細）、実行時のログサンプル、docker / systemd ユニットの例などの追加ドキュメントも作成できます。希望があれば教えてください。