README
======

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
本リポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI を活用したニュース分析などのコンポーネントを含みます。  
設計方針として、コアロジックは可能な限り副作用を避け、DB（SQLite / DuckDB）をデータ永続化・分析の中心にしています。

主な機能
--------
- ExecutionEngine：ブローカークライアント経由で発注を行う実行エンジン（paper_trading モードあり）。
- Monitoring：システム状態・注文状況・リスク（ドローダウン / ポジション上限）を監視し、kill.flag による安全停止をサポート。
- Portfolio construction：候補選定・重み計算・ポジションサイズ決定（等配分・スコア加重・リスクベース）。
- Research：DuckDB を用いたファクター計算（モメンタム・バリュー・ボラティリティ）と特徴量解析（IC 等）。
- AI モジュール：OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント（ai_scores）や市場レジーム判定。
- ユーティリティ：設定ウィザード（.env の生成）、設定検証 CLI、ログ設定ユーティリティ、プロセス優先度設定など。
- ツール：Paper Trading の検証レポート生成スクリプト。

セットアップ
-----------
1. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存関係をインストール
   - 必須パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （本リポジトリには requirements.txt は含まれていません。環境に応じて適切に追加してください。）

3. ディレクトリ準備
   - データ / ログ格納用ディレクトリを作成（通常はプロジェクトルート直下の data/ と logs/）
     - mkdir -p data logs

4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - または .env.example を参考に .env を作成してください。

主要な環境変数（主なもの）
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading モード時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（default: logs）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア、0=クリアしない）

設定の検証 / ウィザード
----------------------
- 対話式ウィザード:
  - python -m kabusys.config_setup
  - .env を生成・更新します（.env は絶対に Git にコミットしないでください）。

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）になります。

使い方（起動・実行例）
--------------------

- 監視（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）。
    - 監視は常に本番用 sqlite_path を使用（環境にかかわらず monitoring DB を参照）。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行えます（stopRequested flag）。
    - ログは logs/monitoring.log に日次ローテートで保存されます。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に注文ログを記録して本番 DB と分離します。
    - 起動直後にプロジェクトルート/data/stop_requested.flag が既に存在する場合は起動せず終了します。
    - 実行中に stop_requested.flag を置くとエンジンを停止します。
    - 実行時に PID は data/execution.pid に書き出されます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db で SQLite DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH > --db > デフォルトの優先順位で解決）。

- AI 関連（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キー（api_key または OPENAI_API_KEY）が必要。

停止フラグ / Kill Switch
-----------------------
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring / run_execution が監視・実行ループでチェックする停止フラグ。ファイルが存在すると該当プロセスは終了します。

- kill.flag（data/kill.flag）
  - KillSwitch（監視コンポーネント）が条件を満たすと書き込みます（ExecutionEngine に対する停止シグナル）。本番運用時は KILL_FLAG_CLEAR_ON_START=0 が推奨されます。

データベース（概要）
------------------
- DuckDB（分析用）
  - デフォルト: data/kabusys.duckdb
  - prices_daily / raw_financials / raw_news / market_regime 等の分析テーブルを想定（データ投入は別スクリプト/パイプライン）。

- SQLite（監視・発注ログ）
  - 監視 DB（monitoring）: data/monitoring.db（init_monitoring_db によりテーブル生成）
    - system_status, trade_logs, positions, risk_logs, dashboard
  - ペーパートレード DB: data/paper_trading.db（paper_trading モード時）

ログ
----
- ログはデフォルト logs/ ディレクトリに日次ローテートで保存されます（TimedRotatingFileHandler）。コンソール出力は stdout に出ます。
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御可能。

ディレクトリ構成（主要ファイル）
--------------------------------
- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数/設定読み込み
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py         (存在前提)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py        (存在前提)
    - execution/
      - execution_engine.py     (存在前提)
      - order_manager.py        (存在前提)
      - order_repository.py     (存在前提)
      - broker_factory.py       (存在前提)
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - logging_setup.py
      - process_priority.py

（注）上記の "存在前提" と表現したファイルは README に載せたコードベースの一部として存在しますが、本 README はリポジトリの主要構造を簡潔に示すための一覧です。

補足・運用上の注意
------------------
- 本番環境（KABUSYS_ENV=live）では環境変数の扱いに慎重になってください（JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD の管理、KILL_FLAG_CLEAR_ON_START の設定等）。
- .env は絶対にバージョン管理にコミットしないでください。
- AI モジュールを運用する場合、OpenAI API のレートリミットやコストに注意し、API キーは安全に管理してください。
- process_priority.set_process_priority を起動直後に呼び出し、プロセス優先度を "high" に設定する設計になっています（権限不足で警告にフォールバックします）。

開発者向けメモ
--------------
- 設定ファイル（config/*.yaml）については validate_config が存在確認と YAML パース検証を行います（PyYAML 必要）。
- 監視 DB のスキーマは monitoring_db.init_monitoring_db で冪等に作成・マイグレーションされます。
- ユニットテストや自動化においては、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env の自動読み込みを無効化できます。

問い合わせ / 変更履歴
--------------------
- 本ドキュメントはコードベースの要点に基づいて作成されています。実運用前に必ず validate_config を実行し、ローカル環境で動作確認を行ってください。

以上。