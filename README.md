README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのコアライブラリ群です。本リポジトリは以下の主要機能を含みます。

- ExecutionEngine（発注エンジン）起動スクリプト
- Monitoring（システム監視・リスク監視・Kill Switch）
- ポートフォリオ構築（銘柄選定・重み付け・数量計算）
- リサーチ用ファクター計算・特徴量解析
- AI モジュール（ニュースのセンチメント評価・市場レジーム判定）
- 各種ユーティリティ（ログ設定・プロセス優先度など）
- 設定ウィザード / 設定検証 / 検証レポート生成ツール

設計の要点
- 実行環境は環境変数（.env）で制御。KABUSYS_ENV により paper_trading / live / development を切替。
- Paper trading（ペーパートレード）は実際の発注を行わず、専用の SQLite DB にログを残す（本番 DB と分離）。
- OpenAI を利用した NLP 部分は API キー（OPENAI_API_KEY）を必要とし、API 呼び出しはリトライ・フェイルセーフを備えています。
- ログは標準出力と日次ローテートファイルに出力（logs/<app>.log）。

主な機能一覧
----------------
- 実行関連
  - run_execution.py: ExecutionEngine を起動（スレッドで実行、停止フラグ検出で終了）
  - ExecutionEngine は RiskManager / OrderManager / Reconciler などと連携（コードベース内に実装）
- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループを起動（デフォルト 60 秒ごと）
  - monitoring パッケージ: SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch
  - monitoring_db: SQLite に監視ログ・トレードログ・リスクログ等を永続化
- ポートフォリオ構築
  - portfolio パッケージ: 銘柄選定、等配分・スコア重み配分、ポジションサイズ計算、セクターキャップ適用、レジーム乗数
- リサーチ
  - research パッケージ: ファクター計算（モメンタム、バリュー、ボラティリティ等）、将来リターン、IC 計算、統計サマリ
  - DuckDB を用いたオフライン集計（prices_daily / raw_financials 等を参照）
- AI（OpenAI）
  - ai.news_nlp: raw_news を集約し LLM（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores に書込
  - ai.regime_detector: ETF（1321）MA200 とマクロニュースの LLM スコアを合成し market_regime に書込
- ツール
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: .env / config/*.yaml の起動前検証 CLI
  - tools.paper_verification_report.py: Paper Trading の検証レポート生成
- ユーティリティ
  - utils.logging_setup: 統一的なロギング設定（stdout + 日次ファイルローテート）
  - utils.process_priority: プラットフォームに依存しないプロセス優先度設定（High/Normal/Low）

前提（Prerequisites）
--------------------
- Python 3.9+
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- （推奨）仮想環境の利用: python -m venv .venv && source .venv/bin/activate

インストール（例）
-----------------
1. リポジトリをクローン / ワークディレクトリへ移動
2. 必要パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 明示的に:
     - pip install duckdb psutil openai pyyaml

環境変数・設定 (.env)
---------------------
プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は .env を上書き）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (監視用デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB; デフォルト data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/...)
- LOG_DIR (ログ保存先）
- MONITOR_POLL_INTERVAL (run_monitoring.py のポーリング間隔を秒で上書き、デフォルト 60)

例 .env（抜粋）
---------------
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

セットアップ手順
----------------
1. リポジトリのルートに .env を作成する:
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - または .env.example を参考に手動作成
2. 設定を検証する:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い
3. 必要な DB ディレクトリを作成（自動で作られることが多いが念のため）
   - mkdir -p data logs

使い方（よく使うコマンド）
------------------------
- Execution（エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と完全分離）
    - 実行中に data/stop_requested.flag が作成されるとエンジンを停止します
    - PID を data/execution.pid に書込（pid_file 設定に従う）
    - 起動時に set_process_priority("high") が呼ばれます（可能な場合）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 設定:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60）
    - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（監視用 DB）を使用
    - 停止: data/stop_requested.flag を作成するとループが終了

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
    - 環境変数 PAPER_TRADING_SQLITE_PATH を優先して使います

- AI まわりの利用（スクリプトまたは REPL）
  - news scoring:
    - from kabusys.ai import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date=datetime.date(2026,4,1), api_key="sk-...")
  - regime scoring:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date=datetime.date(2026,4,1), api_key="sk-...")

停止/Kill スイッチ
------------------
- ExecutionEngine の停止:
  - 管理用フラグファイル data/stop_requested.flag を作成すると run_execution・run_monitoring のループが終了します（両スクリプトともこのフラグを監視しています）。
- KillSwitch:
  - monitoring.kill_switch.KillSwitch が条件を満たすと data/kill.flag を書き込みます。これにより ExecutionEngine の停止を誘導できます。
  - Settings.kill_flag_clear_on_start==1 の場合、起動時に kill.flag を自動クリアする設定があります（本番では推奨しません）。

ログ
----
- デフォルト: logs/<app_name>.log（apps: execution, monitoring など）
- 日次ローテーション（30日保持）
- コンソール出力は stdout（stderr ではない）を使います
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一

設定検証・移行
--------------
- monitoring_db.init_monitoring_db は冪等的にテーブルを作成し、既存 DB に不足カラムがあれば ALTER TABLE によるマイグレーションを行います（peak_value, latency_ms 等）。
- validate_config で .env の必須項目や config/*.yaml の存在（および PyYAML があればパースチェック）を行えます。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主要モジュール一覧（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定読み込みロジック
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP スコアリング
    - regime_detector.py       — 市場レジーム判定
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
    - trade_monitor.py         (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         (参照あり)
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py

（注）本 README はリポジトリ内のソースから抜粋して要点をまとめたものです。実際の実装にはここに挙げていないモジュール（execution.* や order_manager など多数）が存在し、連携して動作します。運用前に必ず python -m kabusys.validate_config による検証と、小規模なローカルテスト（KABUSYS_ENV=development / paper_trading）を行ってください。

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では kill_flag_clear_on_start を 0 に設定することを強く推奨します。
- OpenAI を用いる機能は API 利用料が発生します。API キー管理には注意してください。
- Paper trading 用 DB を本番 DB と分離することで誤発注やログ混在を防いでいますが、設定ミスに注意してください（PAPER_TRADING_SQLITE_PATH を確認）。
- ログ・DB のバックアップ・監視（ディスク容量）を行ってください。Monitoring はディスク使用率閾値も監視できます。

ライセンス / バージョン
-----------------------
パッケージバージョン: kabusys.__version__ = 0.1.0

最終更新
--------
この README はコードベースのソースコメントと CLI ドキュメントに基づいて自動作成・要約されています。詳細は各モジュールの docstring を参照してください。