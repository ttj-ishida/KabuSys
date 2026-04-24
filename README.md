README
======

概要
----
KabuSys は日本株向けの自動売買システムのライブラリ／実行スクリプト群です。本リポジトリは次のような機能を含み、実運用・ペーパートレード・研究用途の共存を想定した設計になっています。

- シグナル生成・ポートフォリオ構築（portfolio）
- ポジションサイズ計算・リスク調整（position_sizing / risk_adjustment）
- ExecutionEngine（発注実行ロジック）と Broker クライアントの抽象化（execution）
- 監視コンポーネント（system / trade / risk）と Kill Switch（monitoring）
- DuckDB を用いたリサーチ／ファクター計算（research）
- OpenAI を利用したニュース NLP / レジーム判定（ai）
- 各種 CLI ユーティリティ（設定ウィザード・設定検証・レポート生成）
- ロギング／プロセス優先度などのユーティリティ（utils）

主な設計方針：
- 本番用データベースとペーパートレード用 DB を分離（KABUSYS_ENV による切替）
- .env による設定をサポートし、自動ロード機能あり（無効化も可能）
- DuckDB/SQLite をデータ永続層に利用
- フェイルセーフ重視（API 障害の際はフォールバックやスキップする設計）

機能一覧
--------
- 実行系
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を使用）
- 監視系
  - run_monitoring.py: SystemMonitor をポーリング実行（MONITOR_POLL_INTERVAL で間隔変更可）
  - 各種 Monitor（system / trade / risk）と MonitoringEngine、KillSwitch、監視用 DB（SQLite）用意
- 設定
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証ツール（--strict オプションあり）
- 研究・分析
  - research モジュール: ファクター計算、特徴量解析（DuckDB 前提）
- AI（OpenAI）
  - ai.news_nlp.score_news: ニュースのセンチメントを LLM で評価して ai_scores に保存（OPENAI_API_KEY 必須）
  - ai.regime_detector.score_regime: マクロ＋ETF MA を使った市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成（DB を読み取って指標を算出）
- 共通ユーティリティ
  - utils.logging_setup.setup_logging: 一貫したログ出力設定（コンソール + ローテートファイル）
  - utils.process_priority.set_process_priority: プラットフォームに依存しない優先度設定

セットアップ手順
--------------
1. Python 環境を用意
   - Python 3.9+ を推奨
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 本リポジトリに requirements.txt は含まれていないため、最低限次のパッケージをインストールしてください:
     - duckdb
     - psutil
     - openai (ai 機能を使う場合)
     - PyYAML（validate_config の YAML 検証を行いたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. 環境変数設定 (.env)
   - リポジトリルートに .env を置くか、環境変数で設定してください。
   - 自動ロード: config.py はプロジェクトルート（.git または pyproject.toml を探索）を検出できれば自動で .env / .env.local を読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数とデフォルト:
     - 必須:
       - JQUANTS_REFRESH_TOKEN (必須)
       - KABU_API_PASSWORD (必須)
     - 任意/デフォルト:
       - KABUSYS_ENV: development | paper_trading | live (default: development)
       - DUCKDB_PATH: data/kabusys.duckdb
       - SQLITE_PATH: data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (ペーパートレード専用 DB)
       - LOG_LEVEL: INFO
       - LOG_DIR: logs
       - OPENAI_API_KEY: OpenAI を使う場合必須（ai.score_news, regime_detector）
       - PAPER_FILL_MODE: instant | partial | never | reject (paper_trading の埋め方)
       - その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）

   - .env を対話的に作るには:
     - python -m kabusys.config_setup

4. DB ファイル / ディレクトリ
   - デフォルトのパスは上記の通り（data/kabusys.duckdb、data/monitoring.db、data/paper_trading.db）。
   - 初回起動時に必要ディレクトリが自動作成されるケースがあります（ログディレクトリ、data/ 等）。
   - run_* スクリプトは起動時に必要なテーブルを初期化します（init_monitoring_db を使用）。

使い方
------
- 設定検証
  - python -m kabusys.validate_config
  - 警告を厳格に扱う場合: python -m kabusys.validate_config --strict

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
  - オプション: --env-file を指定して別パスに保存可能

- 監視モード起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60 秒）
    - 停止: プロジェクトルート/data/stop_requested.flag ファイルが検出されるとループを終了
    - ロギング: setup_logging を使って logs/ に日次ローテートログを出力

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込み
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了
    - 実行中に stop_requested.flag が作られるとエンジンに停止シグナルを送り終了
    - 実行中は data/execution.pid に PID（デフォルトパス）を書く設計を想定

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 出力: 稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・P95）等のサマリと PASS/FAIL 判定

- AI 機能（OpenAI 必須）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY を環境変数に設定するか、api_key を渡してください
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同上
  - 注意: API 呼び出しはリトライやフォールバック（失敗時はスコア 0 など）を行う設計ですが、API キーが未設定だと ValueError が発生します

- ログ設定
  - 簡単に一貫したログを得るには setup_logging(app_name="execution") 等を呼び出してください
  - 環境変数 LOG_DIR でログ出力先を変更可能（デフォルト logs/）
  - LOG_LEVEL で出力レベルを設定

- 停止 / Kill Switch
  - 実行エンジンの停止トリガー:
    - 管理者が手動で停止したい場合: プロジェクトルート/data/stop_requested.flag を作成すると run_execution / run_monitoring は停止処理を行います
    - Kill Switch（監視モジュール）がトリガーすると data/kill.flag が作られ、ExecutionEngine はそれを検出して停止する想定（設定により自動クリアを無効化可）

ディレクトリ構成
----------------
以下は本リポジトリ内の主なファイル/ディレクトリ（src/kabusys 以下）です。実際のツリーは変更される可能性がありますが、主要モジュールは次の通りです。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数読み込み・Settings
    - config_setup.py          # .env 対話ウィザード
    - validate_config.py       # 設定検証 CLI
    - run_execution.py         # ExecutionEngine 起動スクリプト
    - run_monitoring.py        # SystemMonitor 起動スクリプト
    - data/                    # （別パッケージ想定）データ/DB 関連（実装は別ファイル）
    - execution/
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
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

補足・運用上の注意
-----------------
- 環境（KABUSYS_ENV）が live の場合は本番 DB を破壊しないように注意して設定を行ってください。validate_config は live に対する警告を出します。
- .env は機密情報（API トークン）を含むため、決して Git にコミットしないでください。
- run_execution / run_monitoring は psutil によるプロセス優先度設定やディスク使用率取得など OS 依存の機能を使います。権限やプラットフォーム互換に気を付けてください。
- OpenAI API を利用する機能は API コストが発生します。キーの管理と呼び出し頻度に注意してください。
- DuckDB / SQLite のファイルパスは設定で変更できます。バックアップや権限に注意してください。

ライセンス / バージョン
-----------------------
パッケージバージョンは kabusys.__version__ = "0.1.0" に定義されています。ライセンス情報はリポジトリに含まれる LICENSE ファイル等を参照してください（本コードスニペットからはライセンス情報は得られません）。

お問い合わせ / 開発
-------------------
開発者向けには、まず仮想環境を作成し必要パッケージをインストール、.env を作成してから validate_config を実行して問題がないことを確認してください。ユニットテストや CI の整備、requirements.txt の追加を推奨します。

以上。必要であれば README に「セットアップスクリプト例（Docker Compose や systemd ユニット）」や「よくあるトラブルシュート」などの追記を行います。どの項目を詳しく追加しますか？