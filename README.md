README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装した Python パッケージです。
主に次の用途を含みます:

- ExecutionEngine（発注実行）／Order 管理／リスク管理の基本処理
- Monitoring（システム・発注・リスク監視）と Kill Switch
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ計算）
- Research 用ファクター計算・特徴量解析
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

機能一覧
--------
主な機能（実装済みのモジュール）:

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV=paper_trading 時は MockBroker）
  - run_monitoring.py: Monitoring のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔を調整）
- 設定管理
  - config.py / Settings: 環境変数・.env のロードと設定取得
  - config_setup.py: .env の対話式ウィザード生成
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
- 監視
  - monitoring/monitoring_db.py: SQLite ベースの監視ログ永続化層
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py: 各監視ロジックと統合
  - kill_switch.py: データ側から ExecutionEngine を停止するフラグ機能
- 発注関連（execution/*）
  - ExecutionEngine, BrokerClientFactory, OrderManager, RiskManager, Reconciler 等（起動スクリプト経由で連携）
- ポートフォリオ
  - portfolio/*: 候補選定、配分、セクター制限、ポジションサイズ計算
- Research
  - research/*: ファクター計算（momentum, volatility, value）、特徴量探索、IC 計算等
- AI
  - ai/news_nlp.py: OpenAI を用いたニュースセンチメントのバッチスコアリング
  - ai/regime_detector.py: マクロ + ETF MA による市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード履歴の検証レポート生成

動作前提 / 要件
----------------
- Python 3.10+（型注釈で | を使用）
- 主な依存パッケージ:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config 検証で YAML をパースする場合）
- SQLite（標準ライブラリ sqlite3 を使用）
- ネットワークアクセス：kabuステーション API, OpenAI（AI 機能を使う場合）

セットアップ手順
----------------
1. 仮想環境作成（例）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要パッケージをインストール（例）
   pip install duckdb psutil openai
   # config 検証で YAML を使う場合は:
   pip install PyYAML

   （本プロジェクトに requirements.txt があればそちらを利用してください）

3. .env の作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - または手動で .env を作成し、必須項目を設定:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development | paper_trading | live）
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（例: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等

4. 設定検証（任意だが推奨）
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いで exit(1)
   python -m kabusys.validate_config --strict

5. データディレクトリやログディレクトリの準備（通常はコードが自動作成）
   mkdir -p data logs

使い方
------
起動スクリプト例:

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）
  KABUSYS_ENV=development python -m kabusys.run_execution
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  備考:
  - paper_trading の場合、MockBrokerClient を用い data/paper_trading.db に記録します（本番 DB とは分離）。
  - execution は data/stop_requested.flag を検出すると停止します。またエンジンの PID は data/execution.pid に書き出されます。

- Monitoring を起動（定期ポーリング）
  python -m kabusys.run_monitoring

  環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  備考:
  - Monitoring は Settings の sqlite_path（監視 DB）を使用します（環境にかかわらず同じ監視 DB を参照します）。
  - stop フラグとして src/…/data/stop_requested.flag が存在するとループを抜けます。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  # 期間を指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを上書き:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI スコアリング / レジーム判定（ライブラリ関数として利用）
  - news_nlp.score_news(conn, target_date, api_key=None)  # api_key が None の場合は OPENAI_API_KEY を環境変数で参照
  - regime_detector.score_regime(conn, target_date, api_key=None)

  注意:
  - OpenAI の呼び出しは API キーが必須（コスト発生の可能性あり）。テストでは _call_openai_api をモックすることを推奨。

重要となる環境変数（主要項目）
------------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒）
- LOG_LEVEL（デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知に使用）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）

停止・制御ファイル
-----------------
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py が存在を検出するとグレースフルに終了します（運用・CI で利用）。
- data/kill.flag
  - KillSwitch が書き込むことで ExecutionEngine に停止指示を送るために使用されます（実行プロセス自体は stop_requested.flag を監視して停止します）。
- data/execution.pid
  - ExecutionEngine が PID を出力する場所（デフォルト設定）。

ログ
---
- kabusys.utils.logging_setup.setup_logging を全スクリプトで使用しています。
- デフォルトでは logs/<app_name>.log に日次ローテーションで出力（30 日保持）。ログディレクトリが作成できない場合はコンソール出力のみになります。

ディレクトリ構成（要約）
-----------------------
プロジェクトは src/kabusys 以下に主要モジュールを配置しています（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込み・Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は README 作成時点での主要ファイル一覧の抜粋です。詳細はコードベースを参照してください）

注意事項 / 運用上のポイント
--------------------------
- Paper Trading と Live の DB は分離する設計です（settings.is_paper により paper_sqlite_path を使用）。
- Monitoring 側は監視データ用の sqlite_path（デフォルト data/monitoring.db）を使用します。run_monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を参照する実装です。
- OpenAI 呼び出しはリトライ・バックオフやレスポンス検証を行いますが、API コストやレート制限に注意してください。
- ローカルで初回起動する際は .env を正しく設定し、validate_config でチェックすることを推奨します。
- .env は機密情報（API トークン等）を含むため、Git にコミットしないでください（config_setup.py のヘッダにも注意喚起があります）。

ライセンス / バージョン
-----------------------
パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

最終更新
--------
この README はコードベースの主要ファイルから自動的にまとめられています。実際の運用やデプロイ方法は環境に合わせて追加設定（サービスユニット、コンテナ化、プロセスマネージャの設定等）を行ってください。