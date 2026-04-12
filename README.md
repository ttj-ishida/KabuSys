KabuSys — 日本株自動売買システム（コードベース README）
概要、機能、セットアップ、使い方、ディレクトリ構成をまとめています。

プロジェクト概要
- KabuSys は日本株の自動売買およびそれに付随する監視／検証／リサーチ機能を持つ Python パッケージです。
- 実行エンジン（ExecutionEngine）・監視エンジン（MonitoringEngine）・ポートフォリオ構築・ファクター計算・AI（ニュース NLP / レジーム判定）などのモジュール群で構成されています。
- DuckDB を分析用データベース、SQLite を監視ログや注文履歴などの永続化に利用します。
- 設定は .env もしくは環境変数で管理され、自動ロード機能（プロジェクトルートに .env/.env.local があれば読み込む）を備えています。

主な機能一覧
- 実行（Execution）
  - ブローカー抽象化（Mock / 実ブローカー）を通して注文の発行・管理
  - リスク管理（最大ポジション比率、利用率、ドローダウン等）
  - 再起動時のリコンシリエーション（Reconciler）による自動復旧
- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス生存監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン / 保有銘柄数の閾値監視とログ記録
  - KillSwitch: 閾値超過時にフラグファイルを書いて ExecutionEngine を停止させる仕組み
  - AlertManager: LINE Push による通知（設定がある場合）
  - Streamlit ダッシュボード（監視用 UI）
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）
  - 株数決定（単元丸め・リスクベース配分・aggregate cap のスケーリング）
- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリ）
- AI
  - ニュース NLP（OpenAI を用いたニュースセンチメント → ai_scores に書き込み）
  - レジーム検出（ETF ma200乖離 + マクロニュースセンチメント合成）
- ツール
  - paper_trading の検証レポート生成スクリプト（paper_verification_report）

セットアップ手順（開発 / 実行環境）
1. 必要条件
   - Python 3.10 以上
   - OS: Linux / macOS / Windows（プラットフォーム固有の挙動あり）

2. 依存パッケージ（代表例）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit (ダッシュボード利用時)
   - （標準ライブラリ: sqlite3, logging, argparse 等）
   例:
     python -m pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があればそちらを使用してください）

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
       - paper_trading の場合、MockBrokerClient を使用し、paper 用 SQLite を使います
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定モード、デフォルト: instant）
     - PID_FILE_PATH / KILL_FLAG_PATH: PID / kill.flag のパス（デフォルト: data/execution.pid, data/kill.flag）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
     - MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、run_monitoring で有効、デフォルト: 60）

   - サンプル .env（最小例）
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO

4. データフォルダの準備
   - data ディレクトリを作成（SQLite / DuckDB のデフォルトファイルを配置）
     mkdir -p data

基本的な使い方（エントリポイント）
- 監視プロセスを起動（system monitor 単体）
  - デフォルトポーリング間隔 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き）
  - 起動:
    python -m kabusys.run_monitoring
  - 補足:
    - run_monitoring は Settings を読み、production の sqlite_path を使って monitoring DB を初期化します
    - プロセス優先度を "high" に設定しようとします（権限がなければ警告）

- 実行エンジン（ExecutionEngine）を起動
  - paper_trading 環境では MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離します
  - 起動（通常）:
    python -m kabusys.run_execution
  - paper_trading で起動:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート（ツール）
  - 使い方:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    --db PATH で SQLite ファイルを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- Streamlit ダッシュボード（監視可視化）
  - 起動例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only URI モードで SQLite を開きます（MonitoringEngine が DB を作成・更新している前提）

- AI 機能（ニュースセンチメント / レジーム検出）
  - OpenAI API キー（OPENAI_API_KEY）が必要
  - プログラム内から以下を呼び出すことで利用可能:
    - from kabusys.ai import score_news
      score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - これらは DuckDB 接続（duckdb.connect(...)）を受け取り、テーブル（raw_news / news_symbols / ai_scores / prices_daily 等）を参照・更新します

設定上の注意・挙動
- Settings（kabusys.config.Settings）:
  - .env 自動ロードはデフォルトで ON。プロジェクトルートの .env / .env.local を読み込みます。
  - KABUSYS_ENV は development / paper_trading / live のいずれかである必要があります。
  - paper_trading はデータベースを分離する設計（PAPER_TRADING_SQLITE_PATH）。
  - PAPER_FILL_MODE の有効値: instant / partial / never / reject（paper_trading 用、検証目的での挙動制御）
- Monitoring DB の初期化:
  - init_monitoring_db(sqlite_conn) により必要なテーブル（system_status / trade_logs / positions / risk_logs / dashboard） とインデックス を冪等に作成します。
- プロセス優先度設定:
  - set_process_priority("high"|"normal"|"low") で psutil を通じて優先度を設定し、Windows / POSIX を考慮します。権限がない場合は警告でスキップします。
- Kill Switch:
  - KillSwitch は reason をデータフォルダの kill.flag に書き込み、ExecutionEngine 側がそれを検出して停止する運用を想定しています。
  - ExecutionEngine 側は起動時に kill.flag のクリア設定（Settings.kill_flag_clear_on_start）を確認します。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定管理
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite 永続化層（監視用）
    - system_monitor.py       — システム状態 / データ鮮度監視
    - trade_monitor.py        — 注文滞留 / 約定異常監視
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — フラグファイルによる停止信号
    - alert_manager.py        — LINE Push 通知
    - monitoring_engine.py    — 各 Monitor を束ねるランナー
    - streamlit_dashboard.py  — Streamlit 管理ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - ... （ブローカー抽象、order_repository など）
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
  - data/ （実行時に生成される想定）
    - kabusys.duckdb (default)
    - monitoring.db (default)
    - paper_trading.db (paper_trading 用)

開発・運用時のヒント
- ログレベルは LOG_LEVEL 環境変数で設定可能（INFO デフォルト）。
- MonitoringEngine／ExecutionEngine を systemd や supervisor などで管理すると運用が楽になります（PID ファイルを利用）。
- paper_trading モードは本番 DB と切り離して検証できるため、戦略検証・回帰テストに便利です。
- DuckDB / DuckDBPyConnection を用いている箇所は分析処理（ファクター算出、AI 前処理など）向けです。テーブル設計（prices_daily / raw_financials / raw_news 等）が前提になります。

サンプル起動コマンドまとめ
- 監視起動:
  python -m kabusys.run_monitoring
- 実行エンジン起動:
  python -m kabusys.run_execution
- paper_trading 実行:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
- 本 README はコードベース（src/kabusys 配下）を参照してまとめています。実運用前に .env の必須項目（API トークン類）やデータベースの初期化、権限（プロセス優先度設定等）を確認してください。
- 追加のスクリプトや CI／デプロイ手順があればそれに従ってください。

必要であれば、README に含めるサンプル .env のテンプレートや systemd ユニットファイルの例、運用手順（バックアップ、DB マイグレーション）も作成します。どれを追加しますか？