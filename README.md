KabuSys
=======

概要
----
KabuSys は日本株の自動売買 / 研究 / モニタリング用の小規模フレームワークです。本リポジトリは以下の主要機能を提供します。

- 実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注・注文管理を行う（実装の詳細は execution パッケージ参照）。
- 監視（Monitoring）: システム状態・注文状態・リスク（ドローダウン等）を定期チェックし、ログ・アラートや Kill Switch を管理。
- ポートフォリオ構築ロジック: 候補選定、重み計算、ポジションサイズ決定、セクター制約・レジーム調整などの純粋関数群。
- 研究（Research）: DuckDB 上の時系列データを使ったファクター計算や将来リターン・IC 計算。
- AI ユーティリティ: ニュースの NLP によるセンチメントスコアリング（OpenAI API を利用）や市場レジーム判定。
- ツール: ペーパートレードの検証レポート生成など実運用/検証を助けるスクリプト群。
- 設定管理: .env の対話式生成（config_setup）と設定検証（validate_config）。

主な特徴 / 機能一覧
-----------------
- 実行モード分離:
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード用の MockBrokerClient を使用し、専用 DB（data/paper_trading.db）へ記録することで本番 DB と完全分離。
  - 本番/監視系は環境にかかわらず本番用 sqlite_path を監視に使用する（監視の一貫性確保）。
- 監視:
  - CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック、滞留注文・約定異常検出、ドローダウン・ポジション上限監視。
  - リスク発生時に kill.flag を書き込み ExecutionEngine を停止させる Kill Switch 機能。
- ロギング:
  - 標準出力（stdout）と日次ローテートのファイルログ（logs/<app_name>.log）を統一的に設定。
- AI 組み込み:
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント付与・レジーム判定（API キー必要、堅牢なリトライ/バリデーション実装）。
- 研究用ユーティリティ:
  - DuckDB 接続を受け取ってファクター計算（モメンタム／バリュー／ボラティリティ）や IC 計算を行う純粋関数群。
- ツール:
  - Paper Trading 検証レポート（稼働率、注文成功率、レイテンシ等）生成コマンド。

前提（Prerequisites）
--------------------
- Python 3.10 以上（型注釈に | 演算子を使用しているため）
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- オプション:
  - PyYAML（config/*.yaml の構文チェックを有効にする場合）
- SQLite は Python に同梱されています。

インストール（例）
-----------------
1. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール:
   - pip install duckdb psutil openai
   - pip install pyyaml   # optional（設定検証で YAML 検証を有効にする場合）

（プロジェクト配布時に requirements.txt がある場合は pip install -r requirements.txt を利用してください）

環境変数 / .env
----------------
自動で .env を読み込む仕組みがあり、プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に .env/.env.local をロードします。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR: ログディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1 = 有効。live 環境では推奨しない）

.example .env（最小）
- JQUANTS_REFRESH_TOKEN=your_refresh_token_here
- KABU_API_PASSWORD=your_kabu_password_here
- KABUSYS_ENV=development
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

.env の生成（対話式ウィザード）
-----------------------------
対話式で .env を作成・更新できます。

- コマンド:
  - python -m kabusys.config_setup

設定検証
--------
起動前に設定の基本チェックを実行できます（必須変数の未設定、ファイルパスの親ディレクトリ存在確認、config/*.yaml の存在確認など）。

- コマンド:
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

実行方法（主要なスクリプト）
---------------------------
- 監視ループ（Monitoring）:
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成するか KeyboardInterrupt。

- 実行エンジン（ExecutionEngine）:
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）へ記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動を行いません。
    - 実行中に stop flag が検知されるとエンジンを停止します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - デフォルト DB: data/paper_trading.db。別パス指定: --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

停止・Kill Switch
-----------------
- Execution の停止は 2 段階:
  - 監視側からの Kill Switch（監視が重大なリスクを検出した場合）:
    - data/kill.flag に理由テキストを書き込み、ExecutionEngine は起動時にこのフラグをチェックし、また実行中は監視が書き込んだ場合に停止する処理を備えます。
  - 手動停止（安全な停止）:
    - プロジェクトルート/data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します。

ロギング
--------
- ログは以下の 2 箇所へ出力されます:
  - コンソール（stdout）
  - 日次ローテートファイル: logs/<app_name>.log（デフォルト）
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理。LOG_DIR / LOG_LEVEL で調整できます。

データベース
-----------
- DuckDB: 分析用データベース（デフォルト data/kabusys.duckdb）
- SQLite:
  - 監視ログ: data/monitoring.db（monitoring_db.init_monitoring_db が必要テーブルを冪等に作成）
  - ペーパートレード専用: data/paper_trading.db（KABUSYS_ENV=paper_trading の場合 ExecutionEngine が使用）

ディレクトリ構成（主要ファイル）
-------------------------------
下記は src/kabusys 配下の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数 / .env の自動ロード・Settings
  - config_setup.py           # .env 対話式ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_monitoring.py         # Monitoring ポーリング起動スクリプト
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  # Paper Trading 検証レポート
  - utils/
    - logging_setup.py        # ログ設定ユーティリティ
    - process_priority.py     # プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        # SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py        # （存在: 参照されるが詳細はここに依存）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        # アラート（LINE 連携等）を想定
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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

（実際のファイルは src/kabusys 以下を参照してください）

開発上の注意 / ベストプラクティス
--------------------------------
- 実運用（KABUSYS_ENV=live）では以下に注意:
  - .env を絶対にリポジトリへコミットしないこと。
  - KILL_FLAG_CLEAR_ON_START は 0 を推奨（1 にすると Kill Switch が自動クリアされるため危険）。
  - LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を適切に設定しておくとアラートが届きます。
- AI 機能を使う際は OPENAI_API_KEY を適切に設定してください。API 呼び出しはリトライやバリデーションを行いますが、コスト管理に注意してください。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news など）は研究用関数群が期待する形になっている必要があります。

トラブルシューティング
---------------------
- ログディレクトリの作成に失敗した場合、ファイルハンドラは無効化されコンソールログのみになります（警告出力あり）。
- 設定検証でエラーが出た場合、指摘された環境変数や config/*.yaml を確認してください。
- OpenAI API 呼び出しの失敗は一時的なエラー（429/5xx/タイムアウト）に対しては指数バックオフでリトライしますが、API キーが未設定だと例外になります。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（ソース参照）。
- ライセンス情報がなく配布元の指示に従ってください。

最後に
------
この README はコードベースから自動的に要点を抽出してまとめたものです。実装の細部や追加のユーティリティは各モジュール内のドキュメント（docstring）を参照してください。質問や追加のドキュメント化が必要であればお知らせください。