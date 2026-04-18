README — KabuSys
=================

概要
----
KabuSys は日本株自動売買システムの骨格ライブラリです。  
システム監視、注文管理、ポートフォリオ構築、ファクター計算、ニュースNLP によるセンチメントスコアリング、ペーパートレード検証などの機能を備え、実運用（live）・ペーパートレード（paper_trading）・開発（development）それぞれのモードで動作することを想定しています。

主な機能
--------
- システム監視（SystemMonitor / MonitoringEngine）
  - CPU / メモリ / ディスクの監視、データ鮮度チェック、プロセス生存確認
  - 監視ログを SQLite に永続化
- 実行エンジン起動（ExecutionEngine 起動スクリプト）
  - 本番 / ペーパートレード切替（paper_trading 時は MockBrokerClient を使用し専用 DB を使う）
  - リスク管理（RiskManager / Reconciler / OrderManager 等）
- Kill Switch（kill.flag）による安全停止
- ペーパートレード検証レポート生成ツール
- ポートフォリオ構築（候補選定、重み付け、position sizing、セクター制限等）
- リサーチ用ファクター計算（モメンタム / バリュー / ボラティリティ等）
- ニュースNLP（OpenAI を用いた銘柄・マクロのセンチメント集約）
- 設定ウィザード（.env 生成）・設定検証 CLI

必要条件（主な依存）
-------------------
- Python 3.10+
- パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の検証に使用）
- OS：Linux / macOS / Windows（各 OS 向けの挙動は utils/process_priority.py で吸収）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - プロジェクトルートには pyproject.toml または .git がある想定です。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （開発用）pip install PyYAML

   ※ requirements.txt がある場合はそれを利用してください（本コード例には同梱されていません）。

4. .env の作成
   - 対話式ウィザードで作成するのが簡単です：
     - python -m kabusys.config_setup
   - あるいは .env.example を参照して手動作成してください（JQUANTS_REFRESH_TOKEN 等の必須項目あり）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

初期データディレクトリ
- デフォルトの DB / ログ パス（.env で上書き可能）:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - ログ: logs/（アプリ名ごとに logs/<app_name>.log）

主要な環境変数（代表）
----------------------
- KABUSYS_ENV: execution モード（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合）
- PAPER_FILL_MODE: paper_trading の注文約定挙動（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）

使い方（主要 CLI / 実行スクリプト）
-----------------------------------

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（秒）
  - run_monitoring は常に「本番用の sqlite_path」を使用して監視ログを書きます

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます
  - data/execution.pid に PID を出力し、data/stop_requested.flag により外部から停止を指示できます

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH （なければ PAPER_TRADING_SQLITE_PATH 環境変数／デフォルトを使用）

- プログラミング API（モジュール呼び出し）
  - ポートフォリオ構築:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - リサーチ:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - ニュース NLP / レジーム判定:
    - from kabusys.ai import score_news
    - from kabusys.ai.regime_detector import score_regime

停止 / Kill Switch
------------------
- Kill Switch（自動／手動）:
  - 自動: MonitoringEngine 内の評価（ドローダウン・ポジション上限等）により KillSwitch が data/kill.flag を書き込むことがあります。ExecutionEngine はこのフラグを検知して安全終了します。
  - 手動: data/kill.flag を作成することで外部から停止させることができます。
- 一時停止要求（プロセス停止用ファイル）:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します。
- PID ファイル:
  - Execution 用 PID: data/execution.pid（run_execution が出力）

ログ
----
- logs/<app_name>.log に日次ローテーションでログを出力（デフォルト 30 日保持）
- stdout へもログを出力します（StreamHandler）。ログ出力先は環境変数 LOG_DIR / 引数で変更可能。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys/ 以下の主要ファイル・パッケージです（抜粋）。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                — 環境変数/設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py     — マクロ + MA200 を組み合わせた市場レジーム判定

  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義と永続化 API
    - system_monitor.py      — システム監視ロジック
    - trade_monitor.py       — 注文滞留・約定異常などの監視（実装参照）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — LINE などへ通知を行う（実装参照）

  - execution/
    - broker_factory.py      — BrokerClient の生成（live/paper に依存）
    - execution_engine.py    — ExecutionEngine 実装（起動ループ）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - data/
    - pipeline.py             — prices_daily などの取得系（参照）
    - stats.py                — 正規化ユーティリティ等

  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定

開発上の注意点 / 補足
--------------------
- config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env を自動読み込みします。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_execution は KABUSYS_ENV=paper_trading の場合、データを本番 DB と分離して data/paper_trading.db に書き込みます。
- ニュース NLP / レジーム判定は OpenAI API を使用します。API キーを OPENAI_API_KEY に設定してください。失敗時のフォールバックやリトライのロジックが組み込まれていますが、API 利用料・レートにご注意ください。
- DuckDB / SQLite のテーブルスキーマはコード側で必要に応じてマイグレーション（列追加等）を行います。既存 DB のバックアップは必ず取得してください。
- 多くの関数は「ルックアヘッドバイアス回避」のため date / target_date を外部から渡す設計になっています。テスト時に日付を固定することで再現性のある検証が可能です。

ライセンス・バージョン
----------------------
- パッケージバージョンは kabusys.__version__（デフォルト "0.1.0"）で管理されています。ライセンス情報はリポジトリのルートに配置してください（ここでは省略）。

問い合わせ / 贡献
-----------------
バグ報告・機能要望は Issue を立ててください。機能追加・修正は Pull Request をお送りください。

以上です。README の補足や具体的なコマンド例（systemd サービス定義、Dockerfile、CI 設定など）が必要であれば教えてください。