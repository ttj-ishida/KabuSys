README
======

概要
----
KabuSys は日本株の自動売買および関連ツール群を提供する Python パッケージ群です。本リポジトリは次を含みます。

- 戦略・ポートフォリオ構築ロジック（ファクター計算、ポジションサイジング）
- ExecutionEngine（発注エンジン）と監視（Monitoring）コンポーネント
- Paper Trading（検証）用の分離 DB とレポート生成ツール
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- 起動用スクリプト・設定ウィザード・設定検証ツール

目的は安全で再現性のある自動売買パイプラインの基盤提供です。設計上、実際の発注は環境（KABUSYS_ENV）によって切り分けられ、paper_trading では本番 DB と分離された専用 DB を用います。

主な機能
--------
- ExecutionEngine 起動（run_execution.py）
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使い、data/paper_trading.db に記録
  - プロセス優先度の設定、PID ファイル管理、停止フラグ監視
- Monitoring（run_monitoring.py）
  - システム状態・データ鮮度・注文ログ等を定期ポーリングして SQLite に記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - kill.flag による ExecutionEngine 停止（Kill Switch）
- 監視用 DB 層（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを自動作成・マイグレーション
- リスク監視（risk_monitor.py）と KillSwitch（kill_switch.py）
  - ドローダウン・ポジション上限の検出とフラグ書き込み、アラート発生に対応
- ポートフォリオ構築（portfolio/*）
  - 候補選定、等重／スコア重み、ポジションサイズ計算（単元株丸め・利用可能現金に合わせたスケーリング）
  - セクター上限やレジーム乗数の適用
- 研究・ファクター計算（research/*）
  - Momentum / Value / Volatility 等のファクター計算、Forward Returns / IC / 統計サマリ
- ニュース NLP（ai/news_nlp.py）とレジーム判定（ai/regime_detector.py）
  - OpenAI（gpt-4o-mini）を用いた銘柄/マクロセンチメント評価（API キー必須）
  - レスポンスのバリデーション、リトライ、結果の DuckDB への書き込み（ai_scores, market_regime）
- ユーティリティ
  - 対話式 .env ウィザード（config_setup.py）
  - 設定チェック CLI（validate_config.py）
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）
- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

前提（推奨）
------------
- Python 3.9+
- 必要なパッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で利用、必須ではない）
- OS: Linux / macOS / Windows（ただしプロセス優先度 / CPU affinity は OS の差分あり）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動。

2. 仮想環境を作成・有効化（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（requirements.txt があればそれを使ってください）。
   例:
   - pip install duckdb psutil openai PyYAML

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
       - これによりプロジェクトルートに .env を生成・更新できます。
   - あるいは .env.example を参考に手動作成。
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - OpenAI を使う場合:
     - OPENAI_API_KEY を設定

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. ディレクトリ / ファイル（必要に応じて作成）
   - data/ : DB、PID、flag ファイル等（多くのデフォルトが data/ 以下を参照）
   - logs/ : ログ出力先（デフォルト）

使い方
------

起動スクリプト（CLI）
- ExecutionEngine（発注エンジン）を起動:
  - python -m kabusys.run_execution
  - 特記事項:
    - 起動時にプロセス優先度が "high" に設定されます（set_process_priority）
    - KABUSYS_ENV=paper_trading の場合、paper_trading_DB (PAPER_TRADING_SQLITE_PATH) を使用して本番 DB と分離
    - 起動前に data/stop_requested.flag が存在すると起動を中止します
    - 実行中に同ファイルが作成されるとエンジン停止をトリガー

- Monitoring を起動（ポーリングループ）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path（Settings.sqlite_path）を参照してログを残します（環境に依らず本番 DB パスを使用）

停止・Kill Switch
- KillSwitch は条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。ExecutionEngine 起動時にこの flag が存在すると起動しません。
- 一時的な即時停止（強制停止）用にプロジェクトルート data/stop_requested.flag を作成すると、run_execution / run_monitoring のループが検知して安全に終了します。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

Paper Trading 検証レポート
- コマンドライン:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD（期間指定）
    - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）
  - 期間内の稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL を判定

プログラムからの利用（例）
- ポートフォリオ関連:
  - from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
- 研究用:
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
- AI スコアリング:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")  # conn は duckdb 接続

設定（Settings）
- 設定管理は kabusys.config.Settings を通して行います。主要プロパティ:
  - env: KABUSYS_ENV (development|paper_trading|live)
  - sqlite_path: 監視 DB（デフォルト data/monitoring.db）
  - paper_sqlite_path: paper trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）
  - duckdb_path: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - pid_file_path, kill_flag_path, KILL_FLAG_CLEAR_ON_START 等
  - paper_fill_mode: paper_trading 時のフィルモード（instant|partial|never|reject）
- .env は自動ロードされます（プロジェクトルートが特定できる場合）。自動ロードを無効化するには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ログ
- setup_logging() によりルートロガーが初期化されます。
- デフォルト: stdout 出力 + 日次ローテーションで logs/<app_name>.log（30 日保持）
- 環境変数:
  - LOG_LEVEL（INFO 等）
  - LOG_DIR（ログ保存ディレクトリを上書き）
- 起動スクリプトは setup_logging(app_name="execution" / "monitoring") を呼び出します

ディレクトリ構成（主要ファイル）
--------------------------------
- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数 / 設定管理
    - config_setup.py           # 対話式 .env ウィザード（CLI）
    - validate_config.py        # 設定検証 CLI
    - run_execution.py          # ExecutionEngine 起動スクリプト
    - run_monitoring.py         # Monitoring 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (参照されるが実装場所により差分あり)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
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
    - data/ (実行時に生成されることが想定)
      - monitoring.db (SQLITE_PATH)
      - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
      - stop_requested.flag
      - kill.flag
      - execution.pid
    - logs/ (デフォルトログ出力先)

補足・運用上の注意
------------------
- 本番環境（KABUSYS_ENV=live）では設定ミスが重大なリスクを招くため、validate_config で警告・エラーを事前に確認してください。
- OpenAI API を使う機能は API キーが必要です。利用はコストと遅延を伴うため運用ルールを設けてください。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を変更できます。1 秒未満や 0 は無効でデフォルトにフォールバックします。
- Paper Trading 用 DB は本番 DB と分離されます（settings.is_paper を参照）。テストや検証時は paper_trading モードを活用してください。
- ローカルでの自動起動（systemd / cron / supervisor 等）を検討する際は、PID ファイル・ログディレクトリ・data/ のパーミッション管理に注意してください。

よく使うコマンドまとめ
--------------------
- .env を作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ライセンス / 貢献
-----------------
（ここにライセンス情報や貢献方法を追記してください。リポジトリの LICENSE ファイルに従ってください。）

以上。README の補足や運用手順（systemd ユニット例、CI 設定、requirements.txt 追加など）を希望する場合は教えてください。必要に応じて具体例を追加します。