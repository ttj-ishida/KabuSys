README.md

KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視ユーティリティ群をまとめた Python パッケージです。本リポジトリは以下の主要機能を提供します。

- 実行エンジン（ExecutionEngine）による発注処理（本番 / ペーパートレード切替）
- 監視コンポーネント（System / Trade / Risk）による定期チェック・アラート・Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ向けモジュール（ファクター計算、特徴量解析、IC計算）
- AI 支援機能（ニュースの NLP スコアリング、マーケットレジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度、設定ウィザード・検証など）
- ペーパートレード用検証レポート生成ツール

主な機能一覧
--------------
- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて本番 / ペーパー切替）
  - paper_trading 環境では MockBrokerClient を用い、data/paper_trading.db に記録
- run_monitoring.py: SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔制御）
  - 監視は環境に関わらず本番用 sqlite_path を参照します
- config_setup.py: .env 対話式ウィザード（初期設定・更新支援）
- validate_config.py: 環境変数・config/*.yaml の起動前検証 CLI
- tools/paper_verification_report.py: ペーパートレード検証レポート生成
- portfolio/*: 候補選定・重み付け・ポジションサイズ計算・リスク調整
- research/*: ファクター計算（Momentum / Value / Volatility 等）、特徴量解析・IC
- ai/news_nlp.py: OpenAI を使ったニュースセンチメント評価（ai_scores へ書込）
- ai/regime_detector.py: ETF とマクロニュースを組合せたレジーム判定と DB 書込
- monitoring/*: 監視用 DB 層・各種モニタ・KillSwitch・MonitoringEngine
- utils/*: ログ設定、プロセス優先度設定など

前提・依存ライブラリ（例）
-------------------------
推奨 Python バージョン: 3.10+

主な依存パッケージ（pip でインストールしてください）:
- duckdb
- psutil
- openai
- PyYAML（config の YAML 検証を行う場合）
- そのほか、環境に応じて必要になるライブラリ（requests 等）は各ブローカー実装次第

セットアップ手順
-----------------
1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成 & 有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Linux/macOS
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt がある場合は pip install -r requirements.txt）

4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - ウィザードに従って J-Quants リフレッシュトークン、kabu ステーションのパスワード等を設定します
   - 生成された .env は絶対に Git にコミットしないでください

5. 設定検証
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けて警告もエラー扱いにできます

6. データディレクトリ等の準備
   - デフォルト DB / ログの場所は .env で指定できます（デフォルト: data/, logs/）
   - 必要なディレクトリは自動作成されますが、パーミッション等を事前に確認してください

環境変数（主なもの）
--------------------
主な環境変数（.env に記述）:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 環境時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル保存先（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1）

使い方（起動例）
----------------

- ExecutionEngine 起動（本番 / ペーパーは KABUSYS_ENV に依存）
  - 本番（例）
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード（mock ブローカー / 専用 DB）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  補足:
  - paper_trading の場合、MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。
  - ExecutionEngine は data/execution.pid に PID を書き、停止はデータパスの stop フラグや kill.flag により制御します。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は環境に関係なく SQLite の monitoring DB（SQLITE_PATH）を使用します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付与すると警告でも exit(1) になります

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ライブラリ関数として呼ぶ）
  - news_nlp.score_news、regime_detector.score_regime は DuckDB 接続と target_date、API キーを受け取ります。
  - 例（スクリプトから）:
    from openai import OpenAI
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,20), api_key="sk-...")

停止・Kill Switch の運用
-----------------------
- Graceful stop:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了します。
    - touch data/stop_requested.flag
  - 削除して再起動 (rm data/stop_requested.flag)

- Kill Switch（自動的に ExecutionEngine を停止する仕組み）
  - monitoring の KillSwitch は data/kill.flag を書き込んで ExecutionEngine に停止を指示します
  - ExecutionEngine は起動時に kill.flag のクリア運用を制御できます（KILL_FLAG_CLEAR_ON_START）
  - kill.flag の手動クリア:
    - rm data/kill.flag

ログ
----
- ログはデフォルトで logs/ 以下に日次ローテーションで保存されます（TimedRotatingFileHandler）。
- コンソール出力は stdout に出ます。
- ログ設定は kabusys.utils.logging_setup.setup_logging から一貫して行われます。

データベース
-----------
- DuckDB: 分析用（prices_daily / raw_financials / raw_news / ai_scores / market_regime など）
  - デフォルト: data/kabusys.duckdb
- SQLite: 監視ログ・注文ログ・ポジション等
  - 監視 DB（monitoring）デフォルト: data/monitoring.db
  - ペーパートレード専用 DB（paper_trading）デフォルト: data/paper_trading.db

ディレクトリ構成
-----------------
（src/kabusys をルートとした概略）
- kabusys/
  - __init__.py
  - config.py                # 環境変数 / .env の読み込み・Settings
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 起動前検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring 起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP スコアリング
    - regime_detector.py     # 市場レジーム判定
  - monitoring/
    - monitoring_db.py       # SQLite 永続化（schema init + CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       # （実装によっては通知処理を行う）
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
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
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                     # 実行時に使用されるデータファイル（.gitignore 推奨）
    - kill.flag
    - stop_requested.flag
    - execution.pid
    - monitoring.db
    - paper_trading.db
  - logs/                     # ログ出力先（デフォルト）

開発・テストに関する注意
------------------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- KABUSYS_ENV=live 時は本番資金が動くため設定・アクセスキー類は慎重に取り扱ってください。
- validate_config.py によるチェックを必ず行い、特に本番環境では LINE 通知設定などを確認してください。
- AI 機能は OpenAI API キーと料金が発生します。テスト用にはモック化を推奨します（ユニットテスト時に API 呼び出し関数をパッチする設計）。

トラブルシューティング
----------------------
- ログディレクトリ作成に失敗した場合、コンソール出力のみで継続します。パーミッションを確認してください。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使用します。テスト時は sqlite_path を変更するかモックを使ってください。
- OpenAI API 呼び出しでのレート制限や一時エラーは各モジュールでリトライ・フォールバック実装がありますが、API キーやネットワークの状態を確認してください。

貢献・拡張
----------
- ブローカー実装（BrokerClientFactory 配下）を追加して新しい実取引 API を統合できます。
- ポートフォリオ構築・リスク管理のロジックは純関数群として分離されているため、ユニットテストと差し替えが容易です。
- AI モジュールのプロンプトやモデルは定数として分かれているため、モデル変更やプロンプト改善がしやすくなっています。

ライセンス
---------
- 本リポジトリのライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

以上。必要であれば README にサンプル .env テンプレートや具体的なコマンド例（systemd ユニットの例、Docker 利用法等）を追加できます。どの情報を追加しますか？