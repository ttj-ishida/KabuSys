KabuSys — 日本株自動売買システム（README）
=================================

概要
----
KabuSys は日本株向けの自動売買・研究基盤コード群です。  
主な機能は以下の通りです。

- 発注実行エンジン（ExecutionEngine）と監視モジュール（Monitoring）
- Portfolio 構築（候補選定、重み計算、ポジションサイズ算出、セクター制限）
- 研究用ファクター計算・特徴量探索（DuckDB を使用）
- AI 支援（ニュースのセンチメント評価、レジーム判定：OpenAI を利用）
- ペーパートレード用の分離 DB と検証レポート生成ツール
- 環境設定ウィザード・設定検証 CLI、統一ロギング設定ユーティリティ

設計上のポイント
- 実運用（live）とペーパートレード（paper_trading）を環境変数 KABUSYS_ENV により切替可能。paper_trading は本番 DB と完全分離（data/paper_trading.db）。
- .env からの設定読み込みを自動で行う（プロジェクトルート検出により安全にロード）。
- 監視（Monitoring）は sqlite へログを保存し、Kill Switch により安全に ExecutionEngine を停止可能。
- OpenAI を使うモジュールは API キー必須で、失敗時はフェイルセーフ（例: スコアをスキップまたは 0 にフォールバック）。

主な機能一覧
----------------
- 実行 / モニタリング
  - run_execution.py: ExecutionEngine を起動（スレッドで実行・停止フラグ監視）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定）
- 設定・検証
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証（--strict オプションあり）
- ポートフォリオ構築
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py
- 研究（research）
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC、統計サマリ
- AI（ai）
  - news_nlp.py: ニュースを LLM で評価し ai_scores に書き込み
  - regime_detector.py: ETF の MA とマクロニュースで市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポート生成
- ユーティリティ
  - utils/logging_setup.py: 一貫したロギング設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定
- 永続化（監視）
  - monitoring_db.py: monitoring 用 SQLite テーブル初期化・読み書き API

セットアップ手順
----------------
前提
- Python 3.9+（プロジェクトの実行環境に合わせて）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（optional、validate_config の YAML 検証に使用）
  - （sqlite3 は標準モジュール）
- 推奨: 仮想環境（venv / poetry / pipenv 等）

1. リポジトリをクローンして Python 環境を作成
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt  （requirements.txt がある場合）

2. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または .env を手動作成（.env.example を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY を設定

3. 設定検証
   - python -m kabusys.validate_config
   - 厳格モード（警告があれば失敗にしたい場合）
     - python -m kabusys.validate_config --strict

4. DB / ディレクトリ
   - デフォルトで以下のパスを使用（.env で上書き可）
     - DuckDB: data/kabusys.duckdb（設定: DUCKDB_PATH）
     - SQLite (monitoring): data/monitoring.db（設定: SQLITE_PATH）
     - Paper trading SQLite: data/paper_trading.db（設定: PAPER_TRADING_SQLITE_PATH）
     - ログ: logs/<app>.log （LOG_DIR / LOG_LEVEL で設定）
   - 必要に応じて data/ や logs/ を作成（多くは起動時に自動作成）

使い方（起動例）
----------------
- ExecutionEngine を起動（通常）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録されます。live では実際に発注されますので十分注意してください。

- Monitoring を起動（ポーリング）
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path を使用（環境を問わず monitoring DB は本番パスで参照）

- Kill / Stop
  - ExecutionEngine を停止させたいときは data/kill.flag を書き込む（KillSwitch 経由で停止）
  - run_* スクリプトは data/stop_requested.flag を監視して自己終了する（運用上の停止方法）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

主要な環境変数（代表）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合必須）
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH: DB ファイルパス
- LOG_DIR, LOG_LEVEL: ログ出力先・レベル
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアする（0/1。production では 0 推奨）

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py            — ニュースセンチメント LLM 呼び出し
      - regime_detector.py     — 市場レジーム判定
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (※実装がある場合)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py      (MockBroker 等)
      - reconciler.py
      - risk_manager.py
    - utils/
      - logging_setup.py
      - process_priority.py

運用上の注意
-------------
- live モードは実際に発注が行われるため、設定（API パスワード、LINE 通知など）を必ず事前に確認してください。
- validate_config.py の警告やエラーは運用リスク低減に重要です。特に KABUSYS_ENV=live の場合は警告を慎重に確認してください。
- OpenAI API を使用する機能は外部呼び出しなので呼び出しコストとレート制限に注意してください。news_nlp.py や regime_detector.py はエラーハンドリングとリトライを備えていますが、API キー未設定時は ValueError を発生させます。
- run_monitoring と run_execution は stop_requested.flag（プロジェクト直下 data/stop_requested.flag）を確認して自身を終了します。安全に停止するためにこのフラグを利用できます。

開発・拡張のヒント
------------------
- DuckDB 接続を渡して純粋関数群（research や portfolio）をテスト可能にしています。ユニットテストで DuckDB の一時 DB を使うとよいです。
- logging_setup.setup_logging を各起動スクリプトの最初に呼び出してログを統一してください。
- process_priority.set_process_priority("high") が起動時に呼ばれるため、環境によっては権限不足で警告が出ることがあります（無害）。

ライセンス / バージョン
----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（存在する場合）。

おわりに
--------
この README はコードベースに含まれる主要モジュールと運用手順の概要を示しています。具体的な設定や運用フローは運用チームのルールに従ってください。質問や追加のドキュメントが必要なら教えてください。