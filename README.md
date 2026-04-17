README
======

概要
----
KabuSys は日本株の自動売買システムのコアライブラリ群です。マーケットデータの集計・ファクター計算、ポートフォリオ構築、発注エンジンの起動補助、監視・アラート、AI を使ったニュースセンチメント評価などの機能を提供します。パッケージは純粋関数群（研究用）と実行系（ExecutionEngine / Monitoring）を含み、Paper Trading（模擬発注）モードと Live モードを分離して運用できます。

主な機能
--------
- 環境設定ウィザード（.env を対話式で生成 / 更新）
- 設定検証 CLI（.env と config/*.yaml の簡易チェック）
- ExecutionEngine 起動スクリプト（本番 / ペーパー分離、PID 管理）
- Monitoring（システム状態、注文滞留、ドローダウン監視、Kill Switch）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ）
- リサーチ／ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI モジュール（ニュースセンチメントスコアリング、レジーム判定）
- Paper Trading 検証レポート生成ツール

依存関係（主な外部ライブラリ）
------------------------------
- Python 3.8+
- duckdb
- psutil
- openai
- requests
- PyYAML（config 検証時にあれば YAML 内容も検証）
（※標準ライブラリ: sqlite3, pathlib, logging などを使用）

セットアップ手順
----------------
1. リポジトリをクローンし、プロジェクトルートへ移動します。

2. 仮想環境を作成して有効化します（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存関係をインストールします（pip の要件ファイルがある前提）。
   - pip install duckdb psutil openai requests PyYAML

4. .env を準備します（下記「環境変数」を参照）。
   - 対話式ウィザードで作成：
     - python -m kabusys.config_setup
   - 既存の .env がある場合、OS 環境変数より低優先で自動ロードされます（プロジェクトルートが .git または pyproject.toml を含む場合）。

環境変数（主要）
----------------
主に kabusys/config.py で参照される環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: execution モード（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 発注の約定挙動（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

（.env 例）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx

初期設定と検証
----------------
1. .env の作成（対話式）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

使い方（起動 / 実行）
--------------------

- 監視プロセス（SystemMonitor / MonitoringEngine の簡易起動スクリプト）
  - python -m kabusys.run_monitoring
  - 概要:
    - プロセス優先度を高に設定し、SQLite（monitoring DB）と DuckDB を接続。
    - SystemMonitor をポーリングして system_status 等を記録。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）。

  - 停止:
    - プロセスはプロジェクトの data/stop_requested.flag を検知するとループを抜けて終了します。

- 発注実行エンジン（ExecutionEngine 起動スクリプト）
  - python -m kabusys.run_execution
  - 概要:
    - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）。
    - PID ファイルを data/execution.pid に書き、停止フラグ data/stop_requested.flag を監視して終了。
  - 停止:
    - data/stop_requested.flag を置くとエンジンに停止要求を送れます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で SQLite DB を直接指定（デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI 系ユーティリティ（プログラム内 API）
  - ニュースセンチメントスコア:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
      - conn: DuckDB 接続（raw_news / news_symbols / ai_scores 等が必要）
      - api_key: None の場合 OPENAI_API_KEY を参照
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意・運用メモ
--------------
- Paper Trading と Live の DB は分離されています（paper_trading は paper_sqlite_path を使用）。
- Monitoring は KABUSYS_ENV に関わらず、監視用の本番 sqlite_path を使用する設計です（監視データは共通的に扱われます）。
- Process priority / CPU affinity 設定は psutil を利用します。権限不足や未対応 OS の場合は警告を出してスキップします。
- OpenAI を使う機能は API 呼び出しに失敗した際にフェイルセーフ（既定のフォールバック値）で継続する設計ですが、APIキーの設定は必須の処理もあります。
- DuckDB 内のテーブル（prices_daily, raw_financials, raw_news, news_symbols など）はデータパイプライン（本リポジトリ外）で準備する必要があります。

停止と Kill Switch
-------------------
- run_monitoring / run_execution はプロジェクトルートの data/stop_requested.flag を確認して停止します。
  - これを作成すれば安全に両プロセスのループを抜けます。
- KillSwitch（監視サイド）は条件を満たすと data/kill.flag を書き込み、ExecutionEngine の停止トリガーになります（運用上の安全弁）。
- 実運用では KILL_FLAG_CLEAR_ON_START の設定に注意してください（live 環境では自動クリアは危険）。

ディレクトリ構成（抜粋）
------------------------
以下は主要モジュールを抜粋したソースツリーです（src/kabusys 以下）。

- src/
  - kabusys/
    - __init__.py
    - config.py                  # 環境変数・設定読み込みロジック
    - config_setup.py            # .env 対話式ウィザード
    - validate_config.py         # 設定検証 CLI
    - run_monitoring.py          # SystemMonitor ポーリング起動スクリプト
    - run_execution.py           # ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py              # ニュース NLP スコアリング
      - regime_detector.py       # レジーム判定
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - alert_manager.py
      - kill_switch.py
    - execution/                  # （発注エンジン関連、コード一部が本リポジトリにあることを想定）
      - ... (order_manager, order_repository, execution_engine 等)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
    - data/                       # 実行時に生成・利用する場所（DB ファイル・flag 等）
      - monitoring.db (SQLITE_PATH)
      - kabusys.duckdb (DUCKDB_PATH)
      - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
      - execution.pid
      - stop_requested.flag
      - kill.flag

補足
----
- 本 README はコードベースのソースからの概要説明です。データの取得 / 前処理（prices_daily などを作るデータパイプライン）は別途準備が必要です。
- 運用時は .env を絶対にリポジトリにコミットしないでください（秘密情報保護）。

問題や改善提案があれば、Issue を作成してください。