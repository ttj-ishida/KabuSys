README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を想定した Python パッケージです。本コードベースは以下の主要機能を含みます。

 - 注文実行エンジン（ExecutionEngine）
 - システム／注文／リスク監視（Monitoring）
 - ペーパートレード用検証ツール（Paper Trading レポート）
 - ポートフォリオ構築ユーティリティ（銘柄選定・配分・ポジションサイズ）
 - ファクター計算・特徴量探索（Research）
 - ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
 - 環境設定ウィザード・設定検証ツール
 - 汎用ユーティリティ（ロギング設定・プロセス優先度設定等）

主な設計方針：
 - 本番 DB とペーパートレード DB を分離可能
 - ルックアヘッドバイアスを避ける実装方針（date.today() を直接参照しない等）
 - OpenAI 呼び出しはリトライやバリデーションを含む堅牢な処理
 - ログはコンソール + 日次ローテートファイルに出力

機能一覧
--------
主要コンポーネントと機能の一覧（抜粋）：

 - run_execution.py
   - ExecutionEngine の起動スクリプト
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
   - 起動中は data/execution.pid に PID を書き込み、 data/stop_requested.flag による停止に対応

 - run_monitoring.py
   - SystemMonitor のポーリングループ起動スクリプト
   - MONITOR_POLL_INTERVAL 環境変数で間隔変更（デフォルト 60 秒）
   - 監視データは sqlite_path（デフォルト data/monitoring.db）へ永続化

 - monitoring/*
   - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / monitoring_db
   - kill_switch はルールに応じて data/kill.flag を書き、ExecutionEngine 停止をトリガー

 - portfolio/*
   - 銘柄候補選定、等重/スコア重み付け、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ算出

 - research/*
   - ファクター算出（momentum/value/volatility）、将来リターン、IC（Information Coefficient）計算、統計サマリ

 - ai/*
   - news_nlp (OpenAI でニュースをスコア化)
   - regime_detector (ETF とマクロニュースを合成して regime を判定)

 - tools/paper_verification_report.py
   - ペーパートレードの検証レポート生成（稼働率、注文成功率、レイテンシ等）

 - config.py / config_setup.py / validate_config.py
   - 環境変数の読み込み・検証・対話式 .env 作成ウィザード

セットアップ手順
----------------

1. Python 環境
   - Python 3.9+ を想定（使用環境に合わせて調整してください）

2. 依存パッケージ（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で YAML 構文チェックを行う場合に必要）

   例:
     pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを使ってください。

3. .env ファイルの作成
   - 対話式ウィザードで .env を作成できます：
       python -m kabusys.config_setup
   - 手動で作成する場合はプロジェクトルートに .env を置いてください（.env は Git にコミットしないでください）。

4. 設定の検証（起動前推奨）
     python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いします。

主要な環境変数（代表）
--------------------
必須:
 - JQUANTS_REFRESH_TOKEN  — J-Quants API 用リフレッシュトークン（必須）
 - KABU_API_PASSWORD      — kabuステーション API パスワード（必須）

運用 / DB / ログ:
 - KABUSYS_ENV            — 実行環境: development | paper_trading | live （デフォルト development）
 - DUCKDB_PATH            — DuckDB ファイル（デフォルト data/kabusys.duckdb）
 - SQLITE_PATH            — 監視用 SQLite（デフォルト data/monitoring.db）
 - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
 - LOG_LEVEL              — ログレベル（DEBUG/INFO/...、デフォルト INFO）
 - LOG_DIR                — ログディレクトリ（デフォルト logs/）

ペーパートレード関連:
 - PAPER_FILL_MODE        — instant | partial | never | reject （デフォルト "instant"）
 - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB パス

監視・停止:
 - MONITOR_POLL_INTERVAL  — Monitoring のポーリング間隔（秒、デフォルト 60）
 - KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（"1" でクリア）
 - KILL_FLAG_PATH         — kill.flag のパス（デフォルト data/kill.flag）
 - PID_FILE_PATH          — Execution の PID ファイルパス（デフォルト data/execution.pid）

OpenAI:
 - OPENAI_API_KEY         — OpenAI 呼び出しの API キー（ai.news_nlp / regime_detector で使用）

簡単な .env の例（抜粋）
------------------------
以下は例です。実運用では必ず実際の値で設定してください（.env.example を参照）。

  JQUANTS_REFRESH_TOKEN=your_jquants_token_here
  KABU_API_PASSWORD=your_kabu_password_here
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO
  OPENAI_API_KEY=sk-xxxx...

使い方（主要コマンド）
--------------------

 - 環境設定ウィザード（.env を生成）
     python -m kabusys.config_setup

 - 設定検証
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict

 - ExecutionEngine を起動
     python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合はモックブローカーを利用し、デフォルトで data/paper_trading.db に記録します。
   - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。
   - 実行中に data/stop_requested.flag を作成すると実行ループが検知して停止します。
   - 実行中は data/execution.pid に PID が書き込まれます。

 - Monitoring を起動
     python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
   - 監視は sqlite_path（Settings.sqlite_path）に記録します（Monitoring は環境にかかわらず本番 sqlite_path を使用します）。
   - 停止はプロジェクトルート/data/stop_requested.flag を作成します（監視ループはこのファイルを検知して終了）。

 - Paper Trading 検証レポート（標準出力へ）
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で SQLite パスを指定できます（PAPER_TRADING_SQLITE_PATH 環境変数でも可）。

 - ライブラリ関数（プログラム内で利用）
   - ポートフォリオ例:
       from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
   - リサーチ例:
       from kabusys.research import calc_momentum, calc_volatility, calc_value
   - AI スコアリング:
       from kabusys.ai import score_news
       # score_news は DuckDB 接続と target_date を渡して実行

停止・Kill Switch（安全停止）
---------------------------
 - stop_requested.flag
   - run_execution / run_monitoring のループは project_root/data/stop_requested.flag の存在を監視し、存在すると安全に停止します。
 - kill.flag
   - KillSwitch は規定条件（ドローダウン超過、ポジション上限超過等）で data/kill.flag を書き込み、ExecutionEngine に対して停止指示を出します。
   - 設定 KILL_FLAG_CLEAR_ON_START=1 にすると ExecutionEngine 起動時に kill.flag を自動クリアします（本番では通常 0 推奨）。

ロギング
-------
 - 共通のロギング設定ユーティリティが用意されています（kabusys.utils.logging_setup.setup_logging）。
 - ログはコンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）に書き出されます。
 - ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で指定可能。

ディレクトリ構成（抜粋）
---------------------
プロジェクト内の主要ファイル / モジュール構成（src/kabusys 以下）:

 - kabusys/
   - __init__.py
   - config.py
   - config_setup.py
   - validate_config.py
   - run_execution.py
   - run_monitoring.py
   - tools/
     - paper_verification_report.py
   - utils/
     - logging_setup.py
     - process_priority.py
   - monitoring/
     - monitoring_db.py
     - system_monitor.py
     - trade_monitor.py
     - risk_monitor.py
     - monitoring_engine.py
     - kill_switch.py
     - alert_manager.py  (参照箇所あり、実装がある場合)
   - execution/             (注文実行関連の実装群)
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
   - data/                  (実行時に生成されることがある: DB・flag・pid 等)

（実際のリポジトリでは他にも多くのモジュールが存在します。上は主要部分の抜粋です。）

運用上の注意
-----------
 - 本番（KABUSYS_ENV=live）では設定（LINE 通知、KILL_FLAG_CLEAR_ON_START 等）を十分に確認してください。validate_config は live 向けの追加チェックを行います。
 - .env や API キー等のシークレットは決してリポジトリへコミットしないでください。
 - OpenAI 連携はネットワークエラー／レート制限に備えたリトライ実装がありますが、キーやコスト管理に注意してください。
 - 複数プロセスで同一の SQLite ファイルに同時アクセスする場合は注意してください（本設計では monitoring DB と orders DB を分離することで競合を減らす設計になっています）。

サポート / 開発
---------------
 - まずは python -m kabusys.config_setup で .env を作成 → python -m kabusys.validate_config でチェック → ローカルで run_monitoring / run_execution を実行して挙動を確認してください。
 - 単体関数は外部からインポートしてユニットテストしやすいよう純粋関数を多用しています（research / portfolio 等）。

付記
----
この README はコードベースに含まれるモジュールのドキュメントをもとに作成した概要です。詳細な設計仕様（PortfolioConstruction.md や StrategyModel.md 等）がリポジトリ内にある場合はそちらも参照してください。