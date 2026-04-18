KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）の一部を構成するモジュール群です。
主な機能は注文実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、
ニュース NLP によるセンチメント評価などです。設計方針として「本番 DB とペーパートレード DB の分離」や
「ルックアヘッドバイアス回避」「外部 API 呼び出しは明示的に行う（API キー必須）」を採用しています。

主な特徴
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード（KABUSYS_ENV）に応じた振る舞い
  - Broker クライアントの抽象化（BrokerClientFactory）
  - リスク管理・注文管理・照合（reconciler）を組み合わせたエンジン起動
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - system_status, trade_logs, risk_logs, dashboard, positions を永続化する SQLite 層
  - kill.flag による ExecutionEngine 停止（KillSwitch）
- ポートフォリオ構築（portfolio）
  - 候補選定・重み計算・ポジションサイズ計算・セクター制約などの純粋関数群
- リサーチ（research）
  - DuckDB を用いたファクター計算（モメンタム/バリュー/ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（ai）
  - OpenAI を用いたニュースセンチメント評価（news_nlp）
  - マクロニュース + ma200 による市場レジーム判定（regime_detector）
- ユーティリティ
  - .env 対話生成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
  - ロギング・プロセス優先度設定ユーティリティ

セットアップ
-----------
前提
- Python 3.10+ を推奨（コード内での型注釈と構文を踏まえて）
- システムにより追加のネイティブ依存（psutil、duckdb のビルド等）が必要になる場合があります

インストール（例）
1. 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install -U pip
   - pip install duckdb psutil openai
   - （オプション）YAML の検証を行う場合: pip install PyYAML

3. リポジトリルートでデータディレクトリを作成:
   - mkdir -p data logs

環境変数の初期化
- .env を手動で作成するか、付属のウィザードを使用できます:
  - python -m kabusys.config_setup
- 作成後、以下の必須環境変数が設定されていることを確認してください:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
- その他の重要な環境変数（デフォルト有り）:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR（デフォルト: INFO）
  - OPENAI_API_KEY: OpenAI API を使用する場合に必要
  - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定モード、デフォルト: instant）
  - KILL_FLAG_CLEAR_ON_START: 0 | 1（本番では 0 推奨）

設定検証
- .env と config/*.yaml の整合性を起動前にチェック:
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit 1）になります

使い方（起動・実行）
-------------------

1) 監視プロセス（Monitoring）
- 監視ポーリングループを起動:
  - python -m kabusys.run_monitoring
- 環境変数でポーリング間隔を上書き可能:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 停止:
  - data/stop_requested.flag ファイルを作成するとループが終了します（停止フラグ検知）。
  - kill.flag は KillSwitch により ExecutionEngine 停止シグナルとして書き込まれます（場所は Settings.kill_flag_path で設定可）。

2) 実行エンジン（ExecutionEngine）
- エンジン起動:
  - python -m kabusys.run_execution
- 起動時の挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - 実行中は data/execution.pid に PID を書きます
- 停止:
  - data/stop_requested.flag を作成すると監視ループが検知して engine.stop() を呼び、停止処理します
  - kill.flag を監視側から書き込むことで ExecutionEngine に停止シグナルを送れます

3) Paper Trading 検証レポート
- レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間フィルタ:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

プログラム API（ライブラリ的利用）
- 研究・AI モジュール（DuckDB 接続を渡して使用）
  - kabusys.research.calc_momentum(conn, target_date)
  - kabusys.research.calc_volatility(conn, target_date)
  - kabusys.research.calc_value(conn, target_date)
  - kabusys.research.calc_forward_returns(conn, target_date)
  - kabusys.research.calc_ic(...)
- AI（ニュース NLP）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - api_key を渡すか環境変数 OPENAI_API_KEY を設定してください
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

重要な運用ノート
----------------
- DB 分離:
  - 監視（monitoring）は常に settings.sqlite_path（通常 data/monitoring.db）を使用します（環境に依らず本番パス）。
  - ExecutionEngine は KABUSYS_ENV=paper_trading のとき settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。
- ロギング:
  - setup_logging() により stdout と logs/<app_name>.log（日次ローテーション）へ出力します。ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼びます。権限がない環境では警告を出してスキップします。
- Kill Switch:
  - RiskMonitor が閾値を超えると KillSwitch が data/kill.flag を書き込み、ExecutionEngine を停止する仕組みがあります（冪等に実装）。
  - 本番で KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしてしまうため注意（デフォルトは 0）。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（Settings クラス）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — 統一ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成・CRUD）
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py       (参照されるが本 README の抜粋には省略あり)
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       (アラート管理、抜粋に未掲載)
  - execution/               — Execution 関連コンポーネント（Engine, BrokerFactory, OrderManager 等。抜粋あり）
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
  - data/ (ランタイムで使用)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード)
    - kill.flag / stop_requested.flag / execution.pid

トラブルシューティング
----------------------
- .env の自動ロード:
  - プロジェクトルートの判定は .git または pyproject.toml によるため、環境によって自動ロードが働かない場合があります。その場合は明示的に .env を作成するか KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動ロードを無効化できます（テスト用途）。
- DuckDB / SQLite のファイルパス:
  - 指定ファイルの親ディレクトリが存在しない場合、validate_config は警告を出します。起動時に自動作成される場合がありますが、事前に data/ を作成しておくと安全です。
- OpenAI 呼び出し:
  - API キーが未設定だとエラーになります。ニュース NLP / レジーム検出は API のレスポンスに依存するため、API 呼び出し失敗はフェイルセーフ（スコア=0 等）で扱う実装ですが、キーは必須です。

ライセンス / 貢献
-----------------
- 本 README はコードベースから抽出した機能説明・運用メモです。実運用・本番運用前に設定検証（python -m kabusys.validate_config）とステージ環境での十分なテストを行ってください。

以上が本プロジェクトの概要、セットアップ手順、使い方、ディレクトリ構成です。必要であれば各コンポーネント（ExecutionEngine の詳細 API、monitoring のアラート設定、Broker の実装仕様など）について別ファイルでより詳細なドキュメントを作成します。どの部分を深掘りしますか？