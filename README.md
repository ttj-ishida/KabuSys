KabuSys — 日本株自動売買システム（概要 README）
================================

このリポジトリは日本株向けの自動売買フレームワーク「KabuSys」の一部を含むコードベースです。  
README ではプロジェクト概要、主な機能、セットアップ手順、よく使うコマンド（使い方）、およびディレクトリ構成を日本語で説明します。

1. プロジェクト概要
-----------------
- KabuSys は日本株の自動売買を目的としたモジュール群（データパイプライン、リサーチ、ポートフォリオ構築、実行エンジン、監視、AI 補助機能など）を提供します。
- 設計方針の一部：
  - DuckDB / SQLite を使ったローカル DB によるデータ管理（分析用に DuckDB、監視・トレードログに SQLite）。
  - 実運用（live）とペーパートレード（paper_trading）を区別可能。
  - 外部 API（kabuステーション、J‑Quants、OpenAI 等）と接続する機能を持つが、モジュールはフェイルセーフ／部分失敗許容の設計。
  - ログ出力は統一的に設定（ログローテーション対応）。
  - Kill Switch / stop フラグ等により安全にエンジンを停止可能。

2. 主な機能一覧
--------------
- 設定管理
  - .env 自動ロード、Settings クラス（kabusys.config）で環境変数を一元管理
  - 対話式設定ウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）

- 実行エンジン起動 / 停止
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使い paper_trading DB に記録）
  - プロセス優先度の設定、PID ファイル管理、stop フラグ監視を含む

- 監視（Monitoring）
  - run_monitoring.py：SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL による間隔制御）
  - MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager などによる総合的な監視・通知・Kill フラグ運用
  - 監視ログ用 SQLite（monitoring_db.py）に system_status / trade_logs / positions / risk_logs / dashboard を永続化

- ポートフォリオ構築
  - 候補選定・重み計算（等金額・スコア）
  - セクター集中制限、レジーム乗数の適用
  - ポジションサイズ算出（単元株丸め・aggregate cap 等）

- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB 接続を受け取る純粋関数）
  - 将来リターン計算、IC（Information Coefficient）計算、特徴量サマリ

- AI（OpenAI）連携
  - ニュース NLP による銘柄別センチメント算出（ai.news_nlp）
  - マクロニュースと ETF の MA 乖離からレジーム判定（ai.regime_detector）
  - OpenAI 呼び出しはリトライやパース堅牢性を備え、API キーは環境変数で指定

- ツール
  - paper_verification_report：ペーパートレード DB を集計して検証レポートを出力

3. 必要条件（推奨）
----------------
- Python >= 3.10（PEP 604 の型記法（|）を使用）
- 必要なパッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- 実行環境により追加ライブラリや broker client 実装が必要（kabuステーション接続など）。

インストール例:
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- 必要パッケージのインストール（requirements.txt がない場合は手動で）
  - pip install duckdb psutil openai PyYAML

4. セットアップ手順
------------------
1) リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2) Python 仮想環境（上の「インストール例」参照）

3) .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動作成
   - 主要環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV (development | paper_trading | live)
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（例: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG|INFO|...）
     - KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア）

4) 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）

5) データディレクトリ & 権限
   - data/ および logs/ ディレクトリに書き込み可能であることを確認
   - 一部スクリプトは data/stop_requested.flag、data/execution.pid、data/kill.flag を使用します

5. 使い方（主要コマンド）
--------------------

- 対話式 .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格: python -m kabusys.validate_config --strict

- 監視（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60 秒）:
      - export MONITOR_POLL_INTERVAL=30
    - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。
    - 停止: data/stop_requested.flag を作成すると監視ループが終了します。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / settings.paper_sqlite_path）に記録されるため本番 DB と完全に分離されます。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。停止は stop フラグ / kill.flag で制御します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数を優先）

- AI / レジーム判定 / ニューススコアリング（ライブラリ呼び出し）
  - Python API から呼び出し可能:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - どちらも api_key 引数を受け取る（None の場合は環境変数 OPENAI_API_KEY を使用）。未設定の場合 ValueError。

- ログ設定
  - すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出してログを統一的に出力します（logs/<app_name>.log、日次ローテーション、30 日保持）。
  - LOG_DIR 環境変数でログディレクトリを指定可能。

