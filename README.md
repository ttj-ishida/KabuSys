README
=====

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。銘柄選定・配分、ポジションサイズ計算、監視（Monitoring）、実行エンジン（Execution）、リサーチおよび AI 補助（ニュース NLP / レジーム判定）などの機能を備え、ローカル開発・ペーパートレード・本番運用を想定した設計になっています。

主な特徴
-------
- portfolio: 候補選定、重み計算、リスク調整、株数決定（単元丸め・集計上限スケール）などの純粋関数
- monitoring: システム稼働監視、データ鮮度チェック、滞留注文／約定異常監視、ドローダウン監視、Kill Switch（フラグファイルによる実行停止）等
- execution: ブローカークライアント抽象化、リスク管理、注文管理、実行エンジン（paper/live 切替対応）
- research: DuckDB を用いたファクター計算（Momentum, Volatility, Value 等）と特徴量解析（IC 計算など）
- ai: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（ai_scores 登録）および市場レジーム判定
- CLI ツール: .env 設定ウィザード、設定検証、Paper Trading 検証レポート生成など
- ロギング: コンソール（stdout）＋日次ローテートファイル出力（logs/<app>.log）

前提条件
--------
- Python 3.10 以上（型注釈の | 演算子およびその他構文を使用）
- 必要なパッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite は標準ライブラリに含まれます
- ネットワークアクセス（OpenAI API 使用時）

開発環境に合わせて requirements.txt を用意していれば pip install -r requirements.txt を推奨します。手動インストール例:
pip install duckdb psutil openai PyYAML

セットアップ手順
--------------
1. ソースを取得
   - レポジトリをクローンしてプロジェクトルートに移動します。

2. Python 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. 環境変数 (.env) 作成（推奨: ウィザードを使用）
   - python -m kabusys.config_setup
     - 対話式で .env を生成・更新します。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD     （必須）
   - 任意・デフォルト例:
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知設定）
     - OPENAI_API_KEY（AI 機能使用時）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合:
     - python -m kabusys.validate_config --strict

使い方
------

実行エンジン（Execution）
- 本番 / ペーパートレードの起動:
  - python -m kabusys.run_execution
  - 実行挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録して本番 DB と完全に分離します。
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
    - 実行中に data/stop_requested.flag が作成されるとエンジンは停止されます。
  - PID ファイル: data/execution.pid（デフォルト、Settings.pid_file_path）

監視ループ（Monitoring）
- python -m kabusys.run_monitoring
  - 機能:
    - SystemMonitor を定期ポーリングして system_status に記録
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（SQLITE_PATH）を使用します（監視を本番 DB に寄せて確認する設計）
  - ポーリング間隔の変更:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルトは 60 秒。
    - 0 以下や不正値は無視されデフォルトにフォールバック。
  - 停止:
    - プロジェクトルート/data/stop_requested.flag を作成するとループは終了します。

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - --db で PAPER_TRADING_SQLITE_PATH を上書きできます（指定がなければ環境変数、さらに無ければ data/paper_trading.db）

AI（ニュースセンチメント・レジーム判定）
- OpenAI API キーを設定（OPENAI_API_KEY 環境変数）
- 関数:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意:
  - API キーがないと ValueError を投げます
  - API 呼び出しはリトライ処理を持つ（429 / タイムアウト / 5xx 等）
  - レスポンス検証に失敗した場合はフェイルセーフ（スキップ／デフォルト値）で継続する設計

ログ・ファイル
- デフォルトのログディレクトリ: logs/
- ログファイル: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- 環境変数 LOG_DIR でログディレクトリを変更できます
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御（デフォルト INFO）

フラグ・制御ファイル
- data/kill.flag
  - Kill Switch が評価されるとこれを書き込み、ExecutionEngine を停止するためのシグナルとなります
  - Settings.kill_flag_clear_on_start=1 の場合、起動時に自動クリアされる（本番では 0 推奨）
- data/stop_requested.flag
  - run_monitoring / run_execution が監視する単純な停止フラグ（起動・ループ停止制御に使用）
- PID ファイル:
  - data/execution.pid（ExecutionEngine の PID）

ディレクトリ構成（主要ファイル）
--------------------------------
プロジェクトルート
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定管理
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py (※実装ファイル含む)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (※実装ファイル含む)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - data/ (実行時に利用する DB / フラグ / pid などを格納)
      - monitoring.db (デフォルト: SQLITE_PATH)
      - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
      - kabusys.duckdb (デフォルト: DUCKDB_PATH)
      - kill.flag, stop_requested.flag, execution.pid
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py

主要な API / 関数（抜粋）
-----------------------
- Settings（kabusys.config）
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.env, settings.is_paper, settings.is_live 等
- Portfolio
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes
  - apply_sector_cap, calc_regime_multiplier
- Research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
- AI
  - kabusys.ai.score_news
  - kabusys.ai.regime_detector.score_regime
- Monitoring
  - MonitoringDB（監視ログ操作）
  - SystemMonitor.check_once(), RiskMonitor.check_once(), MonitoringEngine.run()

運用上の注意
-----------
- KABUSYS_ENV の値:
  - development: 開発（発注なし）
  - paper_trading: ペーパートレード（MockBrokerClient、paper DB を使用）
  - live: 本番（実発注）
- 本番運用時は LINE 通知（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を設定しておくことを推奨
- KILL_FLAG_CLEAR_ON_START を本番で 1 にすると起動時に kill.flag が自動クリアされてしまい危険です（0 を推奨）
- Monitoring は監視用の DB（SQLITE_PATH）へ書き込みます。監視は常に SQLITE_PATH を参照します（環境に依存せず本番 DB を監視するため）
- OpenAI の API 呼び出しはコストとレート制限に注意してください（バッチ・リトライ実装あり）

トラブルシューティング
---------------------
- config 検証で YAML パースエラーが出る場合は PyYAML をインストールするか、config/*.yaml を確認してください
- ログファイルが作成されない場合は LOG_DIR（またはデフォルト logs/）の書き込み権限を確認してください
- psutil によるプロセス優先度設定は権限に依存します（管理者権限が必要なケースあり）。失敗しても警告を出してスキップします

ライセンス・貢献
---------------
（ここにライセンスと貢献方法を追記してください）

----

この README はリポジトリの主要スクリプトとモジュールから生成した概要です。詳細は各モジュールの docstring を参照してください。README に記載の手順で不明点があれば、どの部分を詳しく知りたいか教えてください。