README
======

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買・研究プラットフォームのコードベースです。  
主な目的は以下です。

- 売買シグナルに基づくポートフォリオ構築および発注（ExecutionEngine）
- 実行・約定の監視とリスクガード（Monitoring）
- ファクター計算・リサーチ用ユーティリティ（Research）
- ニュースの NLP によるセンチメント評価 / レジーム判定（AI）
- ペーパートレードの検証レポート生成などのツール群

本リポジトリはモジュール化されており、ローカル開発（development）、ペーパートレード（paper_trading）、本番（live）を切り替えて動作します。

主な機能（機能一覧）
-------------------
- Execution
  - ExecutionEngine（発注エンジン）起動スクリプト: run_execution.py
  - ブローカー抽象化（実口座 / MockBroker の切り替え）
  - 注文管理・リコンシリエーション・リスク管理
- Monitoring
  - SystemMonitor, TradeMonitor, RiskMonitor を統合する監視エンジン
  - SQLite に監視ログ（system_status, trade_logs, risk_logs, dashboard）を永続化
  - Kill Switch（条件により data/kill.flag を書き込み Execution を停止）
  - run_monitoring.py によるポーリングループ起動
- Portfolio
  - 候補選定・重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（momentum, volatility, value 等）
  - 将来リターン計算、IC（Information Coefficient）などの統計ユーティリティ
- AI（OpenAI）
  - ニュース記事の銘柄別センチメントスコア化（news_nlp.score_news）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（regime_detector.score_regime）
  - OpenAI の呼び出しは冪等・リトライ・フォールバック設計
- ツール
  - 設定ウィザード（config_setup.py）で .env を対話式生成
  - 設定検証 CLI（validate_config.py）で .env / config/*.yaml の基本チェック
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）

セットアップ手順
----------------
前提
- Python 3.10 以上（typing における | 演算子などを使用）
- システムに sqlite3 が利用可能
- 必要な外部ライブラリ（以下を参考にインストール）

推奨パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（config の YAML 検証を行う場合）
- その他（実行環境に応じて）

例: 仮想環境作成とインストール
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- pip install -U pip
- pip install duckdb psutil openai PyYAML

（もし requirements.txt がある場合）
- pip install -r requirements.txt

環境変数 / 設定ファイル
- .env をルートに配置すると自動で読み込まれます（.env.local があれば上書き）。  
  自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 重要な必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabuステーション API）
- 主要な設定（デフォルト値を含む）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO 等
  - OPENAI_API_KEY: OpenAI を使う場合に必要
  - PAPER_FILL_MODE: ペーパートレードの約定方式（instant/partial/never/reject）
- .env を対話的に作る:
  - python -m kabusys.config_setup

設定検証
- .env や config/*.yaml の基本チェック:
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いになります

使い方（起動・実行）
-------------------

1) 監視プロセスを起動
- run_monitoring.py は SystemMonitor のポーリングループを実行します。既定のポーリング間隔は 60 秒で、環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能。
- 起動:
  - python -m kabusys.run_monitoring
- 停止:
  - リポジトリルートの data/stop_requested.flag を作成するとループが終了します（stop フラグ）。
  - kill.flag は ExecutionEngine を止めるためのフラグ（KillSwitch が書き込む）です。

2) 実行エンジン（Execution）を起動
- paper_trading モードでは MockBrokerClient を使い、専用の PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db）に記録されます。
- 起動:
  - python -m kabusys.run_execution
- 停止:
  - data/stop_requested.flag を作成するか、Monitoring 側で kill.flag を書くことで停止命令が発行されます。
- PID 管理:
  - 実行中は data/execution.pid（デフォルト）に PID を書く挙動があります（設定で変更可）。

3) Paper Trading 検証レポート
- データベース（ペーパー用 SQLite）から検証レポートを生成します。
- 例:
  - python -m kabusys.tools.paper_verification_report
  - 日付範囲: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB を直接指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

4) AI 系（OpenAI）の利用
- news_nlp.score_news / regime_detector.score_regime は OpenAI API キーが必要です。環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡します。
- OpenAI 呼び出しは内部でリトライ・フォールバックロジックを持ち、失敗時は安全に継続します。

主要な環境変数のまとめ
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development|paper_trading|live)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- OPENAI_API_KEY (AI 機能利用時に必須)
- MONITOR_POLL_INTERVAL (監視ポーリング秒)
- PAPER_FILL_MODE (paper_trading 用: instant|partial|never|reject)
- LOG_LEVEL / LOG_DIR

ログとデータベース
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて一貫して行われます。
  - デフォルト出力先: stdout + logs/<app_name>.log（日次ローテーション、30 日保持）
- 監視/実行に使う SQLite / DuckDB のデフォルトパスは上記の通り（data フォルダ下）。
- monitoring_db.init_monitoring_db() により監視用テーブル群が自動作成・マイグレーションされます。

停止・Kill Switch の振る舞い
- Monitoring の各チェックにより条件を満たした場合、KillSwitch が data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります（冪等）。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアしますが、本番では推奨されません（安全上の理由）。

ディレクトリ構成
----------------
リポジトリの主要ファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/               — （発注エンジン関連モジュール群）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py

補足・運用上の注意
-----------------
- 本プロジェクトは実際の発注機能を含むため、本番（KABUSYS_ENV=live）での運用前には必ず設定を validate（python -m kabusys.validate_config）してください。
- .env ファイルは機密情報（API トークンなど）を含むため、絶対にバージョン管理にコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。
- Paper Trading は実口座を操作しないモードですが、設定ミスがないか慎重に確認してください（デフォルト DB パス等）。
- OpenAI API を使う機能は追加コストが発生します。使用する際は API キー管理・コスト管理に注意してください。

ライセンス / バージョン
---------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。

問い合わせ・開発者向けメモ
------------------------
- ログの詳細設定やテスト用のモックは各ユーティリティ内（logging_setup, process_priority, AI 呼び出しラッパー等）で差し替え可能です。
- DuckDB 接続を受け取る関数群は副作用を避けるため接続を呼び出し元で作成して渡す設計です（テストが容易）。
- schema や config ファイルの自動生成スクリプトがある場合は scripts ディレクトリ等に配置して運用してください（本リポジトリでは config/*.yaml を参照する機能あり）。

以上が README の概要です。必要であれば「導入に必要な具体的な requirements.txt の例」「systemd / Supervisor 用の起動スクリプト」「運用チェックリスト」などを追記できます。どの情報を優先して追加しますか？