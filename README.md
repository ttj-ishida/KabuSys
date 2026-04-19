README
=====

概要
----
KabuSys は日本株の自動売買およびその運用支援ツール群です。
主な機能は次の通りです:
- 戦略（ファクター計算・特徴量解析）とポートフォリオ構築（候補選定・重み付け・株数算出）
- 実行系（ExecutionEngine）と発注管理（OrderRepository / OrderManager / RiskManager 等）
- 監視系（System / Trade / Risk の定期チェック、Kill Switch、監視ログの永続化）
- AI支援（ニュースの NLP によるセンチメント評価、レジーム判定）
- ペーパートレード用の分離 DB と検証レポート生成ツール
- 環境設定ウィザードおよび起動前設定検証 CLI

このリポジトリはモジュール構成が分離されており、運用時は各起動スクリプトを個別プロセスとして実行する想定です。

主な機能一覧
-------------
- portfolio:
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（多様な配分方法・aggregate cap 対応）
  - セクターキャップ適用・レジーム乗数算出
- research:
  - calc_momentum / calc_volatility / calc_value（DuckDB 上でファクター計算）
  - 特徴量解析（forward returns, IC, 統計サマリー）
- ai:
  - ニュースセンチメント（news_nlp.score_news）
  - レジーム判定（regime_detector.score_regime）
  - OpenAI（gpt-4o-mini 想定）を用いるモジュール（API キー必要）
- execution:
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper trading モードでは MockBrokerClient を使用し、data/paper_trading.db に記録
- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - MonitoringDB（SQLite）による永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - Kill Switch（data/kill.flag）による実行系停止信号
  - run_monitoring.py によるポーリングループ（MONITOR_POLL_INTERVAL で間隔制御）
- utils:
  - ログ設定（setup_logging）
  - プロセス優先度 / CPU affinity 設定（set_process_priority / set_cpu_affinity）
- CLI 補助:
  - config_setup.py（対話式 .env 生成）
  - validate_config.py（起動前の設定チェック）
  - tools.paper_verification_report（ペーパートレード検証レポート生成）

依存関係（主なもの）
-------------------
- Python 3.10+（型注釈: | 演算子等を利用）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定ファイルの YAML 検証を行う場合。未インストール時は検証をスキップ）
- sqlite3（標準ライブラリ）

セットアップ手順
----------------

1. リポジトリを取得して Python 仮想環境を作成
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は最低限 duckdb, psutil, openai, PyYAML を入れてください）

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 主要な設定項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）を対話式で作成できます。
   - .env は機密情報を含むため、絶対に Git にコミットしないでください。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合は --strict を付与します。

5. DB の初期化
   - 各起動スクリプトは接続時に必要テーブルの作成（マイグレーション）を行います。明示的な初期化手順は不要です。

重要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定挙動。instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY（AI モジュールを使う場合）
- LOG_LEVEL / LOG_DIR（ログ設定）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（本番での Kill Flag 自動クリア制御）

使い方（起動スクリプト・ツール）
-------------------------------

- 監視ループを起動（SystemMonitor を常駐させる）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に settings.sqlite_path（監視 DB）を使用します（KABUSYS_ENV に依存しない）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用い data/paper_trading.db に記録します（本番 DB と分離）

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先して DB パスを指定）
  - レポートは稼働率、注文成功率、送信率、P95 レイテンシ等を出力し PASS/FAIL 判定を行います

- AI モジュール（プログラムから呼び出す）
  - ニュースセンチメント:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を渡してください
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

停止 / Kill Switch
------------------
- 監視/実行プロセスを外部から停止したい場合は data/stop_requested.flag（run_monitoring/run_execution で使用）や data/kill.flag（KillSwitch が書き込む実行停止フラグ）を利用します。
  - run_monitoring / run_execution は stop_requested.flag の存在を検知するとループを抜けて終了します。
  - KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine の起動・継続に対する安全弁として機能します。

ログ
----
- ログはデフォルトで stdout（コンソール）と logs/<app_name>.log（日次ローテーション、30 日保持）へ出力されます。
- setup_logging(app_name="execution") のようにアプリ名を渡すことで logs/<app_name>.log に出力されます。
- LOG_LEVEL / LOG_DIR で挙動を制御できます。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみになります。

ディレクトリ構成
----------------
（抜粋、重要ファイルを列挙）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_monitoring.py            — SystemMonitor ポーリングループ起動
  - run_execution.py             — ExecutionEngine 起動（PaperTrading 分離対応）
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (実装ファイルはリポジトリ内にある想定)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (実装ファイルはリポジトリ内にある想定)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                    — Execution 関連コンポーネント（BrokerFactory, Engine, OrderManager 等）
  - data/                         — 実行時 DB・フラグファイル（data/ 以下は運用で生成・管理）
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - kill.flag / stop_requested.flag / execution.pid

設計上の注意点 / 運用上のヒント
------------------------------
- .env は必ずローカルに保ち、機密情報（API トークン等）は漏洩しないよう管理してください。
- KABUSYS_ENV が live の場合は本番動作になります。validate_config の警告や LINE 通知設定を必ず確認してください。
- Paper trading を使うと本番 DB と分離された PAPER_TRADING_SQLITE_PATH に記録されます。安全に検証を行えます。
- AI 機能（news_nlp / regime_detector）は外部 API（OpenAI）に依存します。API キーのレート制限やコストに注意してください。API 呼び出しは冪等性やエラーハンドリング（リトライ・バックオフ）を備えていますが、運用時は監視を強化してください。
- ログはデフォルトで logs/ に保存されます。運用環境では適切にログローテーションや転送を設定してください。

お問い合わせ / 開発
------------------
- 本 README はリポジトリ内のスクリプトとモジュールの docstring を元に作成しています。実装の詳細や追加の CLI・ツールがある場合は該当ファイルの docstring やコメントを参照してください。

以上。必要があれば「インストール手順の詳細」「各モジュールの API 使用例（コード例）」「運用チェックリスト」など追記します。どれを優先して追加しますか？