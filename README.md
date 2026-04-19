KabuSys — 日本株自動売買システム（コードベース README）
概要
- KabuSys は日本株の自動売買／リサーチ／監視を目的としたモジュール群です。
- 主な機能はアルゴリズムによる銘柄選定・配分、発注エンジン（本番／ペーパートレード）、システム監視・アラート、AI を用いたニュースセンチメント／レジーム判定、研究用ファクター計算、各種ユーティリティです。
- パッケージは Python モジュール群として構成され、CLI 風に起動できるスクリプト（python -m kabusys.<module>）を提供します。

主な特徴（機能一覧）
- ExecutionEngine（run_execution.py）
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV による）。
  - ペーパートレード時は MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離。
  - リスク管理（RiskManager）、注文管理（OrderManager）、リコンシリエーション等を組み合わせて取引セッションを実行。

- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして状態を監視。
  - 監視ログを SQLite（デフォルト: data/monitoring.db）に保存。
  - Kill Switch（data/kill.flag）で ExecutionEngine を遠隔停止。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。

- ポートフォリオ構築（portfolio パッケージ）
  - 銘柄選定、等金額・スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ算出（単元株丸め、資金制約対応）。

- リサーチ（research パッケージ）
  - DuckDB 上の prices_daily / raw_financials 等を用いたファクター計算（モメンタム・ボラティリティ・バリュー）。
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー等。

- AI サービス（ai パッケージ）
  - ニュース NLP（news_nlp.py）：OpenAI（gpt-4o-mini）でニュースをスコアリングし ai_scores に保存（OpenAI API キー必要）。
  - 市場レジーム判定（regime_detector.py）：ETF の MA 乖離とマクロニュースセンチメントを組合せて日次判定。

- ツール
  - 環境設定ウィザード（config_setup.py）で .env の生成／更新を対話式で支援。
  - validate_config.py で起動前に環境変数・設定ファイル等の基本検証。
  - paper_verification_report（tools）でペーパートレード DB を集計して PASS/FAIL レポートを出力。

セットアップ手順
1. 前提
   - Python 3.10+ を推奨（typing の | 記法やその他仕様に依存）。
   - システムに DuckDB、psutil、openai、（必要であれば）PyYAML などの依存が入ることを想定。

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - プロジェクトに requirements.txt があれば:
     - pip install -r requirements.txt
   - またはパッケージを editable インストール:
     - pip install -e .

   （少なくとも duckdb, psutil, openai は必要な機能で使用されます）

4. 初期設定
   - 対話式で .env を作る:
     - python -m kabusys.config_setup
   - あるいは .env を自分で作成して以下主要キーを設定:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 用
     - LOG_LEVEL, LOG_DIR, OPENAI_API_KEY（AI 機能を使う場合）
     - その他 README 内の説明を参照してください。

5. 設定検証（起動前）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1) になります:
     - python -m kabusys.validate_config --strict

使い方（起動／コマンド）
- ExecutionEngine を起動（本番 or paper_trading は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了する設計です。
  - 実行中は data/execution.pid に PID を書きます。

- Monitoring を起動（常駐ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で変更できます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視ループは data/stop_requested.flag の存在で停止します。

- Kill Switch（Execution の停止）
  - KillSwitch は data/kill.flag を作成して ExecutionEngine を停止させます（Monitoring の判定により作成されます）。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 に設定されていると自動でクリアされます（本番では 0 推奨）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能の利用
  - OpenAI API を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY の設定が必要です。
  - 関数はパッケージ API としても利用可能（例: from kabusys.ai import score_news）。

重要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL, LOG_DIR: ロギング設定
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（TimedRotatingFileHandler、30日保持）。
- 起動スクリプトでは setup_logging(app_name="execution" or "monitoring") を呼び出します。
- コンソール出力は stdout に出ます（stderr ではない点に注意）。

停止・制御ファイル（data ディレクトリ）
- data/stop_requested.flag: run_execution / run_monitoring の外部停止フラグ（存在すると監視ループ・エンジンは安全停止）。
- data/kill.flag: Kill Switch による Execution 停止フラグ（監視の判定で書き込まれる）。
- data/execution.pid: ExecutionEngine の PID ファイル。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py (パッケージ定義、__version__)
  - config.py (環境変数の自動読み込み・Settings クラス)
  - config_setup.py (対話式 .env ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - utils/
    - logging_setup.py (共通ログ設定)
    - process_priority.py (プロセス優先度 / CPU affinity ユーティリティ)
  - monitoring/
    - monitoring_db.py (SQLite 永続化層)
    - system_monitor.py
    - trade_monitor.py (存在するが詳細は省略)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在するが詳細は省略)
  - execution/ (Execution 関連コンポーネント)
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
  - data/ (想定される実行時データ格納先)
    - monitoring.db (SQLite, 監視ログ)
    - paper_trading.db (ペーパートレード DB)
    - kabusys.duckdb (DuckDB)
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py

設計上の注意点・運用上のポイント
- 環境変数は .env と OS 環境変数の併用を想定。config.py はプロジェクトルートの .env/.env.local を自動ロードします（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
- 本番（KABUSYS_ENV=live）では kill_flag_clear_on_start=0 を推奨。live では通知設定（LINE 等）を確認してください。
- Monitoring と Execution は別 DB を共有しない設計（ペーパートレード時は明確に分離）。
- AI 呼び出しでは冪等性・部分失敗時のデータ保護（取得成功分のみ書き換え）やリトライを実装しており、API キー未設定時は例外やフォールバックの挙動に注意してください。
- ポートフォリオ算出・ポジションサイズ計算は純粋関数群（副作用なし）として設計され、テストしやすくなっています。

トラブルシューティング（よくある疑問）
- 「モジュールを起動しても何も起こらない」: まず .env が正しく設定されているか、ログ（logs/）や data/ にファイルが作成されているかを確認してください。validate_config で基本チェックができます。
- 「監視が止まらない／止めたい」: data/stop_requested.flag を作成すると run_monitoring / run_execution のループは終了します。Kill Switch は data/kill.flag を書き込みます。
- 「DuckDB/SQLite のパスを変えたい」: .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください。

最後に
- この README はコードベースの要点をまとめたものであり、実運用にはログローテーション、バックアップ、監視ルールの調整、外部 API の鍵管理（Secret 管理）など運用面の追加対策が必要です。
- 追加ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）がリポジトリにある場合はそちらを参照して戦略ロジックの詳細を確認してください。

必要ならば、README を Markdown 形式で整形したものや、具体的な .env.example、起動スクリプト例（systemd / supervisor 用）も作成できます。どの形式が欲しいか教えてください。