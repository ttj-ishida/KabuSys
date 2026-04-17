# KabuSys — README (日本語)

概要
- KabuSys は日本株向けの自動売買システムのコードベースです。
- 主要機能は「発注実行（Execution）」「監視（Monitoring）」「ポートフォリオ構築」「ファクター研究」「AI を用いたニュースセンチメント・レジーム判定」などを含みます。
- SQLite / DuckDB をローカル DB として利用し、OpenAI（gpt-4o-mini）をニュース解析やレジーム判定に用いる設計です。
- 環境変数と .env ファイルから設定を読み込み、環境（development / paper_trading / live）に応じた挙動をサポートします。

主な機能一覧
- Execution
  - Broker クライアント生成（本番 API / モックによる paper_trading 切替）
  - OrderManager / Reconciler による注文管理・再同期
  - RiskManager によるリスク制御（利用率・最大ポジション比率・ドローダウンなど）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス存在監視
  - TradeMonitor: 滞留注文・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクログ記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、Engine 停止シグナルを発行
  - AlertManager: LINE へ通知（オプション）
  - Streamlit ダッシュボード（監視データ表示）
- Portfolio（純粋関数モジュール）
  - 候補選定、等金額・スコア加重配分、単元丸め、リスク調整（セクターキャップ、レジーム乗数）
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（情報係数）やファクター統計
- AI
  - news_nlp: raw_news を OpenAI でセンチメント評価し ai_scores に格納
  - regime_detector: 指標＋マクロニュースで market_regime を判定

セットアップ手順（ローカル開発用）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 必要な主要依存（例）
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例: pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があればそれを使用）
4. .env の作成（プロジェクトルート）
   - .env.example を参照し、必須値を設定してください。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
5. データディレクトリを準備
   - data ディレクトリを作成: mkdir -p data
   - 実行で自動的に DB ファイル等が作成されます

主要環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合は必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG | INFO | ...)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト data/monitoring.db) — Monitoring は常に本番 sqlite_path を使用
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定モード
- PID_FILE_PATH (デフォルト data/execution.pid)
- KILL_FLAG_PATH (デフォルト data/kill.flag)
- MONITOR_POLL_INTERVAL (監視ループの秒数、デフォルト 60)
- MONITOR などの閾値: CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT など

簡易 .env 例
- .env:
  - JQUANTS_REFRESH_TOKEN=your_jquants_token
  - KABU_API_PASSWORD=your_kabu_password
  - OPENAI_API_KEY=sk-...
  - KABUSYS_ENV=development
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

使い方（実行方法）
- 監視ループ起動（SystemMonitor 単体起動）
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
    - 監視は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番パス）を使って接続します
    - 停止: プロセスに Ctrl+C、またはプロジェクトルート/data/stop_requested.flag を作成するとループが終了します
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動しません
    - 停止は data/stop_requested.flag の作成で実行中エンジンへ通知され停止処理を呼びます
- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 表示可能: Overview / Positions / Orders / System / Recent Risk Events
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（デフォルト data/paper_trading.db）
- AI 機能（ニュース NLP / レジーム判定）
  - kabusys.ai.score_news（internal API）: DuckDB 接続と target_date を与えて実行
  - kabusys.ai.regime_detector.score_regime: DuckDB 接続と target_date を与えて実行
  - 実行には OPENAI_API_KEY が必要（引数でキーを渡すことも可能）

停止フローとフラグファイル
- stop_requested.flag (data/stop_requested.flag)
  - run_monitoring / run_execution はこのフラグファイルを監視し、存在で安全にシャットダウンします
- kill.flag (Settings.kill_flag_path, デフォルト data/kill.flag)
  - KillSwitch により書き込まれ、ExecutionEngine に停止を促すシグナルとして利用されます
- PID ファイル (data/execution.pid)
  - ExecutionEngine の PID を格納するファイル。SystemMonitor はこのファイルの stale チェックを行います

監視 DB（Monitoring DB）とマイグレーション
- monitoring_db.init_monitoring_db(conn) は必要なテーブルとインデックスを冪等に作成します
- 古い DB に対しては簡単なマイグレーション（dashboard.peak_value / trade_logs.latency_ms の追加）が組み込まれています

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/.env ロードと Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py  — ExecutionEngine 起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py       — raw_news を LLM でスコアリングし ai_scores に書き込み
    - regime_detector.py — レジーム判定（ma200 + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py  — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py  — 注文滞留・約定異常検出
    - risk_monitor.py   — ドローダウン・ポジション上限監視
    - kill_switch.py    — kill.flag 制御
    - alert_manager.py  — LINE push 通知
    - monitoring_engine.py — 各 monitor を束ねる
    - streamlit_dashboard.py — 監視ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (DB 層)
    - execution_engine.py
    - broker_factory.py
    - など（発注・ブローカー関連）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - data/ (ランタイムで生成される想定)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (paper_trading 用 DB)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - execution.pid, stop_requested.flag, kill.flag

注意事項 / 実運用メモ
- Monitoring は常に Settings.sqlite_path（監視 DB）を使用します。KABUSYS_ENV に依存せず監視データは本番向けパスに保管されます（意図的な設計）。
- Execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使い、本番 DB と分離されます。
- process priority / CPU affinity の設定は psutil を使いますが、権限不足や未対応 OS の場合は警告を出してスキップします。
- OpenAI API 呼び出しはリトライ実装（指数バックオフ）を含み、API キー未設定時は明示的なエラーまたはフェイルセーフフォールバック（モジュールにより異なる）があります。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）から行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- セキュリティ: .env にシークレット（API キー等）を保存する場合は取り扱いに注意してください。リポジトリにコミットしないでください。

トラブルシューティング（よくある箇所）
- DB ファイルが見つからない / 読み取り専用
  - Streamlit ダッシュボードは読み取り専用 URI で接続します。MonitoringEngine が DB を作成していないとエラーになります。
- OpenAI 呼び出し失敗
  - OPENAI_API_KEY の設定、ネットワーク、レート制限を確認。ログにリトライ情報が出力されます。
- PID / スタレ PID 検出
  - 実行中の PID が存在しない場合は stale PID として検出され、PID ファイルは削除されます（SystemMonitor がログに残します）。

補足
- 各モジュールの詳細な仕様（PortfolioConstruction.md / StrategyModel.md 等）はコード内の docstring とコメントに沿っています。
- 開発・テスト用途では paper_trading モードを活用して本番口座との完全分離を保ってください。

以上。必要であれば、README に含めるサンプル .env.example や起動スクリプトの systemd ユニット例、より詳細な設計ドキュメントや API 使用例を追加します。どの情報を優先して追記しますか？