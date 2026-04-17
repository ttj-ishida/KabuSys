# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。

この README は、リポジトリ内のモジュール群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI ニュース解析など）を使い始めるための概要、セットアップ、実行方法、ディレクトリ構成をまとめたものです。

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- 環境変数（主な設定項目）
- セットアップ手順
- 使い方（主要コマンド・スクリプト）
- 停止・制御（フラグファイル等）
- ディレクトリ構成（主要ファイル一覧）
- 補足・運用上の注意

---

プロジェクト概要
- KabuSys は日本株自動売買向けのソフトウェア基盤です。
- コンポーネント例：
  - ExecutionEngine: ブローカーへの発注、オーダー管理、リスク管理、リコンシリエーション
  - MonitoringEngine: システム監視、注文監視、リスク検知、アラート送信
  - Portfolio construction: 候補選定、重み付け、ポジションサイズ計算、セクター制限
  - Research: ファクター計算、将来リターン/IC 計算
  - AI モジュール: ニュースセンチメント解析（OpenAI）、市場レジーム判定
  - ツール: Paper Trading 検証レポート生成、Streamlit ダッシュボード等

機能一覧
- 実環境 / Paper Trading 切替（KABUSYS_ENV）
  - paper_trading 時は MockBroker と専用 DB（data/paper_trading.db）を使用し、本番 DB から分離
- ExecutionEngine の起動・停止管理、PID 管理、リコンシリエーション
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）
  - CPU / メモリ / ディスク使用率のログ
  - Execution プロセス生存確認（PID ファイル）
  - データ鮮度の監視（DuckDB の prices_daily）
  - 滞留注文検出、約定価格異常検出、ドローダウン・ポジション上限検出
  - 継続的なログは SQLite（monitoring.db）に永続化
- AlertManager による LINE プッシュ通知（クールダウン管理）
- KillSwitch による停止（data/kill.flag 書込み）
- AI ニュース NLP：OpenAI（gpt-4o-mini）でニュースを銘柄単位にスコア化し ai_scores に保存
- RegimeDetector：ETF（1321）の MA200 とマクロニュースを組合せてレジーム判定
- ポートフォリオ構築ユーティリティ（候補選定、等重・スコア重み、リスクベース発注数計算）
- ツール：
  - paper_verification_report: Paper Trading DB をスキャンして検証レポートを生成
  - streamlit_dashboard: 監視ダッシュボード（streamlit）

前提・依存関係（抜粋）
- Python 3.9+（型アノテーションに Path | None などを使用しているため、実行環境の Python バージョンに注意）
- 主なライブラリ:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード用)
- 依存は環境に合わせ requirements.txt を用意して pip install してください（本リポジトリに requirements.txt がない場合は上のパッケージ群を個別にインストール）。

環境変数（主なもの）
- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）。正の整数で指定（0/負は無効でデフォルトにフォールバック）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject）、デフォルト "instant"
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグファイル（デフォルト: data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動ロードを無効化（テスト用）

.env 自動読み込み
- 起動時にプロジェクトルートが .git または pyproject.toml により自動検出される場合、次の順で読み込みを行う:
  1. OS 環境変数（既に設定されているものは保護）
  2. .env （既存の OS 環境変数を上書きしない）
  3. .env.local（.env を上書き可能。ただし OS 環境変数は保護）
- 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

セットアップ手順（ローカルで動かす最小手順）
1. Python を準備（推奨: 仮想環境を作る）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （任意）その他テストや開発用パッケージを追加
3. データディレクトリを作成
   - mkdir -p data
4. 環境変数を設定（.env をプロジェクトルートに作成しても良い）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - AI 機能を使う場合: OPENAI_API_KEY
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
5. データベース初期化
   - 監視用 SQLite と DuckDB は実行スクリプト内で必要テーブルを作成する処理（init_monitoring_db / 各モジュール）を呼ぶため、初回はそのまま起動してテーブル作成させるのが簡単です。
   - DuckDB に prices_daily 等のデータをロードするには別途パイプライン（kabusys.data.pipeline 等）を準備してください（本 README では詳述しません）。

