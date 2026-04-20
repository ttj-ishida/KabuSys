KabuSys — 日本株自動売買システム（簡易 README）
======================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視を目的とした Python 製モジュール群です。本リポジトリは以下の主要機能を含みます。

- ExecutionEngine の起動スクリプト / 注文管理（実発注・ペーパートレード対応）
- 監視（System / Trade / Risk）用モジュールと常駐ポーリングスクリプト
- ポートフォリオ構築・位置サイズ決定などの純粋関数群（バックテスト／生成ロジック用）
- ファクター計算・特徴量探索（DuckDB を用いたオンデータ計算）
- ニュース NLP / レジーム判定（OpenAI を用いた LLM スコアリング）
- 各種ユーティリティ（ログ設定・プロセス優先度設定・設定ウィザード）
- 運用支援ツール（ペーパートレード検証レポート等）

主な機能一覧
--------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBroker を利用し data/paper_trading.db に記録。
  - run_monitoring.py: 各種モニター（System / Trade / Risk）をポーリングして監視ログを永続化・アラート判定。
- 設定管理
  - config_setup.py: .env を対話式に作成・更新するウィザード。
  - validate_config.py: .env と config/*.yaml の基本検証 CLI。
- 監視
  - monitoring/ : system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_engine, monitoring_db（SQLite ベース）
  - Kill Switch により致命的なリスク（ドローダウン過大、ポジション過多等）で Execution を停止可能。
- ポートフォリオ
  - portfolio/ : 候補選定、重み算出、セクター制限、位置サイズ計算（単元株丸め・資金配分ロジック）
- 研究用
  - research/ : ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリ等（DuckDB 利用）
- AI
  - ai/news_nlp.py: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に書き込む。
  - ai/regime_detector.py: ETF の MA 乖離と LLM マクロセンチメントを合成して日次レジーム判定を実施。
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して PASS/FAIL レポートを出力。

前提（主な依存）
----------------
最低限必要なパッケージ（代表例）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を利用する場合）
- PyYAML（validate_config の YAML 検証を有効にする場合）

インストール例（仮想環境推奨）:
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリに移動。

2. 仮想環境を作成して依存をインストール（上記参照）。

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 環境変数 KABUSYS_ENV は以下いずれか: development / paper_trading / live
     - Paper Trading を使う場合は KABUSYS_ENV=paper_trading を選択（DB は data/paper_trading.db に分離）
   - 生成した .env は絶対に Git にコミットしないこと。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳格扱いする場合は --strict を付けます。

5. データディレクトリの準備
   - デフォルトの DB / ログ / PID / フラグパスは data/ と logs/ 下です。必要に応じて先に作成してくださいが、コードは自動作成する箇所があります。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development) — development / paper_trading / live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db) — 監視 DB（monitoring は常に本番 sqlite_path を使います）
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 専用 DB
- PAPER_FILL_MODE (default: "instant") — instant | partial | never | reject
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- OPENAI_API_KEY (AI 機能を使う場合)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒。デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (0/1) — 本番では 0 推奨

使い方（起動例）
----------------
- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動:
  - 環境変数で本番/ペーパーを切り替え:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 実行時、プロセス優先度を "high" に設定します。ペーパートレードは data/paper_trading.db を使用します。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - 実行中は data/execution.pid に PID を書きます。

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL で間隔を指定可能（秒、デフォルト 60）。
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
  - 監視は監視用 SQLite（settings.sqlite_path）と DuckDB を使用します。Monitoring は環境にかかわらず本番 sqlite_path を使用します。
  - 停止方法: data/stop_requested.flag を作成するとループが終了します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

Kill Switch / 停止フロー
------------------------
- KillSwitch（kabusys.monitoring.kill_switch）は RiskMonitor 等の結果に基づいて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に自動クリアされます（本番では 0 推奨）。
- run_execution/run_monitoring は data/stop_requested.flag を使って安全に停止できます（手動で作成/削除して制御）。

ログ
----
- ログは標準出力とファイル両方に出力されます（kabusys.utils.logging_setup.setup_logging）。
- デフォルトのログディレクトリ: logs/
- 各アプリケーションは logs/<app_name>.log に日次ローテーション（30 日保持）で出力されます。
- 例: logs/execution.log, logs/monitoring.log

ディレクトリ構成（主なファイル）
--------------------------------
src/
  kabusys/
    __init__.py
    config.py                # 環境変数・設定読み込みユーティリティ
    config_setup.py          # .env 対話式ウィザード
    validate_config.py       # 設定検証 CLI
    run_execution.py         # ExecutionEngine 起動スクリプト
    run_monitoring.py        # Monitoring 起動スクリプト
    tools/
      paper_verification_report.py
    ai/
      news_nlp.py
      regime_detector.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    monitoring/
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py   (参照あり)
    utils/
      logging_setup.py
      process_priority.py
    execution/            (Execution 系の実装、BrokerFactory などを含む)
    data/                 (実行時に作成されるデータ/DB/PID/フラグを置く想定)

設計上の注意点 / 重要事項
------------------------
- 本リポジトリは本番発注（live）機能を含みます。JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD などの機密情報は漏洩しないよう .env を管理してください。
- .env は絶対にリポジトリにコミットしないでください。
- Monitoring は監視 DB（SQLite）に書き込みます。Monitoring は KABUSYS_ENV に依存せず settings.sqlite_path を使用します（監視と発注 DB を分離したい場合は設定を調整してください）。
- AI（OpenAI）関連機能は API キーが必要です。API 呼び出しはレート制限・ネットワーク障害に対してリトライやフォールバックを行う設計ですが、コストと安全性を考慮して運用してください。
- run_execution / run_monitoring は起動直後にプロセス優先度を "high" に設定しようとします。環境によっては権限不足で失敗する可能性があります（警告ログのみで処理は継続します）。

トラブルシューティング
-----------------------
- validate_config でエラーや警告が出たら対処してください（特に本番環境では警告も注意深く確認）。
- ログディレクトリ作成に失敗するとファイルログが無効化され、コンソール出力のみになります（エラーメッセージは STDERR に表示）。
- DuckDB/SQLite のパスが正しいか、パーミッションは適切かを確認してください。
- OpenAI 呼び出しで失敗する場合は API キーとネットワーク接続、API 利用制限を確認してください。

ライセンス・バージョン
---------------------
パッケージバージョン等は src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。

最後に
------
この README はコードベースの主要部分に基づいて作成しています。実運用前に validate_config を実行し、.env の設定と DB のバックアップ方針を必ず整備してください。必要であれば README の補足や運用手順書（デプロイ・監視フロー・障害時対応）を別途作成することを推奨します。