6. 安全機構・運用に関する注意点
----------------------------
- Kill Switch / stop フラグ:
  - KillSwitch（monitoring.kill_switch）はリスク条件（ドローダウン超過、ポジション上限超過）で data/kill.flag を書き込み、ExecutionEngine の停止を促します。
  - ExecutionEngine および Monitoring は data/stop_requested.flag を参照して安全に停止します。
- 本番環境（KABUSYS_ENV=live）の設定は慎重に行ってください。validate_config は live の場合に追加の警告を出します。
- KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動でクリアしますが、本番では 0 を推奨します。
- run_monitoring は「監視専用」プロセスとして本番の monitoring DB（Settings.sqlite_path）を常に使用します（環境に依存しない仕様）。

7. 主要モジュール解説（要点）
----------------------------
- kabusys.config
  - .env 自動ロード（プロジェクトルートの .env / .env.local をロード）
  - Settings クラスから各種環境変数を取得（検証やデフォルトの扱い含む）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすれば自動ロードを無効化

- kabusys.utils.logging_setup
  - アプリケーション横断のログ設定（コンソール stdout + 日次ファイルローテーション）

- kabusys.utils.process_priority
  - プロセス優先度 / CPU affinity の設定ユーティリティ（Windows / POSIX を吸収）

- kabusys.monitoring
  - monitoring_db.py：SQLite のスキーマ作成と永続化 API（MonitoringDB クラス）
  - system_monitor.py：システム状態、データ鮮度、実行プロセスの監視
  - risk_monitor.py：ドローダウンやポジション上限の判定とリスクログ
  - kill_switch.py：kill.flag の管理と書き込み
  - monitoring_engine.py：各モニタを束ねるコーディネーター

- kabusys.execution
  - run_execution.py から組み立てられるコンポーネント群（BrokerClientFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler, OrderRepository 等）
  - paper_trading モードでは本番 DB と分離された SQLite を使用

- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment：純粋関数群で銘柄選定・配分・サイズ計算を実装

- kabusys.research
  - factor_research, feature_exploration：DuckDB を用いたファクター計算・統計解析

- kabusys.ai
  - news_nlp, regime_detector：OpenAI を利用したニューススコアリング・レジーム判定（堅牢なリトライ・JSON バリデーション・部分書き込み戦略あり）

8. ディレクトリ構成
-------------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
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
    - monitoring/ (監視関連ファイルは上にまとめてあります)

- data/                 （実行時に生成される SQLite / PID / flag 等）
  - monitoring.db       （デフォルト）
  - paper_trading.db    （paper_trading モード用）
  - execution.pid
  - stop_requested.flag
  - kill.flag

- logs/                 （ログファイル：logs/execution.log, logs/monitoring.log 等）
- config/               （yaml 設定テンプレート: system_config.yaml など）
- pyproject.toml / setup.cfg / requirements.txt （存在すれば依存管理に利用）

9. よくある運用コマンドまとめ
-----------------------------
- .env を作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 監視開始: python -m kabusys.run_monitoring
- エンジン起動: python -m kabusys.run_execution
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

10. 開発・テストに関するメモ
--------------------------
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト環境をコントロールできます。
- AI モジュール関数は API 呼び出し箇所をテスト用に差し替えやすいよう設計されています（内部の _call_openai_api などをモック可能）。
- DuckDB クエリはテスト用に簡単に差し替えられます（conn を引数で受け取る純粋関数設計）。
- 実行時のプロセス優先度設定は set_process_priority を使用しますが、権限不足で失敗する場合はログで警告が出てスキップされます。

11. ライセンス / 貢献
---------------------
- この README ではライセンス情報は含めていません。実プロジェクトでは LICENSE ファイルを参照してください。
- 修正や機能追加の際はテストを追加し、設定検証やマイグレーションの影響を確認してください。

補足
----
- ここに記載した操作やパスはコード内のデフォルト値に基づきます。実運用では .env でパスや閾値、API キー等を適切に設定してください。
- さらに詳しい設計意図やアルゴリズム（PortfolioConstruction.md, StrategyModel.md 等のドキュメント参照）がプロジェクト内にある場合はあわせて参照してください。

必要であれば README に含めるサンプル .env テンプレートや、よくあるトラブルシュート（ログの見方、kill.flag の扱い、DB マイグレーションの注意点）を追記します。どの情報を追加しますか？