使い方（主要スクリプト）
- 監視（SystemMonitor 単独起動）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（秒、デフォルト 60）。
    - 監視は Settings.sqlite_path（＝data/monitoring.db デフォルト）に接続し、テーブルを作成してログを蓄積します。
    - 停止: data/stop_requested.flag を作成するとループが検知して停止します（または Ctrl+C）。
- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、MockBrokerClient により完全分離された Paper Trading 動作をします。
    - 実行中、execution.pid（デフォルト data/execution.pid）が書かれます。PID が stale（プロセス不存在）だと監視が検出して修正します。
    - 停止: data/stop_requested.flag を作成するとエンジンに停止シグナルが送られます（run_execution のループで検知）。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD
    --to YYYY-MM-DD
    --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - 出力: 標準出力に検証サマリ（稼働率、注文成功率、レイテンシ等）
- Streamlit ダッシュボード（監視データを可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開き、Positions / Orders / System / Overview を表示
- AI スコアリング / レジーム判定（プログラム API）
  - kabusys.ai.score_news（news_nlp.score_news）: DuckDB 接続と target_date を渡してスコアを ai_scores テーブルへ書き込む
  - kabusys.ai.regime_detector.score_regime: market_regime テーブルへ日次判定を記録
  - どちらも OPENAI_API_KEY（引数または環境変数）が必要

停止・制御（フラグファイル等）
- data/stop_requested.flag
  - run_monitoring.py / run_execution.py はこのファイルの存在を監視して安全に終了します。運用側からプロセスを停止したい場合に使います。
- data/kill.flag
  - KillSwitch がリスク閾値超過時に書き込むフラグ。ExecutionEngine に停止シグナルを与えるために使用されます（ExecutionEngine 起動時に clear する設定がある）。
- data/execution.pid
  - 実行エンジンの PID を格納。SystemMonitor はこれを参照してプロセス生存確認を行う。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py (バージョン等)
  - config.py (Settings クラス、.env 自動ロード)
  - run_monitoring.py (SystemMonitor ポーリングループ起動スクリプト)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - ai/
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
  - monitoring/
    - monitoring_db.py (監視用 SQLite スキーマ + DB ラッパ)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py (各 Monitor を束ねる)
    - alert_manager.py (LINE Push)
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - order_repository.py (DB 層、実装あり)
    - order_record.py
    - execution_engine.py (Engine 本体: 起動/セッション管理 等)
    - broker_factory.py / broker_api.py (ブローカー抽象)
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
    - process_priority.py (プロセス優先度 / CPU affinity ユーティリティ)
  - data/ (ランタイム生成される可能性のあるディレクトリ、例: monitoring.db, paper_trading.db, stop_requested.flag, execution.pid, kill.flag)
  - その他（data pipeline / data.stats など、リポジトリ内の他モジュールに依存）

補足・運用上の注意
- Paper Trading と本番 DB は明確に分離する設計です。KABUSYS_ENV=paper_trading を使わない限り、Monitoring は本番 sqlite_path（monitoring.db）を利用します。
- .env の自動読み込みは便利ですが、CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して外部影響を避けてください。
- OpenAI を使う機能は API レート制限や料金が発生します。本番運用前に十分な検証・キー管理を行ってください。
- process_priority.set_process_priority() は権限により失敗することがあり、その場合は警告ログのみ出て処理続行します。
- DuckDB / SQLite への書き込みは各モジュールが行うため、バックアップと DB サイズ管理を運用ポリシーとして持つと良いです。
- ログ出力は logging 基準で行われます。LOG_LEVEL を適切に設定してください。

---

追加情報や実行時の具体的な疑問（エラー、設定の細かい説明、実装補足など）があれば、その内容を教えてください。必要に応じて実行例や .env のテンプレート、systemd/サービス化のサンプルなども作成します。