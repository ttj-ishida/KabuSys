KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部を提供する Python パッケージです。  
主に以下の機能を含みます。

- 発注・実行エンジン（ExecutionEngine）
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・株数計算）
- 研究（ファクター計算・特徴量探索）
- AI 支援（ニュース NLP によるセンチメント評価・レジーム検出）
- 運用ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート）

本 README はリポジトリ内の主要スクリプトとモジュール（src/kabusys/*）に基づいた使い方・セットアップ説明を記載しています。

主な機能一覧
--------------
- Execution
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBroker を使用して paper_trading DB（data/paper_trading.db）へ記録。
  - Broker クライアントファクトリ、OrderManager、RiskManager、Reconciler を組み合わせて発注ワークフローを実行。
- Monitoring
  - run_monitoring.py: SystemMonitor のポーリングループを起動。システム状態・データ鮮度・プロセス稼働を監視。
  - MonitoringEngine: 各モニタを束ねて定期チェック、KillSwitch 評価、アラート送信（AlertManager 経由）。
  - MonitoringDB: SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）。
  - KillSwitch: 指定条件で data/kill.flag を書き込み、ExecutionEngine を停止させる仕組み。
- Portfolio（純粋関数）
  - 候補選定、等金額/スコア重み、セクター制限、レジーム乗数、株数計算（単元丸め・資金制約対応）。
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）、将来リターン、IC 計算、統計サマリー。
  - DuckDB 接続を受けて SQL / Python の組み合わせで高速に計算。
- AI
  - news_nlp.score_news: raw_news をまとめて OpenAI（gpt-4o-mini など）に投げ、銘柄別センチメントを ai_scores テーブルへ書き込み。
  - regime_detector.score_regime: ma200 とマクロニュース（LLM）を合成して market_regime を作成。
  - OpenAI API の呼び出しは堅牢なリトライ・バリデーションロジックを備える。
- ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: Paper Trading の検証レポート生成

前提・環境変数（主要）
--------------------
必須（少なくとも実行時に設定が必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（Settings.jquants_refresh_token）
- KABU_API_PASSWORD — kabuステーション API パスワード

主要オプション / 動作に影響する環境変数:
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、Execution は paper_trading DB を使用（本番 DB と分離）。
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR: ログ保存先（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で使用
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- KILL_FLAG_* 関連:
  - Settings.kill_flag_path（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリア（本番では推奨しない）

セットアップ手順
----------------
以下は一般的な開発・実行環境の手順です（パッケージ配布方法等に依存します）。

1. Python 仮想環境の作成
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージのインストール
   - pip install -r requirements.txt
     （このリポジトリに requirements.txt がない場合は必要なライブラリを個別にインストールしてください: duckdb, psutil, openai, PyYAML(任意), など）

3. プロジェクトルートに data / logs 等のディレクトリを作成（多くのコードが起動時に自動作成しますが、権限や運用上先に準備すると安心です）
   - mkdir -p data logs

4. 環境変数設定
   - 対話式に .env を作る:
     - python -m kabusys.config_setup
   - 設定を検証:
     - python -m kabusys.validate_config
     - 本番用チェックは --strict を付与して警告も失敗扱いにできます

5. DB 初期化
   - run_execution / run_monitoring 起動時に必要テーブルが自動作成されます（monitoring_db.init_monitoring_db を経由）。

使い方
-------
実行スクリプト（モジュール実行）:

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 本番厳格チェック: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作環境をペーパートレードに切り替える例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止方法:
    - 実行中のプロセスは data/stop_requested.flag の存在を監視しており、フラグ作成で安全に停止できます。
    - KillSwitch が動作した場合は data/kill.flag に理由が書き込まれ、エンジンは停止する/起動を抑制します。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止方法:
    - data/stop_requested.flag を作成すると監視ループが終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

AI 関連:
- news_nlp.score_news / regime_detector.score_regime は OPENAI_API_KEY の設定が必要です（引数で API キーを渡すことも可能）。
- LLM 呼び出しは堅牢なリトライとレスポンスバリデーションを実装していますが、API 利用料やレート制限等に注意してください。

ログ
----
- setup_logging() で logs/<app_name>.log に日次ローテーションでログを出力します（デフォルト: logs/）。  
- コンソール出力は stdout に出します（cron / systemd 等での出力リダイレクトに配慮）。

運用上の注意
--------------
- KABUSYS_ENV=live のときは設定（特に LINE の通知設定、KILL_FLAG_CLEAR_ON_START 等）を慎重に確認してください。validate_config.py は本番向けの注意喚起を出します。
- paper_trading は本番 DB と分離される設計ですが、環境変数やパスの設定ミスには注意してください。
- KillSwitch（data/kill.flag）を使うと ExecutionEngine を緊急停止できます。ファイル存在チェックは冪等で行われます。
- run_execution / run_monitoring は起動時にプロセス優先度を「high」に設定しようとしますが、権限不足等で設定に失敗する場合は警告となりスキップされます。

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 以下の主要ファイル／パッケージ構成（抜粋）です。実際のリポジトリにはさらにファイルが存在する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト

  - execution/                — 発注関連（OrderManager, RiskManager, Engine 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    ...

  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, ...）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    ...

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

  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

データファイル / フラグ（運用上重要）
-----------------------------------
- data/monitoring.db            — 監視 SQLite DB（デフォルト）
- data/paper_trading.db         — ペーパートレード用 SQLite（paper_trading モード）
- data/kabusys.duckdb           — DuckDB（分析テーブル）
- data/stop_requested.flag      — run_* のポーリングループを安全に停止するためのフラグ
- data/kill.flag                — KillSwitch が書き込む緊急停止フラグ
- data/execution.pid            — ExecutionEngine が書き込む PID ファイル（設定により変わる）

開発者向け補足
--------------
- DuckDB / SQLite のスキーマはコード内で自動作成・マイグレーションします（monitoring_db.init_monitoring_db）。
- AI 関連のユニットテストは OpenAI 呼び出し部分を差し替え（モック）可能なように _call_openai_api を分離しています。
- 研究モジュールは DuckDB の prices_daily / raw_financials 等のテーブルを前提にしています。データ投入手順は別ドキュメントを参照してください。

ライセンス / 貢献
-----------------
この README はコードベースの説明に限定しています。実際のライセンス表記や貢献ルールはリポジトリの LICENSE / CONTRIBUTING.md を参照してください。

最後に
------
この README はリポジトリ内の主要コードを元に手早く運用・開発を始められるようにまとめたものです。詳細な運用手順・設計書（PortfolioConstruction.md, StrategyModel.md 等）がプロジェクトに含まれている場合、それらも必ず参照してください。質問や追加のドキュメント生成が必要であればお知らせください。