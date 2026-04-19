KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群のライブラリ兼起動スクリプト群です。  
主な目的は以下です。

- シグナル生成とポートフォリオ構築（research / portfolio）
- 発注エンジン (ExecutionEngine) — 本番 / ペーパートレード切替対応
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- ニュース NLP を使ったセンチメント評価（OpenAI 経由）
- ペーパートレード検証レポート生成ツール

このリポジトリはモジュール設計されており、コマンドライン実行スクリプト（python -m ...）から起動することが想定されています。

主な機能一覧
---------------
- config
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式環境設定ウィザード（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）
- execution
  - ExecutionEngine（本番 or paper_trading 切替）
  - BrokerClientFactory による本番/モックブローカー選択
  - OrderManager / RiskManager / Reconciler 等の発注周りコンポーネント
- monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存 / データ鮮度監視
  - TradeMonitor：発注レコード監視（滞留注文、約定異常など）
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：条件に応じた data/kill.flag 書き込み
  - MonitoringEngine：上記を束ねて定期ポーリングしアラート/kill を評価
  - SQLite ベースの監視 DB 初期化・読み書き（monitoring_db）
- portfolio
  - 銘柄選別・重み計算（equal / score / risk-based）
  - セクター上限適用、レジーム乗数計算、ポジションサイズ算出
- research
  - DuckDB を使ったファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- ai
  - ニュース NLP（OpenAI）で銘柄ごとに ai_score を生成（news_nlp）
  - 市場レジーム判定（regime_detector）
- tools
  - Paper Trading の検証レポート生成スクリプト（tools.paper_verification_report）

セットアップ手順
-----------------
1. Python 環境
   - 推奨: Python 3.10+（コードは型ヒントや新版モジュール呼び出しを使用）
   - 仮想環境を作成して有効化するのを推奨します。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須パッケージ（例）
     - duckdb
     - psutil
     - openai  （AI 機能を使う場合）
     - PyYAML（config 検証で YAML のパースを行いたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   注: sqlite3 は Python 標準ライブラリに含まれます。

3. .env 作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークンや kabu API パスワード等を入力すると .env を生成します。
   - 重要な環境変数（最低限必須）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 環境 (KABUSYS_ENV)
     - development / paper_trading / live

4. 設定検証（必須ではないが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

5. データディレクトリ
   - デフォルトで data/ 下に SQLite や PID / フラグファイルが置かれます。必要があれば .env で上書きしてください。
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の DB、デフォルト: data/paper_trading.db）
     - PID/FLAG ファイル: data/execution.pid、data/kill.flag、data/stop_requested.flag 等

使い方
------
- 起動スクリプト（主なコマンド）:
  - ExecutionEngine (発注エンジン)
    - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、ペーパートレード専用 DB に書き込みます。
    - 例（本番/通常）:
      - python -m kabusys.run_execution
    - 例（ペーパートレード）:
      - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  - Monitoring（ポーリング監視）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。
    - 例:
      - python -m kabusys.run_monitoring
      - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  - 設定ウィザード:
    - python -m kabusys.config_setup

  - 設定検証:
    - python -m kabusys.validate_config
    - python -m kabusys.validate_config --strict

  - Paper Trading 検証レポート:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB パス指定:
      - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- 環境変数の重要事項:
  - KABUSYS_ENV: development | paper_trading | live
  - JQUANTS_REFRESH_TOKEN: J-Quants API
  - KABU_API_PASSWORD: kabuステーション API パスワード
  - OPENAI_API_KEY: OpenAI を使う機能（ai.score_news / regime_detector）で必要
  - PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject）
  - LOG_LEVEL, LOG_DIR: ログ出力設定
  - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring 用）

- Stop / Kill フラグの扱い
  - run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag を監視します。ファイルが存在すると起動/ループを終了します。
  - KillSwitch は monitoring 内で kill.flag を生成して ExecutionEngine を停止対象にします。KILL_FLAG_CLEAR_ON_START により起動時に自動クリアするか制御可能（本番では 0 推奨）。

- ログ
  - デフォルト: logs/<app_name>.log を日次ローテーションで出力（30 日保持）
  - 標準出力は stdout に出力されます（cron 等でログリダイレクトしやすい）

ライブラリ API（抜粋）
--------------------
- 研究系 / ファクター:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  - これらは DuckDB 接続を受け取り、prices_daily / raw_financials 等のテーブルから計算します。

- ポートフォリオ構築:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

- AI:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None) — ai_scores テーブルへ書き込みます（OPENAI_API_KEY 必須または api_key 引数）。

ディレクトリ構成（主要ファイル）
------------------------------
以下はソースツリーの主要なディレクトリ / ファイルの一例です（src/kabusys を基準）。

- src/kabusys/
  - __init__.py  # パッケージ定義、__version__ 等
  - config.py  # 環境変数読み込み・Settings
  - config_setup.py  # .env ウィザード CLI
  - validate_config.py  # 設定検証 CLI
  - run_execution.py  # ExecutionEngine 起動スクリプト
  - run_monitoring.py  # SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  # Paper Trading レポート生成 CLI
  - ai/
    - __init__.py
    - news_nlp.py  # ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py  # マクロ + MA200 で市場レジーム判定
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py  # SQLite による永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py  # （アラート送信機能、実装ファイルがある想定）
  - execution/
    - execution_engine.py  # ExecutionEngine（エントリは run_execution.py）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

運用上の注意
------------
- 本番環境 (KABUSYS_ENV=live) では特に注意してください。validate_config の警告や LINE 通知設定を事前に確認してください。
- kill.flag / stop_requested.flag / PID ファイルの取り扱いに注意。自動クリア設定は本番では 0 を推奨します。
- OpenAI を用いる機能は API 利用料が発生します。api_key 管理とレートに注意してください。
- DuckDB / SQLite の DB パスは .env で制御可能です。監視 DB とペーパートレード DB は分離推奨です。

トラブルシューティング
----------------------
- モジュールの依存が足りない場合は validate_config で警告が出ます。YAML 検証は PyYAML が無いとスキップされます。
- ログファイルが作れない場合は標準出力のみで起動します（ログディレクトリ作成に失敗した旨が stderr に出ます）。
- run_execution/run_monitoring は data/stop_requested.flag を検知して終了します。手動で強制停止する場合はこのフラグを作成してください（テスト用）。

ライセンス・貢献
----------------
（ここにはプロジェクト固有のライセンス情報や貢献ガイドラインを記載してください）

以上がこのコードベースの概要と基本的な利用方法です。README に追加したい具体的な情報（使用例、環境変数の詳細テーブル、要件ファイル等）があれば教えてください。