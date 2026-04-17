KabuSys — 日本株自動売買システム（README）
概要
本リポジトリは日本株向けの自動売買フレームワーク「KabuSys」の主要コンポーネント群を含みます。  
主に以下を提供します：
- 注文発行 / 発注管理（ExecutionEngine 周り）
- 監視（System / Trade / Risk Monitor）とアラート（LINE）
- ポートフォリオ構築・ポジションサイジングの純関数群
- リサーチ（ファクター計算・特徴量解析）
- AI を使ったニュースセンチメント評価・市場レジーム判定（OpenAI）
- Paper Trading 用検証・レポート出力、Streamlit ダッシュボード

主な機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - Broker クライアント抽象化（本番 / モックによる paper_trading 切替）
  - リコンシリエーション（起動時の注文・ポジション同期）
  - OrderManager / OrderRepository による状態管理
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor（DB へ永続化）
  - KillSwitch（条件に基づき data/kill.flag を書き込んで Engine を停止）
  - AlertManager（LINE push による通知、クールダウン管理）
  - streamlit ベースの監視ダッシュボード（read-only）
- Portfolio
  - 候補選定、等額/スコア配分、リスク調整（セクター上限）、株数決定（lot 丸め）
- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- AI
  - ニュース NLP（OpenAI）による銘柄ごとのセンチメントスコア生成
  - レジーム判定（ETF の MA とマクロニュースの LLM 評価を合成）
- ツール
  - paper_trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
  - 各種ユーティリティ（process priority 等）

前提 / 必要環境
- Python 3.10+（型ヒントで | を使用しているため）
- SQLite（組み込み）
- 外部パッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit（ダッシュボード起動時）
これらは requirements.txt を用意している場合はそれに従ってください（本リポジトリに明示的な requirements ファイルは含まれていません）。

セットアップ手順（ローカル）
1. リポジトリをクローンし、virtualenv を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

3. データディレクトリの作成
   - mkdir -p data

4. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（省略可はデフォルトを併記）：
     - KABUSYS_ENV: environment（development | paper_trading | live）。デフォルト: development
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用（未設定なら通知は送られません）
     - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant | partial | never | reject。デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
     - SQLITE_PATH: data/monitoring.db（監視用 DB、デフォルト）
     - DUCKDB_PATH: data/kabusys.duckdb（DuckDB メタ・履歴データ）
     - PID_FILE_PATH / KILL_FLAG_PATH: デフォルト data/execution.pid / data/kill.flag
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
     - LOG_LEVEL: (DEBUG/INFO/...) デフォルト INFO
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=paper_trading

起動・使い方
- ExecutionEngine の起動
  - 本番または開発環境:
    python -m kabusys.run_execution
  - Paper Trading（環境変数で切替）
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper Trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使い、本番 DB と完全分離されます。
  - 実行中は data/execution.pid に PID が書き込まれ、停止指示は data/stop_requested.flag（run_execution では同名）や data/kill.flag で制御されます。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でループ間隔を秒単位で上書き（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は settings.sqlite_path（デフォルト data/monitoring.db）へログを記録します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（設計上の意図）。

- Streamlit ダッシュボード（読み取り専用）
  - 起動例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB を読み取り専用 URI で開きます。MonitoringEngine を先に起動してデータを作成してください。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
  - レポートは稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを出力します。

- AI 機能（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores を扱い、OpenAI を呼び出して ai_scores に書き込みます。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF（1321）の MA200 乖離とマクロニュースの LLM 評価を合成して market_regime に保存します。
  - OpenAI の呼び出しは API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）。

停止・Kill
- ExecutionEngine 停止方法:
  - data/stop_requested.flag を作成すると安全にエンジンが停止します（run_execution / run_monitoring で確認）。
  - KillSwitch はリスク基準に達した場合に data/kill.flag を書き込み、実行中の Engine に停止を促します（冪等性を担保）。
- run_monitoring/run_execution は KeyboardInterrupt (Ctrl+C) により停止できます。

設定の自動読み込み
- src/kabusys/config.py はプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を自動で読み込みます（OS 環境変数を保護）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py (バージョン情報)
  - config.py (環境変数 / Settings)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - tools/
    - paper_verification_report.py (paper trading レポート)
  - execution/
    - execution_engine.py (Engine 本体) — （ソース全体は省略）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - broker_api.py
    - order_record.py
  - monitoring/
    - monitoring_db.py (SQLite 永続化)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/  (実行時に作成されることを想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (DuckDB)
    - execution.pid, kill.flag, stop_requested.flag

開発ノート / 注意点
- モジュールは意図的に副作用を避ける設計（例: AI モジュールは datetime.today() を参照しない等）で、ルックアヘッドバイアスを防止しています。
- Monitoring の init_monitoring_db() は冪等でマイグレーション的処理（カラム追加）を行います。
- process priority / CPU affinity は psutil を用いて OS 横断で設定を試みますが、権限不足時は警告ログでスキップします。
- DuckDB への書き込みは executemany に空リストを与えないよう実装上の配慮があります（互換性問題回避）。
- OpenAI API 呼び出しはリトライ・バックオフ・レスポンス検証を行い、失敗時は安全にフォールバックします（スコア 0 固定や部分書き込み保護など）。

バージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0"

ライセンス
- 本 README にはライセンス情報が含まれていません。配布時に適切な LICENSE ファイルを追加してください。

問い合わせ・貢献
- バグ報告・改善提案は Issue を通じて行ってください。プルリク歓迎です。

以上。必要であれば README に含める具体的な .env.example や簡易 docker-compose / systemd ユニットの例も作成できます。どの形式が欲しいか教えてください。