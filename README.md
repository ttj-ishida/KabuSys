README — KabuSys
===============

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームです。  
このリポジトリには以下の主要機能が含まれており、取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（DuckDB を用いたファクター計算）、および AI を用いたニュースセンチメント解析などを提供します。

主な特徴
--------
- ExecutionEngine: ブローカークライアント経由で発注を行うエンジン（本番 / ペーパートレード切替可）
- Monitoring: システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を定期監視し、ログとアラートを管理
- Portfolio Construction: 候補選定、重み算出、ポジションサイズ計算（純粋関数、単体テストしやすい）
- Research: DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- AI モジュール: OpenAI（gpt-4o-mini 等）を用いるニュース NLP（銘柄別センチメント）とレジーム判定
- 各種ツール: .env 初期ウィザード、設定検証 CLI、Paper Trading 検証レポート生成など
- ロギング: 統一された logging セットアップ（console + 日次ローテートファイル）

前提（推奨）
------------
- Python 3.10+
- 必要な Python パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定 YAML の検証に必要。無くても動作する）
- OS 標準ライブラリ: sqlite3 等

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （実行環境に合わせて追加パッケージが必要になる場合があります）

4. 環境変数設定（.env を使用）
   - 初期設定ウィザードを実行して .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照してください）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の注文約定挙動）
     - KILL_FLAG_CLEAR_ON_START: 0|1（本番での自動クリアは危険。デフォルト 0）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

使い方（主要スクリプト）
-----------------------
実行用スクリプトはパッケージとしてモジュール実行できます。

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。
    - 停止するには data/stop_requested.flag を作成するか、プロセスに SIGINT（Ctrl+C）を送ってください。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 動作:
    - Settings.sqlite_path（デフォルト data/monitoring.db）に接続して監視ログを記録します（Monitoring は環境に関わらず本番 sqlite_path を使用する設計）。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（デフォルト 60 秒）。
    - 監視ループは data/stop_requested.flag を検出すると終了します。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - オプション --db で SQLite ファイル指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

ログ
----
- デフォルトのログディレクトリ: logs/
- setup_logging() によりコンソール出力（stdout）と日次ローテートファイル（logs/<app_name>.log）が設定されます。
- ログレベルは環境変数 LOG_LEVEL または引数で設定可能。

停止・Kill Switch
-----------------
- ExecutionEngine と Monitoring は data/stop_requested.flag を監視して終了します（run_* スクリプトはこれを参照）。
- KillSwitch（監視側）は data/kill.flag を書き込むことで ExecutionEngine に停止指示を出します。KILL_FLAG_CLEAR_ON_START に注意してください（本番で自動クリアは危険）。

データベース（デフォルトパス）
----------------------------
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

重要な実装メモ
--------------
- Settings は .env 自動ロード（プロジェクトルートに .git または pyproject.toml がある場合）を行います。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring_db.init_monitoring_db() は既存 DB に対して必要なテーブルとマイグレーション（カラム追加）を冪等に実行します。
- AI 機能（news_nlp / regime_detector）は OPENAI_API_KEY が必要です。API 呼び出しはリトライやフェイルセーフが組み込まれていますが、API キーが未設定だと例外になります（明示的なバリデーションあり）。

ディレクトリ構成（抜粋）
-----------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 発注エンジン関連（Broker, Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント合成）
  - data/                    — データファイル（例: data/*.db, pid/flag ファイル）
  - tools/
    - paper_verification_report.py

設定例（.env の抜粋例）
----------------------
例（手動で .env を作る場合）:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
PAPER_FILL_MODE=instant
KILL_FLAG_CLEAR_ON_START=0

運用上の注意
------------
- KABUSYS_ENV=live 設定時はすべての設定を慎重に確認してください（LINE 通知設定なども重要）。
- data ディレクトリおよびログディレクトリのパーミッション、ディスク容量を監視してください（Monitoring は disk 使用率を記録します）。
- Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番運用では危険です。デフォルト 0 を推奨します。

開発／デバッグ
--------------
- 単体関数群（portfolio/*.py、research/*.py）は外部副作用を持たない純粋関数設計になっているため、ユニットテストが容易です。
- validate_config と config_setup を使って環境を整えてから実行することを推奨します。
- ログは stdout とファイルに出るため、nohup や systemd の標準出力キャプチャを活用できます。

お問い合わせ
------------
ソースコード中の docstring とコメントに設計思想や重要な注意点を記載しています。まずはそれらを参照してください。追加の質問や拡張を行う場合は Issue を立ててください。

（バージョン: 0.1.0）