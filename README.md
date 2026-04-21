KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株向けの自動売買フレームワーク（プロトタイプ）です。  
主な目的は、データ取得・ファクター計算・ポートフォリオ構築・注文実行・監視・アラートなどを分離したモジュール群で実装し、実運用／ペーパートレード間で切り替えられることです。

特徴（機能一覧）
----------------
- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使い、paper_trading 用 DB（data/paper_trading.db）へ記録
  - PID ファイル管理、停止フラグ受付（data/stop_requested.flag）
  - リスク管理（RiskManager）、注文管理（OrderManager）、Reconciler 等の組み立て
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - system / trade / risk のログを SQLite（monitoring.db）に永続化
  - Kill Switch: ドローダウン等の条件で ExecutionEngine を停止させる kill.flag の生成
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔の変更（デフォルト 60 秒）
- 研究用モジュール（research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算（等金額・スコア加重）、ポジションサイジング、セクター上限適用、レジーム乗数
- AI 統合（ai）
  - ニュースの NLP スコアリング（OpenAI を利用）、市場レジーム判定の補助
- ツール
  - Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- 設定ユーティリティ
  - .env を対話式作成するウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）
- ログ設定ユーティリティ（utils.logging_setup）
  - stdout 出力と日次ローテーションファイル出力（logs/<app>.log）

セットアップ手順
----------------
1. Python 環境
   - Python 3.10+ を推奨（型注釈で Union | 使用など）
   - 仮想環境を作成してアクティベートしてください。
     - 例: python -m venv .venv && source .venv/bin/activate

2. 依存パッケージのインストール（例）
   - 必要なパッケージ例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config/*.yaml の内容検証を行う場合）
   - pip install duckdb psutil openai PyYAML
   - 実行環境によっては他パッケージ（requests 等）が必要になる場合があります。

3. .env の準備
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
     - これによりプロジェクトルートに .env が作成されます（絶対に Git にコミットしないでください）。
   - あるいは .env.example を参考に手動で作成してください。
   - 自動 .env 読み込みはデフォルトで有効です。無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時など）。

4. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になります。

5. データディレクトリ
   - デフォルトで以下のファイル/ディレクトリが使用されます:
     - data/kabusys.duckdb（DuckDB）
     - data/monitoring.db（SQLite, 監視用）
     - data/paper_trading.db（ペーパートレード用, KABUSYS_ENV=paper_trading の場合）
     - data/execution.pid（ExecutionEngine の PID）
     - data/kill.flag（KillSwitch が生成する停止フラグ）
     - data/stop_requested.flag（run_* スクリプトの外部停止フラグ）
   - logs/ ディレクトリにログが日次ローテーションで保存されます（logs/<app>.log）。

主な環境変数（抜粋）
-------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動で削除するか（0/1）

使い方（コマンド例）
-------------------
- .env を作成
  - python -m kabusys.config_setup

- 設定の検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（メインの発注実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution  # ペーパートレードで起動
  - 実行中に data/stop_requested.flag を作成すると起動スレッドが安全に停止します。
  - 実行は PID ファイル（data/execution.pid）を管理します。

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path を使用します（KABUSYS_ENV に依らず monitoring DB は本番を参照）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニューススコア・レジーム判定）
  - 実行前に OPENAI_API_KEY を環境変数で設定してください。
  - news_nlp.score_news, regime_detector.score_regime などの関数を使って DuckDB の raw_news 等を処理します（ライブラリ関数として呼び出す想定）。

停止フラグ / Kill Switch
-----------------------
- 実行停止: data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して終了します。
- Kill Switch: RiskMonitor が条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側で検出して停止させる運用です。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag をクリアしますが、本番では 0 を推奨します。

ロギング
--------
- logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30 日保持）。
- setup_logging(app_name="execution") のように各スクリプトで統一的に設定されます。
- コンソール出力は stdout を使用します（cron 等でリダイレクトしやすくするため）。

ディレクトリ構成
----------------
（主要ファイル・ディレクトリのみ抜粋）

- project_root/
  - .env (プロジェクト設定、絶対にコミットしない)
  - pyproject.toml / setup.py / …（パッケージメタ情報）
  - data/
    - kabusys.duckdb            # DuckDB（デフォルト）
    - monitoring.db             # SQLite 監視 DB（デフォルト）
    - paper_trading.db          # Paper Trading 用 SQLite（paper_trading）
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - logs/
    - execution.log
    - monitoring.log
    - …（日次ローテーション）
  - config/
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml
  - src/
    - kabusys/
      - __init__.py
      - config.py                 # 環境変数・自動 .env ロード
      - config_setup.py           # .env 対話ウィザード
      - validate_config.py        # 設定検証 CLI
      - run_execution.py          # ExecutionEngine 起動スクリプト
      - run_monitoring.py         # Monitoring 起動スクリプト
      - ai/
        - news_nlp.py
        - regime_detector.py
      - monitoring/
        - monitoring_db.py
        - monitoring_engine.py
        - system_monitor.py
        - trade_monitor.py (実装ファイルは抜粋されていませんが存在想定)
        - risk_monitor.py
        - kill_switch.py
        - alert_manager.py (実装ファイルは抜粋されていませんが存在想定)
      - portfolio/
        - portfolio_builder.py
        - position_sizing.py
        - risk_adjustment.py
      - research/
        - factor_research.py
        - feature_exploration.py
      - tools/
        - paper_verification_report.py
      - utils/
        - logging_setup.py
        - process_priority.py
      - execution/ (Engine, OrderManager, BrokerFactory 等の実装が配置)
      - data/ (データパイプライン・DuckDB スキーマ関連)

注意事項 / トラブルシューティング
---------------------------------
- 必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）が未設定だと起動前検証や実行時に例外になります。validate_config を利用して事前確認してください。
- PyYAML がインストールされていない場合、validate_config は YAML 検証をスキップして警告を出します。
- OpenAI API を用いる機能は API キーが必須です（OPENAI_API_KEY）。
- process priority 設定（psutil を使用）は権限が必要になる場合があります。権限不足だと警告が出ますが処理自体は継続します。
- DuckDB / SQLite の親ディレクトリが存在しない場合は起動時に自動作成されますが、権限がないとファイル作成に失敗します。
- データベーススキーマのマイグレーション（カラム追加等）は init_monitoring_db で行われます。

ライセンス・貢献
----------------
- 本リポジトリに付与されるライセンスやコントリビューションルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（本 README はソースコードに基づく技術ドキュメントです）。

以上。README の補足や特定モジュールの使い方（API 参照、ユニットテストの実行方法、CI 設定など）を追加で作成することもできます。必要であれば教えてください。