KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。本リポジトリは以下の主要コンポーネントを含みます。

- ExecutionEngine（注文発注・リスク管理・発注履歴管理）
- Monitoring（システム稼働監視・注文監視・キルスイッチ）
- Portfolio Construction（銘柄選定・重み付け・株数計算）
- Research（ファクター計算・特徴量探索）
- AI（ニュースを LLM で評価してスコア化するモジュール）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポートなど）

特徴
----
主な機能・特徴は以下の通りです。

- 実運用とペーパートレードの分離（KABUSYS_ENV=paper_trading でペーパーデータベースを使用）
- モジュール化されたポートフォリオ構築（候補選定・重み計算・リスク調整・ポジションサイジング）
- DuckDB を用いたリサーチ/ファクター計算（prices_daily / raw_financials 等）
- OpenAI（gpt-4o-mini）を使ったニュース NLP によるセンチメントスコアリング（ai モジュール）
- SQLite による監視ログ/トレードログ保存（monitoring_db）
- Kill Switch（データフラグにより ExecutionEngine を安全に停止）
- 簡易 CLI: .env ウィザード、設定検証、ペーパートレード検証レポート等
- ログ管理ユーティリティ（コンソール + 日次ローテートファイル）

前提条件
--------
- Python 3.10 以上（型注釈で "|" 演算子を使用）
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証時に推奨）
- 書き込み可能な data/ および logs/ ディレクトリ

（依存関係はプロジェクトの requirements.txt があればそちらを利用してください。なければ次のようにインストールできます）
pip install duckdb psutil openai pyyaml

セットアップ手順
----------------

1. リポジトリをクローンしてソースを配置
   - 仮にプロジェクトルートがリポジトリ直下であることを前提とします。

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
     - J-Quants トークンや kabuAPI パスワードなど必須値を対話的に設定できます。
   - 手動で .env を作る場合は .env.example を参考にしてください（プロジェクトルートに配置）。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合: python -m kabusys.validate_config --strict

重要な環境変数（主要）
--------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- SQLITE_PATH — 監視用 SQLite（monitoring.db）のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading 時に使用）
- PAPER_FILL_MODE — ペーパー注文の約定モード: instant / partial / never / reject（デフォルト: instant）
- OPENAI_API_KEY — OpenAI API を使う機能（ai モジュール）で必須
- LOG_LEVEL / LOG_DIR — ロギング設定
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（本番では 0 推奨）

自動 .env 読み込み
- プロジェクトは自動的にプロジェクトルートの .env と .env.local を読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要コマンド）
--------------------

- 設定ウィザード（.env の作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- 監視プロセス起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒数で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - run_monitoring は KABUSYS_ENV にかかわらず production（settings.sqlite_path） を監視 DB として使用します。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - data/stop_requested.flag が存在する場合、起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

停止方法 / Kill Switch / フラグファイル
---------------------------------------
- run_monitoring や run_execution はプロジェクトルートの data/stop_requested.flag を監視しています。ファイルが存在するとループを抜けて終了します（safe shutdown）。
- KillSwitch（kill.flag）:
  - 監視ロジックにより条件（ドローダウン超過等）を満たすと data/kill.flag が書き込まれ、ExecutionEngine に停止指示が送られます。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 で自動クリアする設定もありますが、本番では 0 を推奨します。

ログ
---
- ログは以下の方式で出力されます（kabusys.utils.logging_setup.setup_logging）。
  - stdout（StreamHandler）
  - 日次ローテートファイル → デフォルト logs/<app_name>.log（30日分保持）
- LOG_DIR 環境変数でログ保存先を変更できます。

データベース / ファイル
-----------------------
- DuckDB（分析用）: デフォルト data/kabusys.duckdb（Settings.duckdb_path）
- SQLite（監視 / 発注ログ）: デフォルト data/monitoring.db（Settings.sqlite_path）
- ペーパートレード用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 用）
- PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

ディレクトリ構成（抜粋）
-----------------------
以下は主要なソースファイルを示した簡易ツリー（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定読み込みロジック
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 起動前設定検証 CLI
  - run_monitoring.py              — Monitoring ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py             — SQLite 永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
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

補足 / 注意点
-------------
- OpenAI 関連機能（news_nlp, regime_detector）は OPENAI_API_KEY を必要とします。キーの取り扱いには十分ご注意ください（.env を絶対にコミットしない）。
- Monitoring の起動スクリプトは docstring にある通り MONITOR_POLL_INTERVAL で間隔を変えられます。0 または負の値は無効とみなされデフォルトにフォールバックします。
- run_monitoring は「監視」用であり、本番 DB（settings.sqlite_path）を参照します。開発時に誤って本番 DB を操作しないようご注意ください。
- config_setup は .env を生成しますが、.env は Git にコミットしないこと（秘密情報を含むため）。

よく使うコマンドまとめ
-------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視開始: MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン開始: python -m kabusys.run_execution
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・バージョン
--------------------
- パッケージバージョンは kabusys.__version__ で確認できます（現時点: 0.1.0）。

問い合わせ / 開発メモ
--------------------
- 開発時は KABUSYS_ENV=development を使用してください。ペーパートレード分離が必要な場合は paper_trading を使ってください。
- 本番（live）に切り替える前に python -m kabusys.validate_config を実行し、すべてのチェックを通過させることを推奨します。

以上が本プロジェクトの README 的な説明です。必要があれば README に含めるコマンド例や環境変数のサンプル .env テンプレートを生成できますので、お申し付けください。