KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買システム（KabuSys）のコアモジュール群を含みます。
設計は「監視 (monitoring)」「実行 (execution)」「リサーチ (research)」「ポートフォリオ構築」「AI（ニュース NLP / レジーム判定）」などの責務分離を前提としています。

主な目的
- 戦略に基づく銘柄選定・ポジションサイズ計算
- 注文実行エンジン（本番 / ペーパートレード切替）
- システム監視と Kill Switch による安全停止
- ニュース NLP / LLM を用いたセンチメント評価・レジーム判定
- DuckDB / SQLite を利用したデータ分析・ログ保存

機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて本番ブローカ or モック（paper_trading）を切替
  - data/execution.pid に PID を出力、data/stop_requested.flag で停止
  - RiskManager / OrderManager / Reconciler 等の組立てと実行
- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor を定期実行（デフォルト 60 秒）
  - モニタリング用 DB（SQLite）と分析 DB（DuckDB）を利用
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能
- 設定ウィザード（config_setup.py）
  - 対話式に .env を生成・更新する
- 設定検証ツール（validate_config.py）
  - .env と config/*.yaml の存在・基本妥当性をチェック
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB から稼働率、注文成功率、レイテンシ等を集計し PASS/FAIL 判定
- AI モジュール
  - news_nlp: raw_news を集約して OpenAI でセンチメントを算出し ai_scores に保存
  - regime_detector: ETF MA とマクロ NLP を合成して market_regime を判定・保存
- ポートフォリオ
  - 銘柄候補選定、等重/スコア加重、セクターキャップ、ポジションサイジング等の純粋関数群
- ユーティリティ
  - logging_setup: 統一的なログ設定（コンソール＋日次ローテーションファイル）
  - process_priority: Windows / POSIX を吸収したプロセス優先度・CPU affinity 設定
- 監視 DB（monitoring_db）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルの初期化・永続化 API

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（代表例）
   - pip install duckdb psutil openai
   - YAML 検証を行う場合: pip install PyYAML
   注: requirements.txt は同梱されていません。実行環境に応じて依存を追加してください。

3. 初期設定（.env の作成）
   - python -m kabusys.config_setup
     対話式に .env を生成します。生成後は .env を Git に入れないでください。

   重要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須) — kabuステーション API 用
   - KABUSYS_ENV (default: development) — development | paper_trading | live
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
   - OPENAI_API_KEY — news_nlp / regime_detector が必要な場合
   - LOG_LEVEL (default: INFO)
   - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（整数）

4. 設定を検証
   - python -m kabusys.validate_config
   - 本番前に --strict を付けると警告もエラー扱いになります:
     python -m kabusys.validate_config --strict

5. ディレクトリ（data/logs）作成
   - 多くのコードは data/ や logs/ にファイルを書きます。実行前に作成しておくか、適切な権限で実行してください。
   - ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます。

使い方（よく使うコマンド）
- 実行エンジン（ExecutionEngine）を起動
  - KABUSYS_ENV=paper_trading を使うとモックブローカー、PAPER_TRADING_SQLITE_PATH に記録される
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成するとエンジンは終了します
  - 実行時に data/execution.pid が作成されます

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番向けの sqlite_path（Settings.sqlite_path）を参照します（環境に依存せず）

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（デフォルトは環境変数または data/paper_trading.db）

- AI 関連の関数を直接呼び出す（サンプル）
  - Python REPL / スクリプトから:
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, datetime.date(2026, 4, 11), api_key='YOUR_OPENAI_KEY')

停止・Kill Switch
- run_execution / run_monitoring の両方はプロジェクトルートの data/stop_requested.flag を検知して安全に終了します。
  - 停止させたい場合は空ファイルを作成するだけで良い（例: touch data/stop_requested.flag）。
- KillSwitch（監視側）は条件を満たした場合に data/kill.flag を書き込みます。
  - ExecutionEngine は起動時に kill.flag を検出すると起動しません（本番安全機構）。
  - Kill flag を手動でクリアするにはファイルを削除してください（.env の KILL_FLAG_CLEAR_ON_START 設定で自動クリア挙動を制御）。

ログ／DB の場所（デフォルト）
- logs/: ログファイル（例: logs/execution.log, logs/monitoring.log）
- data/kabusys.duckdb: DuckDB（分析・price 等）
- data/monitoring.db: 監視用 SQLite（system_status, trade_logs, positions, risk_logs, dashboard）
- data/paper_trading.db: paper_trading 用 SQLite（KABUSYS_ENV=paper_trading 時に使用）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前チェック CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングスクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度設定
  - monitoring/
    - monitoring_db.py        — SQLite 永続化レイヤ
    - system_monitor.py       — システム・データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション制限監視
    - trade_monitor.py        — （trade 監視ロジック）
    - monitoring_engine.py    — 各 Monitor を束ねる
    - kill_switch.py          — kill.flag 書込みロジック
    - alert_manager.py        — アラート送信（LINE 等）※実装参照
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py       — ブローカクライアント生成（Mock / Live 切替）
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py      — レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py
  - data/                    —  実行時に使用する（DB, flags, pid 等） ※リポジトリ外に置くこと推奨

注意点 / 運用上のヒント
- 本番（KABUSYS_ENV=live）では .env の取り扱いに注意し、JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の秘匿情報を安全に保管してください。
- validate_config を本番導入前に必ず実行し、--strict モードで警告も解消しておくことを推奨します。
- OpenAI を利用する機能（news_nlp, regime_detector）は API コスト・レイテンシを考慮して運用してください。API キーが未設定のときは明示的に例外やフォールバックが発生するので確認してください。
- DuckDB / SQLite ファイルのバックアップや権限管理を検討してください。
- ログディレクトリ作成に失敗した場合はコンソールのみのログ出力になります（setup_logging の挙動参照）。

サンプル .env（示例）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=your_openai_api_key
KILL_FLAG_CLEAR_ON_START=0

最後に
- この README はコードベースの主要な使用方法と構成をまとめたものです。詳細な設計仕様（PortfolioConstruction.md、StrategyModel.md 等）は別ドキュメントを参照してください（実装コメントに言及あり）。
- 質問や追加で載せてほしい箇所（例:具体的な設定例、docker 化、systemd ユニット例など）があれば教えてください。必要に応じて追記します。