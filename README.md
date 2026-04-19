KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視ツール群を含む Python パッケージです。  
主な機能は以下のとおりです。

- ExecutionEngine（発注エンジン）: 実取引 / ペーパートレードをサポート
- Monitoring（監視）: システム稼働状況、注文ログ、リスク監視、Kill Switch
- Portfolio / Position Sizing: 候補選定・重み付け・株数決定ロジック
- Research: ファクター計算・将来リターン計算・IC解析など（DuckDB を利用）
- AI 支援: ニュース NLP（OpenAI）による銘柄センチメント、レジーム判定
- 開発用ツール: .env ウィザード、設定検証、Paper Trading 検証レポート 等

特徴
----
- 環境に応じた DB 分離（paper_trading は専用 SQLite を使用）
- 実行中プロセス優先度設定やログの日次ローテーションを標準化
- Kill Switch（ファイルベース）による安全停止
- DuckDB を使った分析 / 研究ワークフローの実装
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント/レジーム判定（オプション）

前提・依存
------------
主な依存パッケージ（実行に必要なものの例）:
- Python 3.9+
- duckdb
- psutil
- openai (AI機能利用時)
- PyYAML（config ファイル検証時に任意）

（実プロジェクトでは requirements.txt / Poetry 等で依存管理してください）

セットアップ手順
----------------

1. リポジトリをクローン / 配布ファイルを取得
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml など（必要に応じて）
4. .env の作成
   - 対話式ウィザードを使用する：
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（下記に典型的な環境変数例を記載）
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）
6. データディレクトリ（data/）やログディレクトリ（logs/）の用意は自動で行われますが、権限により失敗する場合があります。

重要な環境変数（主なもの）
-------------------------
（config_setup の項目を抜粋）

- KABUSYS_ENV: 実行環境 (development / paper_trading / live)
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant/partial/never/reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログの保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）

実行方法
--------

1. ExecutionEngine（エンジン）を起動
   - python -m kabusys.run_execution
   - 特記事項:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
     - 起動時に data/stop_requested.flag が存在すると起動しません。
     - プロセス PID は data/execution.pid に書き込まれます（設定により変更可）。
     - プロセス優先度は起動時に "high" に設定されます（attempt。権限に依存）。

2. Monitoring（監視）を起動
   - python -m kabusys.run_monitoring
   - 特記事項:
     - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、正の整数）。
     - 監視は常に本番の sqlite_path を使用して監視テーブルを初期化します（環境に関わらず）。
     - 停止は data/stop_requested.flag を作成することで行えます（存在検知でループを抜けます）。

3. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い

4. .env の作成 / 更新（ウィザード）
   - python -m kabusys.config_setup

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
   - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH を使用することも可）
   - 出力は標準出力（合否判定: PASS/FAIL）

停止・Kill スイッチ
-------------------
- 停止要求（プロセスを優雅に停止）:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検出して終了します。
- Kill Switch（自動停止トリガ）:
  - KillSwitch は監視処理内で DRAWDOWN_ALERT や POSITION_LIMIT を検出した場合 data/kill.flag を書き込みます。
  - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START の設定に応じて kill.flag を消去できます（本番では 0 推奨）。
  - kill.flag が存在すると ExecutionEngine に停止シグナルを送れる仕様です（実行中は KillSwitch により作成されます）。

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30 日分保持）。
- どのスクリプトも setup_logging を使って統一的にログ設定を行います。
- コンソール出力は stdout、ファイル出力は LOG_DIR 環境変数で変更可能。

データベース
-----------
- DuckDB（分析用）: デフォルト data/kabusys.duckdb
- SQLite（監視 DB）: デフォルト data/monitoring.db
- Paper Trading 用 SQLite（独立）: data/paper_trading.db
- monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB のマイグレーション（列追加）も行います。

主要モジュール概要
-----------------
- kabusys.config: .env 読み込み・Settings クラス（環境変数アクセス）
- kabusys.config_setup: .env 対話ウィザード
- kabusys.validate_config: 起動前設定チェック CLI
- kabusys.run_execution: ExecutionEngine 起動スクリプト
- kabusys.run_monitoring: SystemMonitor ポーリングループ起動スクリプト
- kabusys.monitoring.*: Monitoring の実装（system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db, alert_manager）
- kabusys.execution.*: 発注エンジン・注文関連（BrokerFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等）
- kabusys.portfolio.*: ポートフォリオ構築・ポジションサイジング・リスク調整
- kabusys.research.*: ファクター計算・特徴量探索
- kabusys.ai.*: ニュース NLP（score_news）、レジーム判定（score_regime）
- kabusys.tools.paper_verification_report: ペーパートレードの検証レポート生成

ディレクトリ構成（概要）
----------------------
src/
  kabusys/
    __init__.py
    config.py                    # 環境変数 / Settings
    config_setup.py              # .env ウィザード
    validate_config.py           # 設定検証 CLI
    run_execution.py             # ExecutionEngine 起動スクリプト
    run_monitoring.py            # Monitoring 起動スクリプト
    execution/                   # 発注エンジン関連（Engine, Broker, Order 等）
    monitoring/                  # 監視関連（DB, モニタ, KillSwitch, Engine）
      monitoring_db.py
      system_monitor.py
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      ...
    portfolio/                   # ポートフォリオ構築ロジック
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/                    # ファクター計算・解析ツール
      factor_research.py
      feature_exploration.py
    ai/                          # OpenAI を使った NLP・レジーム判定
      news_nlp.py
      regime_detector.py
    tools/
      paper_verification_report.py
    utils/
      logging_setup.py
      process_priority.py
      ...

README に書ききれない注意点
----------------------------
- 本番環境（KABUSYS_ENV=live）では設定を厳格に確認してください（LINE通知設定等）。
- process priority / cpu affinity の設定は権限によって失敗する場合があります（警告ログのみ）。
- OpenAI API を使う機能は API キーが必須です。API 呼び出しはリトライとフォールバックを備えていますが、課金とレイテンシに注意してください。
- .env は機密情報を含むため、決してリポジトリにコミットしないでください。

よく使うコマンド例
------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問い合わせ / 開発
-----------------
- 開発中は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env ロードを無効化できます（テスト用途）。
- 単体モジュールは外部依存を極力少なく保つ設計になっています（DuckDB / SQLite はデータソースとして中心）。
- 追加の運用スクリプトやデプロイ設定（systemd unit / Supervisor / Dockerfile 等）はプロジェクト運用方針に合わせて用意してください。

以上。必要があれば README を英語版に変換したり、導入手順を具体的な Docker / systemd サンプル付きで拡張します。