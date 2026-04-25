README
======

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を目的とした Python パッケージです。
このリポジトリには、以下の主要機能が含まれます。

- ExecutionEngine（発注エンジン）起動スクリプト
- Monitoring（システム/注文/リスク監視）起動スクリプトと監視エンジン
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、リスク調整）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI 関連（ニュースの NLP スコアリング、市場レジーム判定）
- 各種ユーティリティ（ロギング設定、プロセス優先度設定、設定ウィザード、設定検証）
- 運用ツール（ペーパートレード検証レポート等）

主な機能一覧
--------------
- run_execution: 実際の発注エンジンを起動（KABUSYS_ENV により paper_trading と本番を切替）
  - paper_trading モードでは MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離
- run_monitoring: SystemMonitor をポーリングして system_status / trade_logs / risk_logs / dashboard 等を更新
  - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
- monitoring: SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager を束ねる MonitoringEngine
  - KillSwitch により条件を満たすと data/kill.flag を作成して ExecutionEngine を停止可能
- portfolio: 銘柄選択、重み付け、ポジションサイズ決定、セクター上限・レジーム補正
- research: DuckDB 接続を使ったファクター計算（Momentum / Volatility / Value 等）・IC 計算
- ai:
  - news_nlp: raw_news を LLM（OpenAI）でセンチメント評価し ai_scores テーブルへ保存
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースを組合せ市場レジームを判定・永続化
- tools:
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL レポートを作成
- utils: ロギング設定（ログは logs/<app>.log に日次ローテート）やプロセス優先度設定など
- 設定管理:
  - config_setup: 対話式に .env を生成/更新するウィザード
  - validate_config: .env と config/*.yaml を起動前に検証する CLI

セットアップ手順
----------------

1. Python 仮想環境の作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 本リポジトリの主要依存（参考）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証を行う場合）
   - sqlite3 は標準ライブラリ（追加インストール不要）

3. .env 作成（対話式推奨）
   - python -m kabusys.config_setup
     - ウィザードに従って入力するとプロジェクトルートに .env を作成します。
   - もしくは .env を手動で作成（下記「環境変数」参照）

4. 設定検証（起動前確認）
   - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

5. データディレクトリの確認
   - デフォルト DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - 必要なら .env で上書きしてください。

必須 / 推奨の環境変数（主なもの）
--------------------------------
- 必須（起動前に設定が必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
    - paper_trading: 発注はモック・DBは data/paper_trading.db を使用
    - live: 本番（注意して設定を行うこと）

- OpenAI（AI 機能を使う場合）
  - OPENAI_API_KEY

- ログ / DB / ファイルパス（オプション、デフォルトあり）
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト data/paper_trading.db）
  - LOG_LEVEL（デフォルト INFO）
  - LOG_DIR（デフォルト logs/）
  - PID_FILE_PATH（デフォルト data/execution.pid）
  - KILL_FLAG_PATH（デフォルト data/kill.flag）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）

使い方（起動・ツール）
---------------------

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - 標準起動:
    - python -m kabusys.run_execution
  - Paper trading モード起動例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止:
    - run_execution は data/stop_requested.flag の検知や KillSwitch による data/kill.flag を検出して停止します。
    - 強制的に停止するにはプロセスに SIGINT（Ctrl+C）を送るか、data/stop_requested.flag を作成してください。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring はプロセス優先度を高く設定し、monitoring DB を初期化してからポーリングします。
  - 監視ループの停止:
    - data/stop_requested.flag を作成すると run_monitoring が検知して終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 関連（プログラムから呼び出す）
  - ニューススコアリング（例）:
    - from kabusys.ai.news_nlp import score_news
      - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
      - score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キー（OPENAI_API_KEY）を必要とします。

運用メモ
-------
- ログ:
  - setup_logging により stdout と logs/<app>.log（日次ローテーション、30日保持）に出力します。
  - ログディレクトリが作成できない場合はコンソールのみで継続します。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に列がない場合は ALTER TABLE による追加を行います。

- Kill Switch / Stop Flag:
  - KillSwitch はリスク判定に基づいて data/kill.flag を作成します（ExecutionEngine はこれを検出して安全停止します）。
  - 管理者がプロセスを即時停止したい場合は data/stop_requested.flag を作成すると起動中ループが終了します。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ディレクトリ構成（主なファイル・モジュール）
----------------------------------------
- src/
  - kabusys/
    - __init__.py
    - run_execution.py            — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — SystemMonitor ポーリングスクリプト
    - config.py                  — 環境変数・設定読み込みロジック
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 設定検証 CLI
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py          (参照はコード内にあります)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py         (参照はコード内にあります)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
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
    - data/                      — データファイル（DB・PID・フラグ等）を配置するディレクトリ（プロジェクトルート直下）
    - logs/                      — ログファイル置き場（デフォルト）
  - config/
    - *.yaml                     — system_config.yaml 等（存在しない場合は警告。generate script があれば生成可能）

補足 / 注意事項
--------------
- 本パッケージは本番発注ロジック（kabuステーション等）を含むため、KABUSYS_ENV を live にした状態での起動は十分に注意して行ってください。
- .env は機密情報（API キーやパスワード）を含むため絶対に Git にコミットしないでください。
- AI 機能を利用する場合は OpenAI の利用制限やコストに注意してください。API エラー時はフェイルセーフで処理を続行する実装になっていますが、想定外の挙動が出ることがあります。
- テストや開発では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを抑制できます。

以上。必要であればセクションごとのコマンド例や .env のサンプルを追加できます。どの部分を詳細に拡張しますか？