# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買システム（KabuSys）の一部実装です。本ドキュメントはコードベースに含まれる主要スクリプト・モジュールの概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめた README です。

注意: 本 README は src/ 以下の実装に基づいて作成しています。実行には環境変数や外部 API キー（例: OpenAI、kabu API、J-Quants）などが必要になる箇所があります。API キーの取り扱いは十分に注意してください（課金・レート制限等）。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提（Python バージョン / 依存）
- セットアップ手順
- 環境変数（主なもの）
- 使い方（起動コマンド例）
- 主要 API / 公開関数
- ディレクトリ構成（主なファイル説明）
- 運用上の注意点

---

プロジェクト概要
- KabuSys は日本株自動売買のためのモジュール群です。本コードベースには以下の責務を持つモジュールが実装されています:
  - 注文実行エンジン（ExecutionEngine） / Order 管理（OrderManager, Reconciler）
  - 取引監視・リスク監視（MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor）
  - ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
  - 研究用ファクター計算（momentum / volatility / value）
  - AI を使ったニュース NLP（OpenAI を利用したセンチメント評価）
  - SQLite / DuckDB を使った永続化と集計
- design notes（コード内コメント）に基づき、ルックアヘッドバイアス防止やクラッシュ耐性（2 相永続化など）を考慮した設計になっています。

主な機能一覧
- Execution:
  - Signal を読み取り発注（Gate チェック、Rate limit / Circuit breaker、再送・保留処理）
  - Reconciliation（再起動時の Order 同期、ポジション差分検出）
  - RiskManager による発注判定（Gate1/2/3）
- Monitoring:
  - システムリソース（CPU/Mem/Disk）と Execution プロセス監視
  - 注文滞留（stale orders）・約定異常（price anomaly）検出
  - ドローダウン／ポジション上限監視および kill.flag による停止シグナル
  - LINE へのアラート通知（AlertManager）
  - Streamlit ダッシュボードによるモニタリング可視化
- Portfolio:
  - シグナル候補選定（スコア降順）
  - 等金額・スコア加重の重み算出
  - セクター集中制限・レジーム乗数
  - ポジションサイズ計算（単元丸め、aggregate cap 処理）
- Research:
  - Momentum / Volatility / Value 等ファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Spearman）や統計サマリ
- AI:
  - ニュース記事を OpenAI でセンチメント付与（ai_scores テーブルへ書き込み）
  - マクロニュース + ETF MA200 乖離を組み合わせた市場レジーム判定

前提（Python / 依存）
- Python 3.10+（型記法 X | Y を使用しているため 3.10 以上を推奨）
- 主な Python パッケージ（例、requirements を用意する場合）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを利用する場合)
- 標準ライブラリ: sqlite3, logging, datetime 等

セットアップ手順（開発環境）
1. リポジトリをクローン
2. 仮想環境を作成・有効化（例: python -m venv .venv）
3. 依存インストール
   - 例:
     - pip install -U pip
     - pip install duckdb psutil requests openai streamlit
   - 開発用途なら: pip install -e . （setup.py/pyproject.toml があれば）
4. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須値や推奨値は次節「環境変数」を参照してください。
5. data ディレクトリを作成（必要に応じて）
   - デフォルト DB パスは data/monitoring.db（本番） / data/paper_trading.db（paper_trading）
   - PID / kill flag 用ディレクトリも自動作成されますが、必要に応じて権限確認してください。

環境変数（主なもの）
- KABUSYS_ENV: 起動環境。development / paper_trading / live のいずれか。デフォルト: development
  - paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録して本番 DB と分離します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- SQLITE_PATH: monitoring DB のパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB のパス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト 60 秒。無効値（<=0）は無視してデフォルトを使用。
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant / partial / never / reject）
- LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT 等（細かい挙動を制御）

使い方（起動コマンド例）
- Python パス設定例（開発版を直接実行する場合）
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - PYTHONPATH=src python -m kabusys.run_execution
  - 直接ファイルを実行する場合:
    - python src/kabusys/run_monitoring.py
    - python src/kabusys/run_execution.py
