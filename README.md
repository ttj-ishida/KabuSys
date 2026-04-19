KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本コードベースは以下の機能を含みます:
- 実取引 / ペーパートレードの ExecutionEngine
- システム監視（リソース・データ鮮度・注文状態・リスク監視）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制約・レジーム調整）
- リサーチ（ファクター計算・特徴量探索・IC 計算）
- ニュース NLP を用いた銘柄スコアリング・レジーム判定（OpenAI）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート等）

主な特徴
---------
- 環境分離
  - KABUSYS_ENV によって development / paper_trading / live を切替可能。
  - paper_trading 実行時は MockBroker を使用し、ペーパー専用 SQLite DB（data/paper_trading.db）へ記録。
- 安全機構
  - Kill Switch（data/kill.flag）により ExecutionEngine の即時停止を行える。
  - 停止フラグ（data/stop_requested.flag）や PID ファイルでプロセス管理を補助。
  - リスク監視（ドローダウン・ポジション上限）・監視ログ永続化（SQLite）。
- AI 連携
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・マクロセンチメントでのレジーム判定。
  - API 呼び出しはリトライやフェイルセーフ設計（5xx/429/タイムアウト等対応）。
- データ分析
  - DuckDB を利用したファクター計算・将来リターン計算・レポート作成。
- ロギング
  - 統一的なログ設定（コンソール stdout + 日次ローテーションファイル、logs/<app>.log、30 日保持）。

セットアップ手順
----------------

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python と依存パッケージをインストール
   - 推奨 Python: 3.10+
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config/*.yaml の検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. ディレクトリの準備（通常はスクリプトが自動作成するが事前に用意しておくと良い）
   - data/ （SQLite や PID/flag を格納）
   - logs/ （ログファイル）
   - 例:
     - mkdir -p data logs

4. 環境変数の設定（.env を推奨）
   - 対象の必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - オプション / 重要:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, LOG_DIR, KILL_FLAG_CLEAR_ON_START, PAPER_FILL_MODE など

   - .env を対話式で作る:
     - python -m kabusys.config_setup
     - 生成後は設定検証を実行:
       - python -m kabusys.validate_config
       - --strict を付けると警告も失敗扱いになります

使い方（主要スクリプト）
-----------------------

- 実行（ExecutionEngine）
  - 本番/ペーパー共通起動スクリプト:
    - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に履歴を記録。
    - 起動時に data/stop_requested.flag があれば起動せず終了。
    - 実行中は data/execution.pid に PID を書きます。停止は stop_requested.flag / kill.flag 等で制御。

- 監視（Monitoring）
  - 監視ポーリングループ起動:
    - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
  - グレースフル停止: data/stop_requested.flag を作成するとループが終了します。

- 設定関連
  - .env 対話式ウィザード:
    - python -m kabusys.config_setup
  - 設定検証:
    - python -m kabusys.validate_config [--strict]

- ツール
  - Paper Trading 検証レポート生成:
    - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能（--db が優先）

- AI / 研究用 API（ライブラリ関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news を元に銘柄別センチメントスコアを ai_scores テーブルへ書き込む。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 比・マクロニュースで日次レジームを判定し market_regime に保存。
  - これらは DuckDB 接続を渡して呼び出します。OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用。

運用上の注意
-------------
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch はリスク条件発生時にこのファイルを書き、ExecutionEngine 側で検知して停止します。
  - 本番環境で KILL_FLAG_CLEAR_ON_START=1 を設定するのは危険（起動時に自動クリアされるため）。
- PID / stop フラグ
  - data/execution.pid、data/stop_requested.flag を使って外部から安全に停止できます。
- Monitoring は監視 DB に監視ログ・risk_logs・trade_logs などを書き込みます。monitoring は常に本番用の sqlite_path を使う点に注意。
- OpenAI 使用時は API 呼び出しが料金発生するためキーの管理に注意。

ディレクトリ構成（主要ファイル）
--------------------------------

src/kabusys/
- __init__.py — パッケージ定義、__version__
- config.py — 環境変数 / Settings 管理、.env 自動ロードロジック
- config_setup.py — .env 対話式ウィザード（CLI）
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
- run_monitoring.py — SystemMonitor 起動スクリプト（python -m kabusys.run_monitoring）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- ai/
  - news_nlp.py — ニュース NLP（OpenAI）で ai_scores を生成
  - regime_detector.py — マクロ + MA200 合成で市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite ベースの監視永続化層 + MonitoringDB クラス
  - system_monitor.py — システムリソース・データ鮮度・プロセス監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - trade_monitor.py — （注文滞留・約定異常監視等）※実装ファイル参照
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - kill_switch.py — kill.flag 管理ユーティリティ
  - alert_manager.py — （通知管理。LINE などのアラート送信ロジック）
- execution/ — ExecutionEngine 周り（ブローカー、注文管理、リスク管理等）
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...
- portfolio/
  - portfolio_builder.py — 候補選定、重み付け
  - position_sizing.py — 板・価格に基づく株数決定・集計キャップ
  - risk_adjustment.py — セクター上限、レジーム乗数
- research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- utils/
  - logging_setup.py — ログ初期化ユーティリティ（Stream + TimedRotatingFileHandler）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

設定ファイル
------------
- config/*.yaml — system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
  - validate_config で存在 / パース検証（PyYAML インストール時）を行います。
  - サンプルは scripts/generate_config.py 等で生成する想定。

開発・デバッグ
---------------
- ロギングはデフォルト stdout と logs/<app>.log（日次ローテーション）に出力されます。ログレベルは LOG_LEVEL 環境変数で変更可能。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を検出して行います。無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テストや CI では Settings をモックするか環境変数を注入して使ってください。

以上

README に不明点や追加で欲しい情報（例: 各 config.yaml の項目説明、実際の ExecutionEngine の API 仕様、ブローカープラグインの作り方など）があれば教えてください。必要に応じて追記・補足します。