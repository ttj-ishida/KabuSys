# KabuSys — 日本株自動売買システム（簡易 README）

この README はリポジトリ内の主要スクリプト・モジュールを元に作成した利用ガイドです。開発者向けに設定・起動方法、主要機能、ディレクトリ構成を日本語でまとめています。

概要
- KabuSys は日本株向けの自動売買システムのコンポーネント群です。
- 主要機能は、取引実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・サイズ決定、ファクター計算・リサーチ、AI（ニュース NLP / レジーム判定）など。
- ローカル開発・ペーパートレード・本番（live）の3つの実行モードを想定しており、環境変数（.env）で切り替えます。

主な機能一覧
- 実行エンジン起動（run_execution.py）
  - Broker クライアントの抽象化（実運用は kabuステーション、paper_trading では MockBrokerClient を使用）
  - 注文管理（OrderManager / OrderRepository）
  - リスク管理（RiskManager, RiskConfig）
  - 再整合処理（Reconciler）
  - pid ファイル管理 / 停止フラグ対応
- 監視（run_monitoring.py, monitoring package）
  - システム状態監視（CPU / メモリ / ディスク、プロセス生存確認）
  - 注文ログ / 約定ログ監視、リスク監視（ドローダウン・ポジション上限）
  - Kill Switch（kill.flag）による停止シグナル出力
  - アラート通知連携（LINE 等、設定があれば）
- ポートフォリオ構築（portfolio package）
  - 候補選定・重み付け（等配分、スコア配分）
  - セクターキャップ・レジーム乗数
  - ポジションサイズ計算（単元株丸め、risk-based 等）
- リサーチ（research package）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
  - DuckDB を用いたオフライン計算
- AI（ai package）
  - news_nlp: OpenAI を用いたニュースのセンチメントスコア化（ai_scores テーブルへ）
  - regime_detector: ETF（1321）MA とマクロニュースから市場レジームを判定し保存
  - OpenAI 呼び出しはリトライ・バリデーション機構あり
- ツール
  - config_setup.py: .env を対話式で作成／更新するウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成

セットアップ手順（ローカル開発向け）
1. Python 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必要パッケージの一例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML のパースを行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. プロジェクトルートの確認
   - プロジェクトは .git または pyproject.toml を基準にプロジェクトルートを自動検出します。
   - data/ や logs/ は起動時に自動作成される場合がありますが、手動で作成しておくと安全です：
     - mkdir -p data logs

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または .env を手動で作成（例は下記参照）。
   - 自動ロードはデフォルトで有効（OS 環境変数 > .env.local > .env の順）。

主要な環境変数（代表）
- 必須（起動前に設定）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 重要なもの
  - KABUSYS_ENV: 実行モード（development | paper_trading | live）デフォルト: development
    - paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録し、本番 DB と分離。
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/…）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
  - KILL_FLAG_CLEAR_ON_START: 本番での自動クリア安全フラグ（0/1、デフォルト: 0）
- 監視ループ専用
  - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

最小 .env（例）
- .env.example を参照して作成してください。最低限の例:
  JQUANTS_REFRESH_TOKEN=your_token_here
  KABU_API_PASSWORD=your_password_here
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO

設定検証
- 起動前に設定をチェック:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

使い方（起動・スクリプト）
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 特徴:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒、デフォルト 60）
    - stop 制御: プロジェクトルート/data/stop_requested.flag が存在するとループを終了
    - 監視は本番 sqlite_path（Settings.sqlite_path）を使用（環境にかかわらず）
    - ログは logs/monitoring.log（デフォルト）へ日次ローテーションで保存
- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 特徴:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使って data/paper_trading.db に記録
    - 実行中は data/execution.pid に PID を書く（PID ファイルパスは Settings で上書き可）
    - 停止制御:
      - data/stop_requested.flag により優雅に停止
      - Kill Switch（監視から書き込まれる data/kill.flag）により停止させる設計
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: env PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- AI / プログラム呼び出し例（コードから）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)  # conn は duckdb connection
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)

停止 / Kill Switch
- stop_requested.flag: run_monitoring/run_execution はプロジェクトルート/data/stop_requested.flag の存在を監視し、検出時に優雅に停止します。手動で停止させるにはこのファイルを作成します。
- kill.flag: KillSwitch は監視基準（ドローダウンやポジション上限など）に基づいて data/kill.flag を書きます。ExecutionEngine はこれを見て停止する仕組みです。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（注意: 本番では 0 推奨）。

ログ
- ログ設定は kabusys.utils.logging_setup.setup_logging を通して統一的に行われます。
- デフォルト出力:
  - コンソール（stdout）
  - ファイル: logs/<app_name>.log を日次ローテーションで保存（30日保持）
- LOG_DIR や LOG_LEVEL 環境変数で変更可能

永続化（DB）
- DuckDB（データ分析向け）: default data/kabusys.duckdb
- SQLite（監視・トレードログ）: default data/monitoring.db
- Paper Trading 用 SQLite: data/paper_trading.db（paper_trading モード時に使用）
- monitoring.monitoring_db.init_monitoring_db は必要なテーブル作成と簡易マイグレーション（例: latency_ms, peak_value カラム追加）を行います

開発者向けノート（実装上のポイント）
- Settings クラス（kabusys.config）で環境変数を一元管理。自動 .env 読み込み機構あり（プロジェクトルート検出ベース）。
- process_priority（kabusys.utils.process_priority）でプロセス優先度を設定（High/Normal/Low）。psutil を利用。
- OpenAI 利用部はリトライ・バリデーション・部分書き込み（部分失敗時のデータ保護）を意識した実装。
- リサーチ／ファクター計算は DuckDB を前提に純粋関数で実装（副作用なし、テスト容易）。

ディレクトリ構成（主要ファイルのみ）
- (プロジェクトルート)
  - src/
    - kabusys/
      - __init__.py
      - config.py
      - config_setup.py
      - validate_config.py
      - run_monitoring.py
      - run_execution.py
      - ai/
        - __init__.py
        - news_nlp.py
        - regime_detector.py
      - monitoring/
        - monitoring_db.py
        - monitoring_engine.py
        - system_monitor.py
        - trade_monitor.py
        - risk_monitor.py
        - kill_switch.py
        - alert_manager.py (想定)
      - execution/
        - execution_engine.py
        - broker_factory.py
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
      - tools/
        - __init__.py
        - paper_verification_report.py
      - utils/
        - __init__.py
        - logging_setup.py
        - process_priority.py
  - config/
    - *.yaml（system_config.yaml, data_config.yaml, ...）
  - data/
    - monitoring.db
    - paper_trading.db
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/
    - execution.log
    - monitoring.log
  - pyproject.toml / setup.cfg / .git/
  - .env / .env.local

よくある運用コマンドまとめ
- .env の作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動
  - python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
- 本 README はコードベースから抽出した情報をまとめたものです。実運用・本番導入時は必ず設定（特に KABUSYS_ENV, KILL_FLAG_CLEAR_ON_START, LINE 通知設定、API キー）を慎重に確認してください。
- config/*.yaml（system_config.yaml や risk_config.yaml 等）は運用ルールや戦略パラメータを格納する想定です。存在しない場合は generate スクリプトやテンプレートを用意して取り込みます（validate_config が存在チェックと YAML パースチェックを行います）。

問題が発生した場合や README に追記してほしい内容があれば、使用したいユースケース（例: Docker 起動方法、systemd サービス化、CI/CD）を教えてください。README をその用途に合わせて拡張します。