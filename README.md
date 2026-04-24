KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買フレームワーク「KabuSys」の実装（主要モジュール群）です。  
実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI によるニュース解析などを含み、開発 / ペーパートレード / 本番を想定した構成になっています。

主な特徴
--------
- ExecutionEngine（売買実行）  
  - 本番・ペーパートレード切替（KABUSYS_ENV 環境変数）に対応。paper_trading 時は MockBroker を使用し、データベースは分離されます。
- Monitoring（監視）  
  - システム稼働状況、データ鮮度、注文ログ、リスク指標（ドローダウン・ポジション上限）を定期的にチェックし、kill flag を書き込むことで ExecutionEngine を停止できます。
- Portfolio 構築モジュール（候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム補正）  
  - 純粋関数群により単体テストしやすく設計。
- Research（ファクター計算・特徴量探索）  
  - DuckDB 上の prices_daily / raw_financials 等を参照してファクターを計算。
- AI モジュール（ニュース NLP / レジーム判定）  
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント算出と市場レジーム判定（API キーが必要）。
- ユーティリティ類  
  - ロギング設定、プロセス優先度設定、.env 対話式ウィザード、設定検証 CLI、Paper Trading レポート生成ツール 等。
- データ永続化  
  - DuckDB（分析用）と SQLite（監視・発注ログ用）を利用。

セットアップ手順
----------------
前提:
- Python 3.10+ を推奨（typing の union 演算子 `X | Y` を利用）
- システムに duckdb, psutil, openai 等をインストール可能であること

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML
   - （実際の requirements.txt がある場合はそれを利用してください）

4. 環境変数設定（.env）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または環境変数を直接設定:
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 任意: OPENAI_API_KEY（AI モジュールを使う場合）
   - 自動 .env 読み込み:
     - プロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数が優先）。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告を FAIL としたい場合は --strict を付けます。

6. ディレクトリと初期ファイル
   - data/ や logs/ は起動時に自動作成されますが、手動で作成しておくと権限エラーを回避できます。

主な環境変数（抜粋）
-------------------
- KABUSYS_ENV: 実行モード (development | paper_trading | live)
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
- LOG_LEVEL / LOG_DIR: ログ設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モデル（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 本番で Kill Flag を起動時にクリアするか（0/1、デフォルト 0）

使い方（起動・ツール）
---------------------
主な CLI / モジュールの呼び出し方：

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（売買実行）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV で制御（paper_trading の場合は MockBroker と専用 DB を使用）
  - 停止方法:
    - run_execution と run_monitoring の両方はプロジェクトルート下 data/stop_requested.flag を検知して終了します。
    - Monitoring 側の KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止を指示します。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でループ間隔を上書き可能（秒）
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使います（環境にかかわらず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - 出力: 標準出力にサマリ（稼働率、注文成功率、レイテンシ等）と PASS/FAIL 判定

- AI モジュール（ニューススコア / レジーム判定）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）
    - ai_scores テーブルにスコアを書き込みます
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

重要ファイル（運用時の挙動）
---------------------------
- data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルの存在を監視して安全終了します。
- data/kill.flag
  - Monitoring の KillSwitch が書き込むファイル。ExecutionEngine 側は起動時や監視で検知して停止します。
- data/execution.pid
  - ExecutionEngine の PID を保存するファイルパス（Settings.pid_file_path）
- logs/<app>.log
  - 日次ローテートでログが保存されます（logs ディレクトリ）。

内部の主なモジュール（機能一覧）
------------------------------
- kabusys.config: 環境変数 / .env ロード、Settings クラス
- kabusys.config_setup: .env 対話式ウィザード
- kabusys.validate_config: 起動前検証 CLI
- kabusys.run_execution: ExecutionEngine 起動スクリプト
- kabusys.run_monitoring: Monitoring ポーリング起動スクリプト
- kabusys.utils.logging_setup: ロギング初期化ユーティリティ
- kabusys.utils.process_priority: プロセス優先度・CPU affinity 設定
- kabusys.monitoring.*:
  - monitoring_db: SQLite スキーマ初期化 + 永続化 API
  - system_monitor: CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor: 発注ログの監視（滞留注文／約定異常など）
  - risk_monitor: ドローダウン・ポジション上限監視
  - kill_switch: Kill Switch 実装（kill.flag 書込）
  - monitoring_engine: 各 Monitor を束ねるポーリングエンジン
  - alert_manager: （アラート通知の抽象化）
- kabusys.execution.*: Execution エンジン・Order 管理・ブローカー抽象（実ブローカ/モック）
- kabusys.portfolio.*: 候補抽出、重み計算、ポジションサイジング、セクター調整、レジーム乗数
- kabusys.research.*: ファクター計算、特徴量探索、統計ユーティリティ
- kabusys.ai.*: news_nlp（ニュースセンチメント）, regime_detector（市場レジーム）
- kabusys.tools.paper_verification_report: ペーパートレード検証ツール

ディレクトリ構成（抜粋）
----------------------
リポジトリの主要なファイル構成（src/kabusys 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (想定)
    - execution/
      - execution_engine.py (想定)
      - order_manager.py (想定)
      - broker_factory.py (想定)
      - ... (その他)
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
    - data/ (実行時に作成される想定)
    - logs/ (実行時に作成される想定)
  - config/
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml
    - (yaml ファイルは generate スクリプト等で生成可能)

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では設定（LINE 通知 / kill flag の挙動等）を慎重に確認してください。validate_config は本番向けの追加チェックを行います。
- OpenAI 等外部 API キーは .env を通じて安全に管理し、決して Git にコミットしないでください。
- ペーパートレードは本番 DB と分離されますが、ロジックの検証に利用する場合は定期的に paper_trading DB のバックアップを取ってください。
- run_monitoring は常に Settings.sqlite_path を使用します。監視データは本番の monitoring.db に保存されるため、環境変数によるパス指定に注意してください。

よくある運用コマンド例
--------------------
- .env を作りたい:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- ペーパートレードでエンジン起動:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- 監視を起動（デフォルト 60 秒間隔）:
  - python -m kabusys.run_monitoring
  - 間隔変更: export MONITOR_POLL_INTERVAL=30

サポート / 追加情報
-------------------
- 各モジュールはドキュメント文字列（docstring）で意図と設計方針を明記しています。実装の詳細やパラメータ調整は該当モジュールの docstring を参照してください。
- config/*.yaml や追加の運用用スクリプト（generate_config.py 等）はプロジェクトに含めるか、運用ドキュメントに従って生成してください。

ライセンス / コントリビューション
---------------------------------
- 本 README ではライセンス情報を省略しています。実際のプロジェクトでは LICENSE ファイルを配置してください。  
- コントリビューション方針やコードスタイルについては別途 CONTRIBUTING.md を用意することを推奨します。

以上。セットアップや実行で不明点があれば、どのコマンドやどの機能について追加説明が必要か教えてください。