KabuSys — 日本株自動売買システム（README）
概要
本リポジトリは日本株向け自動売買システム KabuSys の主要モジュール群を含みます。
主な用途は戦略のリサーチ／ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、およびシステム監視／アラート・ダッシュボードです。  
実行時の環境（開発 / ペーパー取引 / 本番）は KABUSYS_ENV により切り替えられます。

主な特徴（機能一覧）
- 環境設定管理
  - .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - Settings クラスで一元的に環境変数を取得・検証
- Execution（発注）関連
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading 時は MockBroker を使用）
  - OrderManager、OrderRepository、Reconciler による発注管理・再同期処理
  - リスクマネジメント（Rate limit、最大ポジション比等）
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（ポーリング監視）
  - 監視データ永続化（SQLite、monitoring_db）
  - LINE によるアラート送信（AlertManager）
  - KillSwitch によるフラグファイル停止（data/kill.flag）
  - Streamlit ダッシュボードで監視データを可視化
- Portfolio（銘柄選定・配分・株数決定）
  - 候補選定・スコア重みや等分配、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（risk_based, equal, score）
- Research（研究／特徴量）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースセンチメント評価（ai.news_nlp.score_news）
  - マクロニュース＋ETF MA200 を合成した市場レジーム判定（ai.regime_detector.score_regime）
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ（psutil ベース）
  - 各種ツールスクリプト（paper_verification_report など）

セットアップ手順
前提
- Python 3.10 以上（| 型注釈などで 3.10+ を想定）
- SQLite は標準ライブラリで利用可
推奨手順（UNIX 系）
1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate
2. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit
   （プロジェクトで requirements.txt を用意している場合は pip install -r requirements.txt を使用）
3. データディレクトリ作成（必要に応じて）
   - mkdir -p data
4. 環境変数設定
   - ルートに .env を作成するか OS 環境変数で設定します。
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development  # development | paper_trading | live
     - PAPER_FILL_MODE=instant  # instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LOG_LEVEL=INFO
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - MONITOR_POLL_INTERVAL=60  # 監視ポーリング間隔（秒）
   - .env.example を作ると初期化が簡単になります（本リポジトリに同梱されていれば参照）。
5. DB 初期化
   - 監視用 DB は起動時に自動でテーブル作成（init_monitoring_db）します。
   - DuckDB（prices_daily 等）は必要に応じて別途データ投入してください。

使い方（主要コマンド）
- ExecutionEngine（発注エンジン）起動
  - 通常:
    - python -m kabusys.run_execution
    - または python src/kabusys/run_execution.py
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBroker が使われ、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます（本番 DB と分離）。
    - 停止指示は data/stop_requested.flag または KillSwitch により行います。
    - 実行時に data/execution.pid が作成されます。
- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path（monitoring.db）へ書き込みます（環境に依らず本番 sqlite_path を使用）。
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only モードで開きダッシュボードを表示します。
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定できます（デフォルト: data/paper_trading.db）。
- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要。API 呼び出しはコストが発生するため注意。
- 開発 / テスト用
  - 個々の純粋関数（portfolio.*, research.*）は外部副作用が少なくユニットテストしやすい設計です。

重要な挙動・運用メモ
- KABUSYS_ENV の有効値: development, paper_trading, live
  - paper_trading は発注処理を完全に本番 DB から分離（paper_sqlite_path を使用）
- PID / フラグファイル
  - data/execution.pid: 実行エンジンの PID を保持
  - data/stop_requested.flag: run_monitoring / run_execution が検知して停止するフラグ
  - data/kill.flag: KillSwitch が作成する停止理由フラグ（ExecutionEngine 停止トリガー）
- プロセス優先度設定
  - 起動スクリプトは psutil を使って process priority を "high" に設定しようとします。権限により失敗する場合はログに WARN を出してスキップします。
- DB マイグレーション（簡易）
  - init_monitoring_db は既存 DB に対して安全に列追加（例: latency_ms, peak_value）を試みます。
- OpenAI 呼び出しはリトライ・バリデーション・クリップ等の保護ロジックを備えていますが、API レートやコストに注意してください。
- データ鮮度チェック: SystemMonitor は DuckDB の get_last_price_date を参照し、最新日からの差が _FRESHNESS_DAYS（デフォルト 3 日）以内かチェックします。

ディレクトリ構成（主要ファイル・説明）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings クラス、.env 自動読み込みロジック
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 監視ログ永続層（init / MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - alert_manager.py — LINE プッシュ通知ラッパ
    - kill_switch.py — kill.flag の作成/管理
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注管理（OrderManager）
    - reconciler.py — 起動時リコンシリエーション
    - その他（broker_factory, execution_engine, order_repository 等が存在）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数決定 / スケーリング
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）処理
    - regime_detector.py — レジーム判定（AI + MA200）
  - data/ (実行時に使用)
    - monitoring.db （デフォルト）
    - paper_trading.db（KABUSYS_ENV=paper_trading 用）
    - stop_requested.flag / kill.flag / execution.pid（フラグ/管理用）
- docs/（リポジトリにあれば設計ドキュメント等。ここで触れている PortfolioConstruction.md, StrategyModel.md 等は参照可能なドキュメント）

よくある質問（FAQ）
- Q: paper_trading と live の DB は分離されていますか？
  - A: はい。paper_trading は Settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 monitoring.db と分離されます。
- Q: 監視ループの間隔は変えられますか？
  - A: 環境変数 MONITOR_POLL_INTERVAL（秒）で変更できます。不正値や 0 以下は無視されデフォルト 60 秒にフォールバックします。
- Q: OpenAI の API キーをどこに置けばよいですか？
  - A: 環境変数 OPENAI_API_KEY、または score_news / score_regime の api_key 引数で渡してください。安全のため .env には機密情報を直接置かない運用も検討してください。

運用上の注意
- 実際の資金を扱う場合は本番環境（KABUSYS_ENV=live）での十分な検証、アクセス制御、ログ監査、バックアップ、レート制御、監視の強化を行ってください。
- OpenAI 呼び出しは外部依存で費用が発生します。コスト＆レート制限を必ず監視してください。
- process priority / cpu affinity の設定は権限に依存します。権限不足時は設定がスキップされますが、処理に致命的な影響はありません（ログ警告のみ）。

補足
- この README はコードベースの主要な挙動をまとめたものであり、個々の関数・クラスの詳細は該当ソース（src/kabusys/ 以下）をご参照ください。
- テストや追加のセットアップ（DuckDB に対する prices_daily / raw_financials のデータ投入等）は運用目的に応じて別途実行してください。

問題報告・貢献
- バグや改善提案があれば Issue を作成してください。プルリク歓迎です（変更時はユニットテストの追加をお願いします）。

以上。必要であればサンプル .env.example や起動スクリプトの具体的な実行例、要求パッケージの requirements.txt を作成して追記します。どの情報を優先して追加しますか？