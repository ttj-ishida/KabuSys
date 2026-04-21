KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株を対象とした自動売買システムの骨格実装です。本リポジトリは以下の主要機能群を持ち、実運用（live）とペーパートレード（paper_trading）の両モードに対応します。

- 戦略・ポートフォリオ構築（ファクター計算、ポジションサイズ決定、セクター制限等）
- ExecutionEngine（ブローカー連携、発注管理、リスク管理、約定ログ）
- Monitoring（システム健全性、注文滞留、ドローダウン監視、Kill Switch）
- AI 支援（ニュースの NLP スコアリング / レジーム判定：OpenAI を使用）
- 開発用ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

主な特徴
--------
- 明確に分離されたコンポーネント（execution / monitoring / portfolio / research / ai）
- ペーパートレード用の完全分離 DB（data/paper_trading.db）と MockBroker のサポート
- DuckDB を用いた研究用テーブル（prices_daily / raw_financials 等）との連携
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価・レジーム判定（オプション）
- 日次ローテーションのログ出力、プロセス優先度設定、Kill Switch による安全停止

セットアップ手順
----------------
1. Python 環境の準備（推奨: venv）
   - Linux / macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 必要パッケージのインストール
   - 必要なパッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML パースを行いたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt が無い場合は上記を参考にインストールしてください。

3. .env の用意
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくはリポジトリルートに .env を配置（.env.example を参照して作成）
   - 自動ロード:
     - config.Settings モジュールはデフォルトでプロジェクトルートの .env / .env.local を自動ロードします。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 設定の検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ作成（任意）
   - data/ や logs/ は起動時に自動作成されることが多いですが、権限等が不安な場合は事前に作成しておくと安全です。

主要な環境変数（抜粋）
----------------------
- JQUANTS_REFRESH_TOKEN : J-Quants API 用（必須）
- KABU_API_PASSWORD     : kabuステーション API 用（必須）
- KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV           : 実行環境（development / paper_trading / live）
- PAPER_FILL_MODE       : ペーパー売買の fill モード（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
- OPENAI_API_KEY        : OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL, LOG_DIR
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアする（本番では 0 推奨）
- MONITOR_POLL_INTERVAL : Monitoring のポーリング間隔（秒、デフォルト 60）

使い方（起動・実行）
--------------------

- ExecutionEngine（発注エンジン）起動
  - 実行:
    - python -m kabusys.run_execution
  - ポイント:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading_db（デフォルト data/paper_trading.db）へ記録します。
    - 起動時に stop flag（data/stop_requested.flag）が立っていると起動しません。
    - 実行中は data/execution.pid に PID を書き込みます。
    - 停止は Kill Switch（data/kill.flag）や stop_requested.flag により制御されます。

- Monitoring 起動（SystemMonitor のポーリング）
  - 実行:
    - python -m kabusys.run_monitoring
  - ポイント:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します。
    - data/stop_requested.flag を作成するとループを安全に終了します。

- .env ウィザード（初期設定）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB は --db または PAPER_TRADING_SQLITE_PATH で指定（デフォルト: data/paper_trading.db）

- AI 関連（ニュース NLP / レジーム判定）
  - ai モジュールは OpenAI API キー（OPENAI_API_KEY）を参照します。
  - 主要 API:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB 接続を作成して渡す必要があります（研究・運用スクリプト内で利用）。

停止・Kill Switch
-----------------
- ExecutionEngine に対する安全停止は以下の仕組みを使用します:
  - KillSwitch: 条件（ドローダウン超過、ポジション上限など）を満たすと data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - 手動停止フラグ: data/stop_requested.flag を作成すると run_monitoring / run_execution の主ループ検出で停止します。
- run_execution は起動時に KILL_FLAG_CLEAR_ON_START 設定を参照し、必要に応じて既存の kill.flag をクリアします（本番では無効推奨）。

ディレクトリ構成（抜粋）
-----------------------
リポジトリの主要なソース配置は src/kabusys 以下です。代表的な構成:

- src/kabusys/
  - __init__.py                (パッケージ定義、バージョン)
  - config.py                  (環境変数 / Settings)
  - config_setup.py            (.env 対話式ウィザード)
  - validate_config.py         (設定検証 CLI)
  - run_execution.py           (ExecutionEngine 起動スクリプト)
  - run_monitoring.py          (SystemMonitor 起動スクリプト)
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (省略参照)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (省略参照)
  - execution/
    - execution_engine.py (省略参照)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - data/ (想定されるディレクトリ)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (ペーパートレード)
  - logs/ (ログ出力先, LOG_DIR)

設計上の注意点 / 動作上の留意点
------------------------------
- 設定の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env / .env.local を読み込みます。
  - OS 環境変数が優先され、.env.local は .env を上書きできます。
- DB マイグレーション:
  - init_monitoring_db() は冪等でテーブルを作成し、既存 DB に不足カラムがあれば ALTER で追加する簡易マイグレーション処理を行います。
- ロギング:
  - 共通の setup_logging() を利用して stdout と日次ローテートファイルログ（logs/<app>.log）を設定します。
- 実行優先度:
  - 起動スクリプトは set_process_priority("high") を呼び出してプロセス優先度を高めようとします。権限によっては失敗して警告になります。
- AI 呼び出し:
  - OpenAI 呼び出しは外部 API 依存です。API キー管理とレート制限に注意してください。ネットワーク／429／5xx の場合は指数バックオフでリトライする設計です。
- ペーパートレード:
  - KABUSYS_ENV=paper_trading の場合は本番 DB と完全分離された paper_trading DB を使用します（デフォルト: data/paper_trading.db）。

トラブルシューティング
---------------------
- .env を作成したが読み込まれない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認。必要なら手動で環境変数を export してください。
- DuckDB / SQLite ファイルが見つからない:
  - デフォルトパスは data/ 以下です。ファイルが無ければ起動コンポーネントが自動作成する場合がありますが、パーミッションやパスが正しいか確認してください。
- OpenAI 呼び出しで失敗する:
  - OPENAI_API_KEY が正しく設定されているか、ネットワーク接続とレート制限を確認してください。

開発者向けメモ
----------------
- 研究用の計算（factor_research, feature_exploration 等）は DuckDB 接続を受け取り SQL と純粋関数で実装されています。ユニットテストが容易な設計です。
- モジュール間でグローバルに OpenAI 呼び出し関数を共有せず、各モジュールでラップしているためテスト時に個別にモックしやすくなっています。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py 内で定義されています（現在: 0.1.0）。
- ライセンス情報はリポジトリに別途含めてください（本 README にライセンスの記載はありません）。

最後に
------
この README はコードベースの主要機能と運用上のポイントをまとめたものです。個別モジュールの詳しい使い方（ExecutionEngine の設定や Broker の実装詳細、strategy の作成方法など）は該当ファイルの docstring / コメントを参照してください。必要であれば運用手順（デプロイ・起動スクリプト・cron/サービス定義）や requirements.txt、サンプル .env を追加で提供できます。希望があれば教えてください。