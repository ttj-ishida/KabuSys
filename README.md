KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。  
価格データや財務データを DuckDB で処理し、発注ロジック・ポートフォリオ構築・監視・リスク管理・AI を用いたニュース解析などを備えます。  
このリポジトリはライブラリ本体と起動スクリプト群（ExecutionEngine / Monitoring 等）、設定ウィザード・検証ツール・分析用スクリプトを含みます。

主な特徴
--------
- 実行環境切替（development / paper_trading / live）に対応する Settings 管理
- ExecutionEngine：ブローカー抽象化（本番とペーパートレードを分離）
- Monitoring：システム稼働監視、データ鮮度チェック、トレード／リスク監視、Kill Switch（フラグファイルによる停止）
- ポートフォリオ構築：候補選定、配分（等金額／スコア重み）、株数決定（リスクベース等）
- リサーチ：ファクター計算（Momentum/Volatility/Value）、特徴量解析（IC 等）
- AI モジュール：ニュースの LLM（OpenAI）によるスコアリング、レジーム判定のサポート
- ツール：ペーパートレード検証レポート生成スクリプト
- ロギングユーティリティ（コンソール + 日次ローテーションファイル）
- 簡易 CLI：.env ウィザード（config_setup）と設定検証（validate_config）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 環境
   - 推奨: Python 3.9+
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主要パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   (実際の requirements.txt がある場合はそれを使用してください。)

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI を使う機能を利用する場合:
     - OPENAI_API_KEY を設定

   自動ロード:
   - .env / .env.local はプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みされます。
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラーとして扱います:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - Monitoring 用 SQLite は起動スクリプトが init を行います（init_monitoring_db）。
   - DuckDB ファイル（デフォルト data/kabusys.duckdb）は事前に用意／書き込み権限を確認してください。

使い方（起動と主な CLI）
------------------------

共通:
- ログ設定は kabusys.utils.logging_setup.setup_logging により行われ、デフォルトで logs/<app_name>.log に日次ローテーションで保存されます。
- プロセス優先度は起動時に "high" に設定されます（psutil を使用）。

1. ExecutionEngine（取引エンジン）起動
   - 本番とペーパートレードを切り替え:
     - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient（実注文は行わない）を使い、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH, default data/paper_trading.db）に記録します。
   - 起動コマンド:
     - python -m kabusys.run_execution

   停止:
   - data/stop_requested.flag を作成すると起動中のスクリプトは検出して安全に停止します。
   - ExecutionEngine は data/execution.pid を PID ファイルとして利用します。

2. Monitoring（監視プロセス）起動
   - 起動コマンド:
     - python -m kabusys.run_monitoring
   - ポーリング間隔の変更:
     - MONITOR_POLL_INTERVAL 環境変数で秒数を指定（デフォルト 60 秒）。
   - Monitoring は Settings.env にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
   - 停止:
     - data/stop_requested.flag の存在で監視ループを終了します。

3. 設定ウィザード / 検証
   - .env 作成:
     - python -m kabusys.config_setup
   - 設定検証:
     - python -m kabusys.validate_config
     - python -m kabusys.validate_config --strict

4. ペーパートレード検証レポート
   - SQLite ファイル（デフォルト data/paper_trading.db）から期間を指定して検証レポートを出力:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

5. AI モジュール（ニュース NLP / レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）が必要。
   - ニューススコアリング呼び出し例（コード内 API）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="sk-...")
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key="sk-...")

実装メモ・重要点
-----------------
- Settings（kabusys.config.Settings）:
  - 環境変数ベースで設定を解決します。KABUSYS_ENV（development/paper_trading/live）を検証します。
  - paper_trading 環境では paper_sqlite_path を使用して本番 DB と完全分離します。
  - 自動ロードはプロジェクトルートの .env / .env.local を読み込みます（既存 OS 環境変数を保護）。

- MonitoringDB:
  - SQLite ベースで system_status / trade_logs / positions / risk_logs / dashboard を管理。
  - init_monitoring_db() は必要なテーブル・インデックスを冪等に作成します。

- Kill Switch:
  - RiskMonitor 等の結果に基づいて data/kill.flag を出力すると ExecutionEngine に停止シグナルを送ります（ExecutionEngine は kill.flag の存在で停止処理を行います）。

- process_priority:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。権限がない環境では警告を出してスキップします。

環境変数（主なもの）
--------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作環境:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DB:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 専用 DB, default: data/paper_trading.db)
- ログ:
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR
- AI:
  - OPENAI_API_KEY
- Monitoring 制御:
  - MONITOR_POLL_INTERVAL (秒, run_monitoring 用。デフォルト 60)
  - KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動でクリアするか: 0/1。production では 0 推奨)
- その他:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env の自動読み込みを無効化

ディレクトリ構成（抜粋）
----------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py        (※ファイルは本 README の抜粋に含まれていませんが存在します)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        (※実装に応じて存在)
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

運用上の注意
------------
- 本番（KABUSYS_ENV=live）での稼働前には必ず validate_config を実行し、LINE 通知設定や Kill Switch 設定を確認してください。
- .env は絶対にリポジトリにコミットしないでください。
- OpenAI を用いる処理は API 利用料が発生します。レート制限やコストに注意してください（news_nlp / regime_detector はリトライ・バッチ処理ロジックを実装しています）。
- ファイルベースのフラグ（data/kill.flag, data/stop_requested.flag）等を使う運用は簡便ですが、複数インスタンス運用時は競合に注意してください。

貢献・拡張案
------------
- ブローカープラグインの追加（各証券会社 API）
- 銘柄別 lot_size の対応（position_sizing の TODO）
- モニタリングアラート送信チャネル（Slack/PagerDuty 等）の強化
- テストカバレッジ強化（ユニット／統合テスト）
- requirements.txt / setup CI の整備

ライセンス / バージョン
-----------------------
- バージョン: __version__ = "0.1.0"（kabusys.__init__）
- ライセンス情報はリポジトリのトップレベルファイルを参照してください（もし未設定なら別途追加してください）。

補足（よく使うコマンド例）
-------------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。必要であれば README に含めるサンプル .env テンプレートや詳細な起動例（systemd unit / supervisor 用）も作成します。どの情報を追加しますか？