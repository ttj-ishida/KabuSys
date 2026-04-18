KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買／研究用ライブラリと起動スクリプト群を含む軽量なフレームワークです。  
本 README ではプロジェクト概要、主な機能、セットアップ手順、使い方（起動方法やユーティリティ）、およびディレクトリ構成を日本語でまとめます。

注意：本 README はソースコード（src/kabusys 以下）を元に作成しています。実行前に .env を正しく設定してください（.env の生成補助ツールあり）。

プロジェクト概要
----------------
- 目的：日本株自動売買システムのコア実装（ポートフォリオ構築、ポジションサイズ計算、モニタリング、Execution エンジン周りのユーティリティ、研究用ファクター計算、AI を用いたニュース評価等）。
- 設計方針：
  - DB（SQLite / DuckDB）を用いた永続化と分析分離
  - ペーパートレード向けに本番 DB と分離可能
  - LLM（OpenAI）を使ったニュースセンチメント、レジーム判定機能を提供（オプション）
  - 各モジュールは可能な限り副作用を抑えた純粋関数／明確な入出力を重視

主な機能一覧
--------------
- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動（CPU/MEM/DISK、データ鮮度、プロセス監視など）
  - monitoring_engine.py / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch：監視・アラート・Kill Switch ロジック
  - monitoring_db.py：監視ログ用 SQLite スキーマ初期化・操作
- 設定・検証
  - config_setup.py: .env を対話式に作成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
  - config.py: Settings クラス（環境変数読み取り・デフォルト管理）
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py：候補選定・重み計算
  - portfolio/position_sizing.py：株数算出・リスク制限・単元丸め
  - portfolio/risk_adjustment.py：セクター上限・レジーム乗数
- 研究用（DuckDB ベース）
  - research/factor_research.py：Momentum/Volatility/Value 等のファクター計算
  - research/feature_exploration.py：将来リターン・IC 計算等
- AI（任意）
  - ai/news_nlp.py：ニュースを OpenAI に送り銘柄ごとのセンチメントを算出・書込
  - ai/regime_detector.py：ETF の MA200 とマクロニュースを合成して市場レジーム判定
- ツール
  - tools/paper_verification_report.py：ペーパートレード用検証レポート生成
- ユーティリティ
  - utils/logging_setup.py：標準化されたログ設定（コンソール + 日次ローテートファイル）
  - utils/process_priority.py：プロセス優先度・CPU affinity 設定ユーティリティ

必須・推奨依存パッケージ
------------------------
主な依存（抜粋）：
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- （任意）PyYAML（validate_config の YAML 検証用）

インストール例：
- 仮想環境作成（推奨）
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- pip インストール（requirements.txt があるならそれを使用）
  - pip install duckdb psutil openai
  - オプション: pip install pyyaml

セットアップ手順
----------------
1. リポジトリをクローン／配置し、仮想環境を作成して有効化します。
2. 必要パッケージをインストールします（上記参照）。
3. .env の作成
   - 対話式で作る（推奨）:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に .env をプロジェクトルートに作成してください。
4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に扱いたい場合: python -m kabusys.validate_config --strict
5. ディレクトリ（data, logs 等）や DB が必要に応じて自動作成されますが、パスや権限を確認してください。

主要な環境変数（抜粋）
--------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
  - paper_trading の場合、発注は MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH へ記録
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）デフォルト INFO
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant | partial | never | reject）

使い方（主要コマンド）
--------------------

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に発注ログを残します。
    - 起動時、data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中は data/execution.pid が使用されます（Settings.pid_file_path）。
    - 停止は監視側が kill.flag を書くか、stop_requested.flag を作ることで検知します。

- 監視プロセス起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL（秒）でポーリング。環境変数で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
    - 監視は Settings.sqlite_path の DB を使用（環境に関係なく本番 sqlite_path を使用する仕様）。
    - data/stop_requested.flag を作成するとループが終了します。

- .env 対話式ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（スクリプトや REPL から呼び出し）
  - ニュースセンチメント:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

停止・Kill Switch
-----------------
- 手動停止（監視により発生）:
  - KillSwitch は条件（ドローダウン超過・ポジション上限等）を満たすと data/kill.flag を書き込みます。ExecutionEngine はこれを検出して停止します。
- 即時停止（run_* スクリプトのループ停止）:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが終了します。

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging を経由して統一されています。
- デフォルトで stdout（コンソール）と logs/<app_name>.log（TimedRotatingFileHandler・日次ローテーション）に出力します。
- ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/ を使用。ディレクトリ作成に失敗するとファイル出力は無効化されコンソール出力のみになります。

注意点・運用メモ
----------------
- run_monitoring は監視データの永続化に settings.sqlite_path を使用します（監視は本番 DB を参照するという設計）。
- run_execution は paper_trading の場合 paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用して、本番 DB と分離します。
- OpenAI API を利用する機能は API キーが必須です。API 呼び出しはリトライやフォールバック（失敗時は安全な既定値）を組み込んでいますが、コストやレート制限に留意してください。
- validate_config は PyYAML がないと YAML の内容検査をスキップします（警告を出力）。
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きがあります）。

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / Settings クラス
- config_setup.py              — .env 対話式ウィザード
- validate_config.py           — 設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                 — ニュース NLP / OpenAI 連携
  - regime_detector.py          — レジーム判定（MA200 + macro sentiment）

- monitoring/
  - monitoring_db.py            — SQLite スキーマ・永続化層
  - monitoring_engine.py        — 各 Monitor を束ねるループ
  - system_monitor.py           — システム状態監視
  - risk_monitor.py             — ドローダウン / ポジション上限監視
  - trade_monitor.py            — （※実装ファイルあり）発注ログ監視
  - kill_switch.py              — kill.flag 書き込みユーティリティ
  - alert_manager.py            — 通知管理（LINE 等、実装に依存）

- execution/
  - ブローカファクトリ、ExecutionEngine、OrderManager 等（起動ロジックに依存）

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- tools/
  - __init__.py
  - paper_verification_report.py

- data/                         — 実行時生成される (data/monitoring.db, data/paper_trading.db, stop/kill フラグ等)
- logs/                         — ログ出力先（デフォルト）

（注）上記は主要ファイルの抜粋です。詳細は src/kabusys 以下の各モジュールの docstring を参照してください。

トラブルシューティング
---------------------
- DB が見つからない／ファイル権限エラー:
  - SQLITE_PATH / DUCKDB_PATH の親ディレクトリが存在するか確認してください。validate_config で事前に警告が出ます。
- OpenAI 呼び出しでエラー:
  - OPENAI_API_KEY を設定しているか確認。ネットワークやレート制限、API バージョン差分に注意。
- ログが出力されない:
  - LOG_DIR の作成に失敗していないか、または LOG_LEVEL を確認してください。setup_logging は既存ハンドラをクリアして再設定します。

最後に
------
この README はコードベース内の docstring と実装に基づく導入ガイドです。実運用に移す前に必ず validate_config で設定を確認し、ペーパートレード環境で十分な検証を行ってください。必要であれば README をプロジェクト特性に合わせて補足してください。