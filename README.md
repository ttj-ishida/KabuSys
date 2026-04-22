KabuSys — 日本株自動売買ライブラリ / 実行環境
=====================================

概要
----
KabuSys は日本株自動売買システムのコアライブラリと起動スクリプト群です。  
本リポジトリには以下の機能群が含まれます（戦略・発注・監視・研究・AI連携など）をモジュール化して提供します。  
設計の方針として、可能な限り副作用を抑えた純粋関数・DB抽象化・フェイルセーフの実装を行っています。

主な機能
--------
- 実行エンジン起動スクリプト (run_execution)：発注エンジンの起動、Broker クライアント生成、リスク管理、リコンシリエーション。
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 SQLite を使って本番 DB と分離します。
- 監視ループ起動スクリプト (run_monitoring)：SystemMonitor をポーリングしてシステム状態・データ鮮度・アラート判定を行う。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は環境に関わらず本番用 sqlite_path を参照して監視ログを永続化します。
- 設定ウィザード (config_setup)：.env ファイルの対話的作成・更新支援。
- 設定検証 CLI (validate_config)：環境変数や config/*.yaml の存在・整合性チェック。
- Paper Trading 検証レポート生成ツール (tools/paper_verification_report)：ペーパートレード DB を解析して PASS/FAIL 判定を行う。
- ポートフォリオ構築ユーティリティ（select_candidates, 重み計算, position sizing, sector cap など）。
- 研究モジュール（ファクター計算、将来リターン、IC 計算、統計サマリー）。
- AI 連携（ニュース NLP によるセンチメントスコア、レジーム判定） — OpenAI API を利用。
- ロギング／プロセス優先度ユーティリティ（共通化されたログ設定、プロセス優先度設定、CPU affinity）。

セットアップ手順
----------------
1. Python 環境を準備
   - Python 3.10+ を推奨（typing の | 記法などを利用）。
   - 仮想環境を作成して有効化するのが望ましい:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - core では少なくとも以下が必要になります:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (config ファイルの検証を行う場合、validate_config で使用)
   - 例（pip）:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合はそれを使ってください）

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env.example / README を参考に手動作成します。
   - 自動読み込み:
     - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に .env と .env.local を自動読み込みします。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - (AI を使う場合) OPENAI_API_KEY — OpenAI API キー

5. ディレクトリ作成（ログ・DB 保存先）
   - デフォルトでは data/ に DB、logs/ にログファイルを出力します。必要に応じて環境変数でパスを上書きしてください（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_DIR）。

主な環境変数（抜粋）
--------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: 発注はモックで本番 DB と分離（PAPER_TRADING_SQLITE_PATH を使用）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の MockBroker の成行約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（本番では 0 推奨）

使い方（よく使うコマンド）
-------------------------
- .env の対話式作成:
  - python -m kabusys.config_setup

- 設定の事前検証:
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH に記録します。
    - 起動前に data/stop_requested.flag が存在すると起動しません。
    - 実行中に data/stop_requested.flag が作成されるとエンジンを停止します。
    - 実行時に PID ファイル (data/execution.pid 等) を作成します（Settings.pid_file_path）。

- 監視ループ起動（SystemMonitor をポーリング）:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
  - 監視は環境変数にかかわらず本番用 sqlite_path を使用してログを残します。
  - 停止: data/stop_requested.flag を作成するとループが終了します。

- Paper Trading 検証レポートの生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / 研究機能（ライブラリとして利用）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続 (duckdb.connect(...)) を受け取り、内部で raw_news / prices_daily 等のテーブルを参照します。
  - OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡してください。

挙動に関する注意点
-------------------
- ロギング:
  - logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30 日分保持）。
  - setup_logging() が全起動スクリプトから利用され、コンソール（stdout）出力も統一されています。

- Kill Switch / 停止フラグ:
  - KillSwitch は監視結果（ドローダウンやポジション上限等）に応じて data/kill.flag を書き込みます。ExecutionEngine は起動時や実行中にこのフラグの存在をチェックして停止します。

- Paper Trading の分離:
  - paper_trading 環境では発注ロジックは MockBroker を使い、記録先は PAPER_TRADING_SQLITE_PATH を使います。これにより本番 DB と安全に分離できます。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル・インデックスを作成し、既存カラムがない場合の簡易マイグレーション（列追加）も行います。

ディレクトリ構成（主要ファイル）
-------------------------------
（root）
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - monitoring_engine.py
      - risk_monitor.py
      - trade_monitor.py (実装あり)
      - kill_switch.py
      - alert_manager.py (実装あり)
    - execution/
      - execution_engine.py (実装あり)
      - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
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
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/ (ランタイムで使用する file/pid/flag 等を置く想定)
- config/
  - *.yaml (system_config.yaml, data_config.yaml, strategy_config.yaml, ...)

さらに詳しい情報・開発者向けメモ
--------------------------------
- 自動 .env ロードの挙動:
  - プロジェクトルートが発見できる（.git または pyproject.toml）場合、.env を自動で読み込みます。
  - OS 環境変数は保護され、.env の既定値で上書きされません（.env.local は上書きモード）。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- テスト / モック:
  - AI API 呼び出しや外部接続部分はテスト時に差し替え可能な設計（関数化・依存注入）になっています。例えば news_nlp._call_openai_api を unittest.mock.patch で置き換えてテスト可能です。

- ローカル検証フロー（推奨）
  1. .env を作成（config_setup）
  2. python -m kabusys.validate_config で設定チェック
  3. データベース（DuckDB/SQLite）を準備（初期データが必要な研究機能はデータ投入）
  4. python -m kabusys.run_monitoring（別プロセスで）
  5. python -m kabusys.run_execution（別プロセスで、paper_trading で検証）

ライセンス / バージョン
----------------------
- パッケージバージョンは kabusys.__version__ で管理されています（現状 0.1.0）。
- ライセンス情報はリポジトリの LICENSE を参照してください（この README には含めていません）。

最後に
------
この README はコードベースの主要機能と典型的な利用手順をまとめたものです。実運用では config/*.yaml の内容や監視・アラート設定、運用手順（バックアップ、メトリクス監視、Alert の受信先）を十分に整備してください。質問や追加のドキュメント化が必要であればお知らせください。