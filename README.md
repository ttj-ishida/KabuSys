KabuSys
=======

日本株向けの自動売買／リサーチ基盤ライブラリ群（モジュール群 + 起動スクリプト）。  
このリポジトリはデータ処理（DuckDB）、監視（SQLite）、Execution / Paper Trading、ポートフォリオ構築、ファクター計算、LLM ベースのニュース NLP 等の機能を含みます。

主な特徴
--------
- ExecutionEngine（実運用 / ペーパートレード対応）および監視デーモンを個別プロセスとして起動可能
- Paper Trading は本番 DB と分離（data/paper_trading.db を使用）
- DuckDB を使ったリサーチ（ファクター算出、将来リターン、IC 計算）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（ニュース NLU、レジーム判定）
- 監視用 SQLite（system_status / trade_logs / risk_logs / dashboard 等）と Kill Switch ロジック
- ロギングユーティリティ（コンソール + 日次ローテーションファイル）
- .env ウィザード（対話式）と設定検証 CLI

必須要件（推奨）
----------------
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能使用時）
  - PyYAML（config/*.yaml の検証を行う場合）
- その他依存は setup / requirements ファイルがあればそちらに従ってください。

セットアップ手順
----------------
1. リポジトリをクローン / 展開する。
2. 仮想環境を作成して依存パッケージをインストールする。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -r requirements.txt  （requirements.txt がある場合）
     - 必要なパッケージを個別に pip install duckdb psutil openai pyyaml 等
3. .env を作成する
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - ウィザードは .env（デフォルト）を作成／更新します。
   - 手動で作成する場合は .env.example を参考にしてください（リポジトリにある場合）。
4. 設定検証（起動前のチェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります（exit code 1）。
5. ディレクトリ作成
   - data/ や logs/ は起動時に自動作成される場合がありますが、必要に応じて手動で作成して権限を確認してください。

主要な環境変数
----------------
- 必須（最低限）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境指定:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
    - paper_trading: MockBrokerClient を使用し、data/paper_trading.db に記録します
- データベース:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading の場合の DB、デフォルト: data/paper_trading.db）
- ログ:
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
  - LOG_DIR（ログ保存先、デフォルト: logs/）
- その他:
  - OPENAI_API_KEY（AI 機能を使うとき）
  - PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject）
  - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）
  - PID_FILE_PATH / KILL_FLAG_PATH（PID / kill flag のパスを上書き）

よく使うコマンド（使い方）
------------------------
- 設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒）
  - 監視は監視用 SQLite（Settings.sqlite_path）を使用（KABUSYS_ENV に関係なく本番 sqlite_path を使う）
  - 停止: data/stop_requested.flag を作成するとループが終了します
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、data/paper_trading.db に記録します
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - 実行中は data/execution.pid に PID が書き込まれます
  - 停止は data/stop_requested.flag 作成で通知、または Kill Switch により data/kill.flag が書かれると停止対象になります
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI / リサーチ系はライブラリ関数として利用
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - duckdb 接続を作成して関数に渡します（ai は OPENAI_API_KEY 必須）

監視・Kill Switch の概略
-----------------------
- 監視データは SQLite（monitoring_db）に永続化されます（system_status, trade_logs, positions, risk_logs, dashboard など）。
- RiskMonitor: ダッシュボードのハイウォーターマーク管理、ドローダウンとポジション上限のチェック。必要時に risk_logs と dashboard を更新します。
- KillSwitch: RiskMonitor（等）がトリガー条件を満たすと data/kill.flag を作成し、ExecutionEngine の停止を促します。
- run_monitoring / run_execution は data/stop_requested.flag を使って安全に停止できます。

ログ設定
-------
- 共通関数: kabusys.utils.logging_setup.setup_logging(app_name="execution")
  - コンソール出力（stdout）と日次ローテーションファイル（logs/<app_name>.log）を設定
  - LOG_DIR / LOG_LEVEL で挙動を上書き可能
  - デフォルトで日次ログを 30 日分保持

ディレクトリ構成（抜粋）
-----------------------
リポジトリの src/kabusys 以下に主要モジュールがあります。以下は主なファイル／ディレクトリと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定管理（Settings クラス）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリング
    - regime_detector.py — マクロ + ETF MA を用いた market regime 判定
  - monitoring/
    - monitoring_db.py — 監視用 SQLite のテーブル初期化・CRUD ラッパー
    - system_monitor.py — システム（CPU/MEM/DISK）およびデータ鮮度監視
    - trade_monitor.py — （trade 監視ロジック）※詳細は実装を参照
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の管理ロジック
    - monitoring_engine.py — 監視コンポーネントの束ね（テスト用 run_once/run 循環）
  - execution/  — ExecutionEngine 系コンポーネント（broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py — 株数計算・単元丸め・aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン・IC 計算・統計サマリ
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/（ランタイムで使用; ソースには含まれないことが多い）
    - monitoring.db（default: data/monitoring.db）
    - paper_trading.db（paper_trading 用）
    - kill.flag / stop_requested.flag / execution.pid などのフラグや PID

設計上の注意点 / 運用上の留意点
------------------------------
- KABUSYS_ENV による分離:
  - paper_trading は本番データベースと完全分離され、専用の SQLite を使用します。
  - ただし monitoring はコード内で「環境にかかわらず本番 sqlite_path を使用する」箇所があるため（意図的設計）、運用時は注意してください。
- Kill Switch は手動／自動で書き込まれうるため、本番運用では kill.flag の取り扱いに注意（KILL_FLAG_CLEAR_ON_START 設定もある）。
- AI 機能は OpenAI API に依存します（コスト・レート制限あり）。API failure 時は安全側でフォールバックする実装（多くはスコア 0 で継続）になっていますが、運用ポリシーを決めてください。
- ログディレクトリの作成に失敗するとファイル出力は無効化されコンソール出力のみになります。パーミッション等を確認してください。
- process_priority の変更はプラットフォーム依存でアクセス権が必要な場合があります。権限不足は警告で済むように実装されています。

サンプル .env（最小構成）
-------------------------
以下は最低限必要なキーの例（実運用では機密情報は適切に管理）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx (AI 機能を使う場合)

追加情報 / 開発
----------------
- ユニットテスト、CI、ドキュメントはプロジェクトの別ファイル（tests/, docs/ 等）を参照してください（この README はコードベースの概要と運用ガイドです）。
- コード内の docstring やコメントは実装の意図・制約を詳細に記載しています。実装を拡張する際は docstring に従ってください。

サポート
--------
- 問題点やバグは issue を作成してください。設計・運用に関する質問は README 更新時に反映します。

以上。運用開始前に必ず python -m kabusys.validate_config で設定を検証してください。