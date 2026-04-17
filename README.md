# KabuSys — README

概要
- KabuSys は日本株の自動売買・調査・監視を行うための軽量なフレームワークです。
- コア機能は注文実行（ExecutionEngine）、監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）、ポートフォリオ構築、リサーチ（ファクター計算・特徴量解析）、およびニュース NLP を用いた AI スコアリングを含みます。
- ローカル SQLite / DuckDB を用いたデータ永続化を前提としており、Paper Trading（検証用）と Live（本番）を切り替えて動作できます。

主な機能
- Execution
  - 実際のブローカー API と接続して注文を送信（設定によって MockBroker を利用可）
  - OrderManager / OrderRepository / Reconciler による堅牢な注文管理と再起動時のリコンシリエーション
  - RiskManager による発注制限（最大ポジション比率、利用率、サーキットブレーカー等）
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス稼働・データ鮮度監視
  - TradeMonitor：滞留注文や約定異常価格の検出
  - RiskMonitor：ドローダウン／ポジション上限監視とリスクログ保存
  - KillSwitch：条件に応じた停止フラグ書き込み（data/kill.flag）で ExecutionEngine を安全に停止
  - AlertManager：LINE Push を使った通知（クールダウン機能付き）
  - Streamlit ダッシュボードで監視情報を可視化
- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value 等）と将来リターン計算、IC 計算、統計サマリー
  - 候補選定、重み付け、ポジションサイズ決定、セクターキャップ、レジーム乗数などの純粋関数群
- AI（ニュース）
  - raw_news を OpenAI に問い合わせて銘柄別センチメントを ai_scores テーブルへ書込
  - 市場レジーム判定（ETF ma200 とマクロニュースセンチメントの合成）

セットアップ手順（開発マシン）
1. リポジトリをクローンし、プロジェクトルートに移動
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （将来的に requirements.txt を用意する場合はそれを利用）
4. 環境変数設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は上書き読み込み）。
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要な環境変数（例）：
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須: J-Quants API 用トークン）
     - KABU_API_PASSWORD: （必須: kabuステーション API パスワード）
     - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector 用）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE通知用（任意）
     - PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH / LOG_LEVEL 等（Settings 参照）

使い方（主要スクリプト）
- 監視ループを起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔秒を上書き可能（デフォルト 60 秒）。
  - 実行:
    - python -m kabusys.run_monitoring
  - 仕様:
    - 起動時にプロセス優先度を "high" に設定し、Monitoring の DB は常に本番 sqlite_path を使用（KABUSYS_ENV に依らず）。
    - 停止: プロジェクトの data/stop_requested.flag ファイルを作成するとループが終了します。

- 実行エンジンを起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
  - 実行:
    - python -m kabusys.run_execution
  - 仕様:
    - 起動時にプロセス優先度を "high" に設定
    - 起動前に data/stop_requested.flag が存在する場合は起動せず終了
    - 実行中に data/stop_requested.flag を作成するとエンジンを安全に停止

- Streamlit ダッシュボード
  - data/monitoring.db を read-only で開いて監視画面を表示します。
  - 実行例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成ツール
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで DB パスを指定可能（デフォルト: data/paper_trading.db）。

- AI ニューススコアリング / レジーム判定（ライブラリAPI）
  - Python から直接呼び出せます（DuckDB 接続を引数に渡す）。
  - 例（概念）:
    - from kabusys.ai import score_news
    - written = score_news(duckdb_conn, date(2026,4,1), api_key="...")

運用上のポイント
- DB パス（デフォルト）
  - DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
- フラグ / PID ファイル
  - 停止フラグ（run_monitoring/run_execution 共通）: data/stop_requested.flag
  - Execution PID: data/execution.pid（ExecutionEngine が作成）
  - Kill Switch が書くフラグ（Execution 停止トリガ）: data/kill.flag（KillSwitch）
- .env の取り扱い
  - プロジェクトルートに .env / .env.local を置くと自動ロードされます。
  - OS 環境変数は優先され、.env.local は上書き可能です。
- Paper Trading と本番 DB は完全分離される設計（KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用）。
- process priority / cpu affinity: run スクリプトは起動時に set_process_priority("high") を呼び出します。psutil により権限不足で失敗した場合は警告ログのみ出ます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py              — 環境変数/設定管理（.env 自動ロード、Settings クラス）
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py     — SQLite スキーマ・永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: order_repository, order_record, execution_engine 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/                  — 実行時に使用する DB / flag / pid を置く（デフォルトパス）

補足・開発者向けメモ
- DuckDB 接続を受け取る関数群は外部 API 呼び出しを行わず、prices_daily / raw_financials 等のテーブルのみ参照する方針です（リサーチ機能）。
- AI（OpenAI） 呼び出しはレート制限・一時エラーを考慮してエクスポネンシャルバックオフでリトライし、失敗時は安全にフォールバックする設計です。
- monitoring_db.init_monitoring_db() は冪等的にスキーマ作成 / マイグレーションを行います（起動時に必ず呼ぶことを推奨）。
- logging レベルは Settings.log_level で制御可能（環境変数 LOG_LEVEL）。

よく使うコマンドまとめ
- 依存インストール:
  - pip install duckdb psutil requests openai streamlit
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

ライセンス / 貢献
- 本ドキュメントにはライセンス情報を含めていません。プロジェクトルートの LICENSE を参照してください。
- バグ報告や機能提案は Issue を通じてお願いします。

以上。README に載せるべき追加情報（例: requirements.txt、起動用 systemd ユニット例、より詳細な環境変数一覧など）があれば教えてください。必要に応じて追記します。