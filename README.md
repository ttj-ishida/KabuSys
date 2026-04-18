README
======

概要
----
KabuSys は日本株向けの自動売買・研究フレームワークです。  
主な目的は次のとおりです。

- マーケットデータ（DuckDB）を使ったファクター計算・研究（research）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- 発注実行エンジン（ExecutionEngine、paper/live 切替対応）
- 実行状況・リスク監視と Kill Switch（monitoring）
- ニュースの LLM ベーススコアリング / レジーム判定（AI モジュール）
- ペーパートレード検証レポート生成ツール

本リポジトリは「実行スクリプト」「設定管理」「DB 永続化」「純粋関数群（ポートフォリオ/研究）」などをモジュール化して提供します。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使い paper_trading DB に記録（本番DBと分離）
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視
- Monitoring（run_monitoring.py）
  - system/trade/risk の監視ポーリング
  - Kill Switch（条件により data/kill.flag を作成して ExecutionEngine を停止）
  - 監視ログは SQLite（デフォルト data/monitoring.db）に永続化
  - ポーリング間隔を MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- 環境設定ウィザード（config_setup.py）
  - .env の初期作成・対話式更新を支援
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の基本チェック（--strict モードあり）
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - paper_trading DB を読み取り稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL 判定
- 研究用モジュール（research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン・IC 計算、統計サマリ等
- ポートフォリオ構築（portfolio）
  - 候補選定、等金額/スコア重み、リスクベースの株数決定、セクターキャップ、レジーム乗数
- AI（ai）
  - ニュースを OpenAI（gpt-4o-mini など）でスコアリングし ai_scores に保存
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（regime_detector）
- ユーティリティ（utils）
  - ロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定

セットアップ
----------
1. Python 環境を用意（推奨: 3.10+）
2. 依存パッケージをインストール（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（config ファイル検証を行う場合）
   - 例: pip install duckdb psutil openai pyyaml
   （実プロジェクトでは requirements.txt を用意している想定です）
3. リポジトリルートで .env を作成
   - 対話式で作る場合:
     python -m kabusys.config_setup
   - 生成後、設定内容を検証:
     python -m kabusys.validate_config

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- LOG_LEVEL / LOG_DIR: ログ出力設定
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1）

自動 .env ロード挙動
- 起動時にプロジェクトルート（.git または pyproject.toml を検出）を基に .env を自動読み込みします。
- 読み込み順: OS 環境 > .env.local > .env
- 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

使い方（主要コマンド）
--------------------
- 設定ウィザード（対話式 .env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も失敗扱い

- ExecutionEngine 起動
  python -m kabusys.run_execution
  補足:
    - KABUSYS_ENV=paper_trading のときは MockBroker を使い PAPER_TRADING_SQLITE_PATH に書き込みます。
    - 起動前に data/stop_requested.flag があると起動しません。
    - PID ファイルのパスは Settings.pid_file_path（デフォルト data/execution.pid）
    - kill.flag（Settings.kill_flag_path）により外部から停止される可能性があります。
    - ExecutionEngine は内部でスレッドを立てて run_session を実行します。停止は stop フラグや kill.flag により行われます。

- Monitoring 起動（ポーリング）
  python -m kabusys.run_monitoring
  環境変数:
    MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  補足:
    - Monitoring は KABUSYS_ENV にかかわらず監視用 sqlite_path（Settings.sqlite_path）を使用します。
    - data/stop_requested.flag を検知すると安全に終了します。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  環境変数:
    PAPER_TRADING_SQLITE_PATH を指定することで DB パスを変更できます。

- AI モジュール（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  例: OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY をセットしてください。

ログ
----
- ログは stdout（StreamHandler）に出力され、デフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30 日保持）。
- ログレベルは LOG_LEVEL 環境変数で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- ログディレクトリを変更する場合は LOG_DIR を設定するか setup_logging に引数で渡します。

データベース（デフォルトパス）
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db

停止・Kill Switch の仕組み
------------------------
- 外部から ExecutionEngine を停止する方法
  - KillSwitch によって data/kill.flag が書かれると、次の監視サイクルで ExecutionEngine に停止シグナルが送られます。
  - run_execution/run_monitoring では stop_requested.flag（data/stop_requested.flag）を使って安全終了できます（管理者が起動/停止を行うためのフラグ）。
- KILL_FLAG_CLEAR_ON_START を 1 に設定すると起動時に自動で kill.flag を削除します（開発用。production では 0 推奨）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                 # Settings（.env 読み込み・設定取得）
  - config_setup.py           # .env 対話式ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                 # 発注関連の実装（BrokerFactory 等）
  - data/                      # データファイル（logs, sqlite, duckdb など）

（注）上記は本リポジトリの一部抜粋です。詳細は各モジュールの docstring を参照してください。

開発メモ / 注意点
-----------------
- .env は秘密情報を含むため絶対にリポジトリにコミットしないでください。
- DuckDB を使った研究モジュールは prices_daily / raw_financials / raw_news 等のテーブルを前提とします。データ投入は別スクリプトで行う想定です。
- AI 関連は OpenAI API を使います。API 呼び出しはリトライやレスポンス検証等を行いますが、API キー管理・利用に注意してください。
- validate_config で PyYAML がインストールされていない場合は config/*.yaml の中身検証をスキップします（警告）。

サンプル .env（最小）
-------------------
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

FAQ（短）
--------
Q: paper_trading と live を切り替えるには？
A: KABUSYS_ENV を paper_trading または live に設定してください。paper_trading では発注はモックされ、専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。

Q: 監視のポーリング間隔を変えたい
A: MONITOR_POLL_INTERVAL 環境変数（秒）で上書きできます（1 秒以上の整数）。

Q: 起動中に強制停止したい
A: data/stop_requested.flag を作るか、monitoring の Kill Switch 条件を満たして kill.flag を作るなどの運用を想定しています。

最後に
------
まずは対話式ウィザードで .env を作成し、validate_config でチェック、その後 run_monitoring と run_execution を別プロセスで起動して動作確認してください。各モジュールは docstring に実装方針や注意点が書かれているので参照してください。