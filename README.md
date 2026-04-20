README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のための Python ライブラリ群です。  
主な機能は以下の通りです:

- 発注実行エンジン（ExecutionEngine） — 本番/ペーパートレード対応
- 監視（Monitoring） — システム状態・注文ログ・リスク監視
- ポートフォリオ構築ユーティリティ（候補選定・重み・株数決定）
- リサーチ（ファクター計算・特徴量解析）
- AI 支援モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 運用用 CLI: .env ウィザード、設定検証、検証レポート生成 等

設計上のポイント
- 設定は .env / 環境変数で管理。自動でプロジェクトルートの .env を読み込みます（必要な場合は無効化可能）。
- Paper Trading 環境は本番 DB と分離（デフォルト: data/paper_trading.db）。
- ログはコンソールと日次ローテーションログ（logs/<app>.log）に出力。
- OpenAI を用いる機能は OPENAI_API_KEY を参照して動作（未設定時は例外またはフェイルセーフ挙動）。

機能一覧
--------
- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録します。
  - 起動時にプロセス優先度を High に設定し、停止フラグ（data/stop_requested.flag）で終了できます。
- run_monitoring.py
  - SystemMonitor をポーリングして system_status / trade_logs / risk_logs / dashboard などを維持します。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
- config_setup.py
  - 対話式ウィザードで .env を作成 / 更新します（必須環境変数の入力を促します）。
- validate_config.py
  - .env と config/*.yaml（存在する場合）を検証。--strict で警告を FAIL 扱いにできます。
- tools/paper_verification_report.py
  - ペーパートレード DB を集計し、稼働率・約定率・レイテンシ等の検証レポートを生成します。
- portfolio/*
  - 銘柄選定（select_candidates）、重み計算（等金額・スコア加重）、株数決定（calc_position_sizes）、
    セクター制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）
- research/*
  - DuckDB 上の prices_daily/raw_financials を参照してモメンタム/ボラティリティ/バリュー等のファクターを計算。
  - 特徴量探索、将来リターン・IC 計算ユーティリティを提供。
- ai/*
  - news_nlp: raw_news をまとめて LLM（OpenAI）に投げ、銘柄ごとのセンチメントを ai_scores に書込む。
  - regime_detector: ETF の MA とマクロセンチメントを合成して market_regime を算出・永続化。
- monitoring/*
  - MonitoringDB（SQLite を用いた永続化層）、SystemMonitor/TradeMonitor/RiskMonitor、KillSwitch、MonitoringEngine、AlertManager 等
- utils/*
  - ロギングセットアップ（setup_logging）、プロセス優先度設定（set_process_priority）等のユーティリティ

セットアップ手順
----------------

1. 推奨 Python バージョン
   - Python 3.10 以上（型ヒントと構文から推奨）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - pyyaml (config/*.yaml の検証を行う場合に任意)
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt があればそれを利用してください）

4. .env の作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要な設定:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（KABUSYS_ENV=paper_trading 時）
     - LOG_LEVEL / LOG_DIR

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - デフォルトで使用するディレクトリ（data/, logs/）は多くのスクリプトで自動作成されますが、権限等に注意してください。

使い方
------

基本的な起動例

- ExecutionEngine を起動（本番 / 開発 / ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 実行中に停止したい場合はプロジェクトルートの data/stop_requested.flag を作成してください（スクリプトが検知してエンジンを停止します）。
  - 起動時に既存の stop フラグがあれば起動せず終了します。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定できます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視プロセスも data/stop_requested.flag を参照して安全終了します。
  - Monitoring は Settings.sqlite_path（監視用 DB）を本番パスとして使用します（環境にかかわらず）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別の DB パスを指定できます。環境変数 PAPER_TRADING_SQLITE_PATH が設定されている場合はそちらを優先します。

- AI 機能
  - news_nlp / regime_detector は OpenAI API を呼び出します。事前に OPENAI_API_KEY を環境変数に設定してください。
  - 例（Python から直接呼ぶ）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=os.environ.get("OPENAI_API_KEY"))

停止・Kill Switch
- 実行を外部から止めるにはプロジェクトの data/stop_requested.flag を作成します（run_execution/run_monitoring はこれを監視して優雅に終了します）。
- KillSwitch（自動的に評価される監視コンポーネント）は必要に応じて data/kill.flag を作成します。KILL_FLAG_CLEAR_ON_START を 1 に設定すると起動時に自動的にクリアされますが、本番では 0 を推奨します。

ログ
- setup_logging により stdout と logs/<app_name>.log（日次ローテーション）が出力されます。
- LOG_DIR 環境変数でログ保存先を指定可能、LOG_LEVEL で出力レベルを設定します。

環境変数一覧（主要）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — 振る舞い分岐
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)
- OPENAI_API_KEY (AI 機能を使う場合)
- MONITOR_POLL_INTERVAL (run_monitoring 用、秒)
- KILL_FLAG_CLEAR_ON_START (0/1, 本番は 0 推奨)

ディレクトリ構成（主要ファイル）
------------------------------

src/
  kabusys/
    __init__.py
    config.py                 # 設定読み込み・Settings
    config_setup.py           # .env 対話ウィザード
    validate_config.py        # 設定検証 CLI

    run_execution.py          # ExecutionEngine 起動スクリプト
    run_monitoring.py         # Monitoring ポーリング起動スクリプト

    utils/
      logging_setup.py        # ログの統一セットアップ
      process_priority.py     # プロセス優先度 / CPU affinity

    execution/                # （発注周りの実装群）
      broker_factory.py
      execution_engine.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py

    monitoring/
      monitoring_db.py        # SQLite 永続化層
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    research/
      factor_research.py
      feature_exploration.py

    ai/
      news_nlp.py             # ニュース NLP（OpenAI）
      regime_detector.py

    tools/
      paper_verification_report.py

data/                # 実行時に使用する DB / フラグファイル（デフォルト）
  monitoring.db
  paper_trading.db
  kabusys.duckdb
  stop_requested.flag
  kill.flag
  execution.pid

logs/                # デフォルトログ出力先（setup_logging で自動作成）

注意事項 / 運用上のヒント
------------------------
- 本番環境（KABUSYS_ENV=live）の場合は特に環境変数（API キー・LINE 通知先等）を慎重に設定してください。validate_config の live 用チェックが警告を出します。
- Kill Switch / stop フラグの挙動をきちんと理解しておくと安全に運用できます。KILL_FLAG_CLEAR_ON_START=1 は開発時の利便性向上のためのオプションで、本番での自動クリアは危険です。
- DuckDB / SQLite のファイルパスは環境変数で上書きできます。運用時は適切にバックアップ / マウントを検討してください。
- OpenAI を使う処理はレート制限や API 障害を考慮しリトライ・フェイルセーフ実装がありますが、API キーの費用管理を行ってください。

貢献 / 変更
------------
- 仕様変更や追加機能を実装する場合は、まず config/*.yaml（存在するなら）や .env.example を更新してください。
- DB スキーマ変更時は monitoring_db.init_monitoring_db の移行処理を拡張してください（既存コードにいくつかのマイグレーション例あり）。

以上。必要に応じて README の補足（インストールコマンド列挙、CI 設定、systemd サービス定義例 など）を追加できます。希望があれば環境別の運用手順や systemd 起動例も作成します。