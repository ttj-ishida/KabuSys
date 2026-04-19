KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム向けライブラリ／コア実装群です。  
主な目的は、戦略の研究（ファクター計算・特徴量探索）、ポートフォリオ構築・ポジションサイジング、注文実行エンジン（paper/live）、監視（モニタリング）および運用支援ツール（設定ウィザード／検証／レポート生成）を提供することです。  
モジュール化されており、DuckDB（分析用）、SQLite（監視／ペーパートレード用）や OpenAI のような外部 API を組み合わせて利用します。

主な機能
---------
- Execution エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db に記録
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行して system_status / trade_logs / risk_logs / dashboard を更新
  - Kill Switch（閾値に達したら data/kill.flag を書き ExecutionEngine を停止）
- 設定管理・ウィザード（config_setup.py）
  - .env の対話的作成・更新支援
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の基本チェック（--strict オプションあり）
- 研究用モジュール（research）
  - ファクター計算（momentum/value/volatility）、将来リターン計算、IC 計算、統計サマリ
- ポートフォリオ構築（portfolio）
  - 候補抽出、等重／スコア重み付け、リスク調整（セクターキャップ／レジーム乗数）、ポジションサイズ算出（単元丸め・aggregate cap）
- AI系モジュール（ai）
  - news_nlp: OpenAI を用いたニュースセンチメントスコアリング（ai_scores テーブル書き込み）
  - regime_detector: ETF MA とマクロニュースから市場レジームを判定し market_regime に書き込み
- 運用ツール（tools）
  - paper_verification_report: ペーパートレード DB を解析して合否レポートを生成
- ユーティリティ
  - ロギング設定（logs ディレクトリに日次ローテートファイル + stdout）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- DB スキーマ用ユーティリティ
  - monitoring_db.init_monitoring_db: 監視用 SQLite の初期化 / マイグレーション処理

システム要件
------------
- Python 3.10+（型注釈で | を使用）
- 依存パッケージ（主に、実行環境で必要なもの）
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML （validate_config の YAML 検証で任意）
- OS：Linux / macOS / Windows（process priority は OS による差分あり）

セットアップ手順
----------------
1. リポジトリをクローン（省略）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （必要に応じて）pip install pyyaml

   ※ requirements.txt がある場合は pip install -r requirements.txt を使用してください。

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env を手動で作成（例を下記参照）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 厳格モード: python -m kabusys.validate_config --strict

6. 初回 DB 作成
   - 実行スクリプト（run_monitoring / run_execution）が起動時に必要なテーブルを作成します。手動での事前準備は不要です。

環境変数（主なもの）
-------------------
（config_setup が扱う項目の主要サマリ）

- KABUSYS_ENV: 実行環境
  - development / paper_trading / live
  - paper_trading: MockBroker を使用し、paper_sqlite_path に記録
  - live: 実際に発注を行うモード（注意）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使用する場合は必須（ai モジュール）

運用時に便利なファイル / フラグ
------------------------------
- data/stop_requested.flag
  - run_monitoring.py / run_execution.py はこのファイルを監視して停止処理を実行します。プロセスの外部停止を行いたい場合はこのファイルを作成してください。
- data/kill.flag
  - KillSwitch により書き込まれるファイル。ExecutionEngine 停止のためのシグナル。
- data/execution.pid
  - run_execution が PID を書き込むパス（設定で変更可）
- logs/
  - デフォルトのログ格納先（app_name に応じてファイル名が決まる。例: logs/execution.log, logs/monitoring.log）

使い方（コマンド）
-----------------

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: プロジェクトルート直下の data/stop_requested.flag を作成するとループが終了します

- Execution（エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録されます（本番 DB と分離）
  - 停止: data/stop_requested.flag を作成することにより実行中エンジンを停止

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI モジュール（プログラム的に利用）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date、OpenAI API キーが必要です。
  - 例（Python REPL）:
    - import duckdb
    - from datetime import date
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, date(2026, 4, 1), api_key="sk-...")

補足（監視と Kill Switch の振る舞い）
-----------------------------------
- Monitoring は Settings の sqlite_path（監視 DB）を使用して system_status / trade_logs 等を書き込み・集計します（KABUSYS_ENV に依らず本番 sqlite_path を使います）。
- KillSwitch は RiskMonitor 等の結果を評価して data/kill.flag を作成します。ExecutionEngine は起動時にこの kill.flag をチェックし、検出されると停止します。

ディレクトリ構成
----------------
以下は src/kabusys 配下の主なファイル／ディレクトリ構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス（自動 .env ロード機能含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB の初期化・永続化クラス
    - system_monitor.py
    - trade_monitor.py       — （ソースに含まれる想定モジュール）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信管理、実装あり）
  - execution/
    - execution_engine.py    — エンジン本体（実行ループ）
    - broker_factory.py      — ブローカークライアント生成（Mock/実ブローカー切替）
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
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

開発メモ / 注意点
-----------------
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注記あり）。
- OpenAI を使う機能は API キーが必須です。API 呼び出しはリトライやフェイルセーフを備えていますが、API 利用コストとレート制限に注意してください。
- run_execution.py は PID ファイルと stop flag による外部制御を行います。運用時は stop_requested.flag / kill.flag の扱いに注意してください。
- logging_setup により stdout と logs/<app>.log に出力されます。ログディレクトリ作成に失敗した場合はファイル出力が無効化され stdout のみになります。
- Settings は自動でプロジェクトルートの .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

サンプル .env（最小例）
---------------------
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

最後に
------
この README はコードベースの主要機能・実行手順の要点をまとめたものです。開発や運用時は config/*.yaml やスクリプト内の docstring（関数コメント）を参照してください。必要であれば、特定モジュール（例: ExecutionEngine の挙動、BrokerClient 実装、trade_monitor の詳細）の追加ドキュメントを作成します。