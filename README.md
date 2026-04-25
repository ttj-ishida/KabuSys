README
====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の実装群です。本リポジトリには以下の主要機能が含まれます:

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理の起動ロジック
- 監視コンポーネント（Monitoring）: システム状態・注文状態・リスクを定期チェックしてログ保存・アラート・Kill Switch を制御
- ポートフォリオ構築ロジック: 候補選定、重み計算、ポジションサイズ計算、セクター制限などの純粋関数群
- 研究/ファクター計算: モメンタム、ボラティリティ、バリューなどのファクター計算（DuckDB 経由）
- AI連携モジュール: OpenAI を用いたニュースセンチメント評価・レジーム判定
- ユーティリティ/ツール: .env 設定ウィザード、設定検証 CLI、Paper Trading 検証レポート等

主な設計方針:
- 設定は環境変数（.env）で管理。自動ロード機能あり（必要に応じて無効化可）。
- DuckDB/SQLite を分析・監視 DB に利用。
- 本番/ペーパートレードの DB を分離可能。
- 外部 API 呼び出し（OpenAI 等）は明示的な API キーが必要で、安全なフォールバック設計あり。

機能一覧
-------
主な機能（抜粋）:

- run_execution.py
  - ExecutionEngine の起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading 専用 DB に記録。
- run_monitoring.py
  - SystemMonitor のポーリングループ。ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60秒）。
- config_setup.py
  - .env を対話的に作成/更新するウィザード。
- validate_config.py
  - .env と config/*.yaml の事前検証 CLI（--strict オプションあり）。
- tools/paper_verification_report.py
  - ペーパートレードの検証レポート生成ツール（期間指定可）。
- portfolio/*.py
  - 銘柄選定、重み付け、ポジションサイズ計算、リスク調整等の純粋関数群。
- research/*.py
  - DuckDB 上でのファクター計算、前方リターン、IC 計算、統計要約。
- ai/news_nlp.py / ai/regime_detector.py
  - OpenAI を用いたニュースセンチメント評価、レジーム判定ロジック。
- monitoring/*
  - MonitoringDB（SQLite）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、AlertManager（通知連携は別実装想定）。

前提条件
--------
- Python 3.10 以上を推奨（型アノテーションや新しい標準ライブラリ機能を使用）
- 必要な Python パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合に必要）
- （任意）仮想環境の使用を推奨

簡易セットアップ例
-----------------
1) 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2) 必要パッケージをインストール:
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使ってください）

3) プロジェクトルートに移動（README のコマンドはプロジェクトルートから想定）
   - cd <project_root>

環境変数・設定
--------------
自動で .env をロードする仕組みがあり、ルートに .env / .env.local があれば読み込まれます（OS 環境変数が優先）。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使うオプション / デフォルト
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- OPENAI_API_KEY: OpenAI API を使用する際に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の fill 動作（instant|partial|never|reject）

PAPER_FILL_MODE の有効値: "instant", "partial", "never", "reject"

セットアップウィザード・検証
--------------------------
- .env の対話式作成:
  - python -m kabusys.config_setup
  - オプション: --env-file を指定して別パスに保存可能

- 設定検証:
  - python -m kabusys.validate_config
  - 警告をエラー扱いにする: python -m kabusys.validate_config --strict

起動・使い方
-----------

1) 監視ループ（SystemMonitor）を起動:
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更できます:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に依らず本番 sqlite を参照する仕様）。
   - 停止方法: 実行ディレクトリの data/stop_requested.flag ファイルを作成するとループを検知して終了します（または Ctrl+C）。

2) 実行エンジンを起動（ExecutionEngine）:
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用します（本番 DB と完全分離）。
   - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
   - 実行中に stop フラグが作成されるとエンジン停止処理が行われます。

3) Paper Trading 検証レポート生成:
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定できます。コマンドラインの --db が優先されます。

4) AI 機能（プログラム的利用）:
   - ai/news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続（duckdb.connect(...) の接続オブジェクト）を与えて呼び出します。
     - api_key が None の場合は OPENAI_API_KEY 環境変数を参照します。
   - ai/regime_detector.score_regime(conn, target_date, api_key=None)
     - 同様に使用。どちらも OpenAI の API 呼び出しでネットワーク・レート制限等を考慮したリトライロジックを備えています。

ユーティリティ
------------
- ロギング: kabusys.utils.logging_setup.setup_logging(app_name="execution") を各起動スクリプトが呼び出します。ログはデフォルト logs/<app_name>.log に日次ローテーション（30日保持）。
- プロセス優先度: kabusys.utils.process_priority.set_process_priority("high"|"normal"|"low") を使用。run_monitoring/run_execution は起動時に "high" を設定を試みます（権限によっては失敗する場合あり）。
- Kill Switch: リスク条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（KillSwitch クラスで制御）。

データベースとファイルパス（デフォルト）
------------------------------------
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- ペーパートレード SQLite: data/paper_trading.db
- PID / フラグファイル:
  - data/execution.pid（ExecutionEngine の PID）
  - data/stop_requested.flag（外部からの停止指示）
  - data/kill.flag（KillSwitch が書き込む停止指示）

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 配下の主要ファイル/ディレクトリ（本リポジトリに含まれるものに基づく抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定読み込み・Settings クラス
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (実装ファイルがある想定)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装ファイルがある想定)
  - execution/
    - execution_engine.py (実装ファイルがある想定)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
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
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - monitoring/ (SQL/DB helper files already listed above)

注意事項 / 運用メモ
-----------------
- .env は絶対に Git にコミットしないでください（config_setup が警告を出します）。
- 本番（KABUSYS_ENV=live）での設定ミスは致命的な実売買につながるため validate_config でしっかり検証してください。
- run_monitoring は環境にかかわらず Settings.sqlite_path（デフォルトで data/monitoring.db）を使用します。ペーパートレードと完全に分離したい場合は実行前に設定を確認してください。
- OpenAI API を使用する機能を使う前に OPENAI_API_KEY を環境変数または関数引数で渡してください。API エラー時には各モジュールがフェイルセーフ（0.0 フォールバックやスキップ）を用意していますが、期待する出力が得られない可能性があります。
- psutil によるプロセス優先度設定や CPU affinity の変更は OS と権限に依存します。権限不足で警告が出ることがあります。

開発・デバッグ
--------------
- モジュールを直接実行する際はプロジェクトルートが Python の import path に入るように実行するか、パッケージとして -m を使います:
  - python -m kabusys.run_monitoring
  - python -m kabusys.run_execution
- テスト環境や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境依存の自動ロードを抑制できます。
- DuckDB / SQLite はファイルベースのため、サンプルデータを用意してローカルで機能を検証できます。

サポート / 追加情報
-------------------
- 各モジュールの docstring と関数コメントに詳細な取り扱いや想定仕様が記載されています。開発時はまずソースコード内のドキュメントを参照してください。
- 設定テンプレート（.env.example や config/*.yaml のサンプル）がある場合はそれに従って初期設定してください（当該ファイルがない場合は config_setup を利用）。

以上。プロジェクト固有の運用ポリシーや追加の依存関係がある場合は、運用チーム向けの別途ドキュメントを用意することを推奨します。