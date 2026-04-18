KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買 / 研究用ライブラリ群です。  
このリポジトリには、以下の主要機能を提供するモジュールが含まれます。

- ExecutionEngine（発注実行 / ペーパートレード）起動スクリプト
- Monitoring（システム・取引・リスク監視）ポーリング実装
- ポートフォリオ構築 / ポジションサイズ決定の純粋関数群
- リサーチ（ファクター計算・特徴量探索）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 環境設定ウィザード・設定検証ツール
- 運用支援ツール（Paper Trading 検証レポート等）

この README はこのコードベースの利用開始手順、使い方、ディレクトリ構成をまとめたものです。

主な機能一覧
-------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker で data/paper_trading.db を使用。
  - run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔を上書き可能（デフォルト 60 秒）。
- 設定管理
  - config_setup.py: .env を対話式に作成 / 更新するウィザード。
  - validate_config.py: 起動前に .env と config/*.yaml の妥当性チェックを行う CLI。
- 監視
  - monitoring/*: system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db（SQLite ベースの永続化）。
  - kill.flag による ExecutionEngine 停止（Kill Switch）サポート。
- 発注 / リスク管理（実行系）
  - execution/*（BrokerFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等） — 実装ファイルはこの README の一覧に含まれる設計に従って動作します。
- ポートフォリオ構築
  - portfolio/*: 銘柄選定、重み算出、セクター制限、ポジションサイズ計算（等金額・スコア加重・リスクベース）。
- リサーチ
  - research/*: ファクター（Momentum/Value/Volatility 等）計算、将来リターン計算、IC 計算、統計サマリー。
- AI
  - ai/news_nlp.py: raw_news を集約して OpenAI (gpt-4o-mini) でセンチメントを算出し ai_scores に書き込む。バッチ・リトライ・レスポンス検証を実装。
  - ai/regime_detector.py: ETF 1321 の MA とマクロニュースの LLM センチメントを合成して市場レジーム判定。
- ユーティリティ
  - utils/logging_setup.py: stdout と日次ローテーションログを統一的に設定。
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ。

前提・依存
-----------
必須（運用に応じて追加で必要になる可能性あり）:
- Python 3.10+
- pip
- パッケージ例:
  - duckdb
  - psutil
  - openai
  - (任意) PyYAML — validate_config の YAML 検証に使用

例（推奨インストール）:
  pip install duckdb psutil openai PyYAML

セットアップ手順
----------------

1. リポジトリをクローン / 展開する
   - プロジェクトルート（pyproject.toml または .git が存在するディレクトリ）が自動的に検出されます。

2. Python 環境を準備
   - Python >= 3.10 を有効にした仮想環境を作成・有効化し、必要パッケージをインストールします。

3. .env 作成（対話式ウィザード）
   - 初期設定を行うには:
     python -m kabusys.config_setup
   - これにより .env が生成されます（.env は絶対に Git にコミットしないでください）。

4. 設定検証
   - 作成後、設定を検証します:
     python -m kabusys.validate_config
   - 本番で警告も失敗にしたい場合:
     python -m kabusys.validate_config --strict

5. データディレクトリ（logs / data 等）の確認
   - デフォルトのパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading DB: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要なら .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_DIR を上書きしてください。

使い方（運用 & 開発）
-------------------

起動スクリプト
- 監視ループ起動（SystemMonitor を定期実行）:
  - MONITOR_POLL_INTERVAL 環境変数で秒数を指定可能（例: 30 秒）
  - 実行:
    python -m kabusys.run_monitoring
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します。

- Execution エンジン起動:
  - KABUSYS_ENV に依存:
    - paper_trading: MockBrokerClient を使用し、paper_trading 用 DB(data/paper_trading.db) に記録
    - live: 実ブローカークライアントを使用（事前に設定必須）
  - 実行:
    python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成して優雅に停止させる
    - または monitoring の Kill Switch が data/kill.flag を書き込むと Execution 側で検出して停止します

ログ
- setup_logging により stdout とファイル（logs/<app_name>.log）に出力されます。
- LOG_LEVEL / LOG_DIR は .env で設定可能（デフォルト INFO / logs/）。

環境変数の主な設定
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH: DB ファイルパス
- OPENAI_API_KEY: ai/news_nlp.py / regime_detector で使用
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 本番では 0 推奨（起動時に kill.flag を自動消去するか）

ツール（CLI）
- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db
  - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ など

プログラムからの利用例（ライブラリ用途）
- AI スコア付与をプログラムから呼ぶ:
  from kabusys.ai import score_news
  score_news(conn, date(2026,4,1), api_key="sk-...")

- リサーチ関数:
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  results = calc_momentum(duckdb_conn, target_date)

注意事項（運用上のポイント）
- KABUSYS_ENV=live の場合は各 API トークン / パスワードなどを慎重に管理してください。
- Kill Switch（data/kill.flag）は本番で重要な安全弁です。KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨します。
- paper_trading モードでは本番 DB と完全に分離された paper_trading.db に書き込みます。
- OpenAI API 呼び出しはコストとレイテンシが発生します。OPENAI_API_KEY の設定・レート制御に注意してください。

ディレクトリ構成
----------------
（抜粋。実際のファイルは src/kabusys 配下にあります）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py       — （trade 関連監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
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

付録: よく使うコマンドまとめ
---------------------------
- .env 作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視起動:
  python -m kabusys.run_monitoring

- 実行エンジン起動:
  python -m kabusys.run_execution

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

お問い合わせ / 貢献
-------------------
- 本リポジトリの改善・バグ報告・機能追加等は PR を歓迎します。README や docstring の指示に従ってください。

以上。運用やローカルで動かす際の不明点があれば、実行環境（OS / Python バージョン / .env の主要設定）を添えて質問してください。