README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買システム向けライブラリ／実行スクリプト群です。本リポジトリは以下の主要機能を含みます:

- 発注実行エンジン（ExecutionEngine） — 実際のブローカーまたはモックを用いた発注処理
- 監視サブシステム（Monitoring） — プロセス稼働状態、データ鮮度、リスク監視、アラート／Kill Switch
- ポートフォリオ構築（ポジションサイジング、セクター制約、重み算出）
- リサーチ（ファクター計算、特徴量解析、IC計算）
- AI連携モジュール（ニュースセンチメント、レジーム判定、OpenAI 呼び出し）
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度設定）
- 検証用ツール（ペーパートレード検証レポート生成）

主な設計方針
- DuckDB / SQLite をデータレイヤに使用し、分析部と実行部を分離
- 本番とペーパートレードは DB を分離（KABUSYS_ENV により切替）
- OpenAI 連携は API キー経由（外部キー未設定時は例外またはフォールバック）
- 多くの処理はフェイルセーフ（API 失敗時はスキップ／デフォルト値で継続）

機能一覧
--------
- 実行関連
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - BrokerClientFactory による本番/モックブローカー切替（KABUSYS_ENV=paper_trading）
  - 発注ログの永続化（SQLite / trade_logs）

- 監視関連
  - SystemMonitor: CPU/メモリ/Disk、Execution プロセス存在、データ鮮度を監視
  - TradeMonitor / RiskMonitor: 滞留注文、約定異常、ドローダウン・ポジション上限監視
  - KillSwitch: リスクトリガーで ExecutionEngine に停止フラグを作成
  - MonitoringEngine: 各 Monitor を束ねるポーリングループ（run_monitoring.py）

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等分配 / スコア加重（calc_equal_weights, calc_score_weights）
  - セクター上限の適用（apply_sector_cap）
  - ポジションサイズ計算（calc_position_sizes）

- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- AI（OpenAI）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）

- ツール・ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - ログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）

前提（推奨環境）
----------------
- Python 3.10+
- 必要な外部ライブラリ（最小セット）:
  - duckdb
  - psutil
  - openai (AI 機能を利用する場合)
  - PyYAML（config 検証で YAML 内容チェックを行う場合に任意）
- SQLite（Python 標準ライブラリで利用）

セットアップ手順
----------------
1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール
   - pip install duckdb psutil openai
   - 任意: pip install pyyaml

3. プロジェクトルート（pyproject.toml/.git が存在するディレクトリ）に移動し、data/ と logs/ が自動作成されます（必要に応じて手動作成可）。

環境変数 / .env
----------------
本プロジェクトは .env（および .env.local）をサポートします。主な環境変数（必須／デフォルト）:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / デフォルト:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — デフォルト: logs/
- OPENAI_API_KEY — OpenAI を使う場合に必要
- PAPER_FILL_MODE — ペーパートレードの fill 挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring 用、デフォルト 60）

.env を対話式に作る:
- python -m kabusys.config_setup
設定検証:
- python -m kabusys.validate_config
  --strict を付けると警告も失敗（exit 1）扱いになります。

実行方法（主要スクリプト）
-------------------------

- 監視ループ（SystemMonitor + 他モニタ）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
    - 監視は環境にかかわらず production の sqlite_path を使用（run_monitoring の仕様）
    - 停止方法: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db に記録
    - 停止は data/stop_requested.flag を作成、起動中の PID は data/execution.pid に書き出されます

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告で終了コード 1 になる

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能（--db が優先）

ログとファイルパス
------------------
- ログ: デフォルト logs/ 下に app_name.log を日次ローテートで保存（TimedRotatingFileHandler）
  - setup_logging(app_name="execution") などでファイル名が決まる
  - 環境変数 LOG_DIR で変更可能
- SQLite / DuckDB デフォルト:
  - SQLite (monitoring): data/monitoring.db
  - DuckDB: data/kabusys.duckdb
  - Paper trading SQLite: data/paper_trading.db
