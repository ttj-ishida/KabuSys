README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のミニマル実装です。本リポジトリは以下の主要機能を含みます。

- 注文実行エンジン（ExecutionEngine）とその起動スクリプト
- システム監視（監視デーモン／ポーリング）と Kill Switch
- ポートフォリオ構築（銘柄選定・重み付け・株数決定）
- 研究用モジュール（ファクター計算・特徴量探索）
- AI を使ったニュースセンチメント / レジーム判定（OpenAI）
- Paper Trading 向けの検証レポート生成ツール
- 環境設定ウィザードと設定検証ツール

設計方針の要約:
- DB/外部API を直接叩く箇所は明確に分離（分析/研究コードは DuckDB を受け取る）
- 本番とペーパートレードの DB を分離（paper_trading モード）
- .env による設定管理、対話式ウィザードと事前検証を提供
- OpenAI 呼び出しはリトライやバリデーションを念入りに実装（フェイルセーフ）

主な機能一覧
-------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV によりペーパートレード用モックを使用）
  - run_monitoring.py: SystemMonitor（監視）ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - config_setup.py: .env を対話式に作成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の検証 CLI
  - config.py: Settings クラス（環境変数のラッパー）
- 監視関連
  - monitoring_engine.py: 各モニタ（System/Trade/Risk）をまとめて実行するエンジン
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 個別監視ロジック
  - monitoring_db.py: SQLite を使った監視ログ永続化層
  - kill_switch.py: 条件に応じて data/kill.flag を書く Kill Switch
- ポートフォリオ構築
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- 研究・分析
  - research/factor_research.py, research/feature_exploration.py
- AI モジュール（OpenAI 使用）
  - ai/news_nlp.py: ニュースを LLM でスコアリングして ai_scores に書き込む
  - ai/regime_detector.py: マクロ + ETF MA で市場レジームを判定して保存
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定（stdout + 日次ローテーション）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成

セットアップ手順
----------------
1. Python 環境を準備
   - 推奨: 仮想環境を作成
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 本リポジトリに requirements.txt がない場合は最低限以下をインストールしてください:
     - duckdb, psutil, openai, (PyYAML は config 検証時にあると便利)
   - 例:
     - pip install duckdb psutil openai PyYAML

3. ディレクトリ初期作成
   - data/ と logs/ はログやフラグファイルの保存に使われます。多くの処理は自動的に作成しますが手動で作る場合:
     - mkdir -p data logs

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいはプロジェクトルートに .env を手動で配置
   - 自動で .env を読み込む仕組み:
     - プロジェクトルートは .git または pyproject.toml を基準に検出されます
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます

5. 設定の検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

注目すべき環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB / ファイルパス（デフォルト値）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
- ログ:
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ保存先（デフォルト: logs/）
- Paper Trading / AI:
  - PAPER_FILL_MODE: instant | partial | never | reject  (default: instant)
  - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector で使用）
- 監視閾値（デフォルト）
  - CPU_THRESHOLD_PCT（デフォルト: 90.0）
  - MEMORY_THRESHOLD_PCT（デフォルト: 85.0）
  - DISK_THRESHOLD_PCT（デフォルト: 90.0）
- 監視ループ間隔:
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

使い方（主要コマンド）
--------------------
- .env の作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - 開発（デフォルト）/ 本番 / ペーパートレードは KABUSYS_ENV で切替
  - 例（ペーパートレード）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 停止方法:
    - data/stop_requested.flag を作成すると起動中のスクリプトが検知して終了します
    - Kill Switch（kill.flag）は監視コンポーネントから書かれることで ExecutionEngine に停止を促します

- 監視デーモン起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書きできます（例: export MONITOR_POLL_INTERVAL=30）
  - run_monitoring は monitoring 用の SQLite（settings.sqlite_path）を使います（環境に関わらず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを直接指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング（プログラム内呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection
    - target_date: datetime.date
    - api_key: None の場合 OPENAI_API_KEY を参照
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI キーが必要（無ければ ValueError）

ログとプロセス制御
------------------
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一されます。ログは stdout と logs/<app_name>.log に日次ローテートで出力されます。
- 起動スクリプトは最初にプロセス優先度を "high" に設定しようとします（psutil を利用）。権限によっては失敗して警告が出ます。
- 停止フラグ:
  - data/stop_requested.flag: run_execution / run_monitoring が外部からの終了要求をポーリングして検出するファイル
  - data/kill.flag: KillSwitch が書き込み、ExecutionEngine の停止トリガーとして使われます
  - 起動時に kill.flag を自動でクリアするオプション（KILL_FLAG_CLEAR_ON_START=1）があるが、本番では危険なのでデフォルトは 0

ディレクトリ構成
----------------
（src 以下を基準に簡易表示）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数ラッパー / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - trade_monitor.py  (存在する想定のファイル; 監視の一部)
    - alert_manager.py  (存在する想定の補助モジュール)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に生成されることが多い)
    - monitoring.db（デフォルト）
    - paper_trading.db（ペーパートレード用）
    - kill.flag, stop_requested.flag, execution.pid などの制御ファイル
  - logs/（デフォルトログ出力先）

補足 / 運用上の注意
-------------------
- 本番環境（KABUSYS_ENV=live）では必ず .env の内容を慎重にレビューしてください（validate_config 参照）。
- OpenAI を用いる機能は API 呼び出しに失敗した場合でもシステムが継続するよう設計されていますが、API キー管理・コストに注意してください。
- monitoring と execution はフラグファイル / PID ファイルを介して連携します。停止や再起動の運用ルールをチームで決めておくと安全です。
- SQLite / DuckDB のパスは環境変数で上書きできます。バックアップや権限設定に注意してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。
- ライセンス情報はリポジトリルートに LICENSE ファイルを置いて管理してください（本コードベースには明示されていません）。

以上。追加で README に含めたい具体的なコマンド例や CI/デプロイ手順、依存関係ファイル（requirements.txt）を生成したい場合は教えてください。