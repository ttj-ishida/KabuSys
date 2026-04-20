KabuSys — 日本株自動売買システム（リポジトリ README）
=======================================

概要
----
KabuSys は日本株自動売買のための内部ライブラリ群と起動スクリプトを含むプロジェクトです。  
主な責務は以下のとおりです。

- 発注エンジン（ExecutionEngine）の起動・管理（本番／ペーパートレード対応）
- システム監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- ポートフォリオ構築（銘柄選定・重み計算・ポジションサイズ算出）
- 研究用ファクター計算・特徴量解析（DuckDB ベース）
- ニュース NLP（OpenAI）を用いたセンチメント評価と市場レジーム判定
- ペーパートレード検証レポート生成スクリプト 等

本 README はコードベース（src/kabusys 以下）を前提に、セットアップ・使い方・ディレクトリ構成を説明します。

主な機能一覧
--------------
- 起動スクリプト
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 環境変数 / config/*.yaml の検証
  - run_execution.py: ExecutionEngine（発注エンジン）起動
  - run_monitoring.py: SystemMonitor のポーリングループ起動
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch（data/kill.flag による発注停止）
  - 永続化: SQLite（monitoring.db）用の monitoring_db モジュール
- ポートフォリオ構築
  - 銘柄選定、等配分／スコア配分、リスク調整（セクター制限・レジーム乗数）、株数決定（単元丸め）
- 研究（research）
  - ファクター計算 (momentum/value/volatility)
  - 将来リターン、IC 計算、統計サマリ
- AI（OpenAI）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
- ユーティリティ
  - logging_setup: 統一的なログ設定（コンソール + 日次ローテート）
  - process_priority: プロセス優先度 / CPU affinity 設定
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート作成

前提 / 必要パッケージ
-------------------
最低限の推奨環境（例）:
- Python 3.10+
- 必須 Python パッケージ（用途に応じてインストール）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config YAML 検証を行う場合)
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（kabuAPI / OpenAI を利用する場合）

※ requirements.txt はリポジトリに含まれていない想定なので、必要なパッケージを pip で個別に入れてください。

環境変数（主なもの）
-------------------
以下は本プロジェクト内で参照される主な環境変数とデフォルト値（存在しない場合）です。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / デフォルト:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI を使う場合に必須
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR — ログ保存先（デフォルト: logs/）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

.env 自動読み込み:
- プロジェクトルートに .env/.env.local があると、自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

セットアップ手順
----------------
1. Python 環境を用意（仮想環境推奨）
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb psutil
   - AI 機能を使う場合: pip install openai
   - YAML 検証を使う場合: pip install PyYAML

3. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
     - あるいは .env.example を参考に手動で作成
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - 厳密モード（警告も FAIL）: python -m kabusys.validate_config --strict

4. ディレクトリ作成（必要に応じて）
   - data/ や logs/ はスクリプトが自動作成しますが、権限や場所を確認してください。

起動 / 使い方
--------------

設定ウィザード・検証
- .env を対話的に生成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

監視（Monitoring）
- SystemMonitor のポーリングを単独で起動:
  - python -m kabusys.run_monitoring
- ポーリング間隔を変更:
  - MONITOR_POLL_INTERVAL 環境変数（秒）を設定（例: export MONITOR_POLL_INTERVAL=30）
- 停止フラグ:
  - プロジェクトルート/data/stop_requested.flag が存在すると run_monitoring はループを終了します

ExecutionEngine（発注エンジン）
- 実際のエンジン起動:
  - python -m kabusys.run_execution
- KABUSYS_ENV による挙動:
  - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録。実際の発注は行われません
  - live: 本番ブローカーを使用（KABU_API_PASSWORD 等が必須）
- 停止制御:
  - data/stop_requested.flag が書かれるとエンジン停止を試みます
  - kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は ExecutionEngine に対する Kill Switch（停止指令）です

AI / レジーム / ニュース
- ニューススコアリング（DB を直接操作する関数）:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キーは OPENAI_API_KEY または引数で渡す
- 市場レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

Paper Trading レポート
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定、未指定時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db を参照

ログ
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテート）に出力されます
- ログレベル:
  - LOG_LEVEL 環境変数で変更（例: export LOG_LEVEL=DEBUG）

Kill Switch / 停止フラグの仕組み
- kill.flag（Settings.kill_flag_path）: リスク監視がトリガーした場合に書き込まれることを想定。ExecutionEngine は起動時や稼働中にこれを検出して停止します
- stop_requested.flag（data/stop_requested.flag）: 手動でプロセスを停止させる単純なフラグ（スクリプト run_* がこれを見て終了する）

主要モジュールの簡単な説明
-------------------------
- kabusys.config: 環境変数 / .env の読み込みと Settings クラス
- kabusys.utils.logging_setup: ルートロガー設定（stdout + 日次ファイル）
- kabusys.utils.process_priority: プロセス優先度・CPU affinity 設定
- kabusys.monitoring.*: 監視ロジック・DB 永続化・Kill Switch・アラート連携
- kabusys.execution.*: ブローカーファクトリ、エンジン、注文管理、リスク管理（主要な実行ロジック）
- kabusys.portfolio.*: 銘柄選定・重み付け・株数決定・リスク調整
- kabusys.research.*: DuckDB を用いたファクター計算・特徴量解析
- kabusys.ai.*: OpenAI を使ったニュース NLP とレジーム判定
- kabusys.tools.paper_verification_report: ペーパートレード検証の集計レポート

ディレクトリ構成（抜粋）
----------------------
以下はリポジトリ内の主要ファイル・ディレクトリ（src/kabusys）を抜粋した構成例です。

- src/
  - kabusys/
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
      - __init__.py
      - monitoring_db.py
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
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - monitoring/
      - monitoring_db.py
      - ...（上で述べた各モジュール）

（注）実際のリポジトリには上記以外のファイルやサンプル設定ファイルが含まれている可能性があります。

開発時の注意点 / 補足
---------------------
- .env は機密情報（API トークン等）を含むため、絶対に Git にコミットしないでください。
- Monitoring や Execution は DB パスや PID ファイルなどファイルシステムへの書き込みを行います。実行ユーザーの権限とパスを確認してください。
- ペーパートレードモードでは DB が分離されます（PAPER_TRADING_SQLITE_PATH）。本番 DB の混入を防ぐ設計になっていますが、設定ミスに注意してください。
- OpenAI など外部 API はレート制限やネットワーク障害を考慮してリトライ等の処理が組まれていますが、API キーや利用料に注意して運用してください。
- validate_config.py では PyYAML が未インストールの場合は YAML の検証をスキップします（警告表示）。

よくあるコマンドまとめ
---------------------
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
この README はコードベースに沿った利用方法と設計説明を提供するものです。実プロダクション運用前に設定と動作を十分にテストし、必要に応じて適切なログ・監視・権限管理、秘密情報の保護を行ってください。

問題報告・機能要望はリポジトリの ISSUE に記載してください（運用方針に従ってください）。

以上。必要ならば、README に追記したい箇所（例: 具体的な .env テンプレート、requirements.txt の推奨内容、より詳細な起動手順）を指定してください。