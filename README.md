KabuSys — 日本株自動売買ライブラリ / 実行スクリプト
================================

概要
----
KabuSys は日本株自動売買システムのライブラリ群と起動スクリプト群を含むプロジェクトです。  
主な責務は以下の通りです。

- 監視（Monitoring）: システム状態・データ鮮度・発注ログなどのポーリング監視とアラート、必要時の Kill Switch 発動
- 実行（Execution）: 発注エンジンの起動・注文管理・リスク管理（ペーパートレードと本番の切替対応）
- 研究（Research）: DuckDB 上でのファクター計算・特徴量解析
- AI 支援: ニュースの NLP スコアリング / 市場レジーム判定（OpenAI を利用）
- ユーティリティ: .env ウィザード、設定検証、ログ設定、プロセス優先度制御、ペーパートレード検証レポート など

特徴（主な機能）
----------------
- 環境別動作:
  - KABUSYS_ENV による動作モード: development / paper_trading / live
  - paper_trading モードでは専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離
- 実行時ユーティリティ:
  - 起動スクリプトはプロセス優先度を「high」に変更（set_process_priority）
  - 統一的なログ設定（console + 日次ローテーションファイル）
- 監視:
  - SystemMonitor, TradeMonitor, RiskMonitor を組み合わせた MonitoringEngine
  - kill.flag による ExecutionEngine 停止（KillSwitch）
  - stop_requested.flag によるループ停止制御（ローカル運用向け）
- 研究モジュール:
  - momentum / volatility / value 等のファクター計算（DuckDB）
  - forward returns / IC / 統計サマリ
- AI モジュール:
  - news_nlp: ニュースを OpenAI（gpt-4o-mini）でスコア化し ai_scores に書き込み
  - regime_detector: ETF（1321）の MA とマクロニュースの組合せで市場レジーム判定
- ペーパートレード検証ツール:
  - paper_verification_report による運用検証レポート（稼働率、注文成功率、レイテンシ等）

セットアップ
-----------
前提:
- Python 3.9+（実際の動作環境に合わせてください）
- SQLite は標準ライブラリに含まれます

推奨パッケージ（例）:
- duckdb
- psutil
- openai
- PyYAML（設定検証で YAML のパースを行う場合）
インストール例:
- pip install duckdb psutil openai PyYAML

環境変数 / .env
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 主な任意/設定項目（デフォルト値は括弧内）:
  - KABUSYS_ENV (development | paper_trading | live) — (development)
  - DUCKDB_PATH (data/kabusys.duckdb)
  - SQLITE_PATH (data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
  - PAPER_FILL_MODE ("instant"|"partial"|"never"|"reject") — (instant)
  - LOG_LEVEL (INFO)
  - LOG_DIR (logs)
  - OPENAI_API_KEY — AI 機能を使う場合は必須
- .env の自動読み込み:
  - プロジェクトルートに .env / .env.local があれば自動で読み込まれます（OS 環境変数が優先）。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

.env の作成補助:
- 対話式ウィザード:
  - python -m kabusys.config_setup
  - これにより .env を生成・更新できます（.env は絶対に Git 管理に含めないでください）。

設定検証:
- 起動前に設定をチェック:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）になります。

起動・使い方
------------

1) ExecutionEngine（発注エンジン）を起動
- 本番 or ペーパートレードの切替は KABUSYS_ENV で制御します。
- 実行:
  - python -m kabusys.run_execution
- 動作ポイント:
  - paper_trading の場合、BrokerClientFactory は MockBrokerClient を生成し、データは PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に保存され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - 実行中に data/stop_requested.flag を作成すると実行スレッドを停止します。
  - PID ファイルは data/execution.pid（Settings.pid_file_path で上書き可）。

2) Monitoring（監視ループ）を起動
- 実行:
  - python -m kabusys.run_monitoring
- 動作ポイント:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - Monitoring では Settings.env に関わらず本番用 sqlite_path（SQLITE_PATH）を使用します（監視は本番 DB を見る想定）。
  - 監視ループはプロジェクトルート/data/stop_requested.flag を検知すると停止します。
  - KillSwitch（監視中に条件を満たしたとき）により data/kill.flag を書き込むと ExecutionEngine 側で検知して停止できます（Execution は起動時に kill.flag を自動クリアする設定が有効な場合注意）。

3) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB:
  - 環境変数 PAPER_TRADING_SQLITE_PATH、未設定であれば data/paper_trading.db

4) 研究・AI 各機能（ライブラリとして利用）
- research モジュール:
  - kabusys.research.calc_momentum(conn, target_date) 等を呼んで DuckDB 結果を得る
- ai モジュール:
  - kabusys.ai.score_news(conn, target_date, api_key=None) — OPENAI_API_KEY を使用
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- これらは DuckDB 接続（duckdb.connect）を引数に取り、DB 上の prices_daily / raw_news などのテーブルを参照します。

ログ
----
- ログはデフォルトで stdout と logs/<app_name>.log に出力されます（TimedRotatingFileHandler、日次ローテーション、30世代保存）。
- LOG_DIR 環境変数または setup_logging() の引数で変更可能。
- LOG_LEVEL 環境変数でログレベルを指定（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

停止制御（運用）
----------------
- stop_requested.flag:
  - プロジェクトルート/data/stop_requested.flag を作成すると run_monitoring/run_execution のポーリングループが検知して終了します（外部管理での一時停止に便利）。
- kill.flag:
  - Monitoring の KillSwitch が異常検出時に data/kill.flag を書き込み、ExecutionEngine が検知して安全停止します。
  - Settings.kill_flag_clear_on_start=1 にすると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ディレクトリ構成（重要ファイル）
------------------------------
以下は src/kabusys 配下の主要ファイル・モジュールです（抜粋）:

- run_monitoring.py
  - Monitoring のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading の切替対応）
- config.py
  - 環境変数 / 設定の集中読み込み・検証ロジック
- config_setup.py
  - .env を対話式に作成・更新するウィザード
- validate_config.py
  - .env と config/*.yaml の静的検証ツール
- utils/
  - logging_setup.py — 共通ログ初期化
  - process_priority.py — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py — SQLite の永続化層（system_status / trade_logs / risk_logs / positions / dashboard）
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py
- execution/
  - ExecutionEngine、OrderManager、RiskManager、BrokerClientFactory 等（発注ロジック）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 銘柄選定・配分・リスク制御
- research/
  - factor_research.py, feature_exploration.py — ファクター計算・IC 等
- ai/
  - news_nlp.py, regime_detector.py — OpenAI を使った NLP / レジーム判定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

（実際のプロジェクトツリー）
- src/
  - kabusys/
    - __init__.py
    - run_execution.py
    - run_monitoring.py
    - config.py
    - config_setup.py
    - validate_config.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - monitoring_engine.py
      - risk_monitor.py
      - kill_switch.py
      - ...
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
      - ...
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
    - data/  (運用時に生成・使用されるディレクトリ)
    - logs/  (ログ出力先、既定)

注意事項 / 運用上のポイント
-------------------------
- .env は機密情報を含むため必ず .gitignore に追加し、リポジトリにコミットしないでください。
- 本番運用時は KABUSYS_ENV=live に設定し、KILL_FLAG_CLEAR_ON_START=0 を推奨します（誤って Kill Switch を消去しないため）。
- AI 機能を利用する際は OPENAI_API_KEY を設定してください。API 呼び出しは失敗時にフォールバックする実装ですが、キーがないと動作しません。
- Monitoring は監視目的のため、本番の sqlite_path（監視 DB）を参照します。Execution は paper_trading モード時に paper_sqlite_path を使用して本番 DB からの分離を行います。
- プロセス優先度設定や CPU affinity は環境によって権限が必要になる場合があります（例: Linux の nice 値変更や Windows の優先度設定でアクセス権限不足になる可能性）。

問題・拡張
-----------
- config/*.yaml の検証には PyYAML が必要です。validate_config.py はインストールされていない場合に YAML 検証をスキップします。
- DuckDB のバージョンや OpenAI SDK の変化により一部 API 呼び出しやバインド方法が影響を受ける可能性があります。CI/デプロイ時に依存パッケージのバージョン固定を推奨します。

サンプルコマンドまとめ
---------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

お問い合わせ / 貢献
------------------
リポジトリの ISSUE / PR を通じてバグ報告・機能提案を受け付けます。セキュリティに関する報告は公開チャンネルを避けてください。

--- 
以上がこのコードベースの概要・セットアップ・使い方の要約です。必要であれば、導入手順や .env の具体例、運用チェックリスト（起動/停止/監視）を別ファイルで作成します。どの内容を優先しますか？