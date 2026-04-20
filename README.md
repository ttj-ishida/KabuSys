KabuSys — 日本株自動売買システム（簡易 README）
=================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
主要コンポーネントとして以下を提供します。

- ExecutionEngine：発注・オーダー管理・リスク管理を担うエンジン（paper_trading と live をサポート）
- Monitoring：システム稼働状況、オーダー状況、リスク（ドローダウン等）を監視してアラート／Kill Switch を管理
- Portfolio モジュール：銘柄選定、重み計算、ポジションサイズ算出（純粋関数群）
- Research/AI モジュール：ファクター計算・特徴量解析、ニュースセンチメント（OpenAI）によるスコアリング、レジーム判定
- Tools：ペーパートレードの検証レポート生成などのユーティリティ

本リポジトリは「ロジック層」「監視」「運用ユーティリティ」「設定管理」等を含む単体の自動売買基盤を意図しています。

主な機能一覧
-------------
- 環境設定ウィザード（.env 作成 / 更新）: kabusys.config_setup.run_wizard（python -m kabusys.config_setup）
- 設定検証 CLI：環境変数 / config/*.yaml の検証（python -m kabusys.validate_config）
- Execution 起動スクリプト：発注エンジンを別スレッドで起動（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し DB を分離
- Monitoring 起動スクリプト：定期ポーリングで各種モニタを実行（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）
- 監視永続化：SQLite ベースの monitoring DB（system_status, trade_logs, positions, risk_logs, dashboard）
- Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- Portfolio 構築ユーティリティ：候補選定、重み計算、ポジションサイズ算出、セクター上限、レジーム乗数
- Research：モメンタム/ボラティリティ/バリュー等のファクター計算、IC/統計サマリ
- AI：ニュースから銘柄別センチメントを生成（OpenAI 使用）、市場レジーム判定

前提 / 依存
------------
（環境や実行目的に応じて取捨選択してください）
- Python 3.9+
- パッケージ（主要）:
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（config/*.yaml の厳密チェックを行う場合に推奨）
- SQLite は標準ライブラリで利用
- ログ出力は logs/ に日次ローテートで保存（ディレクトリ作成権限が必要）

セットアップ手順
----------------
1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （実際は requirements.txt があれば pip install -r requirements.txt）
4. 初期設定（.env）を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参照）
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト development
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用の分離 DB、デフォルト data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR など
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を使うと警告も失敗扱いになります

使い方（主要コマンド）
--------------------
- ExecutionEngine 起動（本番／ペーパー共通）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用
    - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します
    - 実行中は data/execution.pid に PID を書きます

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境変数で上書き可能（秒単位）
  - 監視は常に本番用 sqlite_path を使用します（環境にかかわらず）
  - 停止フラグはプロジェクト下 data/stop_requested.flag を参照

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する例:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI / Research 呼び出し（例: Python REPL）
  - DuckDB 接続例:
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.ai import score_news
    - score_news(conn, datetime.date(2026,4,1))  # OpenAI API key は環境変数 OPENAI_API_KEY か引数で渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, datetime.date(2026,4,1))

重要なファイル・挙動メモ
-----------------------
- .env は絶対にリポジトリにコミットしないこと（機密情報を含む）
- stop/kill フラグ:
  - data/stop_requested.flag : run_monitoring / run_execution が監視する停止フラグ（停止要求）
  - data/kill.flag : KillSwitch が書き込むフラグ（ExecutionEngine に停止を促す）
- PID ファイル:
  - data/execution.pid（ExecutionEngine が使用）
- MONITOR_POLL_INTERVAL: run_monitoring で使用、秒単位（デフォルト 60）
- ログ: logs/<app_name>.log に日次ローテート（30日分）で保存

ディレクトリ構成（抜粋）
---------------------
プロジェクトの主要なディレクトリ／ファイル構成の例（src/kabusys を基準に抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py               # 環境変数 / Settings 管理（.env 自動読み込み）
    - config_setup.py         # .env 対話式ウィザード
    - validate_config.py      # 設定検証 CLI
    - run_execution.py        # ExecutionEngine 起動スクリプト
    - run_monitoring.py       # Monitoring 起動スクリプト
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (参照)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py

（実際のリポジトリにはさらにモジュールや補助ファイルが含まれます）

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では設定ミスが重大な影響を与えるため validate_config を必ず実行し、LINE 通知などアラート経路を確認してください。
- process_priority の設定は psutil を利用し OS によって制約があり、権限不足では警告となります。
- OpenAI API を利用する際はコストやレート制限に注意してください。news_nlp と regime_detector はリトライや失敗時のフォールバックを備えていますが、キーや課金状態は運用者側で管理してください。
- Paper Trading（ペーパー）モードは DB を分離しています。実運用での誤発注を防ぐため KABUSYS_ENV の切り替えに注意してください。

貢献 / 拡張
------------
- 追加のブローカークライアントは execution/broker_factory.py にプラグインする形で実装可能
- Portfolio、Research、AI モジュールは純粋関数ベースで書かれているのでユニットテストや差し替えが容易です
- config/*.yaml（strategy_config 等）を用いた外部設定化が想定されています（validate_config でチェック）

サポート
--------
不明点や実行時の問題があれば、該当モジュールのログ（logs/）と .env を確認のうえ、エラーログやスタックトレースを含めて問い合わせてください。

---
この README はソースツリーの主要機能と使い方に焦点を当てた簡易ドキュメントです。詳しい設計やアルゴリズム（PortfolioConstruction.md 等の設計資料）が別途ある場合はそちらも参照してください。