KabuSys — 日本株自動売買システム (簡易 README)
======================================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
主な責務は以下の通りです。

- 注文作成・管理・実行（ExecutionEngine / OrderManager / Broker 抽象）
- 監視（System / Trade / Risk）とアラート（LINE Push）
- ポートフォリオ構築・配分・ポジションサイズ計算（Portfolio モジュール）
- 研究用途のファクター計算・特徴量探索（Research）
- ニュースの NLP によるセンチメント評価・レジーム判定（AI モジュール）
- Paper Trading 用の分離された DB / Mock ブローカー、検証レポート作成ツール
- Streamlit による監視ダッシュボード

重要な設計上のポイント
- 環境変数 / .env ファイルで設定を管理（kabusys.config.Settings）
- Paper Trading は本番 DB と完全に分離（PAPER_TRADING_SQLITE_PATH）
- 監視（monitoring）は常に本番の sqlite_path を使う（環境に依存しない）
- OpenAI を使った処理は APIキー（OPENAI_API_KEY）または引数で渡す

主な機能一覧
--------------
- Execution
  - 注文作成、注文状態同期、リコンシリエーション（Reconciler）
  - RiskManager、OrderManager、ExecutionEngine の連携
  - Paper Trading モード（MockBrokerClient、別 DB）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / PID 管理
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringEngine: それらを束ねてポーリング、KillSwitch / AlertManager 連携
  - streamlit_dashboard: 監視 DB を可視化するダッシュボード
- Portfolio
  - 候補選定、等金額・スコア加重配分、セクター制限、ポジションサイズ決定
- Research
  - ファクター計算（Momentum / Volatility / Value）、将来リターン、IC 計算、統計サマリー
- AI
  - news_nlp.score_news: ニュースを OpenAI に投げて銘柄ごとのスコアを ai_scores に書込
  - regime_detector.score_regime: ETF MA とマクロニュースで市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB から検証レポートを生成

前提・必須ソフトウェア
-----------------------
- Python 3.9+（型ヒント等を多数使用）
- 必須パッケージ（主に imports から推定）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- SQLite（Python 標準の sqlite3 を使用）
- ネットワークアクセス（LINE Push / OpenAI を使う場合）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... （配布方法に応じて）

2. 仮想環境作成と依存インストール（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install --upgrade pip
   - pip install duckdb psutil openai requests streamlit

   ※ requirements.txt があれば pip install -r requirements.txt を推奨します。

3. データディレクトリの作成
   - mkdir -p data

4. 環境変数 / .env の準備
   - プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます（kabusys.config が自動で読み込み）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要な環境変数（代表）
- KABUSYS_ENV: 起動環境（development | paper_trading | live）デフォルト: development
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- OPENAI_API_KEY: AI モジュール（news_nlp, regime_detector）で使用
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE Push）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の fill モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視関連設定

DB の初期化
-------------
- 監視 DB（monitoring）は init_monitoring_db() を通じてテーブルを作成します。run_monitoring.py や run_execution.py が自動で呼び出します。
- Paper Trading 用 DB も Execution 起動時に init_monitoring_db() を呼びます（冪等）。

使い方（実行例）
----------------

1) 監視ループを起動
- 簡単に実行:
  - python -m kabusys.run_monitoring
- 環境変数で間隔を変更:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 動作:
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行して monitoring DB にログ化。
  - 停止は data/stop_requested.flag を作成することで検知して終了します。

2) 実行エンジン（ExecutionEngine）を起動
- python -m kabusys.run_execution
- KABUSYS_ENV=paper_trading を指定すると MockBroker を使い、Paper Trading DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
- 停止: data/stop_requested.flag を作成するとエンジンが停止処理します。

3) Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 監視 DB を読み取り専用で開いて、Overview / Positions / Orders / System タブを表示します。

4) Paper Trading 検証レポート
- コマンド:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）などのサマリと PASS/FAIL 判定。

5) AI モジュール（ニュース / レジーム判定）
- 呼び出し例（コード内から直接利用する想定）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="sk-...")
- OPENAI_API_KEY を環境変数に設定していれば api_key は省略可能。

停止・Kill フラグの仕組み
--------------------------
- data/stop_requested.flag: run_monitoring / run_execution がポーリング中に検知して安全に終了するためのフラグ。
- KillSwitch: RiskMonitor がトリガーした場合に data/kill.flag を書き、ExecutionEngine 側で停止させる運用を想定。
- PID ファイル: ExecutionEngine は data/execution.pid を書き、SystemMonitor はこの PID をみてプロセス生存を確認します。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                        — 環境変数と .env 読み込みロジック
- run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                 — ExecutionEngine 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py    — Paper Trading 検証レポートツール
- monitoring/
  - __init__.py
  - monitoring_db.py                — SQLite 永続化層（system_status/trade_logs/...）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_repository.py
  - order_manager.py
  - reconciler.py
  - execution_engine.py
  - broker_factory.py
  - ... (ブローカー API 抽象など)
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
- data/ (実行時に生成されることを想定)
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - stop_requested.flag
  - kill.flag
  - execution.pid

開発時の注意
-------------
- .env の自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）に依存します。配布後やパッケージ化後に動作させる場合は環境変数で明示的に設定することを推奨します。
- AI 関連処理は外部 API（OpenAI）に依存するため、API キー・レート制限・コストに注意してください。失敗時はフェイルセーフ（スコア=0、処理スキップ）する実装になっています。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値を検出してデフォルトにフォールバックします。
- Paper Trading と本番 DB は分離されますが、Monitoring は常に sqlite_path（本番）を参照する設計です。テスト環境では適切にパスを設定してください。

サポート・拡張案（短く）
-----------------------
- 銘柄別の lot_size をマスターから読み込む拡張（position_sizing の TODO）
- 更に詳細なメトリクス（注文履歴、イクイティライン）をダッシュボードに追加
- AI モジュールのレスポンス検証・テスト強化（モックの提供）

お問い合わせ・貢献
------------------
本 README はコードベースのコメントと実装をもとに作成しています。実プロジェクトに組み込む際は依存関係（requirements.txt）やセットアップ手順をプロジェクト標準に合わせて整備してください。必要であればサンプル .env.example の作成や起動スクリプトの systemd ユニット例なども追記できます。必要な追加情報を教えてください。