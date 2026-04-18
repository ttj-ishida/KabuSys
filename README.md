KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株向けの自動売買／リサーチ基盤モジュール群（kabusys）です。  
ポートフォリオ構築・ポジションサイジング、モニタリング、実行エンジン（ペーパー／本番切替）や AI 補助のニュースセンチメント、各種ユーティリティを含みます。

主な目的
- 自動売買エンジン（ExecutionEngine）の起動・制御
- システム／取引の監視とアラート・Kill Switch
- ポートフォリオ構築・株数算出ロジック（純粋関数群）
- DuckDB を用いたリサーチ用ファクター計算
- OpenAI を用いたニュース NLP（センチメント）や市場レジーム判定
- ペーパートレードの検証レポート出力ツール

機能一覧
- 環境設定ウィザード（.env の対話的生成）: kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の前倒しチェック）: kabusys.validate_config
- 実行エンジン起動スクリプト（paper_trading 切替対応・専用 DB）: run_execution.py
- 監視ポーリング（SystemMonitor）起動スクリプト: run_monitoring.py
- MonitoringDB（SQLite）による system_status / trade_logs / risk_logs / positions / dashboard の永続化
- RiskMonitor / TradeMonitor / SystemMonitor を束ねる MonitoringEngine
- Kill Switch（data/kill.flag）による安全停止トリガ
- Portfolio construction（選定・重み付け・単元丸め・セクター上限）
- Research: ファクター計算（momentum / volatility / value）、特徴量探索、IC 計算
- AI: news_nlp（OpenAI でニュースをスコアリング）、regime_detector（市場レジーム判定）
- ペーパートレード検証レポート生成ツール: kabusys.tools.paper_verification_report

セットアップ手順（開発マシン想定）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 環境を作成・有効化（推奨: venv / pyenv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - 必須（主に使用されるライブラリの例）:
     - duckdb
     - psutil
     - openai
     - (任意) PyYAML（config/*.yaml の検証で使用）
   - 例:
     - pip install duckdb psutil openai
     - pip install pyyaml   # validate_config で YAML 検証をしたい場合
   - （注）requirements.txt がある場合はそれを使用してください。
4. .env を用意
   - 対話式ウィザード: python -m kabusys.config_setup
     - このウィザードは .env を生成・更新します（デフォルト: プロジェクトルート/.env）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数（一例）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — paper_trading 時の DB（デフォルト: data/paper_trading.db）
     - LOG_LEVEL — DEBUG/INFO/...
     - OPENAI_API_KEY — OpenAI を利用する機能で必要
     - MONITOR_POLL_INTERVAL — 監視ループの間隔（秒、run_monitoring 用）
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も厳格に扱いたい場合: python -m kabusys.validate_config --strict

使い方（主要コマンド）
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite に記録（本番 DB から分離）
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
    - 実行中は data/stop_requested.flag を監視し、存在すれば停止を試みる
    - PID ファイルを data/execution.pid（デフォルト）に書き込む
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor を初期化してポーリング（デフォルト 60 秒）
    - MONITOR_POLL_INTERVAL 環境変数で秒数を変更可能
    - 監視結果は settings.sqlite_path（monitoring.db）に保存（本番 DB を使用）
    - data/stop_requested.flag を検出するとループを抜けて終了
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または PAPER_TRADING_SQLITE_PATH 環境変数で指定

重要ファイル・フラグ
- .env（プロジェクトルート）: 環境設定（config_setup で生成）
- data/stop_requested.flag: run_execution/run_monitoring が存在を検出して終了するためのフラグ
- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine 停止トリガ（冪等）
- data/execution.pid: ExecutionEngine の PID ファイル（デフォルト）
- データベース:
  - DuckDB: data/kabusys.duckdb（分析・リサーチ向け）
  - SQLite (monitoring): data/monitoring.db
  - SQLite (paper trading): data/paper_trading.db（paper_trading 用、設定で分離可能）

ログ
- ログは kabusys.utils.logging_setup.setup_logging によって統一管理されます。
- デフォルト: logs/<app_name>.log 日次ローテーション（30 日分保持） + コンソール出力（stdout）
- app_name 例: "execution", "monitoring"（起動スクリプトが指定）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（自動 .env ロード機能）
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（テーブル初期化 / CRUD）
    - system_monitor.py           — システム状態・データ鮮度監視
    - risk_monitor.py             — ドローダウン / ポジション上限監視
    - trade_monitor.py            — （取引関連の監視ロジック）
    - monitoring_engine.py        — 各 Monitor を束ねる実行ループ
    - kill_switch.py              — kill.flag 書き込みロジック
    - alert_manager.py            — （アラート実装）
  - execution/
    - execution_engine.py         — ExecutionEngine 本体（発注ループ等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み付け
    - position_sizing.py          — 株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py          — セクター上限・レジーム乗数
  - research/
    - factor_research.py          — ファクター計算（momentum/volatility/value）
    - feature_exploration.py      — IC / forward returns / summary
  - data/
    - pipeline.py                 — データパイプライン（prices_daily など）
    - stats.py                    — 正規化ユーティリティ等
  - ai/
    - news_nlp.py                 — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py          — 市場レジーム判定（MA + マクロセンチメント）
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity 設定
  - その他モジュール多数（詳細はソースを参照）

運用上の注意・トラブルシューティング
- 本番環境設定（KABUSYS_ENV=live）時は LINE 通知設定などを必ず確認してください。
- .env の自動ロード:
  - 起動時にプロジェクトルート（.git または pyproject.toml がある場所）を探索して .env/.env.local を自動読み込みします。
  - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Stop / Kill
  - 即時停止を要求する場合は data/stop_requested.flag を作成してください（run_* スクリプトが検出して安全終了します）。
  - 自動的な停止条件（ドローダウン超過など）は KillSwitch が data/kill.flag に理由を書き込みます。ExecutionEngine はこれを検知して停止します。
- デバッグ:
  - LOG_LEVEL=DEBUG を .env に設定して詳細ログを得られます（ログは stdout と logs/ に出力されます）。
- OpenAI/API:
  - news_nlp / regime_detector は OPENAI_API_KEY を参照します。キー未設定時は関連機能はエラー（またはフォールバック挙動）になります。
  - API 呼び出しはリトライ・バックオフ実装がありますが、API レート制限や課金に注意してください。

ライセンス・貢献
- 本ドキュメントにはライセンス情報を含めていません。実際のリポジトリの LICENSE を参照してください。
- バグ報告やプルリクエストはリポジトリの issue / PR を通じて受け付けてください。

最後に
- 各モジュールは基本的に「純粋関数（研究系）」 / 「副作用を持つ I/O 層（execution/monitoring）」に分離して設計されています。まずは config_setup → validate_config → run_monitoring（監視）→ run_execution（発注） の順で動作確認することを推奨します。

必要があれば、インストール用 requirements.txt の推奨パッケージ一覧や systemd / Supervisor 用のユニットファイル例、Dockerfile の雛形なども作成します。希望があれば教えてください。