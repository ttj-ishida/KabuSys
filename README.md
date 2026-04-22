README
======

概要
----
KabuSys は日本株向けの自動売買／研究支援ライブラリ群です。  
主な目的は以下です。

- 株価データや財務データを用いたファクター計算・リサーチ
- ポートフォリオ構築／ポジションサイズ計算（純粋関数群）
- ExecutionEngine（発注実行）および Monitoring（監視）用のユーティリティ
- Paper Trading 用の検証ツールやレポート生成
- OpenAI を利用したニュース NLP / 市場レジーム判定（オプション）

このリポジトリはライブラリとしての再利用を重視して設計されており、起動スクリプトや CLI ツールを通じて実行できます。

主な機能
--------
- 環境設定ウィザード（.env 作成 / 更新）: kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の検証）: kabusys.validate_config
- Execution 起動スクリプト（本番 / ペーパートレード切替対応）: kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に分離
- Monitoring 起動スクリプト（SystemMonitor ポーリング）: kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）
  - kill.flag / stop_requested.flag による停止制御
- Monitoring 永続層（SQLite）操作: kabusys.monitoring.monitoring_db
- 各種監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と MonitoringEngine
- ポートフォリオ構築・重み付け・ポジションサイズ計算（等金額、スコア重み、リスクベース）: kabusys.portfolio
- リサーチ：ファクター計算（モメンタム、ボラティリティ、バリュー）・将来リターン・IC 計算: kabusys.research
- Paper Trading 検証レポート生成スクリプト: kabusys.tools.paper_verification_report
- OpenAI を用いたニュースセンチメント（ai.news_nlp）と市場レジーム判定（ai.regime_detector）

セットアップ手順
----------------
前提
- Python 3.10 以上（型ヒントで X | Y 形式を使用）
- SQLite（標準で同梱）・必要に応じて DuckDB バイナリ

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML
   - ※ 実行環境により必要なパッケージは変わります。openai は ai モジュール利用時に必要、PyYAML は validate_config が config/*.yaml をパースする際に任意で使われます。

3. .env の作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で .env を作成

4. 設定検証（必須項目の確認）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトでは data/ 下に DB やフラグファイル、PID ファイルなどを作成します（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/kill.flag）。
   - ログは logs/ に出力されます（設定可）。

主要な環境変数
-------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading 時のフィルモード: instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY（ai モジュール利用時）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリア、開発用: 1/本番推奨 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（=1 で自動 .env 読み込みを無効化）

使い方（コマンド例）
------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告があると失敗）:
    - python -m kabusys.validate_config --strict

- Monitoring 起動（常駐的に監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を 30 秒にする:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  仕組みメモ:
  - stop_requested.flag が存在すると安全にループを抜けます（data/stop_requested.flag）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用します（監視ログは本番 DB に記録）。

- Execution 起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading に設定してペーパートレード（MockBroker）で起動:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  仕組みメモ:
  - paper_trading の場合、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存され、本番 DB と完全に分離されます。
  - data/execution.pid に PID を書き、data/stop_requested.flag により停止検知を行います。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは data/paper_trading.db。別 DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/db.sqlite

- ai モジュール（ニューススコアリング / レジーム判定）
  - プログラム的に呼び出し:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
  - OpenAI API キーは OPENAI_API_KEY 環境変数または関数引数で渡します。

ログとデータ
-------------
- ログ: logs/<app_name>.log（日次ローテーション、デフォルト 30 日保持）
  - setup_logging(app_name="execution" など) を通じて一元管理
- データ/制御ファイル（デフォルト場所）
  - data/kabusys.duckdb (DuckDB)
  - data/monitoring.db (監視 SQLite)
  - data/paper_trading.db (ペーパートレード SQLite)
  - data/execution.pid (ExecutionEngine の PID)
  - data/stop_requested.flag (監視・実行の停止トリガ)
  - data/kill.flag (Kill Switch が発動した際に作成)

内部ライブラリ・モジュール（概要）
------------------------------
- kabusys.config
  - .env 自動読み込みロジック、Settings クラス（環境設定の中央取得）
- kabusys.config_setup
  - 対話式 .env 生成ウィザード
- kabusys.validate_config
  - 起動前の設定検証 CLI
- kabusys.run_monitoring
  - SystemMonitor のポーリングループ起動スクリプト
- kabusys.run_execution
  - ExecutionEngine 起動スクリプト（thread ベースでセッション実行）
- kabusys.monitoring
  - monitoring_db.py（SQLite 永続化層）
  - system_monitor.py / trade_monitor.py / risk_monitor.py / kill_switch.py / monitoring_engine.py / alert_manager.py（監視ロジック群）
- kabusys.execution
  - ExecutionEngine, OrderManager, RiskManager など（起動スクリプトから組み立て）
- kabusys.portfolio
  - portfolio_builder.py（候補選定、等重・スコア重み）
  - position_sizing.py（株数計算、lot 単位丸め、aggregate cap）
  - risk_adjustment.py（セクター上限・レジーム乗数）
- kabusys.research
  - factor_research.py（mom/vol/value）
  - feature_exploration.py（forward returns / IC / summary）
- kabusys.ai
  - news_nlp.py（ニュース NLP→ai_scores 書込み）
  - regime_detector.py（マクロ + MA200 によるレジーム判定）
- kabusys.utils
  - logging_setup.py（統一ロギング）
  - process_priority.py（プロセス優先度 / CPU affinity 設定）
- kabusys.tools
  - paper_verification_report.py（Paper Trading 検証レポート）

ディレクトリ構成（主要ファイル抜粋）
---------------------------------
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_monitoring.py
    - run_execution.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
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
    - tools/
      - paper_verification_report.py

注意点・運用上の留意事項
-----------------------
- 本番環境（KABUSYS_ENV=live）は強力な影響を及ぼす可能性があります。設定（API キーや kill switch, LINE 通知設定）をよく確認してください。
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください。
- OpenAI など外部 API 呼び出しは失敗を想定した実装になっていますが、API キー漏洩や料金管理に注意してください。
- run_monitoring は監視ログとして sqlite を使用します。モニタリングは常に本番 sqlite_path を参照する設計です（環境に関係なく）。
- run_execution は paper_trading 用に DB を分離できます（settings.is_paper を参照）。Paper と本番の DB を混同しないでください。
- ログディレクトリの作成やファイルハンドラの作成に失敗した場合、コンソールログのみで継続します。

サンプルワークフロー
-------------------
1. 仮想環境作成・依存インストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定を検証
4. 本番監視を起動: python -m kabusys.run_monitoring
5. Execution を起動（ペーパートレードで試す）:
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
6. Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス
---------
（この README にはライセンス情報を含めていません。プロジェクトに合わせて LICENSE ファイルを追加してください。）

お問い合わせ / 貢献
------------------
バグ報告や改善提案は issue を通じてお願いします。PR は歓迎します。README の改善や使用例の追加も歓迎です。