- 監視ループを起動（monitoring）
  - MONITOR_POLL_INTERVAL=120 PYTHONPATH=src python -m kabusys.run_monitoring
  - 動作: SQLite（settings.sqlite_path）へ接続し SystemMonitor をポーリング。MONITOR_POLL_INTERVAL で間隔上書き可能。
- 実行エンジン起動（execution）
  - KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
  - 通常: 実ブローカークライアントを使用（設定に応じて BrokerClientFactory が切り替える）。
  - paper_trading: MockBrokerClient を使用し paper_trading 用 DB に記録（本番 DB と分離）。
- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既存の監視 DB を read-only で開く（存在しない場合はエラーを表示）。
- AI 機能（プログラムから呼び出す）
  - ニュースセンチメント付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # target_date は datetime.date
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

主要 API / 公開関数（抜粋）
- kabusys.config.Settings
  - 設定値の集中管理（.env 自動読み込み）。settings = Settings() / settings.jquants_refresh_token 等。
- kabusys.monitoring
  - MonitoringDB, SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, AlertManager, KillSwitch
- kabusys.execution
  - ExecutionEngine, OrderManager, Reconciler, RiskManager（設定含む）
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.ai
  - score_news (news_nlp), score_regime (regime_detector)

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義 / バージョン
  - config.py — 環境変数 / .env 読み込み・Settings 定義
  - run_monitoring.py — SystemMonitor のポーリングループを起動するスクリプト
  - run_execution.py — ExecutionEngine（注文実行）の起動スクリプト
  - ai/
    - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores に書き込む処理
    - regime_detector.py — マクロニュース + ETF MA200 乖離を使った市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化・CRUD ラッパー（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み / 管理
    - alert_manager.py — LINE API への通知
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - execution_engine.py — Signal Queue Pull 型発注エンジン
    - order_manager.py — Order State Machine 外向き API
    - reconciler.py — 起動時自動復旧・リコンシリエーション
    - order_repository.py, order_record.py, broker_api.py, broker_factory.py 等（本リストの一部は省略）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数・丸め・aggregate cap
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意点
- .env の取り扱い:
  - .env/.env.local を用いて環境変数を設定できます。プロジェクトルートは config._find_project_root() により自動検出（.git または pyproject.toml を上位に探索）。
  - OS 環境変数は上書きされないよう保護されます。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能です。
- OpenAI API:
  - news_nlp / regime_detector は OpenAI API（gpt-4o-mini 等）を呼び出します。API キーの設定・利用にはコストやレート制限・利用規約に注意してください。
  - レスポンスのバリデーションやリトライ戦略が組まれていますが、外部 API の障害時はフェイルセーフ（スコア 0.0 を採用等）になるよう実装されています。
- DB の切り分け:
  - paper_trading モードでは paper_trading 用 SQLite を使用して本番 DB と明確に分離します。設定は Settings によって切り替わります。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。psutil による優先度設定が失敗する場合は警告でスキップされます（権限依存）。
- kill.flag:
  - KillSwitch により重大なリスク（例: ドローダウン閾値超過）で data/kill.flag に理由を書き込み、ExecutionEngine 側が検出して安全停止します。必要に応じて起動時に kill.flag をクリアする設定があります。

最後に
- 本 README はコード内のコメント・docstring をもとに作成しています。実際に稼働させる前に .env (または環境変数) の内容、API キー周り、データベースのバックアップ・権限などを十分に確認してください。
- 追加ドキュメント（例: PortfolioConstruction.md, StrategyModel.md 等）は参照先があれば合わせて読むことを推奨します（コードにドキュメント参照が多く含まれています）。

必要であれば、README に含めるサンプル .env.template、具体的な起動スクリプト（systemd ユニット例）、もしくは requirements.txt 生成例なども作成します。どれが欲しいか教えてください。