KabuSys — 日本株自動売買システム
=================================

この README はリポジトリ内の主要スクリプト・モジュール（実行エンジン、監視、設定ウィザード、リサーチ／ポートフォリオ・ユーティリティ、AI ツール等）について、日本語での概要、セットアップ、実行方法、ディレクトリ構成をまとめたものです。

プロジェクト概要
--------------
KabuSys は日本株の自動売買を目的としたシステム群です。主な機能は次のとおりです。

- ExecutionEngine による注文作成・発注（本番 / ペーパートレード対応）
- Monitoring（System / Trade / Risk）による稼働監視・アラート・Kill Switch
- Portfolio 構築（候補選定、重み計算、株数決定、セクター制限 等）
- Research（ファクター計算、特徴量探索、IC 計算 等） — DuckDB を利用
- AI モジュール（ニュースの NLP スコアリング、レジーム検出：OpenAI を利用）
- 設定ウィザード（.env の対話式作成）、設定検証 CLI、Paper Trading 検証レポート生成ツール
- ログは stdout とログファイル（logs/*.log、日次ローテート）へ出力

機能一覧
--------
主な機能（抜粋）：

- Execution
  - 実口座（live） / ペーパートレード（paper_trading）を切替可能
  - リスク制御（max_position_pct、max_utilization、circuit breaker など）
  - 発注・約定ログの永続化（SQLite）
- Monitoring
  - CPU/メモリ/Disk/プロセス稼働判定
  - データ鮮度チェック（DuckDB の prices_daily 等参照）
  - トレード監視（滞留注文、約定異常など）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
- Portfolio
  - 候補選定（スコア降順）
  - 重み計算（等金額 / スコア加重）
  - ポジションサイジング（リスクベース・等配分等、単元株丸め、aggregate cap）
  - セクターキャップ、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 上で SQL による実行）
  - 将来リターン、IC、統計サマリ等
- AI
  - ニュース記事のセンチメントを OpenAI（gpt-4o-mini）で算出して ai_scores に保存
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定
- ユーティリティ
  - config_setup: .env を対話式に生成
  - validate_config: .env と config/*.yaml の事前検証
  - tools.paper_verification_report: Paper Trading の統計・判定レポート生成

前提条件 / 依存関係
----------------
最低限（代表的なパッケージ）：

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使用する場合）
- PyYAML（設定 YAML の内容検証を行う場合）
- sqlite3（標準ライブラリ）
- （任意）その他のライブラリは requirements.txt があればそちらを参照

セットアップ手順
----------------
1. リポジトリをクローン:
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  # bash/macOS/Linux
   - .venv\Scripts\activate     # Windows (PowerShell/CMD)

3. 依存関係インストール:
   - pip install --upgrade pip
   - pip install duckdb psutil openai pyyaml
   - (requirements.txt がある場合) pip install -r requirements.txt

4. データ / ログ ディレクトリの作成（任意だが推奨）:
   - mkdir -p data logs

5. 環境変数設定:
   - 対話式で .env を作成: python -m kabusys.config_setup
   - もしくは手動で .env を作成（下記「重要な環境変数」参照）

重要な環境変数（主なもの）
--------------------------
以下はコード内 Settings クラスやスクリプトで参照される主要な環境変数とデフォルト値です。

- 必須（必ず設定する）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）

- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — 実行エンジン PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch フラグ（デフォルト: data/kill.flag）

- 実行制御 / ログ
  - LOG_LEVEL — ログレベル（デフォルト: INFO）
  - LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" で有効、デフォルト "0"）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring で使用、デフォルト 60）

- Paper Trading / Mock
  - PAPER_FILL_MODE — ペーパートレード時のマッチングモード ("instant" | "partial" | "never" | "reject")
  - (OPENAI を使う場合) OPENAI_API_KEY — OpenAI API キー

注意:
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- run_monitoring は Monitoring 用 DB（Settings.sqlite_path）を使用します（環境に依存せず本番 sqlite_path を使用する実装上の仕様あり）。

使い方（主要コマンド）
--------------------

- .env の作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告も FAIL 扱いにする: python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - 停止は data/stop_requested.flag を作成するとループ検知で終了します（スクリプトは data/stop_requested.flag を監視）。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - Execution はデフォルトで高優先度にプロセス設定（set_process_priority("high")）してから実行します。
  - 起動中に data/stop_requested.flag を作成すると Engine を停止します。
  - ペーパートレードに切り替えるには KABUSYS_ENV=paper_trading を設定してください（この場合 MockBrokerClient が使用され、data/paper_trading.db に記録されます）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB を指定する場合: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH も利用可能）

- AI モジュール利用（コードレベル）
  - kabusys.ai.score_news(conn, target_date, api_key=None) など（DuckDB 接続を引数に取ります）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- ログ
  - デフォルトは stdout と logs/<app_name>.log（日次ローテート、30日保持）
  - ログ設定は kabusys.utils.logging_setup.setup_logging() で統一的に行われます。

停止 / Kill Switch
-----------------
- Kill Switch はリスクモニタ等が条件を満たしたときに data/kill.flag を書き込み、ExecutionEngine 側で検知して停止する仕組みです（KillSwitch クラス）。
- kill.flag の存在は Settings.kill_flag_path（デフォルト data/kill.flag）で確認できます。
- 実行エンジンは起動時に kill flag が既に存在する場合は起動を拒否する（安全策）設計になっています。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアしますが、本番では 0 推奨です。

データベース / マイグレーション
----------------------------
- monitoring_db.init_monitoring_db(conn) は冪等にテーブルを作成し、必要に応じてカラム追加（マイグレーション）を行います。
- monitoring_db は system_status / trade_logs / positions / risk_logs / dashboard を管理します。
- AI / Research 系は DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）を参照します。データの準備は別途スクリプト / ETL が必要です。

ディレクトリ構成（抜粋）
----------------------
以下は src/kabusys 以下の主要ファイル／モジュールのツリー（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境変数と Settings
    - config_setup.py              # .env 対話ウィザード
    - validate_config.py           # 設定検証 CLI
    - run_monitoring.py            # SystemMonitor ポーリング起動スクリプト
    - run_execution.py             # ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (※存在する想定のファイル)
    - execution/
      - execution_engine.py (※存在する想定のファイル)
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/ (データディレクトリ、実行時に利用)
    - logs/ (ログ保存先、デフォルト)

（注）一部のファイルはリポジトリ抜粋で切れている場合がありますが、上記はコードベースで想定されている機能と配置を反映しています。

開発・運用上の注意点
--------------------
- .env は絶対に Git にコミットしないこと（config_setup.py のヘッダに注意書きあり）。
- KABUSYS_ENV を live に設定する際は全設定（特に LINE 通知、KILL_FLAG_CLEAR_ON_START 等）を慎重に確認してください。validate_config.py に live 向けの警告が組み込まれています。
- OpenAI API を使用する機能は API 利用料が発生します。API キーの管理に注意してください（環境変数 OPENAI_API_KEY を使用）。
- run_execution は起動時にプロセス優先度を上げます（psutil により実行環境により失敗する場合がありますが、安全にフォールバックします）。
- Monitoring は stop flag / kill flag を監視します。運用ではこれらフラグの管理ルールを策定してください。

トラブルシューティング
---------------------
- ログディレクトリ作成に失敗するとコンソール出力のみで継続します（warnings を出します）。logs ディレクトリのパーミッションを確認してください。
- DuckDB / SQLite のパスが存在しない場合、validate_config が警告を出します。起動時に parent ディレクトリを自動作成する場合がありますが、パーミッション等で失敗することがあります。
- OpenAI へのリクエストはレートリミットや一時的な接続障害のためリトライ処理が入っています。失敗した場合はログを確認し、キーやネットワークを見直してください。

最後に
------
本 README はコードベースから抽出した情報に基づいて作成しています。実際の運用や開発では、プロジェクト固有の README、運用手順書、設定ファイル（config/*.yaml）や tests、CI 設定等を併せて参照してください。必要であれば、各モジュールの詳しいドキュメント（関数の使い方やパラメータ説明）を追加で作成できます。