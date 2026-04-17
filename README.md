# KabuSys — README

簡潔な日本語ドキュメントです。KabuSys は日本株向けの自動売買・リサーチ・監視ツール群を含むコードベースです。本 README はこのリポジトリの主要コンポーネント、起動方法、設定方法、ディレクトリ構成などをまとめます。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 起動・使い方（主要スクリプト／ツール）
- 環境変数（主要なもの）
- 注意点 / 運用メモ
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買（Execution）、監視（Monitoring）、ポートフォリオ構築（Portfolio）、リサーチ（Research）、AI 支援（ニュース NLP / レジーム判定）などの機能を持つコード群です。
- SQLite / DuckDB を使ったローカル DB 層と、外部 API（kabuステーション相当のブローカー API、J-Quants、OpenAI 等）を組み合わせて運用します。
- Paper Trading モードを用意しており、本番 DB と分離して検証できます。

機能一覧
- Execution
  - ExecutionEngine を起動してシグナル→発注→注文管理を行う（reconciler による自動復旧機能あり）
  - OrderManager / OrderRepository による状態管理
  - Paper trading モード（MockBrokerClient, data/paper_trading.db）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存在確認、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とアラート記録
  - KillSwitch: 条件発動で ExecutionEngine 停止フラグを書き込み
  - AlertManager: LINE Push による通知（任意）
  - Streamlit ダッシュボードで監視情報を可視化
- Portfolio
  - 候補選定、等配分・スコア加重、セクターキャップ、ポジションサイズ計算（株数決定）
- Research
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索 / IC 計算（Spearman）
  - DuckDB を使った高速な集計処理
- AI
  - news_nlp: raw_news を OpenAI でスコアリングして ai_scores に保存
  - regime_detector: MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定し DB に書き込む
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - 各種ユーティリティ（プロセス優先度設定、DB 初期化等）

セットアップ手順（ローカル開発 / 実行用）
1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS)
   - .venv\Scripts\activate (Windows)

3. 依存ライブラリをインストール
   - requirements.txt がない場合は少なくとも次をインストールしてください:
     - duckdb, psutil, requests, streamlit, openai
   - 例:
     - pip install duckdb psutil requests streamlit openai

4. データディレクトリ作成
   - data ディレクトリを作成（DB・フラグファイル等を格納）
     - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local で上書き可能）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須値や推奨項目は以下「環境変数」セクションを参照。

6. DB 初期化
   - 多くのスクリプトは起動時に init_monitoring_db() を呼び DB スキーマを作成します。手動での初期化は不要ですが、data/*.db が存在しない場合は起動時に作成されます。

主要な起動・使い方
- 実行エンジン（Execution）
  - 動作: ExecutionEngine を起動して取引ループを実行します。
  - 起動例:
    - python -m kabusys.run_execution
  - 動作モード:
    - KABUSYS_ENV=paper_trading の場合 → MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します。
    - それ以外（development / live）では sqlite_path（デフォルト: data/monitoring.db）等を使用します。
  - 停止制御:
    - data/stop_requested.flag を作ると早期停止処理が行われます。
    - 実行中は data/execution.pid が作成されます。

- 監視ループ（Monitoring）
  - 動作: SystemMonitor を定期ポーリングして監視ログを記録します。
  - 起動例:
    - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を参照します（KABUSYS_ENV に依存せず本番 DB を使用する仕様に注意）。

- Streamlit ダッシュボード
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only URI で DB を開くため、MonitoringEngine を先に動かして DB を作成しておく必要があります。

- Paper Trading 検証レポート
  - 起動例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（プログラムからの利用例）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を受け取り DB に書き込みます。
  - 例（Python REPL 内）:
    - import duckdb
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, date(2026,4,10), api_key="sk-...")
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を使用。

環境変数（主要）
- 本質的なもの・説明（デフォルト値はコード内で定義）
  - KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト "development"。
  - SQLITE_PATH: 監視用 SQLite（monitoring）DB のパス。デフォルト data/monitoring.db
  - DUCKDB_PATH: DuckDB ファイルのパス。デフォルト data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（例: data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading 時の約定モード（instant | partial | never | reject）。デフォルト "instant"
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須とされる箇所あり）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector で使用）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）で通知する場合に設定
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視・運用に関する設定は Settings クラスから参照可能

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある .env を自動で読み込みます。
  - .env.local があれば .env の設定を上書きします。
  - OS 環境変数は保護され、.env の値で上書きされません（ただし .env.local は override=True で上書き可能）。
  - 自動読み込みを停止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

注意点 / 運用メモ
- Paper Trading は本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- Monitoring の起動スクリプトは Settings.env に依らず sqlite_path（本番監視 DB）を使用します。ローカル検証時はこの点に注意してください。
- stop_requested.flag（data/stop_requested.flag）および data/stop_requested.flag によるループ終了や data/kill.flag による Execution 停止指示など、フラグファイルベースの停止メカニズムがあります。運用時はこれらのファイルの取り扱いに注意してください。
- OpenAI を使う処理はネットワークエラーや 429 に対して再試行ロジックを持ちますが、API キー未設定時は例外を投げます。運用時は API キーの管理に注意してください。
- streamlit ダッシュボードは DB を読み取り専用で開けるように実行例を示しています。監視 DB が未作成の場合は、MonitoringEngine を最初に起動してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings 管理（.env 自動読み込み等）
  - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite スキーマ / 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (他の execution 関連コンポーネント...)
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
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート用 CLI
    - __init__.py
  - data/                            — 実行時に使用する DB / PID / flag を格納する想定ディレクトリ（プロジェクトルートに配置）

（注）リポジトリ内の細部実装によりさらに多数のモジュールがあります。上記は主要なエントリポイントと機能別モジュールの要約です。

追加情報・トラブルシューティング
- DB マイグレーション: monitoring_db.init_monitoring_db() は冪等でテーブル作成・既存カラムのマイグレーション（例: latency_ms, peak_value）を試みます。
- 実行時に PID ファイル / フラグファイルに関する警告や stale PID 検出が出ることがあります。stale PID は SystemMonitor により検出・削除され、risk_logs に記録されます。
- LINE アラートや OpenAI 呼び出しに失敗した場合はログにエラー/警告が残り、可能であればフェイルセーフ（処理を続行）します。

最後に
- 本 README はソースコード（src/kabusys 以下）の docstring と実装に基づいて作成しています。詳細な API 仕様や追加使い方はソースコード内の docstring を参照してください。
- 追加のドキュメント（.env.example、運用手順書、PortfolioConstruction.md 等）がリポジトリにある場合はそちらも参照することを推奨します。

必要があれば、README に含めるコマンド例の追加（systemd ユニット例、Dockerfile、CI 設定）や、.env.example のサンプルを作成します。どれを追加しますか？