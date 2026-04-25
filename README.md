README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を意図したモジュール群です。本リポジトリは以下の主要機能を含みます。

- 発注エンジン（ExecutionEngine）とその監視（Monitoring）
- ポートフォリオ構築（選定・重み付け・株数算出）
- 研究用ファクター計算・特徴量探索（DuckDB ベース）
- ニュース NLP / レジーム判定（OpenAI を利用）
- ペーパートレード検証レポート生成ツール
- 設定ウィザード・設定検証 CLI、ログ設定・プロセス優先度ユーティリティ

主な設計方針:
- DB 分離: paper_trading モードでは paper_trading DB を使用して本番 DB と分離
- ルックアヘッドバイアス対策: 日付/時間の扱いに注意（各モジュールで説明あり）
- フェイルセーフ: API 失敗や一部エラーはスキップ・ログ化して継続

機能一覧
--------
- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV により paper/live 動作分岐）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔上書き可）
- 設定管理
  - config_setup.py: .env を対話式で作成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の起動前チェック CLI
- 監視
  - monitoring_engine.py: 各 Monitor（system/trade/risk）を束ねて実行、KillSwitch 評価、アラート発行
  - system_monitor.py / trade_monitor.py / risk_monitor.py / kill_switch.py / monitoring_db.py
- ポートフォリオ構築
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py
- 研究
  - research.factor_research: モメンタム・ボラティリティ・バリュー計算
  - research.feature_exploration: 将来リターン計算・IC・統計要約
- AI
  - ai.news_nlp: ニュース記事を OpenAI でセンチメント化して ai_scores に保存
  - ai.regime_detector: ETF とマクロニュースを合成して market_regime を判定
- ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成

セットアップ手順
----------------
前提:
- Python 3.10 以上を推奨（型ヒントの union 記法などを利用）
- system レベルで DuckDB / SQLite ファイルへの書き込み権限が必要

1. 依存パッケージをインストール（例）
   pip install duckdb psutil openai PyYAML

   ※ 実行環境によっては追加のパッケージが必要です（例: requests 等、別途 requirements.txt を参照してください）。

2. プロジェクトルートに移動し、.env を作成
   - 対話式に作る:
     python -m kabusys.config_setup

   - あるいは .env.example を参考に手動で作成する（本リポジトリでは .env.example のファイルは省略されていますが、config_setup がテンプレートを出力します）。

3. 設定を検証:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります:
   python -m kabusys.validate_config --strict

4. データディレクトリ・ログディレクトリ
   - デフォルト DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - PID / flag ファイル: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログ: logs/（デフォルト）
   必要に応じて .env で上書きしてください。

使い方
------
基本的な起動例:

- ExecutionEngine を起動する（実行モードは KABUSYS_ENV で制御）
  python -m kabusys.run_execution

  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading DB に記録します（本番 DB と完全分離）。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に stop フラグが立つとエンジンを停止します。
  - PID ファイルのパスは Settings.pid_file_path（デフォルト data/execution.pid）。

- Monitoring を起動する（システム監視のポーリングループ）
  python -m kabusys.run_monitoring

  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - 監視は常に production 用 sqlite_path（Settings.sqlite_path）を使用します。
  - 停止は data/stop_requested.flag の作成で行います。

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で SQLite のパスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

AI 関連（news_nlp, regime_detector）
- OpenAI API を使うため OPENAI_API_KEY を設定してください（引数経由でも可能）。
- news_nlp.score_news / regime_detector.score_regime を呼び出すと DuckDB 内の raw_news 等を読み、ai_scores / market_regime に書き込みます。
- API 失敗時は安全に 0.0 等でフォールバックする設計ですが、必ずキーを設定してお使いください。

よく使う環境変数（要点）
- 必須 (起動前に設定)
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行/監視系
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
  - PID_FILE_PATH: data/execution.pid（デフォルト）
  - KILL_FLAG_PATH: data/kill.flag（Kill Switch 用）
  - KILL_FLAG_CLEAR_ON_START: 0 or 1（本番で 1 は危険。デフォルト 0）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）

- Paper Trading 固有
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- AI
  - OPENAI_API_KEY: OpenAI 呼び出しに必要

注意事項・運用メモ
-----------------
- Paper Trading と Live の DB は分離されます。paper_trading モードを使うことで本番 DB に影響を与えません。
- Kill Switch: risk_monitor 等の評価結果で KILL_SWITCH が発動すると data/kill.flag が作られ、ExecutionEngine に停止シグナルを送ります。KILL_FLAG_CLEAR_ON_START=1 を本番で使うのは推奨されません。
- ログ: setup_logging により stdout + 日次ローテートファイル（logs/<app>.log）へ出力します。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- 停止フラグ: run_execution/run_monitoring は data/stop_requested.flag を監視して安全停止します。運用ではこのファイルを作成して停止を指示します。
- DB マイグレーション: monitoring_db.init_monitoring_db は単純な後方互換処理（カラム追加）を行いますが、本格的なマイグレーションは別途管理してください。

ディレクトリ構成
----------------
（プロジェクトルート想定。実際は src/kabusys 配下）

- src/
  - kabusys/
    - __init__.py
    - config.py                  # 環境変数 / Settings
    - config_setup.py            # .env 対話式ウィザード
    - validate_config.py         # 設定検証 CLI
    - run_execution.py           # ExecutionEngine 起動スクリプト
    - run_monitoring.py         # Monitoring 起動スクリプト
    - monitoring/
      - monitoring_db.py        # SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py        # （省略されたが該当する）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py        # アラート発行管理（ファイル上では参照のみ）
    - execution/                # 発注エンジン関連（Engine, BrokerFactory, OrderManager, etc.）（実体は省略）
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
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
    - data/                      # (実行時に作成する想定)
      - *.db, kill.flag, stop_requested.flag, execution.pid
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py

サンプル .env（抜粋）
--------------------
JQUANTS_REFRESH_TOKEN=あなたのJQUANTS_REFRESH_TOKEN
KABU_API_PASSWORD=あなたのkabu_api_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=（AI を使う場合に設定）

依存関係（主要）
----------------
- duckdb
- psutil
- openai (OpenAI Python SDK)
- PyYAML（config ファイルの検証を行う場合に推奨）

ライセンス・貢献
----------------
本 README はコードベースの説明を目的としたドキュメントです。実際のライセンスや貢献フローはプロジェクトルートの LICENSE や CONTRIBUTING.md を参照してください。

補足
----
- コード内に多くの注釈コメントとドキュメント文字列があります。各モジュールの実装詳細や設計意図は該当モジュールの docstring を参照してください。
- 実運用では監視・アラート設定、ログの保管期間、DB バックアップなど運用手順を別途整備してください。