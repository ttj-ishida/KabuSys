KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買および運用支援を目的とした軽量フレームワークです。
主な機能はシグナル生成・ポートフォリオ構築・発注エンジン（ExecutionEngine）・監視モジュール・AI を用いたニュースセンチメント判定・研究用ユーティリティなどを含みます。

このリポジトリは実運用を想定したコンポーネント群（Execution/Monitoring/Risk/Portfolio/Research/AI 等）を提供します。実際のブローカ接続は設定に応じてモック（ペーパートレード）と実運用を切り替えられる設計です。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、ペーパートレード用 DB（data/paper_trading.db 標準）に記録します。
- Monitoring（run_monitoring.py）
  - システム稼働状況、データ鮮度、注文状況、リスク指標をポーリングし監視ログ（SQLite）へ保存。Kill Switch / アラートを評価します。
- 設定ウィザード（config_setup.py）
  - .env を対話的に生成・更新する CLI。
- 設定検証（validate_config.py）
  - 起動前に環境変数や config/*.yaml の簡易チェックを実行。
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB を解析して稼働率・約定率・レイテンシ等のレポートを標準出力に出力。
- ポートフォリオ構築ユーティリティ（portfolio/*）
  - 候補選定、重み付け、リスク調整、ポジションサイジング（単元丸め含む）。
- リサーチ用モジュール（research/*）
  - ファクター算出（Momentum/Value/Volatility 等）、将来リターン計算、IC 等の統計指標。
- AI モジュール（ai/*）
  - OpenAI を用いたニュースセンチメント（score_news）、市場レジーム判定（regime_detector）。
- 共通ユーティリティ（utils/*）
  - ロギング設定、プロセス優先度 / CPU affinity 設定など。
- 監視 DB 層（monitoring/monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard の永続化と操作。

前提・依存
----------
最低限の依存（概要）
- Python 3.9+（パッケージは型注釈で 3.9+ を想定）
- pip install で以下を準備することを推奨:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/.yaml の検証を行う場合）
その他: sqlite3 は標準ライブラリ。OS によりプロセス優先度設定に権限が必要になることがあります。

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合は pip install -r requirements.txt を使用してください。

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 必要に応じて OPENAI_API_KEY（AI 機能使用時）、LINE 関連トークン等を設定

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使うなら必須)
- LINE_CHANNEL_ACCESS_TOKEN (任意, アラート通知用)
- LINE_USER_ID (任意)
- KABUSYS_ENV (default: development)
  - 有効値: development, paper_trading, live
- PAPER_FILL_MODE (paper_trading 用, default: instant)
  - 有効値: instant | partial | never | reject
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading DB, default: data/paper_trading.db)
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔 秒、デフォルト: 60)

運用上の注意（主な挙動）
-----------------------
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（デフォルト 60 秒）。
- Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path（SQLITE_PATH）を使用します（監視 DB は環境に依存しない運用前提）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- 停止フラグ:
  - data/stop_requested.flag: run_monitoring/run_execution が監視している停止フラグ（存在するとループ終了やエンジン停止を行う）。
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送る（存在チェック・クリア機能あり）。
  - data/execution.pid: ExecutionEngine の PID ファイル（起動時に作成される想定）。
- Kill Switch は監視（ドローダウン超過・ポジション上限超過等）によりファイルを書き込み、Execution を停止させます。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアしますが、本番環境では推奨されません。

使い方（コマンド例）
-------------------
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（フォアグラウンド）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定するとペーパートレードモードで起動され、data/paper_trading.db を使用します。

- Monitoring を起動（フォアグラウンド）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI スコアリング（プログラム API）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=os.environ["OPENAI_API_KEY"])

ログ
----
- ログはデフォルトで stdout（StreamHandler）と logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション）に出力されます。
- LOG_LEVEL 環境変数で全体のログレベルを制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- LOG_DIR を環境変数で指定するとログ保存先を変更できます。

主要コンポーネント（簡易説明）
----------------------------
- kabusys/config.py
  - 環境変数読み込みと Settings クラス（自動 .env 読み込み機能含む）
- kabusys/config_setup.py
  - .env 対話式生成ウィザード
- kabusys/validate_config.py
  - 起動前の設定検証 CLI
- kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（プロセス優先度設定・DB 初期化・スレッド管理）
- kabusys/run_monitoring.py
  - SystemMonitor をポーリングする監視プロセス起動スクリプト
- kabusys/utils/logging_setup.py
  - ログ設定ユーティリティ
- kabusys/utils/process_priority.py
  - プロセス優先度 / CPU affinity のユーティリティ
- kabusys/monitoring/*
  - 監視系の実装（system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db）
- kabusys/portfolio/*
  - ポートフォリオ構築ロジック（候補選定・重み・ポジションサイズ計算・セクター上限）
- kabusys/research/*
  - ファクター算出・将来リターン・IC 等の研究用ユーティリティ
- kabusys/ai/*
  - OpenAI を使ったニュースNLP・レジーム判定
- kabusys/tools/*
  - 運用支援ツール（レポート生成等）

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py
- utils/
  - __init__.py
  - logging_setup.py
  - process_priority.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - risk_monitor.py
  - trade_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py (実装想定)
- execution/
  - execution_engine.py (実装想定)
  - order_manager.py (実装想定)
  - broker_factory.py (実装想定)
  - order_repository.py (実装想定)
  - reconciler.py (実装想定)
  - risk_manager.py (実装想定)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py
- tools/
  - paper_verification_report.py
  - __init__.py

運用上のヒント
--------------
- 本番運用時は KABUSYS_ENV=live にし、LINE 通知や監視設定を十分に確認してください（validate_config の警告を無視しない）。
- Kill Switch（data/kill.flag）は本番で誤ってクリアしないよう注意してください。KILL_FLAG_CLEAR_ON_START は本番では "0" を推奨します。
- openai API はレート制限やコストがあるため、AI 機能の運用は慎重に行ってください（テスト時はモック化を推奨）。
- run_execution/run_monitoring をデーモン化・サービス化する場合は systemd や Supervisor などでプロセス管理してください。PID ファイル（data/execution.pid）や stop_requested.flag の扱いを運用ルールとして決めると安全です。

ライセンス・貢献
----------------
リポジトリにライセンスファイル（LICENSE）が含まれている場合はそちらに従ってください。バグ報告や改善提案は Issue / PR を通じて歓迎します。

以上がこのコードベースの概要と利用方法です。必要であれば各モジュールの詳細な API ドキュメントや起動時のトラブルシュート案内を追加します。どの部分を詳しく知りたいか教えてください。