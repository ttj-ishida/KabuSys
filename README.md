README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームの一部を実装した Python パッケージです。
このリポジトリは以下の主要機能を備えています:

- 実行エンジン（ExecutionEngine）の起動スクリプト（発注処理・注文管理・リスク管理の起動）
- 監視プロセス（SystemMonitor / TradeMonitor / RiskMonitor）とポーリングループ
- Paper Trading 用の検証ツール（レポート生成）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- 研究用モジュール（ファクター計算・特徴量探索）
- ニュース NLP（OpenAI を用いたセンチメント評価）とレジーム判定
- 環境設定ウィザードおよび設定検証ツール
- ロギング・プロセス優先度などのユーティリティ

主要な設計方針:
- 本番（live）とペーパートレード（paper_trading）は DB を明確に分離
- ルックアヘッドバイアスを避けるため、日付/時間参照は慎重に実装
- OpenAI API 呼び出し等はフェイルセーフ（API障害時はフォールバック）を意識

主な機能一覧
----------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading 時は MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループを開始（ポーリング間隔は環境変数で調整可能）

- 環境設定 / 検証
  - config_setup.py: .env の対話式作成・更新ウィザード
  - validate_config.py: .env と config/*.yaml の起動前検証 CLI

- 監視
  - monitoring/monitoring_db.py: SQLite を使った監視ログ永続化（テーブル作成 / マイグレーション）
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py: 各種監視ロジック
  - monitoring/monitoring_engine.py: 監視コンポーネントの統合とポーリング、KillSwitch 評価、アラート連携

- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定・等重／スコア重み算出
  - portfolio/position_sizing.py: 発注株数・リスクベースのサイズ計算
  - portfolio/risk_adjustment.py: セクターキャップ適用、レジーム乗数

- 研究用
  - research/factor_research.py: Momentum, Volatility, Value 等のファクター計算（DuckDB 使用）
  - research/feature_exploration.py: 将来リターン計算、IC（Information Coefficient）、統計サマリ

- AI（OpenAI）連携
  - ai/news_nlp.py: ニュース記事を集約して OpenAI に送り銘柄ごとにセンチメントを算出し ai_scores に書き込む
  - ai/regime_detector.py: ETF の MA とマクロニュースのセンチメントを合成して日次レジーム判定を行う

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成（稼働率・約定率・レイテンシなど）

セットアップ手順
----------------
1. Python 環境を作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要なパッケージの例:
     - duckdb
     - psutil
     - openai
     - pyyaml（設定検証で YAML 検査を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください。）

3. プロジェクトルートに .env を用意
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考にしてください（リポジトリに例ファイルがある想定）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（抜粋とデフォルト）:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI を利用する場合に必須
     - PAPER_FILL_MODE: instant | partial | never | reject （デフォルト: instant）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict

5. 必要なディレクトリ（logs, data 等）は自動作成されますが、権限に注意してください。

使用方法（例）
----------------
- ExecutionEngine を起動（通常 / ペーパートレードに応じて DB を切り替え）
  - python -m kabusys.run_execution
  - 仕様:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に売買ログを保存します。
    - 起動時に data/stop_requested.flag が存在すると起動を行いません（停止フラグ）。
    - プロセス優先度を high に設定します（可能な場合）。
    - ExecutionEngine は data/execution.pid （デフォルト）を PID ファイルに書きます。

- 監視（SystemMonitor）を起動
  - python -m kabusys.run_monitoring
  - 仕様:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（デフォルト 60）
    - 監視は常に本番用 sqlite_path（settings.sqlite_path）を使用します（環境に関わらず）
    - ループ停止は data/stop_requested.flag を作成することで行う

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI スコアリング（プログラム的に）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定（プログラム的に）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

停止・Kill Switch
----------------
- 強制停止（ExecutionEngine を安全に止める）:
  - monitoring の KillSwitch が条件を満たすと data/kill.flag を書き込みます。ExecutionEngine 起動時にこの flag を検査します。
  - KillSwitch は Reasons をファイルに書き出します。既に存在する場合は上書きしません（冪等）。
- 管理用の停止フラグ:
  - data/stop_requested.flag: run_monitoring/run_execution の起動ループを終了させるために用いるファイル（存在するとループを抜ける）

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて初期化されます。
- 出力:
  - stdout（StreamHandler）
  - ファイル: logs/<app_name>.log （TimedRotatingFileHandler — 日次ローテーション、30世代保持）
- ログレベルは LOG_LEVEL 環境変数で設定（デフォルト INFO）

ディレクトリ構成（概観）
-----------------------
以下は src/kabusys 配下のおおまかな構成（主要ファイルのみ抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数 / .env 自動ロード
    - config_setup.py                # .env 対話式ウィザード
    - validate_config.py             # 設定検証 CLI
    - run_execution.py               # ExecutionEngine 起動スクリプト
    - run_monitoring.py              # SystemMonitor 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py # Paper Trading 検証レポート
    - ai/
      - __init__.py
      - news_nlp.py                  # ニュース NLP / OpenAI 呼び出し
      - regime_detector.py           # 市場レジーム判定
    - monitoring/
      - monitoring_db.py             # SQLite テーブル定義 / ラッパー
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py             # （ファイルは参照されるが本一覧に省略された部分あり）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py             # （アラート実装 / 省略）
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/..., execution/..., data/...   # その他サブパッケージ（実装に依存）

（上記は提供されたコードと参照箇所から推定した構成です。リポジトリ全体の正確な構成は実ディレクトリを参照してください。）

注意事項 / ベストプラクティス
---------------------------
- .env は絶対に Git にコミットしないでください。.env は機密情報（APIキー等）を含みます。
- KABUSYS_ENV を "live" に設定する場合は十分注意してください。validate_config で警告が出ます。
- OpenAI を利用する機能（news_nlp, regime_detector）は API キーが必要です。API 呼び出しによりコストとレート制限が発生します。
- Paper Trading と Live はデータベースを分離する設計です（PAPER_TRADING_SQLITE_PATH を利用）。
- ローカルでの開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化できます（主にテスト用）。

よく使うコマンドまとめ
---------------------
- .env を対話式で作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 開発メモ
-------------------
- DuckDB を利用する研究モジュール（research/*）は prices_daily / raw_financials / raw_news 等のテーブルを前提とします。データ投入パイプラインは別途用意する必要があります。
- モジュール間のテストはユニットテストで個別関数を試験し、OpenAI 等の外部呼び出しはパッチ（モック）してテストしてください。
- 監視 DB のマイグレーション（カラム追加など）は monitoring_db.init_monitoring_db の内部で行っています。既存 DB での互換性に注意してください。

ライセンスや作者情報等はリポジトリのトップレベルファイルを参照してください。README に未記載の実装詳細や追加スクリプトについてはソースコードコメントを参照してください。