- Kill / Stop フラグ:
  - kill.flag: Settings.kill_flag_path（デフォルト data/kill.flag） — KillSwitch が書き込む停止フラグ（Execution 停止要求）
  - stop_requested.flag: run_execution / run_monitoring が監視している停止フラグ（data/stop_requested.flag）

AI（OpenAI）関連
-----------------
- news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news / news_symbols を集約して OpenAI に送信し ai_scores テーブルへ書き込む
  - api_key を渡すか環境変数 OPENAI_API_KEY を設定してください
  - バッチサイズ、リトライ、レスポンス検証、スコアクリップなどを行います

- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 乖離とマクロニュース LLM センチメントを合成して market_regime テーブルへ保存

開発者向け（API / モジュールの使い方）
-----------------------------------
- Research / ファクター計算
  - calc_momentum(conn, target_date), calc_volatility(...), calc_value(...)
  - DuckDB 接続（kabusys.data.pipeline 等で DuckDB を開いて渡す）を受け取り prices_daily / raw_financials を参照します

- ポートフォリオ構築
  - select_candidates(buy_signals, max_positions)
  - calc_equal_weights(candidates) / calc_score_weights(candidates)
  - calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices, ...)

- 監視 DB 操作
  - MonitoringDB クラスを通して system_status, trade_logs, positions, risk_logs, dashboard の読み書きが行えます

停止／Kill の挙動
----------------
- RiskMonitor 等が基準を満たすと KillSwitch.evaluate() が reason を生成し、kill.flag（Settings.kill_flag_path）を書き込みます。ExecutionEngine は起動時に kill.flag を検出すると起動を中止し、起動中は kill.flag の有無で停止処理をトリガーできます。
- 管理者は kill.flag を手動で削除（clear）することで再起動を許可できます（ただし KILL_FLAG_CLEAR_ON_START の設定にも依存）。

ディレクトリ構成（主なファイル）
------------------------------
以下は主要なパッケージ/ファイル一覧（抜粋）です:

- src/kabusys/
  - __init__.py
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — Monitoring ポーリングループ起動スクリプト
  - config.py                       — Settings / 環境変数管理
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI
  - tools/
    - paper_verification_report.py   — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py                    — ニュース NLP / OpenAI 連携
    - regime_detector.py             — レジーム判定（MA200 + マクロ感情）
  - monitoring/
    - monitoring_db.py               — Monitoring 用 SQLite 永続化層
    - monitoring_engine.py           — 各 Monitor を束ねるエンジン
    - system_monitor.py              — システム・データ鮮度監視
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — Kill Switch（kill.flag）管理
    - ...（trade_monitor, alert_manager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py               — 共通ログ初期化ユーティリティ
    - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - execution/
    - ... （BrokerFactory, ExecutionEngine, OrderManager, RiskManager 等 実装）

注意事項 / 運用上のヒント
------------------------
- .env を絶対にバージョン管理にコミットしないでください（秘密情報を含むため）。
- KABUSYS_ENV=live を使用する際は LINE 通知設定や Kill Switch の扱いを慎重に設定してください（validate_config にガードがあります）。
- OpenAI を利用するスクリプトは API キーの漏洩とコストに注意してください。失敗時のフォールバックが組まれていますが、運用ルールを定めてください。
- Logs/DB のディスク使用量に注意し、ログローテーションや DB バックアップ・保守を行ってください。

ライセンス / 貢献
-----------------
（この README にはライセンス情報が含まれていません。リポジトリルートの LICENSE / CONTRIBUTING を参照してください。）

--------------------------------
この README はソースコードのヘッダコメント・設定ファイル・関数名から生成した概要です。詳細な挙動はそれぞれのモジュールの docstring / ソースコードを参照してください。必要であれば、特定モジュールの詳しい使い方や例を追記します。